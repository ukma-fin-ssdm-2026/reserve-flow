"""Межа строку дії JWT з фіксованим часом (L6-10, #257).

Годинник підмінено детерміновано (без sleep): одна фікстура `clock` керує і часом
видачі токена (security.create_access_token), і часом перевірки (PyJWT).
За RFC 7519 §4.1.4 токен дійсний лише ДО моменту exp: рівно в exp він уже прострочений.
"""

from datetime import datetime, timedelta, timezone

import jwt
import jwt.api_jwt
import pytest

import security
from security import InvalidToken, create_access_token, decode_access_token

USER_ID = "11111111-1111-4111-8111-111111111111"
START = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    """datetime, у якого now() повертає час керованого годинника."""

    current = START

    @classmethod
    def now(cls, tz=None):
        moment = cls.current
        return moment if tz is None else moment.astimezone(tz)


@pytest.fixture
def clock(monkeypatch):
    """Заморожений годинник: clock(seconds=…) переводить час уперед."""
    _FrozenDatetime.current = _FrozenDatetime.fromtimestamp(START.timestamp(), timezone.utc)
    monkeypatch.setattr(security, "datetime", _FrozenDatetime)
    monkeypatch.setattr(jwt.api_jwt, "datetime", _FrozenDatetime)

    def advance(**delta):
        _FrozenDatetime.current = _FrozenDatetime.current + timedelta(**delta)

    return advance


@pytest.fixture(params=[15, 30, 60], ids=lambda m: f"ttl-{m}min")
def ttl_minutes(request, monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(request.param))
    return request.param


def test_token_times_come_from_the_clock(clock, ttl_minutes):
    # Act
    claims = jwt.decode(create_access_token(USER_ID, "Client"), options={"verify_signature": False})

    # Assert: iat — момент видачі, exp — рівно через TTL
    assert claims["iat"] == int(START.timestamp())
    assert claims["exp"] - claims["iat"] == ttl_minutes * 60


def test_token_valid_one_second_before_expiry(clock, ttl_minutes):
    # Arrange
    token = create_access_token(USER_ID, "Client")
    clock(minutes=ttl_minutes, seconds=-1)

    # Act
    claims = decode_access_token(token)

    # Assert
    assert claims["sub"] == USER_ID


def test_token_rejected_exactly_at_expiry(clock, ttl_minutes):
    # Arrange: рівно в момент exp — токен уже недійсний (RFC 7519 §4.1.4)
    token = create_access_token(USER_ID, "Client")
    clock(minutes=ttl_minutes)

    # Act / Assert
    with pytest.raises(InvalidToken, match="expired"):
        decode_access_token(token)


def test_token_rejected_one_second_after_expiry(clock, ttl_minutes):
    # Arrange
    token = create_access_token(USER_ID, "Client")
    clock(minutes=ttl_minutes, seconds=1)

    # Act / Assert
    with pytest.raises(InvalidToken, match="expired"):
        decode_access_token(token)
