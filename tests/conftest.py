"""Спільні фікстури для тестів API."""

import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

# Модулі застосунку імпортуються як у uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "api"))

# Секрет JWT і пароль тестових користувачів генеруються на кожен запуск тестів:
# у репозиторії немає жодного секрету (ADR-003, detect-secrets).
os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
os.environ.setdefault("SEED_USER_PASSWORD", secrets.token_urlsafe(16))

from db import get_session, make_engine  # noqa: E402
from main import app  # noqa: E402
from mocks import USER_ADMIN_ID, USER_CLIENT_ID, USER_PROVIDER_ID  # noqa: E402
from security import create_access_token  # noqa: E402

# Ключ -> (id, роль) користувача з seed.py
TEST_USERS = {
    "client": (USER_CLIENT_ID, "Client"),
    "provider": (USER_PROVIDER_ID, "Provider"),
    "admin": (USER_ADMIN_ID, "Admin"),
}
from seed import seed  # noqa: E402


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    """Фіксований «зараз» для правила 2 годин (FR-007): тести не залежать від дати запуску."""
    import routes.bookings as bookings_module
    from mocks import KYIV

    monkeypatch.setattr(bookings_module, "_now", lambda: datetime(2026, 10, 8, 10, 0, tzinfo=KYIV))


@pytest.fixture
def db_engine():
    """Чиста БД із seed з mocks.py на кожен тест.
    За замовчуванням SQLite in-memory; TEST_DATABASE_URL — окрема тестова PostgreSQL."""
    engine = make_engine(os.getenv("TEST_DATABASE_URL", "sqlite://"))
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def override_session(db_engine):
    def _get_session():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def client(override_session) -> TestClient:
    return TestClient(app)


def auth(who: str) -> dict[str, str]:
    """Заголовок з JWT тестового користувача ("client", "provider", "admin").
    Будь-який інший рядок передається як є — для перевірки підроблених токенів."""
    token = create_access_token(*TEST_USERS[who]) if who in TEST_USERS else who
    return {"Authorization": f"Bearer {token}"}
