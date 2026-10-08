"""Спільні фікстури для тестів API."""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Модулі застосунку імпортуються як у uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "api"))

from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    """Фіксований «зараз» для правила 2 годин (FR-007): тести не залежать від дати запуску."""
    import routes.bookings as bookings_module
    from mocks import KYIV

    monkeypatch.setattr(bookings_module, "_now", lambda: datetime(2026, 10, 8, 10, 0, tzinfo=KYIV))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
