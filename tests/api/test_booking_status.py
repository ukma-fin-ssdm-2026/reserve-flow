"""Тести статусів бронювання і переходів (D-03)."""

import pytest

from conftest import auth

BOOKING_URL = "/api/v1/bookings/c3000000-0000-4000-8000-000000000001"
CLIENT = auth("mock-client-token")
PROVIDER = auth("mock-provider-token")


def test_new_booking_is_pending(client):
    r = client.post(
        "/api/v1/bookings",
        headers=CLIENT,
        json={"slot_id": "b2000000-0000-4000-8000-000000000001", "purpose": "Семінар"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "Pending"


def test_status_enum_matches_data_model(client):
    spec = client.get("/openapi.json").json()
    assert spec["components"]["schemas"]["BookingStatus"]["enum"] == [
        "Pending",
        "Confirmed",
        "Rejected",
        "Cancelled",
    ]


@pytest.mark.parametrize(
    ("headers", "payload"),
    [
        (PROVIDER, {"status": "Confirmed"}),
        (PROVIDER, {"status": "Rejected", "reason": "Аудиторія на ремонті"}),
        (CLIENT, {"status": "Cancelled"}),
        (CLIENT, {"status": "Cancelled", "reason": "Змінився розклад"}),
    ],
)
def test_allowed_transitions(client, headers, payload):
    r = client.patch(BOOKING_URL, headers=headers, json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == payload["status"]


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_reject_without_reason_returns_422(client, reason):
    payload = {"status": "Rejected"}
    if reason is not None:
        payload["reason"] = reason
    r = client.patch(BOOKING_URL, headers=PROVIDER, json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("headers", "payload"),
    [
        (CLIENT, {"status": "Confirmed"}),
        (CLIENT, {"status": "Rejected", "reason": "Хочу"}),
        (PROVIDER, {"status": "Cancelled"}),
    ],
)
def test_wrong_role_returns_403(client, headers, payload):
    r = client.patch(BOOKING_URL, headers=headers, json=payload)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_transition_to_pending_returns_409(client):
    r = client.patch(BOOKING_URL, headers=CLIENT, json={"status": "Pending"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_old_status_values_rejected(client):
    r = client.patch(BOOKING_URL, headers=CLIENT, json={"status": "ACTIVE"})
    assert r.status_code == 422
