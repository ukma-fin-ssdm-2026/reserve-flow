
"""Тести матриці переходів статусів бронювання."""

from datetime import timedelta, timezone
from uuid import UUID

import pytest
from sqlmodel import Session

import routes.bookings as bookings_module
from conftest import auth
from models import Booking, TimeSlot
from schemas.bookings import BookingStatus

pytestmark = pytest.mark.req("FR-010", "FR-007", "FR-002")

BOOKING_ID = UUID("c3000000-0000-4000-8000-000000000001")
BOOKING_URL = f"/api/v1/bookings/{BOOKING_ID}"

TRANSITIONS = [
    ("TR-01", "Pending", "Confirmed", "provider", 200),
    ("TR-02", "Pending", "Confirmed", "client", 403),
    ("TR-03", "Pending", "Rejected", "provider", 200),
    ("TR-04", "Pending", "Rejected", "client", 403),
    ("TR-05", "Pending", "Cancelled", "client", 200),
    ("TR-06", "Pending", "Cancelled", "provider", 403),
    ("TR-07", "Confirmed", "Cancelled", "client", 200),
    ("TR-08", "Confirmed", "Cancelled", "provider", 403),
    ("TR-09", "Confirmed", "Confirmed", "provider", 409),
    ("TR-10", "Confirmed", "Rejected", "provider", 409),
    ("TR-11", "Rejected", "Cancelled", "client", 409),
    ("TR-12", "Cancelled", "Confirmed", "provider", 409),
    ("TR-13", "Pending", "Pending", "client", 409),
]


@pytest.mark.parametrize(
    "test_id,initial_status,target_status,role,expected_code",
    TRANSITIONS,
    ids=[item[0] for item in TRANSITIONS],
)
def test_booking_status_transition_matrix(
    client,
    db_engine,
    monkeypatch,
    test_id,
    initial_status,
    target_status,
    role,
    expected_code,
):
    # Arrange: задаємо початковий статус безпосередньо в тестовій БД.
    with Session(db_engine) as session:
        booking = session.get(Booking, BOOKING_ID)
        assert booking is not None, "Seeded-бронювання не знайдено"

        booking.status = BookingStatus(initial_status)
        session.add(booking)
        session.commit()

        slot = session.get(TimeSlot, booking.slot_id)
        if slot is not None:
            slot_start = slot.start_time
            if slot_start.tzinfo is None:
                slot_start = slot_start.replace(tzinfo=timezone.utc)

            # Скасування в цьому тесті має перевіряти переходи статусів,
            # а не випадково провалюватися через дедлайн.
            monkeypatch.setattr(
                bookings_module,
                "_now",
                lambda: slot_start - timedelta(hours=3),
            )

    payload = {"status": target_status}
    if target_status == "Rejected":
        payload["reason"] = "Причина відмови"

    # Act
    response = client.patch(
        BOOKING_URL,
        headers=auth(role),
        json=payload,
    )

    # Assert
    assert response.status_code == expected_code, (
        f"[{test_id}] Очікувався {expected_code} для переходу "
        f"{initial_status} -> {target_status} ({role}), "
        f"отримано {response.status_code}: {response.text}"
    )
