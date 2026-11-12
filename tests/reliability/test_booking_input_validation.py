"""Знахідка №13 (#457): нормалізація purpose та межа довжини reason."""

import pytest

from conftest import auth

pytestmark = pytest.mark.req("FR-005", "FR-010")

CLIENT = auth("client")
PROVIDER = auth("provider")
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"
BOOKING_ID = "c3000000-0000-4000-8000-000000000001"


def _post(client, purpose: str):
    return client.post(
        "/api/v1/bookings",
        headers=CLIENT,
        json={"slot_id": SLOT_FREE, "purpose": purpose},
    )


@pytest.mark.parametrize("purpose", ["", "   "], ids=["empty", "whitespace-only"])
def test_purpose_empty_after_trimming_returns_422(client, purpose):
    response = _post(client, purpose)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_purpose_at_max_length_is_accepted_and_trimmed(client):
    purpose = f"  {'x' * 200}  "

    response = _post(client, purpose)

    assert response.status_code == 201
    assert response.json()["purpose"] == "x" * 200


def test_purpose_over_max_length_returns_422(client):
    response = _post(client, "x" * 201)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reason_at_max_length_is_accepted_and_trimmed(client):
    reason = f" {'r' * 500} "

    response = client.patch(
        f"/api/v1/bookings/{BOOKING_ID}",
        headers=PROVIDER,
        json={"status": "Rejected", "reason": reason},
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "r" * 500


def test_reason_over_max_length_returns_422(client):
    response = client.patch(
        f"/api/v1/bookings/{BOOKING_ID}",
        headers=PROVIDER,
        json={"status": "Rejected", "reason": "r" * 501},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_whitespace_only_reason_returns_422(client):
    response = client.patch(
        f"/api/v1/bookings/{BOOKING_ID}",
        headers=PROVIDER,
        json={"status": "Rejected", "reason": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
