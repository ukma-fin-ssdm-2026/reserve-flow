"""Спільні фікстури для тестів API."""

import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Модулі застосунку імпортуються як у uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "api"))

# Секрет JWT і пароль тестових користувачів генеруються на кожен запуск тестів:
# у репозиторії немає жодного секрету (ADR-003, detect-secrets).
os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
os.environ.setdefault("SEED_USER_PASSWORD", secrets.token_urlsafe(16))

from main import app  # noqa: E402
from mocks import USER_ADMIN_ID, USER_CLIENT_ID, USER_PROVIDER_ID  # noqa: E402
from security import create_access_token  # noqa: E402

# Ключ -> (id, роль) користувача з seed.py
TEST_USERS = {
    "client": (USER_CLIENT_ID, "Client"),
    "provider": (USER_PROVIDER_ID, "Provider"),
    "admin": (USER_ADMIN_ID, "Admin"),
}


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    """Фіксований «зараз» для правила 2 годин (FR-007): тести не залежать від дати запуску."""
    import routes.bookings as bookings_module
    from mocks import KYIV

    monkeypatch.setattr(bookings_module, "_now", lambda: datetime(2026, 10, 8, 10, 0, tzinfo=KYIV))


@pytest.fixture
def client(override_session) -> TestClient:
    """POST /bookings працює з БД: підміняємо сесію на тестову (tests/conftest.py)."""
    return TestClient(app)


def auth(who: str) -> dict[str, str]:
    """Заголовок з JWT тестового користувача ("client", "provider", "admin").
    Будь-який інший рядок передається як є — для перевірки підроблених токенів."""
    token = create_access_token(*TEST_USERS[who]) if who in TEST_USERS else who
    return {"Authorization": f"Bearer {token}"}
