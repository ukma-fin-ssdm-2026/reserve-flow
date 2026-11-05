"""Тести скрипта перевірки простежуваності scripts/check_traceability.py (Лаб 7, #326).

Кожен тест будує в tmp_path маленький «репозиторій»: rtm.md, pyproject.toml і tests/,
і запускає перевірку на ньому — справжні файли проєкту не зачіпаються.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_req("інструмент CI: перевірка простежуваності, не поведінка системи")

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_traceability.py"

RTM = """\
| ID | Тип | Опис |
|----|-----|------|
| US-001 | User Story | Історія |
| FR-001 | Функціональна | Вхід |
| FR-002 | Функціональна | Права доступу |
| PERF-001 | Нефункціональна | Швидкість пошуку |
"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Тимчасовий репозиторій і модуль скрипта, налаштований на нього."""
    (tmp_path / "docs" / "requirements").mkdir(parents=True)
    (tmp_path / "docs" / "requirements" / "rtm.md").write_text(RTM, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[tool.traceability.out_of_scope]\n"PERF-001" = "немає сервісу"\n', encoding="utf-8"
    )

    spec = importlib.util.spec_from_file_location("check_traceability", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RTM", tmp_path / "docs" / "requirements" / "rtm.md")
    monkeypatch.setattr(module, "TESTS", tmp_path / "tests")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    def write_test(name, code):
        (tmp_path / "tests" / name).write_text(code, encoding="utf-8")

    return module, write_test


def test_all_requirements_covered_passes(repo, capsys):
    # Arrange
    check, write_test = repo
    write_test(
        "test_a.py",
        "import pytest\n\n"
        '@pytest.mark.req("FR-001")\ndef test_login(): pass\n\n'
        '@pytest.mark.req("FR-002", "US-001")\ndef test_rbac(): pass\n',
    )

    # Act
    code = check.main()

    # Assert
    assert code == 0
    assert "❌" not in capsys.readouterr().out


def test_requirement_without_test_fails(repo, capsys):
    # Arrange: FR-002 не має жодного тесту
    check, write_test = repo
    write_test("test_a.py", 'import pytest\n\n@pytest.mark.req("FR-001")\ndef test_login(): pass\n')

    # Act
    code = check.main()

    # Assert
    assert code == 1
    assert "FR-002: вимога без жодного тесту" in capsys.readouterr().out


def test_test_without_requirement_fails(repo, capsys):
    # Arrange: test_orphan не має мітки
    check, write_test = repo
    write_test(
        "test_a.py",
        'import pytest\n\npytestmark = pytest.mark.req("FR-001", "FR-002")\n\n'
        "def test_ok(): pass\n",
    )
    write_test("test_b.py", "def test_orphan(): pass\n")

    # Act
    code = check.main()

    # Assert
    assert code == 1
    assert "tests/test_b.py::test_orphan: тест не посилається" in capsys.readouterr().out


def test_unknown_requirement_id_fails(repo, capsys):
    # Arrange: описка FR-01 замість FR-001
    check, write_test = repo
    write_test(
        "test_a.py",
        'import pytest\n\npytestmark = pytest.mark.req("FR-001", "FR-002", "FR-01")\n\n'
        "def test_ok(): pass\n",
    )

    # Act
    code = check.main()

    # Assert
    assert code == 1
    assert "невідомий ID вимоги FR-01" in capsys.readouterr().out


def test_no_req_and_class_marks_are_respected(repo):
    # Arrange: мітка на класі поширюється на методи, no_req звільняє службовий тест
    check, write_test = repo
    write_test(
        "test_a.py",
        "import pytest\n\n"
        '@pytest.mark.req("FR-001", "FR-002")\nclass TestAuth:\n    def test_one(self): pass\n\n'
        '@pytest.mark.no_req("інфраструктура")\ndef test_infra(): pass\n',
    )

    # Act / Assert
    assert check.main() == 0


def test_out_of_scope_requirement_does_not_fail(repo, capsys):
    # Arrange: PERF-001 без тесту, але позначена поза обсягом у pyproject.toml
    check, write_test = repo
    write_test(
        "test_a.py",
        'import pytest\n\npytestmark = pytest.mark.req("FR-001", "FR-002")\n\n'
        "def test_ok(): pass\n",
    )

    # Act
    code = check.main()

    # Assert
    assert code == 0
    assert "поза обсягом: немає сервісу" in capsys.readouterr().out


# Тести нижче фіксують поведінку, яку ще не перевіряли, — додано перед рефакторингом
# скрипта (Лаб 8, #402), щоб довести, що він її не змінює.


def test_out_of_scope_with_tests_warns(repo, capsys):
    # Arrange: PERF-001 позначено поза обсягом, але тест на неї вже є
    check, write_test = repo
    write_test(
        "test_a.py",
        'import pytest\n\npytestmark = pytest.mark.req("FR-001", "FR-002", "PERF-001")\n\n'
        "def test_ok(): pass\n",
    )

    # Act
    code = check.main()

    # Assert: попередження, а не помилка
    out = capsys.readouterr().out
    assert code == 0
    assert "### ⚠️ Попередження" in out
    assert "PERF-001: позначено поза обсягом, але тести вже є" in out


def test_out_of_scope_unknown_id_fails(repo, capsys, tmp_path):
    # Arrange: у pyproject.toml поза обсягом ID, якого немає в rtm.md
    check, write_test = repo
    (tmp_path / "pyproject.toml").write_text(
        '[tool.traceability.out_of_scope]\n"PERF-001" = "немає сервісу"\n"FR-999" = "описка"\n',
        encoding="utf-8",
    )
    write_test(
        "test_a.py",
        'import pytest\n\npytestmark = pytest.mark.req("FR-001", "FR-002")\n\n'
        "def test_ok(): pass\n",
    )

    # Act
    code = check.main()

    # Assert
    assert code == 1
    assert (
        "pyproject.toml: FR-999 у out_of_scope, але його немає в rtm.md" in capsys.readouterr().out
    )


def test_report_is_appended_to_step_summary(repo, capsys, tmp_path, monkeypatch):
    # Arrange: у CI звіт дописується у файл GITHUB_STEP_SUMMARY
    check, write_test = repo
    summary = tmp_path / "summary.md"
    summary.write_text("попередній крок\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    write_test("test_a.py", 'import pytest\n\n@pytest.mark.req("FR-001")\ndef test_login(): pass\n')

    # Act
    code = check.main()

    # Assert: той самий звіт, що й у stdout, + анотації ::error:: лише в stdout
    out = capsys.readouterr().out
    written = summary.read_text(encoding="utf-8")
    assert code == 1
    assert written.startswith("попередній крок\n## Простежуваність «вимога ↔ тест»")
    assert out.startswith(written.removeprefix("попередній крок\n"))
    assert "::error::FR-002: вимога без жодного тесту" in out
    assert "::error::" not in written


def test_scan_finds_async_and_nested_class_tests(repo):
    # Arrange: async-тест, вкладений клас Test*, клас без префікса Test і допоміжна функція
    check, write_test = repo
    write_test(
        "test_a.py",
        "import pytest\n\n"
        'pytestmark = pytest.mark.req("FR-001")\n\n'
        "async def test_async(): pass\n\n"
        "def helper(): pass\n\n"
        '@pytest.mark.req("FR-002")\nclass TestOuter:\n'
        '    @pytest.mark.no_req("службовий")\n    class TestInner:\n'
        "        def test_deep(self): pass\n\n"
        "class Helper:\n    def test_ignored(self): pass\n",
    )

    # Act
    tests = check.scan_tests()

    # Assert: мітки модуля й класів успадковуються; Helper і helper не є тестами
    assert tests == [
        ("tests/test_a.py::test_async", {"FR-001"}, False),
        ("tests/test_a.py::TestOuter::TestInner::test_deep", {"FR-001", "FR-002"}, True),
    ]
