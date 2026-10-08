"""Схеми для заглушки автентифікації (рішення D-06)."""

from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    """Ролі користувачів (docs/architecture/data-model.md, User.role)."""

    CLIENT = "Client"
    PROVIDER = "Provider"
    ADMIN = "Admin"


class TokenRequest(BaseModel):
    """Облікові дані тестового користувача."""

    email: EmailStr = Field(
        ...,
        description="Email тестового користувача",
        examples=["client@ukma.edu.ua"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Пароль тестового користувача (лише для Lab 4, не секрет)",
        examples=["lab4-demo"],
    )


class UserOut(BaseModel):
    """Публічні дані поточного користувача."""

    id: str = Field(..., description="ID користувача", examples=["11111111-1111-4111-8111-111111111111"])
    email: EmailStr = Field(..., description="Email", examples=["client@ukma.edu.ua"])
    full_name: str = Field(..., description="Ім'я", examples=["Тестовий Клієнт"])
    role: Role = Field(..., description="Роль", examples=["Client"])


class TokenOut(BaseModel):
    """Відповідь з токеном доступу."""

    access_token: str = Field(
        ...,
        description="Токен для заголовка `Authorization: Bearer <токен>`",
        examples=["mock-client-token"],
    )
    token_type: str = Field("bearer", description="Тип токена", examples=["bearer"])
    expires_in: int = Field(
        3600,
        description="Час життя токена в секундах (у заглушці не перевіряється)",
        examples=[3600],
    )
    user: UserOut
