"""Спільні фікстури для тестів API."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Модулі застосунку імпортуються як у uvicorn --app-dir src/api
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "api"))

from main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
