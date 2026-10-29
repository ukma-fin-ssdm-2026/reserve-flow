"""Модульні тести security.py — паролі (bcrypt) і JWT за ADR-003.

Модульні: функції викликаються напряму, без сервера, HTTP і БД.
Залежності від оточення (JWT_SECRET, строк дії) задаються фікстурами через
monkeypatch; внутрішні виклики перевіряються моками (unittest.mock).
Кожен тест — за шаблоном AAA (Arrange – Act – Assert).
"""

import secrets
import time
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
import pytest

import security
from security import (
    BCRYPT_MAX_BYTES,
    JWT_ALGORITHM,
    JWT_ISSUER,
    InvalidToken,
    access_token_ttl,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)

pytestmark = pytest.mark.req("FR-001", "SEC-001")

USER_ID = "11111111-1111-4111-8111-111111111111"
GOOD = "correct horse battery staple"


# --- Фікстури ------------------------------------------------------------------


@pytest.fixture
def jwt_key(monkeypatch) -> str:
    """Свій випадковий секрет на кожен тест: тести не залежать один від одного й від .env."""
    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("JWT_SECRET", key)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    return key


@pytest.fixture(scope="module")
def stored_hash() -> str:
    """bcrypt навмисно повільний (~0,25 с), тому хеш рахуємо один раз на модуль."""
    return hash_password(GOOD)


def _encode(payload: dict, key: str, algorithm: str = JWT_ALGORITHM) -> str:
    return jwt.encode(payload, key, algorithm=algorithm)


def _valid_payload(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": USER_ID,
        "role": "Client",
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return payload


# --- hash_password -------------------------------------------------------------


def test_hash_password_returns_bcrypt_hash_not_plaintext():
    # Act
    result = hash_password(GOOD)

    # Assert
    assert result.startswith("$2b$12$")  # bcrypt, cost 12 (SEC-001)
    assert GOOD not in result


def test_hash_password_uses_random_salt():
    # Act
    first, second = hash_password(GOOD), hash_password(GOOD)

    # Assert: однаковий пароль -> різні хеші (за хешем не видно однакових паролів)
    assert first != second


@pytest.mark.parametrize(
    "too_long",
    [
        pytest.param("a" * (BCRYPT_MAX_BYTES + 1), id="73-ascii-bytes"),
        pytest.param("ї" * 37, id="74-bytes-cyrillic-37-chars"),
    ],
)
def test_hash_password_rejects_more_than_72_bytes(too_long):
    # Act / Assert
    with pytest.raises(ValueError, match="72"):
        hash_password(too_long)


# --- verify_password -----------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        pytest.param(GOOD, True, id="correct"),
        pytest.param("wrong", False, id="wrong"),
        pytest.param(GOOD.upper(), False, id="case-sensitive"),
        pytest.param(GOOD + " ", False, id="trailing-space"),
        pytest.param("", False, id="empty"),
        # bcrypt 5 падає на > 72 байтах; має бути False, а не виняток (інакше 500)
        pytest.param("ї" * 60, False, id="over-72-bytes"),
    ],
)
def test_verify_password(stored_hash, candidate, expected):
    # Act
    result = verify_password(candidate, stored_hash)

    # Assert
    assert result is expected


def test_verify_password_accepts_exactly_72_bytes():
    # Arrange: межа bcrypt — рівно 72 байти ще дозволені
    boundary = "a" * BCRYPT_MAX_BYTES
    stored = hash_password(boundary)

    # Act / Assert
    assert verify_password(boundary, stored) is True


@pytest.mark.parametrize(
    "unusable_hash",
    [
        pytest.param("!no-login", id="seed-without-password"),
        pytest.param("", id="empty"),
        pytest.param(GOOD, id="plaintext-in-db"),
    ],
)
def test_verify_password_returns_false_for_unusable_hash(unusable_hash):
    # Act: не виняток, а False — користувач без пароля просто не може увійти
    result = verify_password(GOOD, unusable_hash)

    # Assert
    assert result is False


# --- verify_dummy_password (захист від перебору email за часом відповіді) ------------


def test_verify_dummy_password_runs_real_bcrypt_check():
    # Arrange: мок замість справжньої перевірки
    with mock.patch.object(security, "verify_password", return_value=False) as fake_verify:
        # Act
        verify_dummy_password("any-input")

    # Assert: викликано рівно один раз зі справжнім bcrypt-хешем
    fake_verify.assert_called_once()
    candidate, dummy = fake_verify.call_args.args
    assert candidate == "any-input"
    assert dummy.startswith("$2b$")


def test_dummy_hash_is_computed_once():
    # Arrange
    security._dummy_hash.cache_clear()
    with mock.patch.object(
        security._password_hash, "hash", wraps=security._password_hash.hash
    ) as spy:
        # Act
        verify_dummy_password("first")
        verify_dummy_password("second")

    # Assert: другий виклик не хешує заново (lru_cache)
    assert spy.call_count == 1


