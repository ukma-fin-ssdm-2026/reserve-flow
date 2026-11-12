"""Лаб 9, знахідки #2, #3: тайм-аути до БД і швидка відмова 503 замість «зависання»."""

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

import db
import services.bookings as booking_service
from conftest import auth
from mocks import SLOT_1_ID

# Тайм-аути обмежують час відповіді (PERF-001) і очікування блокування слота (REL-001)
pytestmark = pytest.mark.req("REL-001", "PERF-001")


BOOKING = {"slot_id": SLOT_1_ID, "purpose": "Зустріч команди"}


def test_postgres_engine_gets_timeouts(monkeypatch):
    captured = {}
    monkeypatch.setattr(db, "create_engine", lambda url, **kw: captured.update(kw))

    db.make_engine("postgresql+psycopg://u:p@localhost/x")

    assert captured["pool_timeout"] == db.DB_POOL_TIMEOUT_S
    assert captured["connect_args"]["connect_timeout"] == db.DB_CONNECT_TIMEOUT_S
    options = captured["connect_args"]["options"]
    assert f"statement_timeout={db.DB_STATEMENT_TIMEOUT_MS}" in options
    assert f"lock_timeout={db.DB_LOCK_TIMEOUT_MS}" in options


def test_explicit_kwargs_override_default_timeouts(monkeypatch):
    captured = {}
    monkeypatch.setattr(db, "create_engine", lambda url, **kw: captured.update(kw))

    db.make_engine("postgresql+psycopg://u:p@localhost/x", pool_timeout=1)

    assert captured["pool_timeout"] == 1


def _raise(exc):
    def _fail(*_args, **_kwargs):
        raise exc

    return _fail


def test_lock_timeout_returns_503_with_retry_after(client, monkeypatch):
    # Fault injection: PostgreSQL перервав очікування блокування (lock_timeout)
    lock_timeout = OperationalError("SELECT ... FOR UPDATE", {}, Exception("lock timeout"))
    monkeypatch.setattr(booking_service, "lock_slot", _raise(lock_timeout))

    response = client.post("/api/v1/bookings", json=BOOKING, headers=auth("client"))

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    body = response.json()["error"]
    assert body["code"] == "SERVICE_UNAVAILABLE"
    assert "lock timeout" not in body["message"]  # без внутрішніх деталей


def test_pool_timeout_returns_503(client, monkeypatch):
    monkeypatch.setattr(booking_service, "lock_slot", _raise(PoolTimeoutError("pool exhausted")))

    response = client.post("/api/v1/bookings", json=BOOKING, headers=auth("client"))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
