"""Автентифікація: видача JWT за email і паролем (ADR-003, L5-12).

Єдина кінцева точка, доступна без токена (default deny, Лекція 5).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from config import API_PREFIX
from db import get_session
from deps import CurrentUser, to_user_out
from errors import error_responses
from models import User
from schemas.auth import TokenOut, TokenRequest, UserOut
from security import (
    access_token_ttl,
    create_access_token,
    verify_dummy_password,
    verify_password,
)

router = APIRouter(prefix=f"{API_PREFIX}/auth", tags=["auth"])

_INVALID_CREDENTIALS = "Невірний email або пароль"


@router.post(
    "/token",
    response_model=TokenOut,
    summary="Отримати токен доступу",
    description=(
        "Перевіряє email і пароль (bcrypt-хеш у БД) і повертає JWT, який далі "
        "передається в заголовку `Authorization: Bearer <токен>` "
        "(кнопка **Authorize** у Swagger UI).\n\n"
        "Токен підписано секретом сервера (HS256), у ньому — id і роль користувача; "
        "строк дії — `expires_in` секунд.\n\n"
        "Тестові користувачі після `python src/api/seed.py`: `client@ukma.edu.ua`, "
        "`provider@ukma.edu.ua`, `admin@ukma.edu.ua`; пароль — значення "
        "`SEED_USER_PASSWORD` з вашого `.env`.\n\n"
        "Невірні email або пароль → `401`; заблокований користувач → `403`."
    ),
    responses=error_responses(401, 403, 422),
)
def issue_token(
    credentials: TokenRequest,
    session: Annotated[Session, Depends(get_session)],
) -> TokenOut:
    user = session.exec(
        select(User).where(func.lower(User.email) == credentials.email.lower())
    ).first()

    if user is None:
        verify_dummy_password(credentials.password)  # однаковий час відповіді
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)
    if not verify_password(credentials.password, user.password_hash):
        # Одне повідомлення для невірного email і пароля: не підказуємо, що саме не так.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)
    if user.is_blocked:
        # Лише після перевірки пароля: інакше 403 видавав би, що такий email існує.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Обліковий запис заблоковано")

    return TokenOut(
        access_token=create_access_token(str(user.id), user.role.value),
        expires_in=int(access_token_ttl().total_seconds()),
        user=to_user_out(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Хто я",
    description="Повертає користувача, якому належить токен. "
    "Зручно перевірити, чи працює **Authorize**.",
    responses=error_responses(401),
)
async def read_me(current_user: CurrentUser) -> UserOut:
    return current_user
