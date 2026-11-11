"""Лаб 9, №8 (#469): некоректна конфігурація зупиняє старт сервера (fail fast)."""

import asyncio
import logging

import pytest

import main
from config_check import ConfigError, validate_config

pytestmark = pytest.mark.no_req("інфраструктура: перевірка конфігурації на старті (Лаб 9, №8)")

SECRET = "s" * 32
VALID = {"JWT_SECRET": SECRET, "ACCESS_TOKEN_EXPIRE_MINUTES": "30", "DATABASE_URL": "sqlite://"}


def _env(**changes):
    env = {**VALID, **changes}
    return {key: value for key, value in env.items() if value is not None}


def test_valid_config_passes():
    validate_config(VALID)


def test_ttl_defaults_to_30_when_not_set():
    validate_config(_env(ACCESS_TOKEN_EXPIRE_MINUTES=None))


@pytest.mark.parametrize("ttl", ["30m", "", "0", "-5"])
def test_invalid_token_ttl_is_rejected(ttl):
    with pytest.raises(ConfigError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
        validate_config(_env(ACCESS_TOKEN_EXPIRE_MINUTES=ttl))


@pytest.mark.parametrize(
    ("ttl", "valid"),
    [("4", False), ("5", True), ("1440", True), ("1441", False)],
    ids=["below-min", "min", "max", "above-max"],
)
def test_token_ttl_boundaries(ttl, valid):
    env = _env(ACCESS_TOKEN_EXPIRE_MINUTES=ttl)
    if valid:
        validate_config(env)
    else:
        with pytest.raises(ConfigError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
            validate_config(env)


@pytest.mark.parametrize("secret", [None, "", "s" * 31], ids=["missing", "empty", "too-short"])
def test_weak_jwt_secret_is_rejected(secret):
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        validate_config(_env(JWT_SECRET=secret))


def test_database_needs_url_or_password():
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        validate_config(_env(DATABASE_URL=None))
    validate_config(_env(DATABASE_URL=None, POSTGRES_PASSWORD="change-me"))


def test_all_problems_reported_at_once_without_secret_values():
    env = {"JWT_SECRET": "short-secret-value", "ACCESS_TOKEN_EXPIRE_MINUTES": "0"}

    with pytest.raises(ConfigError) as exc:
        validate_config(env)

    message = str(exc.value)
    for name in ("JWT_SECRET", "ACCESS_TOKEN_EXPIRE_MINUTES", "DATABASE_URL"):
        assert name in message
    assert "short-secret-value" not in message  # значення секрету не потрапляє в лог


def _start_app():
    async def run():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run())


def test_server_does_not_start_with_invalid_config(monkeypatch, caplog):
    # Ін'єкція збою: строк дії токена «30m» замість числа
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30m")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    with pytest.raises(ConfigError):
        _start_app()

    assert any(
        r.levelno == logging.CRITICAL and "ACCESS_TOKEN_EXPIRE_MINUTES" in r.message
        for r in caplog.records
    )
