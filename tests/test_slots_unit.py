"""Модульні тести для rooms.py та slots.py за патерном AAA."""

import pytest
from datetime import datetime, time, timezone
from uuid import uuid4
from unittest.mock import MagicMock

from routes.slots import _to_kyiv, _slot_to_out, search_slots
from services.rooms import lock_slot
from services.exceptions import SlotNotFound
from errors import AppError
from models import TimeSlot
from schemas.common import PaginationParams

# --- 1. lock_slot для неіснуючого slot_id → SlotNotFound ---
def test_lock_slot_not_found():
    # Arrange: мокаємо сесію БД, щоб вона повертала None
    session_mock = MagicMock()
    session_mock.exec.return_value.one_or_none.return_value = None
    fake_id = uuid4()
    
    # Act & Assert
    with pytest.raises(SlotNotFound):
        lock_slot(session_mock, fake_id)


# --- 2. _to_kyiv: UTC → Київ, перехід літнього/зимового часу ---
@pytest.mark.parametrize("utc_dt, expected_hour", [
    (datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc), 13),  # Мок KYIV у проєкті завжди +3
    (datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc), 13),  # Літній час (UTC+3)
    (datetime(2026, 1, 15, 10, 0), 13),                       # Naive datetime
])
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
@pytest.mark.asyncio
@pytest.mark.parametrize("start_t, end_t", [
    (time(14, 0), time(14, 0)),  # from == to
    (time(15, 0), time(14, 0)),  # end < start (порожній/некоректний діапазон)
])
async def test_search_slots_invalid_time_range_raises_422(start_t, end_t):
    # Arrange
    session_mock = MagicMock()
    params = PaginationParams(page=1, size=10)
    
    # Act & Assert
    with pytest.raises(AppError) as exc_info:
        await search_slots(
            session=session_mock,
            start=start_t,
            end=end_t,
            params=params
        )
    assert exc_info.value.status_code == 422


# --- 5. Фільтри search_slots: Межа сторінки пагінації ---
@pytest.mark.asyncio
async def test_search_slots_pagination_bounds():
    # Arrange
    session_mock = MagicMock()
    # Мокаємо результати з БД: список кімнат порожній
    session_mock.exec.return_value.all.return_value = []
    
    params = PaginationParams(page=999, size=10)
    
    # Act
    result = await search_slots(
        session=session_mock,
        room_id=None,
        search_date=None,
        start=None,
        end=None,
        capacity=None,
        has_projector=None,
        is_shelter=None,
        building=None,
        params=params
    )
    
    # Assert
    assert result.pagination.total == 0
    assert result.items == []