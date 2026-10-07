import uuid
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = Field(None, description="Поле запиту з помилкою", examples=["end"])
    issue: str = Field(..., description="Що саме не так", examples=["Час закінчення має бути пізніше за час початку"])


class ErrorBody(BaseModel):
    code: str = Field(..., description="Фіксований код помилки", examples=["SLOT_UNAVAILABLE"])
    message: str = Field(..., description="Зрозуміле повідомлення про помилку", examples=["Обраний час уже зайнято"])
    details: list[ErrorDetail] = Field(default_factory=list, description="Список деталей помилки")
    correlation_id: str = Field(..., description="Унікальний ідентифікатор запиту для трасування")


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Базовий виняток для доменних помилок застосунку."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "APP_ERROR",
        details: list[ErrorDetail] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or []
        super().__init__(message)


def get_correlation_id(request: Request) -> str:
    """Отримує correlation_id зі стану запиту або ґенерує новий."""
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = get_correlation_id(request)
    body = ErrorBody(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=body).model_dump())


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    correlation_id = get_correlation_id(request)
    details: list[ErrorDetail] = []
    
    for err in exc.errors():
        loc = err.get("loc", [])
        field_name = " -> ".join(str(l) for l in loc if l != "body") if loc else None
        issue_msg = err.get("msg", "Некоректне значення")
        details.append(ErrorDetail(field=field_name, issue=issue_msg))

    body = ErrorBody(
        code="VALIDATION_ERROR",
        message="Помилка валідації вхідних даних",
        details=details,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error=body).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    correlation_id = get_correlation_id(request)
    
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    msg = str(exc.detail) if isinstance(exc.detail, str) else "Помилка обробки запиту"

    body = ErrorBody(
        code=code,
        message=msg,
        details=[],
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=body).model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = get_correlation_id(request)
    body = ErrorBody(
        code="INTERNAL_ERROR",
        message="Внутрішня помилка сервера",
        details=[],
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error=body).model_dump(),
    )

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini. 
    # Код вичитано, відредаговано та затверджено учасниками команди