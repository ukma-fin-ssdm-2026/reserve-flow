"""Тести автентифікації за ADR-003: bcrypt + JWT (L5-12, #205)."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlmodel import Session

from conftest import TEST_USERS, auth
from models import Role, User
from security import JWT_ALGORITHM, JWT_ISSUER, decode_access_token

pytestmark = pytest.mark.req("FR-001", "FR-002", "FR-012")

TOKEN_URL = "/api/v1/auth/token"
BOOKINGS_URL = "/api/v1/bookings"


def _password() -> str:
    return os.environ["SEED_USER_PASSWORD"]


def _forge(**overrides) -> str:
    """Токен із довільним payload, підписаний справжнім секретом (якщо не вказано інше)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": TEST_USERS["client"][0],
        "role": "Client",
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    secret = overrides.pop("secret", os.environ["JWT_SECRET"])
    algorithm = overrides.pop("algorithm", JWT_ALGORITHM)
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm=algorithm)


def _update_user(db_engine, key: str, **fields) -> None:
    with Session(db_engine) as s:
        user = s.get(User, uuid.UUID(TEST_USERS[key][0]))
        for name, value in fields.items():
            setattr(user, name, value)
        s.add(user)
        s.commit()


# --- POST /auth/token ----------------------------------------------------------


@pytest.mark.parametrize(
    ("email", "role"),
    [
        ("client@ukma.edu.ua", "Client"),
        ("provider@ukma.edu.ua", "Provider"),
        ("admin@ukma.edu.ua", "Admin"),
    ],
)
def test_login_returns_signed_jwt(client, email, role):
    r = client.post(TOKEN_URL, json={"email": email, "password": _password()})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["user"]["role"] == role

    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == body["user"]["id"]
    assert claims["role"] == role


def test_login_email_is_case_insensitive(client):
    r = client.post(TOKEN_URL, json={"email": "Client@UKMA.edu.ua", "password": _password()})
    assert r.status_code == 200


def test_login_token_works_for_protected_endpoint(client):
    login = client.post(TOKEN_URL, json={"email": "provider@ukma.edu.ua", "password": _password()})
    token = login.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["email"] == "provider@ukma.edu.ua"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "client@ukma.edu.ua", "password": "wrong"},
        {"email": "nobody@ukma.edu.ua", "password": "wrong"},
        # bcrypt не приймає > 72 байтів: має бути 401, а не 500
        {"email": "client@ukma.edu.ua", "password": "ї" * 60},
    ],
)
def test_wrong_credentials_return_401(client, payload):
    r = client.post(TOKEN_URL, json=payload)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
    assert r.json()["error"]["message"] == "Невірний email або пароль"


def test_invalid_email_returns_422(client):
    r = client.post(TOKEN_URL, json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "email"


def test_blocked_user_cannot_log_in(client, db_engine):
    _update_user(db_engine, "client", is_blocked=True)
    r = client.post(TOKEN_URL, json={"email": "client@ukma.edu.ua", "password": _password()})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_user_without_password_cannot_log_in(client, db_engine):
    _update_user(db_engine, "client", password_hash="!no-login")
    r = client.post(TOKEN_URL, json={"email": "client@ukma.edu.ua", "password": "!no-login"})
    assert r.status_code == 401


def test_passwords_are_stored_as_bcrypt_hashes(db_engine):
    with Session(db_engine) as s:
        user = s.get(User, uuid.UUID(TEST_USERS["client"][0]))
    assert user.password_hash.startswith("$2b$")
    assert _password() not in user.password_hash


# --- Bearer-токен на захищених кінцевих точках --------------------------------


def test_no_token_returns_401_in_error_format(client):
    r = client.get(BOOKINGS_URL)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    error = r.json()["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert error["correlation_id"]


def test_valid_token_passes(client):
    r = client.get(BOOKINGS_URL, headers=auth("client"))
    assert r.status_code == 200


def test_me_returns_current_user(client):
    r = client.get("/api/v1/auth/me", headers=auth("provider"))
    assert r.status_code == 200
    assert r.json()["email"] == "provider@ukma.edu.ua"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("forged-token", id="not-a-jwt"),
        pytest.param("mock-client-token", id="old-lab4-stub-token"),
        pytest.param(_forge(secret="x" * 48), id="wrong-secret"),
        pytest.param(_forge(exp=datetime.now(timezone.utc) - timedelta(seconds=1)), id="expired"),
        pytest.param(_forge(iss="someone-else"), id="wrong-issuer"),
        pytest.param(_forge(sub=str(uuid.uuid4())), id="unknown-user"),
        pytest.param(_forge(sub="not-a-uuid"), id="bad-sub"),
        # роль у токені не збігається з роллю в БД (напр. роль змінили після входу)
        pytest.param(_forge(role="Admin"), id="role-differs-from-db"),
    ],
)
def test_invalid_tokens_return_401(client, token):
    r = client.get(BOOKINGS_URL, headers=auth(token))
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_unsigned_alg_none_token_rejected(client):
    header_payload = jwt.encode(
        {"sub": TEST_USERS["admin"][0], "role": "Admin", "iss": JWT_ISSUER},
        key=None,
        algorithm="none",
    )
    r = client.get(BOOKINGS_URL, headers=auth(header_payload))
    assert r.status_code == 401


def test_blocked_user_token_stops_working_immediately(client, db_engine):
    # Контрзахід ADR-003: блокування діє одразу, не чекаючи закінчення строку токена
    headers = auth("client")
    assert client.get(BOOKINGS_URL, headers=headers).status_code == 200
    _update_user(db_engine, "client", is_blocked=True)
    assert client.get(BOOKINGS_URL, headers=headers).status_code == 401


def test_role_change_invalidates_token(client, db_engine):
    headers = auth("client")
    _update_user(db_engine, "client", role=Role.PROVIDER)
    assert client.get(BOOKINGS_URL, headers=headers).status_code == 401


def test_wrong_role_returns_403(client):
    # Бронювати може лише клієнт (require_role)
    r = client.post(
        BOOKINGS_URL,
        headers=auth("provider"),
        json={"slot_id": "b2000000-0000-4000-8000-000000000001", "purpose": "Семінар"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_swagger_has_authorize_button(client):
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    # /auth/token доступна без токена
    assert "security" not in spec["paths"]["/api/v1/auth/token"]["post"]
