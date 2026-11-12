"""Службова кінцева точка: перевірка стану API і бази даних (Лаб 9, №7).

`render.yaml` використовує `/api/v1/health` як `healthCheckPath`: платформа має бачити,
що сервіс не може працювати без БД, а не отримувати «healthy» за будь-яких умов.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from config import API_PREFIX
from db import get_session

logger = logging.getLogger("reserve_flow.health")

router = APIRouter(tags=["System"])


class HealthOut(BaseModel):
    """Стан API і його залежностей — без внутрішніх деталей (хост, текст помилки)."""

    status: Literal["healthy", "unhealthy"] = Field(
        ..., description="Чи може сервіс обслуговувати запити", examples=["healthy"]
    )
    db: Literal["ok", "unavailable"] = Field(
        ..., description="Чи відповідає база даних", examples=["ok"]
    )


@router.get("/health", include_in_schema=False)  # старий шлях, лишається для сумісності
@router.get(
    f"{API_PREFIX}/health",
    response_model=HealthOut,
    summary="Перевірити стан API і БД",
    description=(
        "Виконує `SELECT 1` у БД (з тайм-аутами з `db.py`). `200 healthy`, якщо БД відповіла; "
        "`503 unhealthy`, якщо ні. Не потребує автентифікації."
    ),
    responses={503: {"model": HealthOut, "description": "БД недоступна"}},
)
def health_check(
    response: Response, session: Annotated[Session, Depends(get_session)]
) -> HealthOut:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Лише тип помилки: текст може містити хост або параметри з'єднання
        logger.warning("Health check: БД недоступна (%s)", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthOut(status="unhealthy", db="unavailable")
    return HealthOut(status="healthy", db="ok")


# Використання ШІ: перевірку БД (Лаб 9, #458) підготовано ШІ-агентом Claude Code;
# перевірено учасниками команди.
