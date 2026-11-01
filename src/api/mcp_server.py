"""MCP-сервер Reserve Flow: обгортка FastAPI над інструментами агента.

Генерує інструменти з OpenAPI-схеми FastAPI (рішення FastMCP.from_fastapi):
кожна кінцева точка API стає інструментом агента без дублювання логіки.

Запуск у терміналі (з кореня репо):
    python src/api/mcp_server.py

Перевірка в MCP Inspector:
    npx @modelcontextprotocol/inspector python src/api/mcp_server.py
"""

import os
import sys
from pathlib import Path

# Імпортуємо модулі API так само, як uvicorn (через sys.path)
API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

try:
    from fastmcp import FastMCP
except ImportError:
    sys.exit("fastmcp не встановлено. Запустіть: pip install -r requirements-mcp.txt")

from main import app  # noqa: E402
from mocks import USER_ADMIN_ID, USER_CLIENT_ID, USER_PROVIDER_ID  # noqa: E402
from security import create_access_token  # noqa: E402

# Користувач за замовчуванням — клієнт. Щоб агент діяв як постачальник
# або адмін: RESERVE_FLOW_ROLE=provider python src/api/mcp_server.py
AGENT_USERS = {
    "client": (USER_CLIENT_ID, "Client"),
    "provider": (USER_PROVIDER_ID, "Provider"),
    "admin": (USER_ADMIN_ID, "Admin"),
}
AGENT_ROLE = os.environ.get("RESERVE_FLOW_ROLE", "client").lower()
if AGENT_ROLE not in AGENT_USERS:
    sys.exit(f"RESERVE_FLOW_ROLE має бути одним із: {', '.join(AGENT_USERS)}")


def _add_token(request):
    """httpx auth-хук: додає свіжий JWT до кожного запиту агента."""
    token = os.environ.get("RESERVE_FLOW_TOKEN") or create_access_token(*AGENT_USERS[AGENT_ROLE])
    request.headers["Authorization"] = f"Bearer {token}"
    return request


# Короткі назви інструментів замість автоматичних operationId FastAPI
# (напр. search_slots_api_v1_slots_get): агенту легше обрати потрібний.
TOOL_NAMES = {
    "get_health_api_v1_health_get": "check_health",
    "health_check_api_v1_health_get": "check_health",
    # bandit B105 — хибне спрацювання: ключ містить «token», а значення — назва інструмента
    "issue_token_api_v1_auth_token_post": "issue_token",  # nosec B105
    "read_me_api_v1_auth_me_get": "who_am_i",
    "search_slots_api_v1_slots_get": "search_slots",
    "patch_slot_api_v1_slots__slot_id__patch": "update_slot_availability",
    "get_room_api_v1_rooms__room_id__get": "get_room",
    "create_booking_api_v1_bookings_post": "create_booking",
    "get_bookings_api_v1_bookings_get": "list_bookings",
    "get_booking_api_v1_bookings__booking_id__get": "get_booking",
    "update_booking_api_v1_bookings__booking_id__patch": "change_booking_status",
}

mcp = FastMCP.from_fastapi(
    app=app,
    name="Reserve Flow",
    mcp_names=TOOL_NAMES,
    # Кожен виклик інструмента йде з JWT тестового користувача
    httpx_client_kwargs={"auth": _add_token},
)


if __name__ == "__main__":
    # fastmcp run бере назву об'єкта або запускає stdio-транспорт напряму
    mcp.run()

# Використання ШІ: при написанні коду використано допомогу ШІ Claude
# на основі прикладу курсу (FastMCP.from_fastapi). Код перевірено учасниками команди.
