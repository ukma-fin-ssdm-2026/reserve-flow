"""#421: час нагадування під час створення бронювання — за compute_reminder_time."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from conftest import auth
from mocks import KYIV, ROOM_2_ID
from models import Notification, TimeSlot

pytestmark = pytest.mark.req("FR-014")

CLIENT = auth("client")
NOW = datetime(2026, 10, 8, 10, 0, tzinfo=KYIV)  # той самий «зараз», що й conftest.fixed_now


def _book_slot_starting_in(client, db_engine, delta: timedelta) -> datetime:
    """Слот, що починається через `delta` від NOW: бронює його й повертає час нагадування."""
    start = (NOW + delta).astimezone(timezone.utc)
    with Session(db_engine) as s:
        slot = TimeSlot(
            room_id=uuid.UUID(ROOM_2_ID), start_time=start, end_time=start + timedelta(hours=1)
        )
        s.add(slot)
        s.commit()
        slot_id = str(slot.id)

    r = client.post(
        "/api/v1/bookings", headers=CLIENT, json={"slot_id": slot_id, "purpose": "Семінар"}
    )
    assert r.status_code == 201

    with Session(db_engine) as s:
        notification = s.exec(
            select(Notification).where(Notification.booking_id == uuid.UUID(r.json()["id"]))
        ).one()
    scheduled = notification.scheduled_time
    return scheduled if scheduled.tzinfo else scheduled.replace(tzinfo=timezone.utc)


def test_reminder_for_slot_within_24h_is_not_in_the_past(client, db_engine):
    # Слот через 2 год: start − 24 год було б 22 год тому → нагадування «зараз»
    assert _book_slot_starting_in(client, db_engine, timedelta(hours=2)) == NOW


def test_reminder_for_slot_beyond_24h_is_24h_before_start(client, db_engine):
    # Слот через 48 год: поведінка не змінилась — за 24 год до початку
    assert _book_slot_starting_in(client, db_engine, timedelta(hours=48)) == NOW + timedelta(
        hours=24
    )
