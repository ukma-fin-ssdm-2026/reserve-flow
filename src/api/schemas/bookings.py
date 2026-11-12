"""Схеми для ресурсу бронювань."""

from datetime import datetime, timezone
from enum import Enum
from typing import Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class BookingStatus(str, Enum):
    """Статуси бронювання (D-03)."""

    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"


class BookingCreate(BaseModel):
    """Модель створення нового бронювання."""

    model_config = ConfigDict(str_strip_whitespace=True)

    slot_id: UUID = Field(
        ...,
        description="Унікальний ідентифікатор слоту, який бронюється",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    purpose: str = Field(
        ...,
        description="Мета бронювання приміщення",
        examples=["Зустріч студентського самоврядування"],
        min_length=1,
        max_length=200,
    )

    @field_validator("purpose", mode="before")
    @classmethod
    def trim_purpose(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class BookingUpdate(BaseModel):
    """Модель оновлення бронювання (переходи статусів)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: BookingStatus = Field(
        ...,
        description="Новий статус бронювання. Дозволені переходи — в описі PATCH (D-03).",
        examples=["Rejected"],
    )
    reason: str | None = Field(
        None,
        max_length=500,
        description=(
            "Причина. Обов'язкова при відхиленні (`Rejected`, FR-010); "
            "при скасуванні (`Cancelled`) — за бажанням."
        ),
        examples=["Аудиторія на ремонті"],
    )

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def check_reason_for_rejection(self) -> Self:
        """Відхилення без причини -> 422 VALIDATION_ERROR (FR-010)."""
        if self.status == BookingStatus.REJECTED and not (self.reason and self.reason.strip()):
            raise ValueError("Поле 'reason' є обов'язковим при відхиленні бронювання")
        return self


class BookingOut(BaseModel):
    """Модель віддачі даних про бронювання."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Унікальний ідентифікатор бронювання",
        examples=["987fcdeb-51a2-43d7-9012-3456789abcde"],
    )
    slot_id: UUID = Field(
        ...,
        description="Унікальний ідентифікатор заброньованого слоту",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    user_id: UUID = Field(
        ...,
        description="Ідентифікатор користувача, який створив бронювання",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: BookingStatus = Field(
        ...,
        description="Поточний статус",
        examples=["Pending"],
    )
    purpose: str = Field(
        ...,
        description="Мета бронювання",
        examples=["Зустріч студентського самоврядування"],
    )
    reason: str | None = Field(
        None,
        description="Причина відхилення (`Rejected`) або скасування (`Cancelled`)",
        examples=["Змінився розклад пар"],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Час створення запису",
        examples=["2025-10-24T14:30:00Z"],
    )
