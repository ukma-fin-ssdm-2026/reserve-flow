"""
Сервіс перевіряється без HTTP: реальна SQLite-сесія з seed (фікстура db_engine),
а виклики блокування й відкат транзакції — через spy/mock.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from mocks import SLOT_1_ID, SLOT_2_ID, USER_CLIENT_ID, SLOTS, find_by_id
from models import Booking, BookingStatus, Notification
from services import bookings as booking_engine
from services.exceptions import SlotNotFound, SlotUnavailable
from datetime import timezone

CLIENT_ID = uuid.UUID(USER_CLIENT_ID)
SLOT_FREE = uuid.UUID(SLOT_1_ID)
SLOT_WITH_PENDING = uuid.UUID(SLOT_2_ID)  # у seed має бронювання Pending
SLOT_CLOSED = uuid.UUID("b2000000-0000-4000-8000-000000000003")
UNKNOWN_SLOT = uuid.UUID("00000000-0000-4000-8000-000000000000")


@pytest.fixture
def session(db_engine):
    with Session(db_engine) as s:
        yield s


def _count(session, model):
    return session.exec(select(func.count()).select_from(model)).one()


def test_create_booking_returns_pending_booking_with_notification(session):
    # Arrange
    bookings_before = _count(session, Booking)

    # Act
    booking = booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Семінар")

    # Assert
    assert booking.status == BookingStatus.PENDING
    assert (booking.client_id, booking.slot_id, booking.purpose) == (
        CLIENT_ID,
        SLOT_FREE,
        "Семінар",
    )
    assert _count(session, Booking) == bookings_before + 1
    notification = session.exec(
        select(Notification).where(Notification.booking_id == booking.id)
    ).one()
    assert notification.retry_count == 0

    slot_data = find_by_id(SLOTS, str(SLOT_FREE))
    expected_time = slot_data["start_time"] - booking_engine.REMINDER_LEAD
    scheduled = notification.scheduled_time
    if scheduled.tzinfo is None:  # SQLite не зберігає часовий пояс; значення вже в UTC
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    # PostgreSQL повертає дату з часовим поясом; порівнюємо як моменти часу
    assert scheduled == expected_time


@pytest.mark.parametrize(
    ("slot_id", "expected_error"),
    [
        (SLOT_CLOSED, SlotUnavailable),
        (SLOT_WITH_PENDING, SlotUnavailable),
        (UNKNOWN_SLOT, SlotNotFound),
    ],
    ids=["closed-by-provider", "already-booked", "unknown-slot"],
)
def test_create_booking_rejects_unavailable_slot(session, slot_id, expected_error):
    # Arrange
    bookings_before = _count(session, Booking)

    # Act / Assert
    with pytest.raises(expected_error):
        booking_engine.create_booking(session, CLIENT_ID, slot_id, "Семінар")
    assert _count(session, Booking) == bookings_before


@pytest.mark.parametrize(
    ("existing_status", "slot_is_free"),
    [
        (BookingStatus.PENDING, False),
        (BookingStatus.CONFIRMED, False),
        (BookingStatus.CANCELLED, True),
        (BookingStatus.REJECTED, True),
    ],
)
def test_only_active_bookings_block_slot(session, existing_status, slot_is_free):
    # Arrange
    existing = session.exec(select(Booking).where(Booking.slot_id == SLOT_WITH_PENDING)).one()
    existing.status = existing_status
    session.commit()

    # Act
    def act():
        return booking_engine.create_booking(session, CLIENT_ID, SLOT_WITH_PENDING, "Семінар")

    # Assert
    if slot_is_free:
        assert act().status == BookingStatus.PENDING
    else:
        with pytest.raises(SlotUnavailable):
            act()


def test_create_booking_locks_the_requested_slot(session, monkeypatch):
    # Arrange
    spy = MagicMock(wraps=booking_engine.lock_slot)
    monkeypatch.setattr(booking_engine, "lock_slot", spy)

    # Act
    booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Семінар")

    # Assert
    spy.assert_called_once_with(session, SLOT_FREE)


def test_unexpected_error_rolls_back_whole_transaction(session, monkeypatch):
    # Arrange: збій на другому кроці (запис Notification) після вставки Booking
    def boom(**_kwargs):
        raise RuntimeError("збій")

    monkeypatch.setattr(booking_engine, "Notification", boom)

    rollback_spy = MagicMock(wraps=session.rollback)
    commit_spy = MagicMock(wraps=session.commit)
    monkeypatch.setattr(session, "rollback", rollback_spy)
    monkeypatch.setattr(session, "commit", commit_spy)

    bookings_before = _count(session, Booking)

    # Act
    with pytest.raises(RuntimeError):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Семінар")

    # Assert: нічого не збережено — Booking відкотився разом з Notification
    assert _count(session, Booking) == bookings_before
    rollback_spy.assert_called_once()
    commit_spy.assert_not_called()


def test_integrity_error_is_reported_as_slot_unavailable(session, monkeypatch):
    # Arrange: COMMIT падає на унікальному індексі uq_bookings_active_slot
    rollback = MagicMock(wraps=session.rollback)
    monkeypatch.setattr(session, "rollback", rollback)
    monkeypatch.setattr(
        session, "commit", MagicMock(side_effect=IntegrityError("INSERT", {}, Exception("dup")))
    )

    # Act / Assert
    with pytest.raises(SlotUnavailable):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Семінар")
    rollback.assert_called_once()


# Вмкористання ШІ: використано ШІ Gemini ля прискорення написання тестів. Код перевірено,
# відредаговано та затверджено учасником команди.
