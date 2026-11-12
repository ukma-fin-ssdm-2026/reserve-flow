"""Знахідка №9a (#456): бронювання дозволене лише до початку слота."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlmodel import Session, select

from conftest import auth
from models import Booking, TimeSlot

pytestmark = pytest.mark.req("FR-005")

URL = "/api/v1/bookings"
CLIENT = auth("client")
SLOT_FREE = UUID("b2000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("seconds_from_now", "expected_status"),
    [(-1, 409), (0, 409), (1, 201)],
    ids=["one-second-past", "exactly-now", "one-second-future"],
)
def test_booking_time_boundary(
    client, db_engine, monkeypatch, caplog, seconds_from_now, expected_status
):
    """Слот у минулому або рівно зараз відхиляється; слот за секунду приймається."""
    import routes.bookings as bookings_route

    monkeypatch.setattr(bookings_route, "_now", lambda: NOW)
    slot_start = NOW + timedelta(seconds=seconds_from_now)
    with Session(db_engine) as session:
        slot = session.get(TimeSlot, SLOT_FREE)
        assert slot is not None
        slot.start_time = slot_start
        slot.end_time = slot_start + timedelta(hours=1)
        session.add(slot)
        session.commit()

    with caplog.at_level(logging.WARNING, logger="services.bookings"):
        response = client.post(
            URL,
            headers=CLIENT,
            json={"slot_id": str(SLOT_FREE), "purpose": "Семінар"},
        )

    assert response.status_code == expected_status
    with Session(db_engine) as session:
        booking = session.exec(select(Booking).where(Booking.slot_id == SLOT_FREE)).first()

    if seconds_from_now <= 0:
        assert response.json()["error"]["code"] == "SLOT_ALREADY_STARTED"
        assert "час початку слота вже настав" in response.json()["error"]["message"]
        assert booking is None
        assert "Rejecting booking for slot that has already started" in caplog.text
    else:
        assert response.json()["status"] == "Pending"
        assert booking is not None
