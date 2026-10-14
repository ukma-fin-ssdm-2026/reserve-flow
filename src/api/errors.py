import logging
import uuid
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("reserve_flow.api")


class ErrorCode(str, Enum):
    """Фіксований перелік кодів помилок API."""

    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    SLOT_UNAVAILABLE = "SLOT_UNAVAILABLE"
    CANCELLATION_TOO_LATE = "CANCELLATION_TOO_LATE"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    ACTIVE_BOOKING_NEEDS_CONFIRMATION = "ACTIVE_BOOKING_NEEDS_CONFIRMATION"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    """Одна конкретна проблема у запиті."""

    field: str | None = Field(
        None,
        description="Поле запиту, у якому помилка (для помилок валідації)",
        examples=["end"],
    )
    issue: str = Field(
        ...,
        description="Що саме не так",
        examples=["Час закінчення має бути пізніше за час початку"],
    )


class ErrorBody(BaseModel):
    """Тіло помилки."""

    code: ErrorCode = Field(..., description="Машинозчитуваний код помилки")
    message: str = Field(
        ...,
        description="Повідомлення для користувача, без внутрішніх деталей",
        examples=["Обраний час уже зайнято"],
    )
    details: list[ErrorDetail] = Field(
        default_factory=list, description="Деталі, зокрема список некоректних полів"
    )
    correlation_id: str = Field(
        ...,
        description="Ідентифікатор для звернення в підтримку; той самий записано в лог",
        examples=["6f1c2a3e-8b7d-4e0a-9f21-3c4d5e6f7a8b"],
    )


class ErrorResponse(BaseModel):
    """Єдиний формат відповіді з помилкою."""

    error: ErrorBody


class AppError(Exception):
    """Помилка бізнес-логіки, яку роутери кидають замість HTTPException.

    Приклад:
        raise AppError(409, ErrorCode.SLOT_UNAVAILABLE, "Обраний час уже зайнято")
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


# Стандартні повідомлення для кодів статусу, які не прийшли з AppError.
_DEFAULT_ERRORS: dict[int, tuple[ErrorCode, str]] = {
    status.HTTP_401_UNAUTHORIZED: (ErrorCode.UNAUTHORIZED, "Потрібна автентифікація"),
    status.HTTP_403_FORBIDDEN: (ErrorCode.FORBIDDEN, "Недостатньо прав"),
    status.HTTP_404_NOT_FOUND: (ErrorCode.NOT_FOUND, "Ресурс не знайдено"),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        ErrorCode.METHOD_NOT_ALLOWED,
        "Метод не підтримується для цього ресурсу",
    ),
}

# Описи для розділу responses в анотаціях кінцевих точок.
_RESPONSE_DESCRIPTIONS: dict[int, str] = {
    400: "Некоректний запит",
    401: "Немає токена або токен недійсний",
    403: "Недостатньо прав або ресурс належить іншому користувачу",
    404: "Ресурс не знайдено",
    409: "Конфлікт стану ресурсу",
    422: "Помилка валідації вхідних даних",
    500: "Внутрішня помилка сервера",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Повертає блок responses для декоратора кінцевої точки.

    Так кожна точка документує свої помилки у форматі ErrorResponse, а 422
    замінює стандартну схему FastAPI (HTTPValidationError).

    Приклад:
        @router.post("", responses=error_responses(401, 404, 409, 422))
    """
    return {
        code: {"model": ErrorResponse, "description": _RESPONSE_DESCRIPTIONS.get(code, "Помилка")}
        for code in status_codes
    }


def _get_correlation_id(request: Request) -> str:
    """Отримує correlation_id зі стану запиту або ґенерує новий, якщо той відсутній."""
    return getattr(request.state, "correlation_id", None) or str(uuid.uuid4())


def _error_json(
    status_code: int,
    code: ErrorCode,
    message: str,
    correlation_id: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or [],
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = _get_correlation_id(request)
    response = _error_json(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=correlation_id,
        details=exc.details,
    )
    logger.info(
        "AppError %s %s [%s] %s -> %s",
        request.method,
        request.url.path,
        correlation_id,
        exc.code.value,
        response.status_code,
    )
    return response


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    correlation_id = _get_correlation_id(request)
    code, default_message = _DEFAULT_ERRORS.get(
        exc.status_code, (ErrorCode.INTERNAL_ERROR, "Помилка обробки запиту")
    )
    message = (
        exc.detail if isinstance(exc.detail, str) and exc.status_code != 404 else default_message
    )
    return _error_json(
        status_code=exc.status_code,
        code=code,
        message=message,
        correlation_id=correlation_id,
        headers=getattr(exc, "headers", None),
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    correlation_id = _get_correlation_id(request)
    details = [
        ErrorDetail(
            # loc виглядає як ("query", "limit") або ("body", "slot_id")
            field=".".join(str(part) for part in err.get("loc", ())[1:]) or None,
            issue=err.get("msg", "Некоректне значення"),
        )
        for err in exc.errors()
    ]
    return _error_json(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ErrorCode.VALIDATION_ERROR,
        message="Некоректні дані запиту",
        correlation_id=correlation_id,
        details=details,
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = _get_correlation_id(request)
    response = _error_json(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="Внутрішня помилка сервера. Повідомте correlation_id у підтримку.",
        correlation_id=correlation_id,
    )
    # Повні деталі — лише в лог разом з correlation_id (Лекція 5, обробка помилок).
    logger.exception(
        "Unhandled error on %s %s [%s]",
        request.method,
        request.url.path,
        correlation_id,
    )
    return response


def register_error_handlers(app: FastAPI) -> None:
    """Підключає всі обробники помилок до застосунку."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
