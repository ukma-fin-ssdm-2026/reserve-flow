"""Залежності автентифікації й авторизації (ADR-003, L5-12, #205).

Замість заглушки D-06 (фіксовані токени) — JWT, підписаний секретом із JWT_SECRET.
Сигнатура для роутерів не змінилася:
    current_user: Annotated[UserOut, Depends(get_current_user)]
    _: Annotated[UserOut, Depends(require_role(Role.PROVIDER))]
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from db import get_session
from models import User
from schemas.auth import Role, UserOut
from security import InvalidToken, decode_access_token

# auto_error=False: відсутній заголовок обробляємо самі, щоб віддати 401 у форматі ErrorResponse.
# Саме HTTPBearer додає кнопку Authorize у Swagger UI.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT з `POST /api/v1/auth/token` (поле `access_token`)",
)

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_UNAUTHORIZED_HEADERS,
    )


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=Role(user.role.value),
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> UserOut:
    """Повертає користувача за JWT або 401 UNAUTHORIZED.

    Підпис і строк дії перевіряє PyJWT. Додатково (контрзахід з ADR-003) користувача
    читаємо з БД за id: заблокований, видалений або зі зміненою роллю користувач
    втрачає доступ одразу, а не після закінчення строку дії токена.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized(
            "Потрібна автентифікація: додайте заголовок Authorization: Bearer <токен>"
        )

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (InvalidToken, ValueError):
        raise _unauthorized("Недійсний або застарілий токен") from None

    user = session.get(User, user_id)
    if user is None or user.is_blocked or user.role.value != claims["role"]:
        raise _unauthorized("Недійсний або застарілий токен")
    return to_user_out(user)


def require_role(*roles: Role) -> Callable[..., UserOut]:
    """Залежність: пропускає лише користувачів з однією з ролей, інакше 403 FORBIDDEN.

    Приклад:
        @router.patch("/{slot_id}", dependencies=[Depends(require_role(Role.PROVIDER))])
    """

    async def _check_role(
        user: Annotated[UserOut, Depends(get_current_user)],
    ) -> UserOut:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостатньо прав для цієї дії",
            )
        return user

    return _check_role


# Короткі псевдоніми для анотацій у роутерах.
CurrentUser = Annotated[UserOut, Depends(get_current_user)]


# Використання ШІ: при написанні коду використано допомогу ШІ Claude.
# Код перевірено учасниками команди.
