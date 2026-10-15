"""POST /bookings працює через БД: транзакція, Notification, AuditLog, відкат при конфлікті."""

import uuid

from sqlmodel import Session, func, select

from conftest import auth
from models import Booking, BookingStatus, Notification, TimeSlot, AuditLog, AuditAction, EntityType

CLIENT = auth("mock-client-token")
SLOT_FREE = "b2000000-0000-4000-8000-000000000001"
SLOT_BOOKED = "b2000000-0000-4000-8000-000000000002"


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
