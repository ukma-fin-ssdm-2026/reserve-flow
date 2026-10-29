"""Регресійні тести межі правила двох годин для скасування (FR-007)."""

from datetime import timedelta, timezone
from uuid import UUID

import pytest
from sqlmodel import Session

import routes.bookings as bookings_module
from conftest import auth
from models import Booking, TimeSlot
from schemas.bookings import BookingStatus

pytestmark = pytest.mark.req("FR-007")

CLIENT = auth("client")
BOOKING_ID = UUID("c3000000-0000-4000-8000-000000000001")
BOOKING_URL = f"/api/v1/bookings/{BOOKING_ID}"


@pytest.mark.parametrize(
    ("time_before_start", "expected_status"),
    [
        (timedelta(hours=2, seconds=1), 200),
        (timedelta(hours=2), 200),
        (timedelta(hours=1, minutes=59, seconds=59), 409),
    ],
    ids=["2h+1s-allowed", "exactly-2h-allowed", "2h-1s-too-late"],
)
def test_cancel_deadline_boundary(
    client,
    db_engine,
    monkeypatch,
    time_before_start,
    expected_status,
):
    # Arrange: отримуємо час слота з тестової БД.
    with Session(db_engine) as session:
        booking = session.get(Booking, BOOKING_ID)
        assert booking is not None, "Seeded-бронювання не знайдено"

        # Кожен тест починається з Pending, незалежно від інших тестів.
        booking.status = BookingStatus.PENDING
        session.add(booking)
        session.commit()

        slot = session.get(TimeSlot, booking.slot_id)
        assert slot is not None, "Для бронювання не знайдено слот"

        slot_start = slot.start_time
        # SQLite може повертати datetime без інформації про часовий пояс.
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)

    # Arrange: «зараз» = початок слота мінус заданий проміжок.
    monkeypatch.setattr(
        bookings_module,
        "_now",
        lambda: slot_start - time_before_start,
    )

    # Act
    response = client.patch(
        BOOKING_URL,
        headers=CLIENT,
        json={"status": "Cancelled"},
    )

    # Assert
    assert response.status_code == expected_status, response.text

    if expected_status == 200:
        with Session(db_engine) as session:
            booking = session.get(Booking, BOOKING_ID)
            slot = session.get(TimeSlot, booking.slot_id)

            assert booking.status == BookingStatus.CANCELLED
            assert slot.is_available is True
