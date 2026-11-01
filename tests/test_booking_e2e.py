"""Рядок 0 тест-плану (UC-001, ризик 0, #383).

POST → GET → PATCH Cancelled → слот знову вільний у пошуку → повторне бронювання.
До PR #370 GET / PATCH читали заглушки mocks.py, і тест падав з 404.
"""

import pytest
from conftest import auth

pytestmark = pytest.mark.req("UC-001", "FR-005", "FR-007")
CLIENT = auth("client")
SLOT = "b2000000-0000-4000-8000-000000000001"  # перший вільний слот із seed (mocks.SLOTS)


def test_row0_end_to_end(client):
    # Arrange / Act: клієнт бронює вільний слот
    r = client.post("/api/v1/bookings", headers=CLIENT, json={"slot_id": SLOT, "purpose": "E2E"})
    assert r.status_code == 201
    booking_id = r.json()["id"]

    # бронювання видно через GET
    got = client.get(f"/api/v1/bookings/{booking_id}", headers=CLIENT)
    assert got.status_code == 200 and got.json()["status"] == "Pending"

    # скасування через PATCH
    cancelled = client.patch(
        f"/api/v1/bookings/{booking_id}", headers=CLIENT, json={"status": "Cancelled"}
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "Cancelled"

    # слот знову в пошуку, і його можна забронювати повторно
    search = client.get("/api/v1/slots", headers=CLIENT)  # без дати: не залежить від дат у seed
    assert search.status_code == 200
    assert SLOT in [s["id"] for s in search.json()["items"]]
    again = client.post(
        "/api/v1/bookings", headers=CLIENT, json={"slot_id": SLOT, "purpose": "E2E"}
    )
    assert again.status_code == 201


# Використання ШІ: тест підготовано за допомогою Claude (Anthropic) за рядком 0 тест-плану;
# перевірено командою: на коді до PR #370 падав (GET → 404), після — зелений.
