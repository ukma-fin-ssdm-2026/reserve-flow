"""Перевірка конфігурації на старті (Лаб 9, знахідка №8, #469).

Швидка відмова (fail fast): якщо змінні оточення некоректні, сервер не стартує
з повідомленням, яку змінну виправити. Інакше він працює «здоровим», а користувачі
отримують 500 на вході або 401 на кожен запит. Значення секретів у повідомлення
не потрапляють — лише назви змінних.
"""

import os
from collections.abc import Mapping

from security import MIN_SECRET_LENGTH

# Межі строку дії access-токена, хв: від 5 хв до доби
TOKEN_TTL_MIN_MINUTES = 5
TOKEN_TTL_MAX_MINUTES = 1440


class ConfigError(RuntimeError):
    """Конфігурація некоректна — сервер не повинен стартувати."""


def _check_jwt_secret(env: Mapping[str, str]) -> str | None:
    if len(env.get("JWT_SECRET", "")) < MIN_SECRET_LENGTH:
        return f"JWT_SECRET не задано або він коротший за {MIN_SECRET_LENGTH} символи"
    return None


def _check_token_ttl(env: Mapping[str, str]) -> str | None:
    raw = env.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    try:
        minutes = int(raw)
    except ValueError:
        return "ACCESS_TOKEN_EXPIRE_MINUTES має бути цілим числом хвилин"
    if not TOKEN_TTL_MIN_MINUTES <= minutes <= TOKEN_TTL_MAX_MINUTES:
        return (
            f"ACCESS_TOKEN_EXPIRE_MINUTES має бути від {TOKEN_TTL_MIN_MINUTES} "
            f"до {TOKEN_TTL_MAX_MINUTES}"
        )
    return None


def _check_database(env: Mapping[str, str]) -> str | None:
    if not env.get("DATABASE_URL") and not env.get("POSTGRES_PASSWORD"):
        return "не задано ні DATABASE_URL, ні POSTGRES_PASSWORD"
    return None


def validate_config(env: Mapping[str, str] | None = None) -> None:
    """Перевіряє всі змінні одразу й кидає ConfigError зі списком усіх порушень."""
    env = os.environ if env is None else env
    problems = [
        problem
        for check in (_check_jwt_secret, _check_token_ttl, _check_database)
        if (problem := check(env))
    ]
    if problems:
        raise ConfigError("Некоректна конфігурація: " + "; ".join(problems))


# Використання ШІ: при написанні коду використано допомогу ШІ Claude.
# Код перевірено учасниками команди.
