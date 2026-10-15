"""Схеми автентифікації (ADR-003, L5-12)."""

from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    """Ролі користувачів (docs/architecture/data-model.md, User.role)."""

    CLIENT = "Client"
    PROVIDER = "Provider"
    ADMIN = "Admin"


class TokenRequest(BaseModel):
    """Облікові дані користувача."""

    email: EmailStr = Field(
        ...,
        description="Email користувача",
        examples=["client@ukma.edu.ua"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Пароль",
        examples=["your-password"],
    )


class UserOut(BaseModel):
    """Публічні дані поточного користувача."""

    id: str = Field(
        ..., description="ID користувача", examples=["11111111-1111-4111-8111-111111111111"]
    )
    email: EmailStr = Field(..., description="Email", examples=["client@ukma.edu.ua"])
    full_name: str = Field(..., description="Ім'я", examples=["Тестовий Клієнт"])
    role: Role = Field(..., description="Роль", examples=["Client"])


class TokenOut(BaseModel):
    """Відповідь з токеном доступу."""

    access_token: str = Field(
        ...,
        description="JWT для заголовка `Authorization: Bearer <токен>`",
        examples=["<header>.<payload>.<signature>"],
    )
    token_type: str = Field("bearer", description="Тип токена", examples=["bearer"])
    expires_in: int = Field(
        1800,
        description="Час життя токена в секундах (ACCESS_TOKEN_EXPIRE_MINUTES)",
        examples=[1800],
    )
    user: UserOut
