"""Схеми для слотів."""
from datetime import datetime
from pydantic import BaseModel, Field

class SlotOut(BaseModel):
    """Схема виводу для часового слота."""
    id: str = Field(..., description="UUID слота")
    room_id: str = Field(..., description="UUID приміщення")
    start_time: datetime = Field(..., description="Початок у форматі ISO 8601 (з часовою зоною)")
    end_time: datetime = Field(..., description="Кінець у форматі ISO 8601 (з часовою зоною)")
    is_available: bool = Field(..., description="Чи доступний слот для бронювання")
    closure_reason: str | None = Field(None, description="Причина закриття слота (якщо is_available=False)")

class SlotPatchIn(BaseModel):
    """Схема для оновлення статусу слота постачальником."""
    is_available: bool = Field(..., description="Новий статус доступності слота")
    closure_reason: str | None = Field(None, max_length=200, description="Причина закриття (обов'язково, якщо слот закривається)")