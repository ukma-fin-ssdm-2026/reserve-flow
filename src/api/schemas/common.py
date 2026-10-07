"""Спільні схеми: пагінація (рішення D-05)."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class PaginationParams(BaseModel):
    """Параметри пагінації із запиту."""

    limit: int = Field(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(0, ge=0)


def pagination_params(
    limit: int = Query(
        DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Скільки елементів повернути (1–100)"
    ),
    offset: int = Query(0, ge=0, description="Скільки елементів пропустити від початку"),
) -> PaginationParams:
    """Залежність для списків: `params: PaginationParams = Depends(pagination_params)`."""
    return PaginationParams(limit=limit, offset=offset)


class PaginationInfo(BaseModel):
    """Метадані сторінки."""

    limit: int = Field(..., ge=1, le=MAX_LIMIT, description="Розмір сторінки", examples=[20])
    offset: int = Field(..., ge=0, description="Скільки елементів пропущено", examples=[0])
    total: int = Field(..., ge=0, description="Загальна кількість елементів", examples=[57])
    has_more: bool = Field(..., description="Чи є наступна сторінка", examples=[True])


class Page(BaseModel, Generic[T]):
    """Однаковий конверт для всіх списків: `response_model=Page[SlotOut]`."""

    items: list[T] = Field(..., description="Елементи поточної сторінки")
    pagination: PaginationInfo


def paginate(items: list[T], params: PaginationParams) -> Page[T]:
    """Ріже вже відсортований список на сторінку."""
    page_items = items[params.offset : params.offset + params.limit]
    return Page[T](
        items=page_items,
        pagination=PaginationInfo(
            limit=params.limit,
            offset=params.offset,
            total=len(items),
            has_more=params.offset + params.limit < len(items),
        ),
    )


    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude. 
    # Код вичитано, відредаговано та затверджено учасниками команди