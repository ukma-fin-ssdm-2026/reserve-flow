"""Модульні тести службових маршрутів (routes/health.py та main.py).

Поведінка перевірки БД (200 / 503, ін'єкція збою) — у tests/reliability/test_health_db.py.
"""

import pytest
from fastapi.testclient import TestClient

from db import get_session
from main import app, root
from routes.health import HealthOut, health_check

pytestmark = pytest.mark.no_req(
    "інфраструктура: службова кінцева точка перевірки стану сервісу (healthcheck)"
)


class _Response:
    status_code = 200


class _Session:
    def execute(self, statement):
        self.sql = str(statement)


def test_health_check_runs_select_1():
    session = _Session()

    result = health_check(_Response(), session)

    assert session.sql == "SELECT 1"
    assert result == HealthOut(status="healthy", db="ok")


@pytest.mark.parametrize("path", ["/api/v1/health", "/health"])
def test_health_router_is_connected(path):
    app.dependency_overrides[get_session] = lambda: _Session()
    try:
        response = TestClient(app).get(path)
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.json() == {"status": "healthy", "db": "ok"}


def test_main_root():
    assert root() == {"status": "healthy", "docs": "/api-docs"}
