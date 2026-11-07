"""Лаб 9, знахідка #4: бронювання й аудит — одна транзакція (fault injection).

Раніше бронювання комітилося першим, а AuditLog — окремо. Збій аудиту давав клієнту 500,
хоча бронювання вже було в БД, а повтор отримував 409 на власне бронювання.
"""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

import services.bookings as booking_service
from conftest import auth
from main import app
from mocks import SLOT_1_ID
from models import AuditAction, AuditLog, Booking, Notification

pytestmark = pytest.mark.req("FR-005", "FR-013")

BOOKING = {"slot_id": SLOT_1_ID, "purpose": "Зустріч команди"}


def _count(engine, model) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(model)).one()


def test_audit_failure_rolls_back_whole_booking(override_session, db_engine, monkeypatch):
    bookings_before = _count(db_engine, Booking)
    notifications_before = _count(db_engine, Notification)

    def broken_audit(**_kwargs):
        raise RuntimeError("audit storage is down")

    monkeypatch.setattr(booking_service, "AuditLog", broken_audit)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/bookings", json=BOOKING, headers=auth("client"))

    assert response.status_code == 500
    assert "audit storage" not in response.text  # без внутрішніх деталей
    assert _count(db_engine, Booking) == bookings_before
    assert _count(db_engine, Notification) == notifications_before

    # Після відновлення той самий запит проходить: слот не «зависає» зайнятим
    monkeypatch.undo()
    retry = client.post("/api/v1/bookings", json=BOOKING, headers=auth("client"))
    assert retry.status_code == 201


def test_successful_booking_writes_exactly_one_audit_record(client, db_engine):
    response = client.post("/api/v1/bookings", json=BOOKING, headers=auth("client"))
    assert response.status_code == 201
    booking_id = UUID(response.json()["id"])

    with Session(db_engine) as session:
        records = session.exec(select(AuditLog).where(AuditLog.entity_id == booking_id)).all()
    assert [r.action for r in records] == [AuditAction.BOOKING_CREATED]
