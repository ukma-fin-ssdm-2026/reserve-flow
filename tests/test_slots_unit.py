"""Модульні тести для rooms.py та slots.py за патерном AAA."""

import asyncio
from datetime import datetime, time, timezone

import pytest
from uuid import UUID, uuid4
from unittest.mock import MagicMock

from routes.slots import _to_kyiv, _slot_to_out, search_slots
from services.rooms import lock_slot
from services.exceptions import SlotNotFound
from errors import AppError
from models import TimeSlot
from schemas.common import PaginationParams
from sqlmodel import Session


# --- 1. lock_slot: реальні запити до БД замість моків ---
def test_lock_slot_returns_existing_slot(db_engine):
    with Session(db_engine) as session:
        # Використовуємо валідний ID слота з тестової БД (FREE_1)
        slot_id = UUID("b2000000-0000-4000-8000-000000000001")
        slot = lock_slot(session, slot_id)
        assert slot is not None
        assert slot.id == slot_id


def test_lock_slot_not_found_raises(db_engine):
    with Session(db_engine) as session:
        fake_id = uuid4()
        with pytest.raises(SlotNotFound):
            lock_slot(session, fake_id)


# --- 2. _to_kyiv: UTC → Київ, перехід літнього/зимового часу ---
@pytest.mark.parametrize(
    "utc_dt, expected_hour",
    [
        (datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc), 12),  # Зимовий час (UTC+2)
        (datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc), 13),  # Літній час (UTC+3)
        (datetime(2026, 1, 15, 10, 0), 12),  # Naive datetime (SQLite) — вважаємо UTC
    ],
)
def test_to_kyiv_converts_correctly(utc_dt, expected_hour):
    # Act
    kyiv_dt = _to_kyiv(utc_dt)

    # Assert
    assert kyiv_dt.hour == expected_hour


# --- 3. _slot_to_out: перевірка конвертації моделі ---
def test_slot_to_out_mapping():
    # Arrange
    slot = TimeSlot(
        id=uuid4(),
        room_id=uuid4(),
        start_time=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc),
        is_available=True,
    )

    # Act
    out = _slot_to_out(slot)

    # Assert
    assert out.id == slot.id
    assert out.is_available is True
    # Перевіряємо, що _to_kyiv застосувався (10:00 UTC у жовтні = 13:00 Київ)
    assert out.start_time.hour == 13


# --- 4. Фільтри search_slots: from == to та порожній діапазон ---
@pytest.mark.parametrize(
    "start_t, end_t",
    [
        (time(14, 0), time(14, 0)),  # from == to
        (time(15, 0), time(14, 0)),  # end < start (порожній/некоректний діапазон)
    ],
)
def test_search_slots_invalid_time_range_raises_422(start_t, end_t):
    # Arrange
    session_mock = MagicMock()
    params = PaginationParams(limit=10, offset=0)

    # Act & Assert: роутер async, тож викликаємо через asyncio.run
    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            search_slots(
                session=session_mock,
                room_id=None,
                search_date=None,
                start=start_t,
                end=end_t,
                capacity=None,
                has_projector=None,
                is_shelter=None,
                building=None,
                params=params,
            )
        )
    assert exc_info.value.status_code == 422


# --- 5. Фільтри search_slots: Межа сторінки пагінації ---
def test_search_slots_pagination_bounds():
    # Arrange
    session_mock = MagicMock()
    # Мокаємо результати з БД: список кімнат порожній
    session_mock.exec.return_value.all.return_value = []

    params = PaginationParams(limit=10, offset=990)  # сторінка далеко за межами даних

    # Act
    result = asyncio.run(
        search_slots(
            session=session_mock,
            room_id=None,
            search_date=None,
            start=None,
            end=None,
            capacity=None,
            has_projector=None,
            is_shelter=None,
            building=None,
            params=params,
        )
    )

    # Assert
    assert result.pagination.total == 0
    assert result.items == []
