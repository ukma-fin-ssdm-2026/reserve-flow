"""Тести заглушки автентифікації (L4-05, D-06)."""

import pytest

from conftest import auth

TOKEN_URL = "/api/v1/auth/token"


@pytest.mark.parametrize(
    ("email", "token", "role"),
    [
        ("client@ukma.edu.ua", "mock-client-token", "Client"),
        ("provider@ukma.edu.ua", "mock-provider-token", "Provider"),
        ("admin@ukma.edu.ua", "mock-admin-token", "Admin"),
    ],
)
def test_token_for_each_test_user(client, email, token, role):
    r = client.post(TOKEN_URL, json={"email": email, "password": "lab4-demo"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] == token
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == role


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "client@ukma.edu.ua", "password": "wrong"},
        {"email": "nobody@ukma.edu.ua", "password": "lab4-demo"},
    ],
)
def test_wrong_credentials_return_401(client, payload):
    r = client.post(TOKEN_URL, json=payload)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_email_returns_422(client):
    r = client.post(TOKEN_URL, json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "email"


def test_no_token_returns_401_in_error_format(client):
    r = client.get("/api/v1/bookings")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    error = r.json()["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert error["correlation_id"]


def test_unknown_token_returns_401(client):
    r = client.get("/api/v1/bookings", headers=auth("forged-token"))
    assert r.status_code == 401


def test_valid_token_passes(client):
    r = client.get("/api/v1/bookings", headers=auth("mock-client-token"))
    assert r.status_code == 200


def test_me_returns_current_user(client):
    r = client.get("/api/v1/auth/me", headers=auth("mock-provider-token"))
    assert r.status_code == 200
    assert r.json()["email"] == "provider@ukma.edu.ua"


def test_wrong_role_returns_403(client):
    # Бронювати може лише клієнт (require_role)
    r = client.post(
        "/api/v1/bookings",
        headers=auth("mock-provider-token"),
        json={"slot_id": "b2000000-0000-4000-8000-000000000001", "purpose": "Семінар"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_swagger_has_authorize_button(client):
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    # /auth/token доступна без токена
    assert "security" not in spec["paths"]["/api/v1/auth/token"]["post"]
