"""Отримання тестового токена (заглушка JWT, рішення D-06).

Єдина кінцева точка, доступна без токена (default deny, Лекція 5).
"""

from fastapi import APIRouter, HTTPException, status

from config import API_PREFIX
from deps import CurrentUser, authenticate
from errors import error_responses
from schemas.auth import TokenOut, TokenRequest, UserOut

router = APIRouter(prefix=f"{API_PREFIX}/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenOut,
    summary="Отримати тестовий токен",
    description=(
        "Lab 4: заглушка замість справжнього JWT. Повертає фіксований токен "
        "тестового користувача, який далі передається в заголовку "
        "`Authorization: Bearer <токен>` (кнопка **Authorize** у Swagger UI).\n\n"
        "| email | Роль | Токен |\n"
        "|---|---|---|\n"
        "| `client@ukma.edu.ua` | Client | `mock-client-token` |\n"
        "| `provider@ukma.edu.ua` | Provider | `mock-provider-token` |\n"
        "| `admin@ukma.edu.ua` | Admin | `mock-admin-token` |\n\n"
        "Пароль для всіх: `lab4-demo`. Невірні email або пароль → `401`."
    ),
    responses=error_responses(401, 422),
)
async def issue_token(credentials: TokenRequest) -> TokenOut:
    result = authenticate(credentials.email, credentials.password)
    if result is None:
        # Одне повідомлення для невірного email і пароля: не підказуємо, що саме не так.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
        )
    token, user = result
    return TokenOut(access_token=token, user=user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Хто я",
    description="Повертає користувача, якому належить токен. Зручно перевірити, чи працює **Authorize**.",
    responses=error_responses(401),
)
async def read_me(current_user: CurrentUser) -> UserOut:
    return current_user
