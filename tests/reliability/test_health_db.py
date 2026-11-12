"""Лаб 9, №7 (#458): /api/v1/health перевіряє БД.

Ін'єкція збою: залежність `get_session` підміняється сесією, що кидає помилку БД, або сесією
на сервер, якого немає. Очікування: `503 unhealthy` без внутрішніх деталей, попередження
в лозі, а коли БД знову відповідає — знову `200 healthy`.
"""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlmodel import Session

from db import get_session, make_engine
from main import app

pytestmark = pytest.mark.no_req("інфраструктура: перевірка стану сервісу і БД (Лаб 9, №7)")

HEALTH = "/api/v1/health"
INTERNAL_DETAIL = "connection to server at db-internal.example (10.0.0.7) failed: role rf_admin"
HEALTHY = {"status": "healthy", "db": "ok"}
UNHEALTHY = {"status": "unhealthy", "db": "unavailable"}


def _db_error(kind: type[Exception]) -> Exception:
    if kind is PoolTimeoutError:
        return PoolTimeoutError(INTERNAL_DETAIL)
    return kind("SELECT 1", {}, Exception(INTERNAL_DETAIL))


class _BrokenSession:
    """Сесія, у якої будь-який запит до БД падає з заданою помилкою."""

    def __init__(self, error: Exception):
        self.error = error

    def execute(self, *args, **kwargs):
        raise self.error

    exec = execute


@pytest.fixture
def broken_db():
    """Підміняє сесію на зламану; повертає функцію, що вмикає конкретну помилку."""

    def _break(kind: type[Exception] = OperationalError) -> None:
        def _get_session():
            yield _BrokenSession(_db_error(kind))

        app.dependency_overrides[get_session] = _get_session

    yield _break
    app.dependency_overrides.pop(get_session, None)


# --- Поведінка, коли БД працює --------------------------------------------------------


def test_healthy_when_db_answers(client):
    response = client.get(HEALTH)

    assert response.status_code == 200
    assert response.json() == HEALTHY


def test_no_auth_required(client):
    response = client.get(HEALTH, headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 200


# --- Ін'єкція збою БД ------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind",
    [OperationalError, InterfaceError, PoolTimeoutError],
    ids=["operational", "connection-lost", "pool-timeout"],
)
def test_db_failure_gives_503(broken_db, kind):
    broken_db(kind)

    response = TestClient(app).get(HEALTH)

    assert response.status_code == 503
    assert response.json() == UNHEALTHY


def test_unreachable_database_gives_503():
    """Справжній збій: сервера БД на цьому порту немає — з'єднання відхиляється."""
    engine = make_engine("postgresql+psycopg://127.0.0.1:1/none")

    def _get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    try:
        response = TestClient(app).get(HEALTH)
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()

    assert response.status_code == 503
    assert response.json() == UNHEALTHY


def test_legacy_path_also_checks_db(broken_db):
    broken_db()

    response = TestClient(app).get("/health")

    assert response.status_code == 503
    assert response.json() == UNHEALTHY


def test_response_has_no_internal_details(broken_db):
    broken_db()

    body = TestClient(app).get(HEALTH).text

    for leaked in ("db-internal", "10.0.0.7", "rf_admin", "OperationalError", "SELECT"):
        assert leaked not in body


def test_failure_is_logged_without_details(broken_db, caplog):
    broken_db()

    with caplog.at_level(logging.WARNING):
        TestClient(app).get(HEALTH)

    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("OperationalError" in m for m in messages), messages
    assert not any("rf_admin" in m or "10.0.0.7" in m for m in messages)


def test_recovers_when_db_returns(client, broken_db):
    """Відновлення автоматичне: щойно БД знову відповідає, health — знову 200."""
    working = app.dependency_overrides[get_session]  # тестова БД із фікстури client
    broken_db()
    assert client.get(HEALTH).status_code == 503

    app.dependency_overrides[get_session] = working  # «БД повернулась»

    assert client.get(HEALTH).json() == HEALTHY


# --- Документація -------------------------------------------------------------------------


def test_openapi_documents_503_and_keeps_operation_id():
    operation = app.openapi()["paths"][HEALTH]["get"]

    assert "503" in operation["responses"]
    # назва інструменту MCP-агента (check_health) залежить від operationId
    assert operation["operationId"] == "health_check_api_v1_health_get"
