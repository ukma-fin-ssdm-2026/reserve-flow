"""MCP-сервер, згенерований з API Reserve Flow (бонус Lab 4).

Кожна кінцева точка FastAPI стає інструментом MCP: назва, опис і схема
параметрів беруться з тих самих анотацій, що й OpenAPI / Swagger UI.
FastMCP викликає застосунок напряму, тож окремо запускати API не потрібно.

Запуск (з кореня репозиторію):
    pip install -r requirements-mcp.txt
    python src/api/mcp_server.py                      # транспорт stdio

Перевірка в MCP Inspector:
    npx @modelcontextprotocol/inspector python src/api/mcp_server.py

Агент працює від імені тестового користувача (заглушка D-06). Роль задається
змінною середовища, за замовчуванням — клієнт:
    RESERVE_FLOW_TOKEN=mock-provider-token python src/api/mcp_server.py
"""

import os
import sys
from pathlib import Path

# Імпорти застосунку працюють так само, як з uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP  # noqa: E402

from main import app  # noqa: E402

TOKEN = os.environ.get("RESERVE_FLOW_TOKEN", "mock-client-token")

# Короткі назви інструментів замість автоматичних operationId FastAPI
# (напр. search_slots_api_v1_slots_get): агенту легше обрати потрібний.
TOOL_NAMES = {
    "get_health_api_v1_health_get": "check_health",
    "issue_token_api_v1_auth_token_post": "issue_test_token",
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
    # Кожен виклик інструмента йде з токеном тестового користувача
    httpx_client_kwargs={"headers": {"Authorization": f"Bearer {TOKEN}"}},
)


if __name__ == "__main__":
    mcp.run()  # транспорт stdio за замовчуванням


# Використання ШІ: при написанні коду використано допомогу ШІ Claude
# на основі прикладу курсу (FastMCP.from_fastapi). Код перевірено учасниками команди.
