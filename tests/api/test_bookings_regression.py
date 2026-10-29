"""Регресійні тести (L6-07): межа правила 2 годин для скасування (FR-007).

Скасувати можна, якщо до початку слота лишилося НЕ МЕНШЕ 2 год, тож рівно 2 год — ще можна.
Помилка `<` -> `<=` у routes/bookings.py давала 409 CANCELLATION_TOO_LATE рівно на межі,
а наявні тести перевіряли лише 1 год і 3 год і її не помічали.
"""

from datetime import timedelta

import pytest

import routes.bookings as bookings_module
from conftest import auth

pytestmark = pytest.mark.req("FR-007")

CLIENT = auth("client")
BOOKING_1 = "/api/v1/bookings/c3000000-0000-4000-8000-000000000001"
SLOT_BOOKED = "b2000000-0000-4000-8000-000000000002"


@pytest.mark.parametrize(
    ("time_before_start", "expected_status"),
    [
        (timedelta(hours=2, seconds=1), 200),
        (timedelta(hours=2), 200),
        (timedelta(hours=1, minutes=59, seconds=59), 409),
    ],
    ids=["2h+1s-allowed", "exactly-2h-allowed", "2h-1s-too-late"],
)
def test_cancel_deadline_boundary(client, monkeypatch, time_before_start, expected_status):
    # Arrange: «зараз» = початок слота мінус заданий проміжок
    slot = bookings_module.find_by_id(bookings_module.SLOTS, SLOT_BOOKED)
    monkeypatch.setattr(bookings_module, "_now", lambda: slot["start_time"] - time_before_start)

    # Act
    response = client.patch(BOOKING_1, headers=CLIENT, json={"status": "Cancelled"})

    # Assert
    assert response.status_code == expected_status
