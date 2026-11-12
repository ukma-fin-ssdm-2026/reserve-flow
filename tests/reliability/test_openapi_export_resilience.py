"""Лаб 9, №10: експорт OpenAPI на старті — вимкнення через EXPORT_OPENAPI=0 і логування зі стеком.

Перевіряє:
1. За прапорцем `EXPORT_OPENAPI=0` (`false`, `no`, `off`) файли на диск при старті не пишуться.
2. Помилка запису (наприклад, read-only файлова система) не зупиняє старт сервера, але логується
   через `logging.exception` разом зі стеком (`exc_info`), а не ховається без traceback.
3. Відсутність внутрішньої залежності (`yaml`) не маскується під «Модуль export_openapi не
   знайдено», а логується як `ERROR` зі стеком.
"""

import logging
import sys
import types

import pytest

import main

pytestmark = pytest.mark.no_req(
    "інфраструктура: відмовостійкість експорту OpenAPI на старті (Лаб 9, №10)"
)


def _use_export(monkeypatch, export_fn):
    module = types.ModuleType("export_openapi")
    module.export_openapi = export_fn
    monkeypatch.setitem(sys.modules, "export_openapi", module)


@pytest.mark.parametrize("flag", ["0", "false", "FALSE", "no", "off", " 0 "])
def test_export_skipped_when_disabled_by_env(monkeypatch, caplog, flag):
    """Лаб 9, №10: при EXPORT_OPENAPI=0 сервер не пише файли в каталог репозиторію на старті."""
    called = []
    _use_export(monkeypatch, called.append)
    monkeypatch.setenv("EXPORT_OPENAPI", flag)
    caplog.set_level(logging.INFO)

    main._export_openapi_on_startup(main.app)

    assert called == []
    assert any("EXPORT_OPENAPI вимкнено" in r.getMessage() for r in caplog.records)


def test_export_runs_by_default_and_when_enabled(monkeypatch, caplog):
    """За замовчуванням (або при EXPORT_OPENAPI=1) схема експортується штатно."""
    called = []
    _use_export(monkeypatch, called.append)
    monkeypatch.setenv("EXPORT_OPENAPI", "1")
    caplog.set_level(logging.INFO)

    main._export_openapi_on_startup(main.app)

    assert called == [main.app]
    assert any("успішно експортовано" in r.getMessage() for r in caplog.records)


def test_readonly_filesystem_error_logs_traceback_and_survives(monkeypatch, caplog):
    """Лаб 9, №10: помилка запису на read-only ФС логується з повним traceback (exc_info)."""

    def readonly_boom(_app):
        raise PermissionError(13, "Read-only file system", "docs/api/openapi-generated.json")

    _use_export(monkeypatch, readonly_boom)
    monkeypatch.delenv("EXPORT_OPENAPI", raising=False)
    caplog.set_level(logging.ERROR)

    main._export_openapi_on_startup(main.app)

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert "Read-only file system" in error_records[0].getMessage()
    assert error_records[0].exc_info is not None
    assert error_records[0].exc_info[0] is PermissionError


def test_missing_yaml_dependency_is_not_masked_as_missing_export_module(
    monkeypatch, caplog, builtins_import=None
):
    """Лаб 9, №10: відсутність пакета yaml логується як ERROR зі стеком, а не WARNING."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "export_openapi":
            raise ModuleNotFoundError("No module named 'yaml'", name="yaml")
        return real_import(name, *args, **kwargs)

    monkeypatch.delenv("EXPORT_OPENAPI", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    caplog.set_level(logging.WARNING)

    main._export_openapi_on_startup(main.app)

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert "відсутня залежність" in error_records[0].getMessage()
    assert "yaml" in error_records[0].getMessage()
    assert error_records[0].exc_info is not None
    assert not any("Модуль export_openapi не знайдено" in r.getMessage() for r in caplog.records)


def test_missing_export_openapi_module_logs_warning(monkeypatch, caplog):
    """Якщо відсутній сам модуль export_openapi, логується WARNING."""
    monkeypatch.delenv("EXPORT_OPENAPI", raising=False)
    monkeypatch.setitem(sys.modules, "export_openapi", None)
    caplog.set_level(logging.WARNING)

    main._export_openapi_on_startup(main.app)

    assert any(
        r.levelno == logging.WARNING and "Модуль export_openapi не знайдено" in r.getMessage()
        for r in caplog.records
    )


# Використання ШІ: При написанні коду було використано допомогу ШІ Gemini, код перевірено та
# затверджено учасником команди.
