#!/usr/bin/env python3
"""Calculate approximate DORA metrics from GitHub Actions runs on main.

Requires GitHub CLI (`gh`) authenticated for the repository.
The script is intentionally manual/local; it does not create a scheduled workflow.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Розрахувати DORA-метрики за історією CI на main.")
    parser.add_argument("--since", required=True, help="Початкова дата YYYY-MM-DD (включно)")
    parser.add_argument("--until", required=True, help="Кінцева дата YYYY-MM-DD (включно)")
    parser.add_argument(
        "--repo",
        help="owner/repository; за замовчуванням визначається через `gh repo view`",
    )
    parser.add_argument(
        "--output",
        default="docs/ci-cd/dora-automated.md",
        help="Шлях до Markdown-звіту (типово docs/ci-cd/dora-automated.md)",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Некоректна дата {value!r}; очікується YYYY-MM-DD"
        ) from exc


def gh_json(endpoint: str, *, paginate: bool = False) -> Any:
    command = ["gh", "api"]
    if paginate:
        command += ["--paginate", "--slurp"]
    command.append(endpoint)
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Не знайдено GitHub CLI `gh`. Встанови його та повтори запуск.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(f"Помилка `gh api {endpoint}`: {message}") from exc
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GitHub API повернув не JSON для {endpoint}") from exc


def flatten_pages(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        payload = [payload]

    flattened: list[dict[str, Any]] = []
    for page in payload:
        if isinstance(page, list):
            flattened.extend(item for item in page if isinstance(item, dict))
        elif isinstance(page, dict):
            for key in ("workflow_runs", "jobs"):
                items = page.get(key)
                if isinstance(items, list):
                    flattened.extend(item for item in items if isinstance(item, dict))
                    break
            else:
                flattened.append(page)

    return flattened


def iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minutes_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() / 60)


def fmt_minutes(value: float | None) -> str:
    if value is None:
        return "н/д"
    total = round(value)
    days, remainder = divmod(total, 1440)
    hours, mins = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} д")
    if hours:
        parts.append(f"{hours} год")
    if mins or not parts:
        parts.append(f"{mins} хв")
    return " ".join(parts)


def stats(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.mean(values), statistics.median(values)


def stat_text(values: list[float]) -> str:
    mean, median = stats(values)
    if mean is None or median is None:
        return "н/д"
    return f"середнє {fmt_minutes(mean)}; медіана {fmt_minutes(median)}"


def get_jobs(
    repo: str, run_id: int, cache: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    if run_id not in cache:
        payload = gh_json(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100", paginate=True)
        cache[run_id] = flatten_pages(payload)
    return cache[run_id]


def run_timing(repo: str, run: dict[str, Any], jobs_cache: dict[int, list[dict[str, Any]]]):
    jobs = get_jobs(repo, run["id"], jobs_cache)
    starts = [iso(job.get("started_at")) for job in jobs if iso(job.get("started_at"))]
    ends = [iso(job.get("completed_at")) for job in jobs if iso(job.get("completed_at"))]
    created = iso(run.get("created_at"))
    if not created or not starts or not ends:
        completed = max(ends) if ends else iso(run.get("updated_at"))
        return None, None, completed, "немає повних часових міток jobs"
    first_start, last_end = min(starts), max(ends)
    return (
        minutes_between(created, first_start),
        minutes_between(first_start, last_end),
        last_end,
        None,
    )


def associated_pr(repo: str, sha: str, cache: dict[str, dict[str, Any] | None]):
    if sha not in cache:
        prs = gh_json(f"repos/{repo}/commits/{sha}/pulls")
        if not prs:
            cache[sha] = None
        else:
            # Prefer merged PR whose merge commit matches the workflow's pushed SHA.
            matching = [pr for pr in prs if pr.get("merge_commit_sha") == sha]
            cache[sha] = (matching or prs)[0]
    return cache[sha]


def first_pr_commit_date(repo: str, pr_number: int, cache: dict[int, datetime | None]):
    if pr_number not in cache:
        commits = flatten_pages(
            gh_json(f"repos/{repo}/pulls/{pr_number}/commits?per_page=100", paginate=True)
        )
        authored = [
            iso(commit.get("commit", {}).get("author", {}).get("date")) for commit in commits
        ]
        authored = [value for value in authored if value is not None]
        cache[pr_number] = min(authored) if authored else None
    return cache[pr_number]


def main() -> int:
    args = parse_args()
    since = parse_date(args.since)
    until = parse_date(args.until)
    if until < since:
        print("--until не може бути раніше за --since", file=sys.stderr)
        return 2

    repo = args.repo
    if not repo:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        repo = result.stdout.strip()
    if "/" not in repo:
        print("Репозиторій має бути у форматі owner/repository", file=sys.stderr)
        return 2

    start_utc = datetime.combine(since, time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(until + timedelta(days=1), time.min, tzinfo=timezone.utc)
    created_filter = f"{since.isoformat()}..{until.isoformat()}"
    endpoint = (
        f"repos/{repo}/actions/workflows/360345078/runs"
        f"?branch=main&event=push&per_page=100&created={created_filter}"
    )
    response = gh_json(endpoint, paginate=True)
    runs = flatten_pages(response)
    runs = [
        run
        for run in runs
        if run.get("head_branch") == "main"
        and run.get("event") == "push"
        and run.get("status") == "completed"
    ]
    runs.sort(
        key=lambda run: iso(run.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
    )

    if not runs:
        print("За цей період завершених запусків CI на main не знайдено.", file=sys.stderr)
        return 1

    jobs_cache: dict[int, list[dict[str, Any]]] = {}
    timings = {}
    warnings: list[str] = []
    for run in runs:
        queue, execution, completed, warning = run_timing(repo, run, jobs_cache)
        timings[run["id"]] = {"queue": queue, "execution": execution, "completed": completed}
        if warning:
            warnings.append(
                f"Run {run['id']}: {warning}; "
                "для часу завершення використано updated_at, якщо доступний."
            )

    green = [run for run in runs if run.get("conclusion") == "success"]
    red = [run for run in runs if run.get("conclusion") == "failure"]
    weeks = (end_exclusive - start_utc).total_seconds() / (7 * 86400)
    deployment_frequency = len(green) / weeks if weeks else 0
    change_failure_rate = (len(red) / len(runs) * 100) if runs else 0

    recovery_values: list[float] = []
    for failed in red:
        failed_end = timings[failed["id"]]["completed"]
        if not failed_end:
            continue
        next_green = next(
            (
                run
                for run in green
                if timings[run["id"]]["completed"] and timings[run["id"]]["completed"] > failed_end
            ),
            None,
        )
        if next_green:
            recovery_values.append(
                minutes_between(failed_end, timings[next_green["id"]]["completed"])
            )

    pr_cache: dict[str, dict[str, Any] | None] = {}
    commit_cache: dict[int, datetime | None] = {}
    lead_times: list[float] = []
    unmapped_pr = 0
    for index, run in enumerate(runs):
        pr = associated_pr(repo, run.get("head_sha", ""), pr_cache)
        if not pr:
            unmapped_pr += 1
            continue
        first_commit = first_pr_commit_date(repo, pr["number"], commit_cache)
        if not first_commit:
            unmapped_pr += 1
            continue
        target_run = run
        if run.get("conclusion") != "success":
            run_end = timings[run["id"]]["completed"]
            target_run = next(
                (
                    candidate
                    for candidate in runs[index + 1 :]
                    if candidate.get("conclusion") == "success"
                    and timings[candidate["id"]]["completed"]
                    and run_end
                    and timings[candidate["id"]]["completed"] > run_end
                ),
                None,
            )
        completed = timings[target_run["id"]]["completed"] if target_run else None
        if completed and completed >= first_commit:
            lead_times.append(minutes_between(first_commit, completed))

    queues = [
        timings[run["id"]]["queue"] for run in runs if timings[run["id"]]["queue"] is not None
    ]
    executions = [
        timings[run["id"]]["execution"]
        for run in runs
        if timings[run["id"]]["execution"] is not None
    ]
    recovery_mean, recovery_median = stats(recovery_values)
    lead_mean, lead_median = stats(lead_times)
    queue_mean, queue_median = stats(queues)
    execution_mean, execution_median = stats(executions)

    report = [
        "# Автоматичний розрахунок DORA за GitHub Actions",
        "",
        f"**Репозиторій:** `{repo}`  ",
        (f"**Період:** {since.isoformat()} – {until.isoformat()} " "(UTC-фільтр GitHub API)  "),
        "**Workflow:** `CI`, подія `push`, гілка `main`  ",
        (f"**Завершені запуски:** {len(runs)}; " f"зелені — {len(green)}; червоні — {len(red)}"),
        "",
        "## Чотири метрики",
        "",
        "| Метрика | Розрахунок | Результат |",
        "|---|---|---:|",
        (
            f"| Частота розгортань (наближення) "
            f"| зелені запуски / тривалість періоду "
            f"| {deployment_frequency:.1f} на тиждень |"
        ),
        (
            f"| Час виконання змін "
            f"| перший authored commit PR → перший зелений main "
            f"(для червоного — наступний зелений) "
            f"| {stat_text(lead_times)}; вибірка {len(lead_times)} |"
        ),
        (
            f"| Частота збоїв змін "
            f"| червоні / усі завершені запуски × 100 % "
            f"| {change_failure_rate:.1f} % |"
        ),
        (
            f"| Час відновлення "
            f"| завершення червоного → завершення наступного зеленого main "
            f"| {stat_text(recovery_values)}; "
            f"інцидентів {len(recovery_values)} |"
        ),
        "",
        "## Черга й виконання CI окремо",
        "",
        "| Частина | Визначення | Результат |",
        "|---|---|---:|",
        (
            f"| Черга до першого job "
            f"| `created_at` запуску → `started_at` першого job "
            f"| {stat_text(queues)}; запусків {len(queues)} |"
        ),
        (
            f"| Виконання workflow "
            f"| старт першого job → завершення останнього job (wall-clock) "
            f"| {stat_text(executions)}; запусків {len(executions)} |"
        ),
        "",
        "## Методика та можливі розбіжності з ручним підрахунком",
        "",
        (
            "- Скрипт використовує часові мітки GitHub REST API в UTC; "
            "у `metrics-raw.md` час показано за Києвом. "
            "Перехід UTC ↔ EET/EEST може змінювати відображення дати/години, "
            "але не тривалість."
        ),
        (
            "- Для часу завершення береться максимальний `completed_at` "
            "серед jobs, а не `updated_at` самого workflow run."
        ),
        (
            "- Черга — від створення запуску до старту першого job; "
            "виконання — від старту першого до завершення останнього job. "
            "Це wall-clock інтервали, а не сума тривалостей усіх jobs."
        ),
        (
            "- Час виконання зміни прив'язується до PR, асоційованого з SHA "
            "запуску; початок — найраніший `commit.author.date` у PR. "
            "Це може відрізнятися від ручного зіставлення merge-комітів "
            "або `authoredDate` у зведеній таблиці."
        ),
        (
            "- Для червоного запуску час виконання зміни завершується "
            "наступним зеленим запуском на `main`; час відновлення "
            "рахується окремо від завершення червоного до завершення "
            "наступного зеленого."
        ),
        (
            "- Якщо API не повернув пов'язаний PR або коміти PR, "
            "такий запуск не входить у вибірку часу виконання зміни; "
            "кількість пропусків наведена нижче."
        ),
        (
            "- Частота розгортань є наближенням: рахується зелений CI "
            "на `main`, а не незалежно підтверджена подія деплою Render/Pages."
        ),
        "",
        f"**Не зіставлено з PR для lead time:** {unmapped_pr}.",
    ]

    if warnings:
        report += ["", "## Попередження", ""]
        report += [f"- {warning}" for warning in warnings]

    report += [
        "",
        "---",
        (
            f"*Згенеровано локально "
            f"{datetime.now().astimezone().isoformat(timespec='minutes')} "
            "командою `scripts/dora_metrics.py`; "
            "повторний запуск перезаписує цей файл.*"
        ),
        "",
    ]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(report), encoding="utf-8")
    print(f"Звіт збережено: {output}")
    print(
        f"Запуски: {len(runs)} (green {len(green)}, red {len(red)}); "
        f"lead time: {len(lead_times)}; recovery: {len(recovery_values)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Помилка: {error}", file=sys.stderr)
        raise SystemExit(1)
