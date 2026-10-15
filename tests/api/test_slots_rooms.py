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


def test_provider_cannot_patch_foreign_room_slot(client, monkeypatch):
    from mocks import ROOMS

    monkeypatch.setitem(ROOMS[0], "provider_id", "00000000-0000-4000-8000-999999999999")
    r = client.patch(
        SLOT_1, headers=PROVIDER, json={"is_available": False, "closure_reason": "Ремонт"}
    )
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
        SLOT_WITH_BOOKING,
        headers=PROVIDER,
        json={"is_available": False, "closure_reason": "Ремонт"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ACTIVE_BOOKING_NEEDS_CONFIRMATION"


def test_search_slots_date_filter_param(client):
    paths = client.get("/openapi.json").json()["paths"]
    names = [p["name"] for p in paths["/api/v1/slots"]["get"]["parameters"]]
    assert "date" in names
    r = client.get("/api/v1/slots?date=bad", headers=CLIENT)
    assert r.status_code == 422


# --- Фільтрація GET /slots ----------------------------------------------------

FREE_1 = "b2000000-0000-4000-8000-000000000001"
FREE_4 = "b2000000-0000-4000-8000-000000000004"
FREE_5 = "b2000000-0000-4000-8000-000000000005"


def _ids(client, query=""):
    r = client.get(f"/api/v1/slots{query}", headers=CLIENT)
    assert r.status_code == 200
    return [s["id"] for s in r.json()["items"]]


def test_only_free_slots_returned(client):
    # SLOT_2 заброньовано (BOOKING_1), SLOT_3 закрито постачальником
    assert _ids(client) == [FREE_1, FREE_4, FREE_5]


def test_filter_by_date(client):
    assert _ids(client, "?date=2026-10-16") == [FREE_5]
    assert _ids(client, "?date=2026-10-20") == []


def test_filter_by_time_interval(client):
    assert _ids(client, "?date=2026-10-15&start=14:00:00&end=15:30:00") == [FREE_1]
    assert _ids(client, "?date=2026-10-15&start=15:00:00") == [FREE_4]


def test_filter_by_room_properties(client):
    assert _ids(client, "?is_shelter=true") == [FREE_4]
    assert _ids(client, "?has_projector=true") == [FREE_1, FREE_5]
    assert _ids(client, "?capacity=30") == [FREE_1, FREE_5]
    assert _ids(client, "?building=Корпус 3") == [FREE_4]


def test_filter_by_room_id(client):
    # D-02: GET /slots?room_id={id} замість вкладеного /rooms/{id}/slots
    room_1 = "a1000000-0000-4000-8000-000000000001"
    room_2 = "a1000000-0000-4000-8000-000000000002"
    assert _ids(client, f"?room_id={room_1}") == [FREE_1, FREE_5]
    assert _ids(client, f"?room_id={room_2}") == [FREE_4]
    assert _ids(client, f"?room_id={room_1}&date=2026-10-15") == [FREE_1]
    assert _ids(client, "?room_id=00000000-0000-4000-8000-000000000000") == []


def test_filter_by_room_id_invalid_returns_422(client):
    r = client.get("/api/v1/slots?room_id=abc", headers=CLIENT)
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "room_id"
