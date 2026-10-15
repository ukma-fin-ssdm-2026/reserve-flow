"""REL-001 (quality-attributes.md): 10 паралельних POST /bookings на один слот ->
рівно один 201, решта 409, жодного 500, у БД одне активне бронювання.

Потрібна PostgreSQL: SQLite ігнорує SELECT ... FOR UPDATE, тож на ньому тест
нічого не доводить і пропускається.
    TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/reserveflow_test pytest
"""

import asyncio
import os
import threading
import uuid

import httpx
import pytest
from sqlmodel import Session, func, select

from conftest import auth
from main import app
from services import bookings as booking_engine
from models import Booking, BookingStatus

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="потрібна тестова PostgreSQL (TEST_DATABASE_URL)",
)

PARALLEL_REQUESTS = 10
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"


@pytest.fixture
def widen_race_window(monkeypatch):
    """Без цього тест пройшов би навіть без блокування: перший потік встигає закомітити
    раніше, ніж решта перевірять слот. Бар'єр стоїть після перевірки доступності й
    вставки Booking, але до COMMIT: жодна транзакція не комітиться, доки всі 10 не дійшли
    сюди. З FOR UPDATE дійти може лише одна (решта чекає на блокування), тож бар'єр
    спрацьовує за тайм-аутом; без блокування всі 10 вставили б бронювання."""
    barrier = threading.Barrier(PARALLEL_REQUESTS)
    real_notification = booking_engine.Notification

    def notification_after_barrier(**kwargs):
        try:
            barrier.wait(timeout=0.5)
        except threading.BrokenBarrierError:
            pass
        return real_notification(**kwargs)

    monkeypatch.setattr(booking_engine, "Notification", notification_after_barrier)


async def _fire_parallel() -> list[httpx.Response]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        return await asyncio.gather(
            *(
                http.post(
                    "/api/v1/bookings",
                    headers=auth("mock-client-token"),
                    json={"slot_id": SLOT_FREE, "purpose": "Семінар"},
                )
                for _ in range(PARALLEL_REQUESTS)
            )
        )


def test_ten_parallel_posts_create_exactly_one_booking(
    override_session, db_engine, widen_race_window
):
    responses = asyncio.run(_fire_parallel())

    codes = sorted(r.status_code for r in responses)
    assert codes == [201] + [409] * (PARALLEL_REQUESTS - 1), codes
    assert all(r.json()["error"]["code"] == "SLOT_UNAVAILABLE" for r in responses if r.status_code == 409)

    with Session(db_engine) as s:
        active = s.exec(
            select(func.count())
            .select_from(Booking)
            .where(Booking.slot_id == uuid.UUID(SLOT_FREE))
            .where(Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]))
        ).one()
    assert active == 1
