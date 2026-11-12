"""Лаб 9, №14: StarletteHTTPException з кодом 4xx не маркується як INTERNAL_ERROR.

Раніше будь-який `HTTPException` поза 401/403/404/405 (наприклад, 400, 409, 413, 415, 429)
отримував у тілі відповіді `code = "INTERNAL_ERROR"`, через що клієнти та моніторинг
сприймали помилку клієнта (4xx) як збій сервера (5xx). Тепер невідомі 4xx отримують
`BAD_REQUEST`, відомі 401/403/404/405 зберігають свої коди, а `INTERNAL_ERROR` — лише для 5xx.
"""

import json
from types import SimpleNamespace

import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException

from errors import ErrorCode, _default_http_error, _http_exception_handler

pytestmark = pytest.mark.no_req("інфраструктура: класифікація HTTP-помилок 4xx vs 5xx (Лаб 9, №14)")

CORRELATION_ID = "11111111-2222-4333-8444-555555555555"


def _make_request(correlation_id: str | None = CORRELATION_ID):
    state = SimpleNamespace(correlation_id=correlation_id) if correlation_id else SimpleNamespace()
    return SimpleNamespace(state=state)


def _run_handler(exc: StarletteHTTPException, correlation_id: str | None = CORRELATION_ID):
    """Виконує _http_exception_handler синхронно (обробник не має await-викликів)."""
    coro = _http_exception_handler(_make_request(correlation_id), exc)
    try:
        coro.send(None)
    except StopIteration as stop:
        response = stop.value
        return response, json.loads(response.body.decode("utf-8"))
    raise AssertionError("Coroutine did not finish synchronously")


@pytest.mark.parametrize(
    ("status_code", "detail"),
    [
        (400, "Malformed request syntax"),
        (409, "Conflict state"),
        (413, "Payload too large"),
        (415, "Unsupported media type"),
        (429, "Too many requests"),
    ],
    ids=["400-bad-request", "409-conflict", "413-payload-too-large", "415-media", "429-rate-limit"],
)
def test_unmapped_4xx_http_exception_gets_bad_request_not_internal_error(status_code, detail):
    """Лаб 9, №14: 4xx поза 401/403/404/405 отримує BAD_REQUEST, а не INTERNAL_ERROR."""
    exc = StarletteHTTPException(status_code=status_code, detail=detail)

    response, payload = _run_handler(exc)

    assert response.status_code == status_code
    assert payload["error"]["code"] == ErrorCode.BAD_REQUEST.value
    assert payload["error"]["code"] != ErrorCode.INTERNAL_ERROR.value
    assert payload["error"]["message"] == detail
    assert payload["error"]["correlation_id"] == CORRELATION_ID


@pytest.mark.parametrize(
    ("status_code", "expected_code", "expected_default_msg"),
    [
        (401, ErrorCode.UNAUTHORIZED, "Потрібна автентифікація"),
        (403, ErrorCode.FORBIDDEN, "Недостатньо прав"),
        (404, ErrorCode.NOT_FOUND, "Ресурс не знайдено"),
        (405, ErrorCode.METHOD_NOT_ALLOWED, "Метод не підтримується для цього ресурсу"),
    ],
    ids=["401", "403", "404", "405"],
)
def test_known_4xx_http_exceptions_keep_specific_error_codes(
    status_code, expected_code, expected_default_msg
):
    """Відомі коди 401/403/404/405 зберігають свої спеціалізовані ErrorCode."""
    code, default_msg = _default_http_error(status_code)
    assert code == expected_code
    assert default_msg == expected_default_msg

    exc = StarletteHTTPException(status_code=status_code)
    exc.detail = None  # перевірка підстановки default_message, коли detail порожній

    response, payload = _run_handler(exc)

    assert response.status_code == status_code
    assert payload["error"]["code"] == expected_code.value
    assert payload["error"]["message"] == expected_default_msg


def test_404_ignores_framework_detail_and_uses_safe_default_message():
    """Для 404 стандартний detail 'Not Found' замінюється локалізованим повідомленням."""
    exc = StarletteHTTPException(status_code=404, detail="Not Found")

    response, payload = _run_handler(exc)

    assert response.status_code == 404
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value
    assert payload["error"]["message"] == "Ресурс не знайдено"


def test_unmapped_4xx_with_non_string_detail_falls_back_to_default_message():
    """Якщо detail у 4xx не є рядком, використовується безпечне повідомлення за замовчуванням."""
    exc = StarletteHTTPException(status_code=400, detail={"raw": "dict"})  # type: ignore[arg-type]

    response, payload = _run_handler(exc, correlation_id=None)

    assert response.status_code == 400
    assert payload["error"]["code"] == ErrorCode.BAD_REQUEST.value
    assert payload["error"]["message"] == "Некоректний запит"
    assert payload["error"]["correlation_id"]


@pytest.mark.parametrize("status_code", [500, 502, 504], ids=["500", "502", "504"])
def test_5xx_http_exceptions_map_to_internal_error(status_code):
    """Коди 5xx у StarletteHTTPException залишаються з кодом INTERNAL_ERROR."""
    code, default_msg = _default_http_error(status_code)
    assert code == ErrorCode.INTERNAL_ERROR
    assert default_msg == "Помилка обробки запиту"

    exc = StarletteHTTPException(
        status_code=status_code, detail="Gateway error", headers={"X-Retry": "1"}
    )
    response, payload = _run_handler(exc)

    assert response.status_code == status_code
    assert payload["error"]["code"] == ErrorCode.INTERNAL_ERROR.value
    assert response.headers.get("X-Retry") == "1"


# Використання ШІ: тести згенеровано ШІ Gemini, перевірено та затверджено учасником команди.
