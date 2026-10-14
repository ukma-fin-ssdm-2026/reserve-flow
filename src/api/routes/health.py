"""Службова кінцева точка: перевірка, що API працює.

Також слугує зразком оформлення для інших роутерів: prefix з API_PREFIX,
tags, summary, description, response_model, responses з error_responses().
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import API_PREFIX, API_VERSION
from errors import error_responses

router = APIRouter(prefix=API_PREFIX, tags=["system"])


class HealthOut(BaseModel):
    """Стан API."""

    status: str = Field(..., description="Стан сервісу", examples=["ok"])
    version: str = Field(..., description="Версія API (документа OpenAPI)", examples=["1.0.0"])


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Перевірити стан API",
    description="Повертає `ok`, якщо сервер запущено. Не потребує автентифікації.",
    responses=error_responses(500),
)
async def get_health() -> HealthOut:
    return HealthOut(status="ok", version=API_VERSION)

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
