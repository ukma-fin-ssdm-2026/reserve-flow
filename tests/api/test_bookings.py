
"""Тести роутера bookings на тестовій БД (404, 403, 409)."""

from datetime import timedelta, timezone
from uuid import UUID

import pytest
from sqlmodel import Session

import routes.bookings as bookings_module
from conftest import auth
from models import Booking, TimeSlot
from schemas.bookings import BookingStatus

pytestmark = pytest.mark.req("FR-005", "FR-007", "FR-002")

CLIENT = auth("client")
PROVIDER = auth("provider")
ADMIN = auth("admin")

BOOKING_ID = UUID("c3000000-0000-4000-8000-000000000001")
BOOKING_1 = f"/api/v1/bookings/{BOOKING_ID}"
UNKNOWN_BOOKING = "/api/v1/bookings/00000000-0000-4000-8000-000000000000"
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"
SLOT_BOOKED = "b2000000-0000-4000-8000-000000000002"
SLOT_CLOSED = "b2000000-0000-4000-8000-000000000003"


def _post(client, slot_id, headers=CLIENT):
    return client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"slot_id": slot_id, "purpose": "Семінар"},
    )


def _set_booking(db_engine, **changes):
    """Оновлює seeded-бронювання в БД для підготовки тесту."""
    with Session(db_engine) as session:
        booking = session.get(Booking, BOOKING_ID)
        assert booking is not None, "Очікуване тестове бронювання відсутнє в БД"

        for field, value in changes.items():
            setattr(booking, field, value)

        session.add(booking)
        session.commit()


def _slot_start(db_engine):
    with Session(db_engine) as session:
        booking = session.get(Booking, BOOKING_ID)
        assert booking is not None

        slot = session.get(TimeSlot, booking.slot_id)
        assert slot is not None, "Для тестового бронювання має існувати слот"

        start = slot.start_time
        # SQLite може повертати datetime без tzinfo.
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return start


# --- POST ----------------------------------------------------------------------


def test_create_returns_location(client):
    r = _post(client, SLOT_FREE)
    assert r.status_code == 201
    assert r.headers["location"] == f"/api/v1/bookings/{r.json()['id']}"


def test_create_unknown_slot_returns_404(client):
    r = _post(client, "00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_create_closed_slot_returns_409(client):
    r = _post(client, SLOT_CLOSED)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SLOT_UNAVAILABLE"


def test_create_already_booked_slot_returns_409(client):
    r = _post(client, SLOT_BOOKED)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SLOT_UNAVAILABLE"


# --- GET -----------------------------------------------------------------------


def test_list_is_stable_and_from_database(client):
    first_response = client.get("/api/v1/bookings", headers=CLIENT)
    second_response = client.get("/api/v1/bookings", headers=CLIENT)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert [
        item["id"] for item in first_response.json()["items"]
    ] == [str(BOOKING_ID)]


def test_list_for_provider_and_admin(client):
    provider_response = client.get("/api/v1/bookings", headers=PROVIDER)
    admin_response = client.get("/api/v1/bookings", headers=ADMIN)

    assert provider_response.status_code == 200
    assert admin_response.status_code == 200
    assert provider_response.json()["pagination"]["total"] == 1
    assert admin_response.json()["pagination"]["total"] == 1


def test_get_booking(client):
    r = client.get(BOOKING_1, headers=CLIENT)
    assert r.status_code == 200
    assert r.json()["status"] == "Pending"
    assert r.json()["purpose"]


def test_get_unknown_booking_returns_404(client):
    r = client.get(UNKNOWN_BOOKING, headers=CLIENT)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"



def test_foreign_booking_returns_403(client, db_engine):
    # ADMIN — існуючий користувач у тестовій БД,
    # але не власник бронювання клієнта.
    from conftest import TEST_USERS

    other_client_id = UUID(str(TEST_USERS["admin"][0]))

    _set_booking(db_engine, client_id=other_client_id)

    r = client.get(BOOKING_1, headers=CLIENT)

    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


# --- PATCH ---------------------------------------------------------------------


def test_patch_unknown_booking_returns_404(client):
    r = client.patch(
        UNKNOWN_BOOKING,
        headers=CLIENT,
        json={"status": "Cancelled"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_confirm_from_rejected_returns_409(client, db_engine):
    _set_booking(db_engine, status=BookingStatus.REJECTED)

    r = client.patch(
        BOOKING_1,
        headers=PROVIDER,
        json={"status": "Confirmed"},
    )

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_cancel_less_than_2h_before_start_returns_409(
    client, db_engine, monkeypatch
):
    start = _slot_start(db_engine)
    monkeypatch.setattr(
        bookings_module,
        "_now",
        lambda: start - timedelta(hours=1),
    )

    r = client.patch(
        BOOKING_1,
        headers=CLIENT,
        json={"status": "Cancelled"},
    )

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CANCELLATION_TOO_LATE"


def test_cancel_more_than_2h_before_start(client, db_engine, monkeypatch):
    start = _slot_start(db_engine)
    monkeypatch.setattr(
        bookings_module,
        "_now",
        lambda: start - timedelta(hours=3),
    )

    r = client.patch(
        BOOKING_1,
        headers=CLIENT,
        json={"status": "Cancelled"},
    )

    assert r.status_code == 200
    assert r.json()["status"] == "Cancelled"

    # Перевіряємо збережений стан, а не лише HTTP-відповідь.
    with Session(db_engine) as session:
        booking = session.get(Booking, BOOKING_ID)
        slot = session.get(TimeSlot, booking.slot_id)

        assert booking.status == BookingStatus.CANCELLED
        assert slot.is_available is True
