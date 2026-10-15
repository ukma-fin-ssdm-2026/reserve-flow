"""Спільні фікстури для тестів API."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

# Модулі застосунку імпортуються як у uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "api"))

from db import get_session, make_engine  # noqa: E402
from main import app  # noqa: E402
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


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
