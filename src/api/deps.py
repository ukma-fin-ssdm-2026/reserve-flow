"""Залежності автентифікації й авторизації (рішення D-06).

Lab 4: справжнього JWT ще немає, токени — фіксовані рядки-заглушки.
У наступних лабораторних get_current_user перевірятиме підпис JWT (PyJWT, ADR-003),
але сигнатура лишиться та сама, тож роутери не зміняться.

Використання в роутері:
    current_user: Annotated[UserOut, Depends(get_current_user)]
    _: Annotated[UserOut, Depends(require_role(Role.PROVIDER))]
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mocks import USER_ADMIN_ID, USER_CLIENT_ID, USER_PROVIDER_ID
from schemas.auth import Role, UserOut

# auto_error=False: відсутній заголовок обробляємо самі, щоб віддати 401 у форматі ErrorResponse.
# Саме HTTPBearer додає кнопку Authorize у Swagger UI.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Тестовий токен з `POST /api/v1/auth/token`, напр. `mock-client-token`",
)

# Тестовий пароль для всіх користувачів-заглушок. Це НЕ секрет: справжніх
# облікових записів у Lab 4 немає. Справжні ключі в репозиторій не комітимо.
# bandit B105 — ризик свідомо прийнято (див. docs/code-quality/static-analysis.md):
# це спільний пароль заглушки D-06, не секрет; зникне разом із заглушкою (L5-12, #205).
MOCK_PASSWORD = "lab4-demo"  # nosec B105

# Токен -> користувач. id збігаються з mocks.py, щоб перевірки "свій / чужий ресурс" працювали.
MOCK_USERS: dict[str, UserOut] = {
    "mock-client-token": UserOut(
        id=USER_CLIENT_ID,
        email="client@ukma.edu.ua",
        full_name="Тестовий Клієнт",
        role=Role.CLIENT,
    ),
    "mock-provider-token": UserOut(
        id=USER_PROVIDER_ID,
        email="provider@ukma.edu.ua",
        full_name="Тестовий Постачальник",
        role=Role.PROVIDER,
    ),
    "mock-admin-token": UserOut(
        id=USER_ADMIN_ID,
        email="admin@ukma.edu.ua",
        full_name="Тестовий Адміністратор",
        role=Role.ADMIN,
    ),
}

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def authenticate(email: str, password: str) -> tuple[str, UserOut] | None:
    """Шукає тестового користувача за email і паролем; None, якщо дані невірні."""
    if password != MOCK_PASSWORD:
        return None
    for token, user in MOCK_USERS.items():
        if user.email.lower() == email.lower():
            return token, user
    return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserOut:
    """Повертає користувача за токеном або 401 UNAUTHORIZED."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Потрібна автентифікація: додайте заголовок Authorization: Bearer <токен>",
            headers=_UNAUTHORIZED_HEADERS,
        )

    user = MOCK_USERS.get(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або застарілий токен",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return user


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
