"""Лаб 9, знахідка #6: гонка при зміні статусу бронювання (lost update).

Два запити читають `Pending`, обидва проходять перевірку переходу, і без умовного
UPDATE обидва отримують 200, хоча зміна одного з них фактично перезаписана.
Тут «паралельний» запит імітується: між перевіркою прав і записом інша сесія
встигає змінити статус (fault injection через дублер _can_view).
"""

from uuid import UUID

import pytest
from sqlmodel import Session, select

import routes.bookings as bookings_module
from conftest import auth
from models import AuditAction, AuditLog, Booking, BookingStatus

# Скасування (FR-007) не має «губитися», а журнал (FR-013) — суперечити стану
pytestmark = pytest.mark.req("FR-007", "FR-013")

BOOKING_ID = UUID("c3000000-0000-4000-8000-000000000001")
BOOKING_URL = f"/api/v1/bookings/{BOOKING_ID}"


def _change_status_concurrently(monkeypatch, db_engine, new_status):
    original = bookings_module._can_view

    def can_view_then_race(session, user, booking):
        allowed = original(session, user, booking)
        with Session(db_engine) as other:  # інший запит встиг першим
            competitor = other.get(Booking, BOOKING_ID)
            competitor.status = new_status
            other.add(competitor)
            other.commit()
        return allowed

    monkeypatch.setattr(bookings_module, "_can_view", can_view_then_race)


def test_concurrent_cancel_makes_confirm_fail_with_409(client, db_engine, monkeypatch):
    _change_status_concurrently(monkeypatch, db_engine, BookingStatus.CANCELLED)

    response = client.patch(BOOKING_URL, json={"status": "Confirmed"}, headers=auth("provider"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    with Session(db_engine) as session:
        assert session.get(Booking, BOOKING_ID).status == BookingStatus.CANCELLED
        actions = session.exec(
            select(AuditLog.action).where(AuditLog.entity_id == BOOKING_ID)
        ).all()
    assert AuditAction.BOOKING_CONFIRMED not in actions  # журнал не суперечить стану


def test_status_change_without_race_still_works(client, db_engine):
    response = client.patch(BOOKING_URL, json={"status": "Confirmed"}, headers=auth("provider"))

    assert response.status_code == 200
    assert response.json()["status"] == "Confirmed"
    with Session(db_engine) as session:
        assert session.get(Booking, BOOKING_ID).status == BookingStatus.CONFIRMED