# --- access_token_ttl ----------------------------------------------------------


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, timedelta(minutes=30), id="default-30"),
        pytest.param("15", timedelta(minutes=15), id="adr-lower-bound"),
        pytest.param("60", timedelta(minutes=60), id="custom"),
    ],
)
def test_access_token_ttl(monkeypatch, env_value, expected):
    # Arrange
    if env_value is None:
        monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    else:
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", env_value)

    # Act / Assert
    assert access_token_ttl() == expected


# --- секрет JWT ----------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_key",
    [
        pytest.param(None, id="missing"),
        pytest.param("", id="empty"),
        pytest.param("x" * 31, id="31-chars-too-short"),
    ],
)
def test_token_functions_refuse_missing_or_short_secret(monkeypatch, bad_key):
    # Arrange
    if bad_key is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", bad_key)

    # Act / Assert: ні видати, ні перевірити токен без надійного секрету не можна
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_access_token(USER_ID, "Client")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        decode_access_token("any.token.value")


def test_secret_of_exactly_32_chars_is_accepted(monkeypatch):
    # Arrange
    monkeypatch.setenv("JWT_SECRET", "x" * 32)

    # Act
    token = create_access_token(USER_ID, "Client")

    # Assert
    assert decode_access_token(token)["sub"] == USER_ID


# --- create_access_token / decode_access_token ----------------------------------


def test_create_and_decode_roundtrip(jwt_key):
    # Act
    claims = decode_access_token(create_access_token(USER_ID, "Provider"))

    # Assert
    assert claims["sub"] == USER_ID
    assert claims["role"] == "Provider"
    assert claims["iss"] == JWT_ISSUER


def test_token_lifetime_matches_ttl(jwt_key, monkeypatch):
    # Arrange
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")

    # Act
    claims = decode_access_token(create_access_token(USER_ID, "Client"))

    # Assert
    assert claims["exp"] - claims["iat"] == 15 * 60


def test_token_is_signed_with_hs256(jwt_key):
    # Act
    header = jwt.get_unverified_header(create_access_token(USER_ID, "Client"))

    # Assert
    assert header["alg"] == "HS256"


def test_expired_token_rejected(jwt_key, monkeypatch):
    # Arrange: строк дії -1 хв — токен прострочений одразу після видачі
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "-1")
    token = create_access_token(USER_ID, "Client")

    # Act / Assert
    with pytest.raises(InvalidToken, match="expired"):
        decode_access_token(token)


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda key: _encode(_valid_payload(), "y" * 48), id="wrong-secret"),
        pytest.param(lambda key: _encode(_valid_payload(iss="evil"), key), id="wrong-issuer"),
        pytest.param(lambda key: _encode(_valid_payload(), key, "HS512"), id="other-algorithm"),
        pytest.param(
            lambda key: jwt.encode(_valid_payload(role="Admin"), None, algorithm="none"),
            id="alg-none-unsigned",
        ),
        pytest.param(lambda key: "not-a-jwt", id="garbage"),
        pytest.param(lambda key: "mock-client-token", id="old-lab4-stub"),
    ],
)
def test_decode_rejects_invalid_tokens(jwt_key, make_token):
    # Arrange
    token = make_token(jwt_key)

    # Act / Assert
    with pytest.raises(InvalidToken):
        decode_access_token(token)


@pytest.mark.parametrize("missing_claim", ["sub", "role", "iss", "iat", "exp"])
def test_decode_requires_every_claim(jwt_key, missing_claim):
    # Arrange: правильно підписаний токен, але без одного обов'язкового поля
    payload = _valid_payload()
    del payload[missing_claim]
    token = _encode(payload, jwt_key)

    # Act / Assert
    with pytest.raises(InvalidToken):
        decode_access_token(token)


def test_tampered_payload_rejected(jwt_key):
    # Arrange: підміняємо payload чужого токена на інший, з role=Admin, лишаючи підпис
    header, _, signature = create_access_token(USER_ID, "Client").split(".")
    _, forged_payload, _ = _encode(_valid_payload(role="Admin"), "z" * 48).split(".")
    tampered = f"{header}.{forged_payload}.{signature}"

    # Act / Assert: клієнт не може підвищити собі роль (Elevation of Privilege, ADR-003)
    with pytest.raises(InvalidToken):
        decode_access_token(tampered)


# Використання ШІ: тести підготовлено з допомогою ШІ Claude, перевірено учасниками команди.


# --- Регресійний тест: час у токені — завжди UTC (налагодження «Зламай, потім відлагодь») ---


@pytest.fixture
def kyiv_local_time(monkeypatch):
    """Локальний час процесу — Київ (UTC+2/+3), як на ноутбуках команди; після тесту — як було."""
    monkeypatch.setenv("TZ", "Europe/Kyiv")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="time.tzset є лише в Unix/macOS")
def test_token_times_are_utc_regardless_of_server_timezone(jwt_key, kyiv_local_time):
    # Arrange
    now_utc = int(time.time())  # Unix-час не залежить від часового поясу

    # Act
    token = create_access_token(USER_ID, "Client")
    claims = jwt.decode(token, options={"verify_signature": False})

    # Assert: iat — «зараз» в UTC, а не місцевий час, записаний як UTC (+3 год)
    assert abs(claims["iat"] - now_utc) <= 5
    assert decode_access_token(token)["sub"] == USER_ID  # не «token is not yet valid (iat)»
