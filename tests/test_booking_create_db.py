"""POST /bookings працює через БД: транзакція, Notification, AuditLog, відкат при конфлікті."""

import pytest
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, func, select

from conftest import auth
from mocks import KYIV, ROOM_2_ID
from models import Booking, BookingStatus, Notification, TimeSlot, AuditLog, AuditAction, EntityType

pytestmark = pytest.mark.req("FR-005", "FR-006", "FR-013", "FR-014")

CLIENT = auth("client")
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"
SLOT_BOOKED = "b2000000-0000-4000-8000-000000000002"
# Інша кімната, той самий час, що й SLOT_BOOKED (15:40–17:00), на який клієнт уже має Pending
SLOT_SAME_TIME_OTHER_ROOM = "b2000000-0000-4000-8000-000000000004"


def _post(client, slot_id):
    return client.post(
        "/api/v1/bookings", headers=CLIENT, json={"slot_id": slot_id, "purpose": "Семінар"}
    )


def _count(db_engine, model):
    with Session(db_engine) as s:
        return s.exec(select(func.count()).select_from(model)).one()


def test_create_persists_booking_notification_and_audit_log_in_one_transaction(client, db_engine):
    bookings_before = _count(db_engine, Booking)
    audit_logs_before = _count(db_engine, AuditLog)

    r = _post(client, SLOT_FREE)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Pending" and body["purpose"] == "Семінар"
    assert body["slot_id"] == SLOT_FREE

    with Session(db_engine) as s:
        booking = s.get(Booking, uuid.UUID(body["id"]))
        assert booking is not None and booking.status == BookingStatus.PENDING

        # Перевірка Notification
        notification = s.exec(
            select(Notification).where(Notification.booking_id == booking.id)
        ).one()
        slot = s.get(TimeSlot, booking.slot_id)
        assert notification.scheduled_time.replace(tzinfo=None) < slot.start_time.replace(
            tzinfo=None
        )

        # Перевірка AuditLog (FR-013)
        audit_log = s.exec(select(AuditLog).where(AuditLog.entity_id == booking.id)).one()
        assert audit_log.action == AuditAction.BOOKING_CREATED
        assert audit_log.entity_type == EntityType.BOOKING
        assert audit_log.user_id == booking.client_id

    assert _count(db_engine, Booking) == bookings_before + 1
    assert _count(db_engine, AuditLog) == audit_logs_before + 1


def test_second_post_on_same_slot_is_409_and_leaves_no_rows(client, db_engine):
    assert _post(client, SLOT_FREE).status_code == 201
    bookings, notifications, audits = (
        _count(db_engine, Booking),
        _count(db_engine, Notification),
        _count(db_engine, AuditLog),
    )

    r = _post(client, SLOT_FREE)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SLOT_UNAVAILABLE"
    assert (
        _count(db_engine, Booking),
        _count(db_engine, Notification),
        _count(db_engine, AuditLog),
    ) == (bookings, notifications, audits)


def test_seeded_active_booking_blocks_slot(client):
    assert _post(client, SLOT_BOOKED).status_code == 409


def test_cancelled_booking_frees_slot(client, db_engine):
    first = _post(client, SLOT_FREE).json()
    with Session(db_engine) as s:
        s.get(Booking, uuid.UUID(first["id"])).status = BookingStatus.CANCELLED
        s.commit()
    assert _post(client, SLOT_FREE).status_code == 201


@pytest.mark.req("FR-016")
@pytest.mark.xfail(
    strict=True,
    reason="Дефект FR-016: services/bookings.py викликає AppError(error_code=...) — "
    "неіснуючий аргумент, і коду CLIENT_SCHEDULE_CONFLICT немає в ErrorCode, тому 500 замість 409. "
    "Після виправлення прибрати xfail (strict=True нагадає).",
)
def test_client_cannot_book_overlapping_slot_in_other_room(client, db_engine):
    # Arrange: у клієнта з seed активне бронювання на 15:40–17:00 (кімната 1)
    bookings_before = _count(db_engine, Booking)

    # Act: той самий час, але кімната 2
    r = _post(client, SLOT_SAME_TIME_OTHER_ROOM)

    # Assert
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CLIENT_SCHEDULE_CONFLICT"
    assert _count(db_engine, Booking) == bookings_before


@pytest.mark.req("FR-016")
def test_cancelled_booking_does_not_block_overlapping_slot(client, db_engine):
    # Arrange: скасовуємо активне бронювання клієнта на 15:40–17:00
    with Session(db_engine) as s:
        booking = s.exec(select(Booking).where(Booking.slot_id == uuid.UUID(SLOT_BOOKED))).one()
        booking.status = BookingStatus.CANCELLED
        s.commit()

    # Act / Assert: скасоване бронювання не враховується
    assert _post(client, SLOT_SAME_TIME_OTHER_ROOM).status_code == 201


@pytest.mark.req("FR-016")
def test_client_can_book_adjacent_back_to_back_slot(client, db_engine):
    # Arrange: у клієнта з seed активне бронювання на 15:40–17:00 (кімната 1);
    # додаємо слот «впритул» 17:00–18:20 того ж дня в кімнаті 2 (у БД — UTC, як у seed)
    with Session(db_engine) as s:
        slot = TimeSlot(
            room_id=uuid.UUID(ROOM_2_ID),
            start_time=datetime(2026, 10, 15, 17, 0, tzinfo=KYIV).astimezone(timezone.utc),
            end_time=datetime(2026, 10, 15, 18, 20, tzinfo=KYIV).astimezone(timezone.utc),
        )
        s.add(slot)
        s.commit()
        slot_id = str(slot.id)

    # Act
    r = _post(client, slot_id)

    # Assert: кінець одного = початок іншого — це не перетин
    assert r.status_code == 201
    assert r.json()["slot_id"] == slot_id


# Використання ШІ: для допрацювання тесту на основі ідей учасника команди
# було використано ШІ Claude. Код був перевірений та затверджений командою.
