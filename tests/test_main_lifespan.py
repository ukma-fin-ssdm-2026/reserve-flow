"""Життєвий цикл застосунку (main.lifespan): експорт OpenAPI під час старту сервера.

Справжній export_openapi пише файли в docs/api/, тому в тестах модуль підмінено:
файли не змінюються, а перевіряються всі три гілки — успіх, модуля немає, помилка експорту.
"""

import pytest
import asyncio
import logging
import sys
import types

import main

pytestmark = pytest.mark.no_req("інфраструктура: експорт OpenAPI під час старту сервера (D-07)")


def _start_and_stop_app():
    async def run():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run())


def _use_export(monkeypatch, export):
    module = types.ModuleType("export_openapi")
    module.export_openapi = export
    monkeypatch.setitem(sys.modules, "export_openapi", module)


def test_lifespan_exports_openapi_on_startup(monkeypatch, caplog):
    # Arrange
    exported = []
    _use_export(monkeypatch, exported.append)
    caplog.set_level(logging.INFO)

    # Act
    _start_and_stop_app()

    # Assert
    assert exported == [main.app]
    assert "успішно експортовано" in caplog.text


def test_lifespan_skips_export_when_module_missing(monkeypatch, caplog):
    # Arrange: None у sys.modules → import кидає ImportError
    monkeypatch.setitem(sys.modules, "export_openapi", None)

    # Act
    _start_and_stop_app()

    # Assert: сервер стартує, у журналі — попередження
    assert any(
        r.levelno == logging.WARNING and "Експорт пропущено" in r.message for r in caplog.records
    )


def test_lifespan_survives_export_error(monkeypatch, caplog):
    # Arrange
    def broken_export(app):
        raise OSError("docs/api недоступна для запису")

    _use_export(monkeypatch, broken_export)

    # Act
    _start_and_stop_app()

    # Assert: помилка експорту не зупиняє сервер, а потрапляє в журнал як ERROR
    assert any(
        r.levelno == logging.ERROR and "docs/api недоступна для запису" in r.message
        for r in caplog.records
    )
