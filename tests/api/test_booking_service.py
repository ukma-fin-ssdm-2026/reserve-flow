"""
Сервіс перевіряється без HTTP: реальна SQLite-сесія з seed (фікстура db_engine),
а виклики блокування й відкат транзакції — через spy/mock.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from mocks import SLOT_1_ID, SLOT_2_ID, USER_CLIENT_ID
from models import Booking, BookingStatus, Notification
from services import bookings as booking_engine
from services.exceptions import SlotNotFound, SlotUnavailable

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
    bookings_before = _count(session, Booking)

    # Act
    with pytest.raises(RuntimeError):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Семінар")

    # Assert: нічого не збережено — Booking відкотився разом з Notification
    assert _count(session, Booking) == bookings_before


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
