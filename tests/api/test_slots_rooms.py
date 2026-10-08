"""Тести роутерів slots і rooms (L4-07)."""

import pytest

from conftest import auth

CLIENT = auth("mock-client-token")
PROVIDER = auth("mock-provider-token")

ROOM_1 = "/api/v1/rooms/a1000000-0000-4000-8000-000000000001"
SLOT_1 = "/api/v1/slots/b2000000-0000-4000-8000-000000000001"
SLOT_WITH_BOOKING = "/api/v1/slots/b2000000-0000-4000-8000-000000000002"


def test_slots_and_rooms_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/slots"]
    assert "patch" in paths["/api/v1/slots/{slot_id}"]
    assert "get" in paths["/api/v1/rooms/{room_id}"]


# --- GET /slots ---------------------------------------------------------------


def test_search_slots_returns_page(client):
    r = client.get("/api/v1/slots?limit=1", headers=CLIENT)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["pagination"]["has_more"] is True


def test_search_slots_end_before_start_returns_422(client):
    r = client.get("/api/v1/slots?start=15:00:00&end=14:00:00", headers=CLIENT)
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "end"


def test_search_slots_unknown_building_returns_422(client):
    r = client.get("/api/v1/slots?building=Корпус 99", headers=CLIENT)
    assert r.status_code == 422


# --- GET /rooms/{id} ------------------------------------------------------------


def test_get_room(client):
    r = client.get(ROOM_1, headers=CLIENT)
    assert r.status_code == 200
    assert r.json()["name_ua"] == "Аудиторія 1-225"


def test_unknown_room_returns_404(client):
    r = client.get("/api/v1/rooms/nope", headers=CLIENT)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("url", ["/api/v1/slots", ROOM_1])
def test_no_token_returns_401(client, url):
    r = client.get(url)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


# --- PATCH /slots/{id} ------------------------------------------------------------


def test_provider_closes_slot(client):
    r = client.patch(
        SLOT_1, headers=PROVIDER, json={"is_available": False, "closure_reason": "Ремонт"}
    )
    assert r.status_code == 200
    assert r.json()["is_available"] is False
    assert r.json()["closure_reason"] == "Ремонт"


def test_provider_opens_slot_clears_reason(client):
    r = client.patch(SLOT_1, headers=PROVIDER, json={"is_available": True, "closure_reason": "x"})
    assert r.status_code == 200
    assert r.json()["closure_reason"] is None


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_close_without_reason_returns_422(client, reason):
    payload = {"is_available": False}
    if reason is not None:
        payload["closure_reason"] = reason
    r = client.patch(SLOT_1, headers=PROVIDER, json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_body_returns_422(client):
    r = client.patch(SLOT_1, headers=PROVIDER)
    assert r.status_code == 422


def test_client_cannot_patch_slot(client):
    r = client.patch(SLOT_1, headers=CLIENT, json={"is_available": False, "closure_reason": "x"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_unknown_slot_returns_404(client):
    r = client.patch(
        "/api/v1/slots/nope", headers=PROVIDER, json={"is_available": False, "closure_reason": "x"}
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_close_slot_with_active_booking_returns_409(client):
    r = client.patch(
        SLOT_WITH_BOOKING, headers=PROVIDER, json={"is_available": False, "closure_reason": "Ремонт"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ACTIVE_BOOKING_NEEDS_CONFIRMATION"


def test_search_slots_date_filter_param(client):
    paths = client.get("/openapi.json").json()["paths"]
    names = [p["name"] for p in paths["/api/v1/slots"]["get"]["parameters"]]
    assert "date" in names
    r = client.get("/api/v1/slots?date=bad", headers=CLIENT)
    assert r.status_code == 422
