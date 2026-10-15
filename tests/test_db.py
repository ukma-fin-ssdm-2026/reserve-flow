"""Тести моделей і seed. За замовчуванням — SQLite in-memory;
TEST_DATABASE_URL=postgresql+psycopg://... — окрема тестова PostgreSQL-база
(УВАГА: таблиці в ній видаляються)."""

import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

import models  # noqa: F401
from db import make_engine
from mocks import BOOKINGS, ROOMS, SLOT_1_ID, SLOT_2_ID, SLOTS, USER_CLIENT_ID
from models import (
    ActorType,
    AuditAction,
    AuditLog,
    Booking,
    BookingStatus,
    EntityType,
    Room,
    TimeSlot,
    User,
)
from seed import seed


@pytest.fixture()
def session():
    engine = make_engine(os.getenv("TEST_DATABASE_URL", "sqlite://"))
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_seed_loads_mocks_and_is_idempotent(session):
    seed(session)
    seed(session)
    assert len(session.exec(select(User)).all()) == 3
    assert len(session.exec(select(Room)).all()) == len(ROOMS)
    assert len(session.exec(select(TimeSlot)).all()) == len(SLOTS)
    assert len(session.exec(select(Booking)).all()) == len(BOOKINGS)


def test_seeded_values_roundtrip(session):
    seed(session)
    room = session.get(Room, uuid.UUID(ROOMS[1]["id"]))
    assert room.name_ua == "Аудиторія 3-101"
    assert room.building_ua.value == "Корпус 3" and room.is_shelter is True
    slot = session.get(TimeSlot, uuid.UUID(SLOT_1_ID))
    assert slot.end_time - slot.start_time == timedelta(minutes=80)


def _booking(slot_id, status):
    return Booking(client_id=uuid.UUID(USER_CLIENT_ID), slot_id=uuid.UUID(slot_id), status=status)


def test_second_active_booking_on_slot_is_rejected(session):
    seed(session)  # SLOT_2 вже має Pending-бронювання
    session.add(_booking(SLOT_2_ID, BookingStatus.CONFIRMED))
    with pytest.raises(IntegrityError):
        session.commit()


def test_cancelled_booking_does_not_block_new_one(session):
    seed(session)
    session.add(_booking(SLOT_1_ID, BookingStatus.CANCELLED))
    session.add(_booking(SLOT_1_ID, BookingStatus.PENDING))
    session.commit()


def test_slot_end_must_be_after_start(session):
    seed(session)
    s = session.get(TimeSlot, uuid.UUID(SLOT_1_ID))
    session.add(TimeSlot(room_id=s.room_id, start_time=s.end_time, end_time=s.start_time))
    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("actor", "with_user"),
    [(ActorType.USER, False), (ActorType.SYSTEM, True)],
)
def test_audit_log_actor_invariant(session, actor, with_user):
    seed(session)
    session.add(
        AuditLog(
            actor_type=actor,
            user_id=uuid.UUID(USER_CLIENT_ID) if with_user else None,
            action=AuditAction.NOTIFICATION_FAILED,
            entity_type=EntityType.NOTIFICATION,
            entity_id=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_system_audit_entry_without_user_is_ok(session):
    seed(session)
    session.add(
        AuditLog(
            actor_type=ActorType.SYSTEM,
            action=AuditAction.NOTIFICATION_FAILED,
            entity_type=EntityType.NOTIFICATION,
            entity_id=uuid.uuid4(),
        )
    )
    session.commit()
