"""Лаб 9, знахідка #1: синхронна сесія БД не може працювати в async-обробнику.

FastAPI виконує `async def` прямо в event loop, тож блокувальний виклик psycopg
зупиняє обробку всіх інших запитів. Звичайний `def` FastAPI виносить у пул потоків.
"""

import inspect

import pytest
from fastapi.routing import APIRoute

import main
from db import get_session
from routes import auth, bookings, rooms, slots

# Заблокований event loop затримує всі відповіді, зокрема пошук (PERF-001)
pytestmark = pytest.mark.req("PERF-001")


def _db_routes() -> list[APIRoute]:
    """Ендпоінти, які напряму отримують Session (Depends(get_session))."""
    routers = [auth.router, bookings.router, rooms.router, slots.router, main.app.router]
    return [
        route
        for router in routers
        for route in router.routes
        if isinstance(route, APIRoute)
        and any(dep.call is get_session for dep in route.dependant.dependencies)
    ]


def test_check_finds_db_routes():
    # Захист від «порожнього зеленого» тесту: перевірка справді бачить маршрути з БД
    names = {route.endpoint.__name__ for route in _db_routes()}
    assert {"create_booking", "get_bookings", "search_slots", "get_room"} <= names


def test_handlers_with_db_session_are_sync():
    offenders = [
        route.endpoint.__name__
        for route in _db_routes()
        if inspect.iscoroutinefunction(route.endpoint)
    ]
    assert offenders == [], f"async-обробники з синхронною Session: {offenders}"
