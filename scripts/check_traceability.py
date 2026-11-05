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
RTM_ROW = re.compile(r"^\|\s*((?:US|UC|FR|PERF|SEC|REL)-\d{3})\s*\|([^|]*)\|")
# Тип вимоги, для якої обов'язковий хоча б один тест
REQUIRED_TYPES = {"Функціональна", "Нефункціональна"}


def read_requirements() -> tuple[set[str], set[str]]:
    """Повертає (усі відомі ID, ID, що потребують тесту)."""
    known, required = set(), set()
    for line in RTM.read_text(encoding="utf-8").splitlines():
        match = RTM_ROW.match(line)
        if match:
            req_id, req_type = match.group(1), match.group(2).strip()
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


def _decorator_marks(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """Мітки req / no_req з декораторів класу або функції."""
    return [call for decorator in node.decorator_list for call in _marks(decorator)]


def _is_pytestmark(node: ast.stmt) -> bool:
    return isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets
    )


def _module_marks(tree: ast.Module) -> list[ast.Call]:
    """Мітки всього модуля: pytestmark = pytest.mark.req(...) або список міток."""
    return [call for node in tree.body if _is_pytestmark(node) for call in _marks(node.value)]


def _is_test_class(node: ast.stmt) -> bool:
    return isinstance(node, ast.ClassDef) and node.name.startswith("Test")


def _is_test_function(node: ast.stmt) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
        "test_"
    )


def _visit(body: list[ast.stmt], inherited: list[ast.Call], prefix: str, result: list) -> None:
    """Збирає тести з модуля або класу; мітки модуля й класів успадковуються."""
    for node in body:
        if _is_test_class(node):
            marks = inherited + _decorator_marks(node)
            _visit(node.body, marks, f"{prefix}{node.name}::", result)
        elif _is_test_function(node):
            ids, exempt = _collect(inherited + _decorator_marks(node))
            result.append((f"{prefix}{node.name}", ids, exempt))


def scan_tests() -> list[tuple[str, set[str], bool]]:
    """Список (тест, ID вимог, свідомо без вимоги) для кожної тестової функції."""
    result = []
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(ROOT).as_posix()
        _visit(tree.body, _module_marks(tree), f"{rel}::", result)
    return result


def _check_tests(
    tests: list[tuple[str, set[str], bool]], known: set[str]
) -> tuple[list[str], dict[str, list[str]]]:
    """Помилки в мітках тестів і список тестів для кожної відомої вимоги."""
    errors = []
    tests_by_req = defaultdict(list)
    for name, ids, exempt in tests:
        errors += [f"{name}: невідомий ID вимоги {r} (немає в rtm.md)" for r in sorted(ids - known)]
        for req_id in ids & known:
            tests_by_req[req_id].append(name)
        if not ids and not exempt:
            errors.append(f"{name}: тест не посилається на жодну вимогу (додайте pytest.mark.req)")
    return errors, tests_by_req


def _check_coverage(
    known: set[str],
    required: set[str],
    out_of_scope: dict[str, str],
    tests_by_req: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """Помилки (ID поза обсягом без рядка в rtm.md, вимога без тестів) і попередження."""
    errors = [
        f"pyproject.toml: {req_id} у out_of_scope, але його немає в rtm.md"
        for req_id in sorted(set(out_of_scope) - known)
    ]
    errors += [
        f"{req_id}: вимога без жодного тесту"
        for req_id in sorted(required - set(tests_by_req) - set(out_of_scope))
    ]
    warnings = [
        f"{req_id}: позначено поза обсягом, але тести вже є — приберіть з out_of_scope"
        for req_id in sorted(set(out_of_scope) & set(tests_by_req))
    ]
    return errors, warnings


def _req_sort_key(req_id: str) -> tuple[str, int]:
    """FR-002 перед FR-010: сортування за номером, а не за рядком."""
    prefix, number = req_id.split("-")
    return prefix, int(number)


def _requirement_state(req_id: str, count: int, out_of_scope: dict[str, str]) -> str:
    if req_id in out_of_scope:
        return f"поза обсягом: {out_of_scope[req_id]}"
    return "✅" if count else "❌ немає тесту"


def _build_report(
    tests: list[tuple[str, set[str], bool]],
    required: set[str],
    out_of_scope: dict[str, str],
    tests_by_req: dict[str, list[str]],
    errors: list[str],
    warnings: list[str],
) -> str:
    """Звіт у Markdown: підсумок, таблиця вимог, помилки й попередження."""
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
    for req_id in sorted(required, key=_req_sort_key):
        count = len(tests_by_req.get(req_id, []))
        lines.append(f"| {req_id} | {count} | {_requirement_state(req_id, count, out_of_scope)} |")
    if errors:
        lines += ["", f"### ❌ Помилок: {len(errors)}", ""] + [f"- {e}" for e in errors]
    if warnings:
        lines += ["", "### ⚠️ Попередження", ""] + [f"- {w}" for w in warnings]
    return "\n".join(lines) + "\n"


def _publish(report: str, errors: list[str]) -> None:
    """Друкує звіт, дописує його в підсумок кроку CI і додає анотації помилок."""
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    for error in errors:
        print(f"::error::{error}")


def main() -> int:
    known, required = read_requirements()
    out_of_scope = read_out_of_scope()
    tests = scan_tests()

    errors, tests_by_req = _check_tests(tests, known)
    coverage_errors, warnings = _check_coverage(known, required, out_of_scope, tests_by_req)
    errors += coverage_errors

    report = _build_report(tests, required, out_of_scope, tests_by_req, errors, warnings)
    _publish(report, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

# Використання ШІ: скрипт і його тести (tests/test_traceability.py) згенеровано за допомогою
# Claude (Anthropic); регулярний вираз RTM_ROW спрощено за зауваженням SonarCloud.
# Код переглянуто, перевірено локально й у CI (червоний і зелений прогони в PR #351)
# та затверджено учасниками команди.
# Лаб 8 (#402): рефакторинг Extract Method (Cognitive Complexity: main 23 → 1, scan_tests 20 → 1)
# виконано ШІ-агентом Claude Code; переглянуто рядок за рядком, вивід скрипта до/після однаковий.
