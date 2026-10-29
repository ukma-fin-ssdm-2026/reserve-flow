"""Перевірка простежуваності «вимога ↔ тест» (Лаб 7, бонус, #326).

Звіряє ID вимог з docs/requirements/rtm.md з мітками тестів у tests/:
  * @pytest.mark.req("FR-007", ...) — тест перевіряє ці вимоги;
  * @pytest.mark.no_req("причина") — тест свідомо без вимоги (з поясненням);
  * мітку можна поставити на функцію, клас або весь модуль (pytestmark = ...).

Збірка падає (код виходу 1), якщо:
  * функціональна / нефункціональна вимога з rtm.md не має жодного тесту
    (крім вимог зі списку [tool.traceability.out_of_scope] у pyproject.toml);
  * тест не посилається на жодну вимогу і не має no_req;
  * у мітці є ID, якого немає в rtm.md (описка).

Запуск: python scripts/check_traceability.py
Тести не імпортуються: файли розбираються як текст (ast), тож скрипту не потрібні
залежності проєкту і БД.
"""

import ast
import os
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RTM = ROOT / "docs" / "requirements" / "rtm.md"
TESTS = ROOT / "tests"

# Рядок матриці: | FR-007 | Функціональна | ...
RTM_ROW = re.compile(r"^\|\s*((?:US|UC|FR|PERF|SEC|REL)-\d{3})\s*\|\s*([^|]+?)\s*\|")
# Тип вимоги, для якої обов'язковий хоча б один тест
REQUIRED_TYPES = {"Функціональна", "Нефункціональна"}


def read_requirements() -> tuple[set[str], set[str]]:
    """Повертає (усі відомі ID, ID, що потребують тесту)."""
    known, required = set(), set()
    for line in RTM.read_text(encoding="utf-8").splitlines():
        match = RTM_ROW.match(line)
        if match:
            req_id, req_type = match.groups()
            known.add(req_id)
            if req_type in REQUIRED_TYPES:
                required.add(req_id)
    return known, required


def read_out_of_scope() -> dict[str, str]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return config.get("tool", {}).get("traceability", {}).get("out_of_scope", {})


def _marks(node: ast.expr) -> list[ast.Call]:
    """Виклики pytest.mark.req / no_req у декораторі або в pytestmark."""
    items = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    found = []
    for item in items:
        if (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr in ("req", "no_req")
            and isinstance(item.func.value, ast.Attribute)
            and item.func.value.attr == "mark"
        ):
            found.append(item)
    return found


def _collect(calls: list[ast.Call]) -> tuple[set[str], bool]:
    ids, exempt = set(), False
    for call in calls:
        if call.func.attr == "no_req":
            exempt = True
        else:
            ids |= {a.value for a in call.args if isinstance(a, ast.Constant)}
    return ids, exempt


def scan_tests() -> list[tuple[str, set[str], bool]]:
    """Список (тест, ID вимог, свідомо без вимоги) для кожної тестової функції."""
    result = []
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(ROOT).as_posix()
        module_calls = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
            ):
                module_calls += _marks(node.value)

        def visit(body, inherited, prefix):
            for node in body:
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    calls = [c for d in node.decorator_list for c in _marks(d)]
                    visit(node.body, inherited + calls, f"{prefix}{node.name}::")
                elif isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and node.name.startswith("test_"):
                    calls = inherited + [c for d in node.decorator_list for c in _marks(d)]
                    ids, exempt = _collect(calls)
                    result.append((f"{rel}::{prefix}{node.name}", ids, exempt))

        visit(tree.body, module_calls, "")
    return result


def main() -> int:
    known, required = read_requirements()
    out_of_scope = read_out_of_scope()
    tests = scan_tests()

    errors = []
    tests_by_req = defaultdict(list)
    for name, ids, exempt in tests:
        for req_id in sorted(ids - known):
            errors.append(f"{name}: невідомий ID вимоги {req_id} (немає в rtm.md)")
        for req_id in ids & known:
            tests_by_req[req_id].append(name)
        if not ids and not exempt:
            errors.append(f"{name}: тест не посилається на жодну вимогу (додайте pytest.mark.req)")

    for req_id in sorted(set(out_of_scope) - known):
        errors.append(f"pyproject.toml: {req_id} у out_of_scope, але його немає в rtm.md")
    uncovered = sorted(required - set(tests_by_req) - set(out_of_scope))
    for req_id in uncovered:
        errors.append(f"{req_id}: вимога без жодного тесту")
    warnings = [
        f"{req_id}: позначено поза обсягом, але тести вже є — приберіть з out_of_scope"
        for req_id in sorted(set(out_of_scope) & set(tests_by_req))
    ]

    exempt_count = sum(1 for _, ids, exempt in tests if exempt and not ids)
    lines = [
        "## Простежуваність «вимога ↔ тест»",
        "",
        f"Тестових функцій: {len(tests)} · без вимоги з поясненням (`no_req`): {exempt_count} · "
        f"вимог з тестами: {len(set(tests_by_req) & required)} з {len(required)} · "
        f"поза обсягом: {len(out_of_scope)}",
        "",
        "| Вимога | Тестів | Стан |",
        "|---|---|---|",
    ]
    for req_id in sorted(required, key=lambda r: (r.split("-")[0], int(r.split("-")[1]))):
        count = len(tests_by_req.get(req_id, []))
        if req_id in out_of_scope:
            state = f"поза обсягом: {out_of_scope[req_id]}"
        else:
            state = "✅" if count else "❌ немає тесту"
        lines.append(f"| {req_id} | {count} | {state} |")
    if errors:
        lines += ["", f"### ❌ Помилок: {len(errors)}", ""] + [f"- {e}" for e in errors]
    if warnings:
        lines += ["", "### ⚠️ Попередження", ""] + [f"- {w}" for w in warnings]

    report = "\n".join(lines) + "\n"
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    for error in errors:
        print(f"::error::{error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
