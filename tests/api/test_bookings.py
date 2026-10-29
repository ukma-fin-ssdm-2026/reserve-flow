"""Тести роутера bookings на спільних заглушках mocks.py (404, 403, 409).

Покриті граничні випадки (Edge Cases):
- Спроба створити бронювання на неіснуючий  або вже зайнятий слот (409 Conflict).
- Спроба забронювати слот, який закрито провайдером (SLOT_CLOSED).
- Спроба скасувати бронювання менш ніж за 2 години до початку (CANCELLATION_TOO_LATE).
- Спроба доступу до чужого бронювання (403 Forbidden).
- Неможливість перевести відхилене бронювання у статус Confirmed (INVALID_STATUS_TRANSITION).
"""

import pytest
from datetime import timedelta

import routes.bookings as bookings_module
from conftest import auth

pytestmark = pytest.mark.req("FR-005", "FR-007", "FR-002")

CLIENT = auth("client")
PROVIDER = auth("provider")
ADMIN = auth("admin")

BOOKING_1 = "/api/v1/bookings/c3000000-0000-4000-8000-000000000001"
UNKNOWN_BOOKING = "/api/v1/bookings/00000000-0000-4000-8000-000000000000"
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"
SLOT_BOOKED = "b2000000-0000-4000-8000-000000000002"
SLOT_CLOSED = "b2000000-0000-4000-8000-000000000003"


def _post(client, slot_id, headers=CLIENT):
    return client.post(
        "/api/v1/bookings", headers=headers, json={"slot_id": slot_id, "purpose": "Семінар"}
    )


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


def test_list_is_stable_and_from_mocks(client):
    first = client.get("/api/v1/bookings", headers=CLIENT).json()
    second = client.get("/api/v1/bookings", headers=CLIENT).json()
    assert first == second
    assert [b["id"] for b in first["items"]] == ["c3000000-0000-4000-8000-000000000001"]


def test_list_for_provider_and_admin(client):
    assert client.get("/api/v1/bookings", headers=PROVIDER).json()["pagination"]["total"] == 1
    assert client.get("/api/v1/bookings", headers=ADMIN).json()["pagination"]["total"] == 1


def test_get_booking(client):
    r = client.get(BOOKING_1, headers=CLIENT)
    assert r.status_code == 200
    assert r.json()["status"] == "Pending"
    assert r.json()["purpose"]


def test_get_unknown_booking_returns_404(client):
    r = client.get(UNKNOWN_BOOKING, headers=CLIENT)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_foreign_booking_returns_403(client, monkeypatch):
    # Бронювання належить іншому клієнту
    other = dict(bookings_module.BOOKINGS[0], client_id="99999999-9999-4999-8999-999999999999")
    monkeypatch.setattr(bookings_module, "BOOKINGS", [other])
    r = client.get(BOOKING_1, headers=CLIENT)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


# --- PATCH ---------------------------------------------------------------------


def test_patch_unknown_booking_returns_404(client):
    r = client.patch(UNKNOWN_BOOKING, headers=CLIENT, json={"status": "Cancelled"})
    assert r.status_code == 404


def test_confirm_from_rejected_returns_409(client, monkeypatch):
    rejected = dict(bookings_module.BOOKINGS[0], status="Rejected")
    monkeypatch.setattr(bookings_module, "BOOKINGS", [rejected])
    r = client.patch(BOOKING_1, headers=PROVIDER, json={"status": "Confirmed"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_cancel_less_than_2h_before_start_returns_409(client, monkeypatch):
    slot = bookings_module.find_by_id(bookings_module.SLOTS, SLOT_BOOKED)
    monkeypatch.setattr(bookings_module, "_now", lambda: slot["start_time"] - timedelta(hours=1))
    r = client.patch(BOOKING_1, headers=CLIENT, json={"status": "Cancelled"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CANCELLATION_TOO_LATE"


def test_cancel_more_than_2h_before_start(client, monkeypatch):
    slot = bookings_module.find_by_id(bookings_module.SLOTS, SLOT_BOOKED)
    monkeypatch.setattr(bookings_module, "_now", lambda: slot["start_time"] - timedelta(hours=3))
    r = client.patch(BOOKING_1, headers=CLIENT, json={"status": "Cancelled"})
    assert r.status_code == 200
    assert r.json()["status"] == "Cancelled"
