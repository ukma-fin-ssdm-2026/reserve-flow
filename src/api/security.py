"""Паролі й JWT за ADR-003 (L5-12, #205).

- Паролі зберігаються лише як bcrypt-хеші (pwdlib), SEC-001.
- Access-токен — JWT HS256, підписаний секретом зі змінної JWT_SECRET (не в git).
  У payload: user_id (sub) і role; час життя — ACCESS_TOKEN_EXPIRE_MINUTES (за ADR 15–30 хв).

Модуль не залежить від FastAPI і БД: його використовують deps.py, routes/auth.py,
seed.py, mcp_server.py і тести.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.bcrypt import BcryptHasher

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "reserve-flow"
# HS256: ключ має бути не коротшим за 256 біт (RFC 7518, розд. 3.2)
MIN_SECRET_LENGTH = 32

# bcrypt обробляє не більше 72 байтів пароля; довший bcrypt 5 відхиляє з ValueError
BCRYPT_MAX_BYTES = 72

_password_hash = PasswordHash((BcryptHasher(),))


class InvalidToken(Exception):
    """Підпис, строк дії або вміст токена некоректні (-> 401)."""


def access_token_ttl() -> timedelta:
    return timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))


def _secret() -> str:
    """Секрет читається під час виклику, а не імпорту: застосунок і експорт OpenAPI
    стартують і без нього, але видати чи перевірити токен без секрету не можна."""
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET не задано або він коротший за {MIN_SECRET_LENGTH} символи. "
            'Згенеруйте: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    return secret


def hash_password(password: str) -> str:
    if len(password.encode()) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Пароль довший за {BCRYPT_MAX_BYTES} байти (обмеження bcrypt)")
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """False і для невірного пароля, і для хеша, якого не можна перевірити
    (напр. "!no-login" у користувача без пароля), і для пароля, довшого за 72 байти:
    такий пароль не міг бути збережений, а bcrypt на ньому падає (було б 500)."""
    if len(password.encode()) > BCRYPT_MAX_BYTES:
        return False
    try:
        return _password_hash.verify(password, password_hash)
    except UnknownHashError:
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _password_hash.hash("dummy-password-for-timing")


def verify_dummy_password(password: str) -> None:
    """Перевірка «навхолосту» для неіснуючого email: відповідь займає стільки ж часу,
    скільки для існуючого, тож за часом не можна дізнатися, чи зареєстрований email."""
    verify_password(password, _dummy_hash())


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + access_token_ttl(),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Перевіряє підпис, алгоритм, issuer і строк дії. Будь-яка помилка -> InvalidToken."""
    try:
        return jwt.decode(
            token,
            _secret(),
            algorithms=[JWT_ALGORITHM],  # явно: токени з alg=none чи іншим алгоритмом відхиляються
            issuer=JWT_ISSUER,
            options={"require": ["sub", "role", "iss", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc


# Правила надійності пароля: (код порушення, перевірка, що правило виконано)
_PASSWORD_RULES = (
    ("too_short", lambda p: len(p) >= 8),
    ("no_digit", lambda p: any(ch.isdigit() for ch in p)),
)


def validate_password_strength(password: str) -> list[str]:
    """Повертає коди порушених правил; порожній список — пароль достатньо надійний."""
    return [code for code, is_ok in _PASSWORD_RULES if not is_ok(password)]


# Використання ШІ: при написанні коду використано допомогу ШІ Claude.
# Код перевірено учасниками команди.
