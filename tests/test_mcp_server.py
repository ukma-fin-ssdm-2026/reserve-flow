"""Характеризаційні тести src/api/mcp_server.py (Лаб 8, бонус, #413).

Фіксують поточну поведінку модуля перед рефакторингом — зокрема ту, що виглядає дивно
(вихід через sys.exit під час імпорту). Справжній fastmcp не потрібен: його замінює
заглушка, яка запам'ятовує аргументи FastMCP.from_fastapi, тож тести йдуть у CI
без requirements-mcp.txt.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest
from main import app
from mocks import USER_ADMIN_ID, USER_CLIENT_ID
from security import decode_access_token

pytestmark = pytest.mark.no_req("бонус Лаб 4: MCP-обгортка над API, не вимога системи")

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "api" / "mcp_server.py"

# Операції API → назви інструментів агента, як зараз бачить їх агент
EXPECTED_TOOLS = {
    "health_check_api_v1_health_get": "check_health",
    "issue_token_api_v1_auth_token_post": "issue_token",  # nosec B105 — назва інструмента
    "read_me_api_v1_auth_me_get": "who_am_i",
    "search_slots_api_v1_slots_get": "search_slots",
    "patch_slot_api_v1_slots__slot_id__patch": "update_slot_availability",
    "get_room_api_v1_rooms__room_id__get": "get_room",
    "create_booking_api_v1_bookings_post": "create_booking",
    "get_bookings_api_v1_bookings_get": "list_bookings",
    "get_booking_api_v1_bookings__booking_id__get": "get_booking",
    "update_booking_api_v1_bookings__booking_id__patch": "change_booking_status",
}


class _FakeFastMCP:
    """Заглушка fastmcp.FastMCP: запам'ятовує, з чим викликано from_fastapi."""

    calls: list[dict] = []

    @classmethod
    def from_fastapi(cls, **kwargs):
        cls.calls.append(kwargs)
        return cls()


@pytest.fixture
def load_mcp(monkeypatch):
    """Імпортує mcp_server.py заново із заглушкою fastmcp і заданою роллю агента."""
    fake = types.ModuleType("fastmcp")
    fake.FastMCP = _FakeFastMCP
    monkeypatch.setitem(sys.modules, "fastmcp", fake)
    monkeypatch.delenv("RESERVE_FLOW_TOKEN", raising=False)
    _FakeFastMCP.calls = []

    def load(role=None):
        if role is None:
            monkeypatch.delenv("RESERVE_FLOW_ROLE", raising=False)
        else:
            monkeypatch.setenv("RESERVE_FLOW_ROLE", role)
        spec = importlib.util.spec_from_file_location("mcp_server_under_test", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


def _operation_ids() -> set[str]:
    return {op["operationId"] for path in app.openapi()["paths"].values() for op in path.values()}


def test_every_api_operation_has_short_tool_name(load_mcp):
    # Arrange
    mcp_server = load_mcp()

    # Act: які назви отримає агент для кожної операції API
    tools = {op: mcp_server.TOOL_NAMES.get(op) for op in _operation_ids()}

    # Assert
    assert tools == EXPECTED_TOOLS


def test_from_fastapi_receives_app_names_and_auth_hook(load_mcp):
    # Act
    mcp_server = load_mcp()

    # Assert: один виклик FastMCP.from_fastapi з нашим застосунком і JWT-хуком
    assert len(_FakeFastMCP.calls) == 1
    kwargs = _FakeFastMCP.calls[0]
    assert kwargs["app"] is app
    assert kwargs["name"] == "Reserve Flow"
    assert kwargs["mcp_names"] is mcp_server.TOOL_NAMES
    assert kwargs["httpx_client_kwargs"] == {"auth": mcp_server._add_token}


def test_default_role_is_client(load_mcp):
    assert load_mcp().AGENT_ROLE == "client"


def test_role_from_env_is_case_insensitive(load_mcp):
    assert load_mcp("PROVIDER").AGENT_ROLE == "provider"


def test_unknown_role_exits_on_import(load_mcp):
    # Дивна, але поточна поведінка: модуль завершує процес під час імпорту
    with pytest.raises(SystemExit) as exc:
        load_mcp("guest")

    assert str(exc.value) == "RESERVE_FLOW_ROLE має бути одним із: client, provider, admin"


def test_missing_fastmcp_exits_with_install_hint(load_mcp, monkeypatch):
    # Arrange: fastmcp не встановлено
    monkeypatch.setitem(sys.modules, "fastmcp", None)

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        load_mcp()

    assert "pip install -r requirements-mcp.txt" in str(exc.value)


def test_add_token_issues_jwt_for_agent_role(load_mcp):
    # Arrange
    mcp_server = load_mcp("admin")
    request = types.SimpleNamespace(headers={})

    # Act
    result = mcp_server._add_token(request)

    # Assert: той самий запит, з JWT адміністратора
    assert result is request
    scheme, token = request.headers["Authorization"].split(" ")
    payload = decode_access_token(token)
    assert scheme == "Bearer"
    assert (payload["sub"], payload["role"]) == (str(USER_ADMIN_ID), "Admin")


def test_add_token_prefers_token_from_env(load_mcp, monkeypatch):
    # Arrange: готовий токен у RESERVE_FLOW_TOKEN має пріоритет над згенерованим
    mcp_server = load_mcp()
    monkeypatch.setenv("RESERVE_FLOW_TOKEN", "ready-made-token")
    request = types.SimpleNamespace(headers={})

    # Act
    mcp_server._add_token(request)

    # Assert
    assert request.headers["Authorization"] == "Bearer ready-made-token"


def test_client_token_is_for_seed_client(load_mcp):
    # Arrange
    mcp_server = load_mcp()
    request = types.SimpleNamespace(headers={})

    # Act
    mcp_server._add_token(request)

    # Assert
    payload = decode_access_token(request.headers["Authorization"].removeprefix("Bearer "))
    assert payload["sub"] == str(USER_CLIENT_ID)
