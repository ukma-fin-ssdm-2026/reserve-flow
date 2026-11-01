"""Модульні тести для перевірки стану сервісу (routes/health.py та main.py)."""

import pytest

from config import API_VERSION
from main import health_check, root
from routes.health import HealthOut, get_health, router

pytestmark = pytest.mark.no_req(
    "інфраструктура: службова кінцева точка перевірки стану сервісу (healthcheck)"
)


def test_routes_health_get_health():
    coro = get_health()
    try:
        coro.send(None)
    except StopIteration as exc:
        result = exc.value

    assert isinstance(result, HealthOut)
    assert result.status == "ok"
    assert result.version == API_VERSION
    assert router.prefix == "/api/v1"


def test_main_health_check_and_root():
    assert health_check() == {"status": "healthy"}
    assert root() == {"status": "healthy", "docs": "/api-docs"}
