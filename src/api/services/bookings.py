"""Booking Engine Service: створення бронювання в одній транзакції."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from errors import AppError, ErrorCode
from models import (
    ActorType,
    AuditAction,
    AuditLog,
    Booking,
    BookingStatus,
    EntityType,
    Notification,
    TimeSlot,
)
from services.exceptions import SlotNotFound, SlotUnavailable
from services.notifications import compute_reminder_time
from services.rooms import lock_slot
from services.validators import slots_overlap

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def _as_utc(dt: datetime) -> datetime:
    """Нормалізує datetime до UTC; SQLite може повертати naive-значення."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_booking(
    session: Session,
    client_id: UUID,
    slot_id: UUID,
    purpose: str,
    now: datetime | None = None,
) -> Booking:
    """Створює бронювання, сповіщення й запис аудиту в одній транзакції.

    Перевіряє доступність слота, час його початку та перетини з іншими
    активними бронюваннями клієнта.
    """
    current_time = _as_utc(now or datetime.now(timezone.utc))

    try:
        # Блокування слота до завершення транзакції.
        slot = lock_slot(session, slot_id)

        if not slot:
            raise SlotNotFound(str(slot_id))

        if not slot.is_available:
            raise SlotUnavailable(str(slot_id))

        # Не дозволяємо бронювати слот, який уже почався або починається зараз.
        slot_start = _as_utc(slot.start_time)
        if slot_start <= current_time:
            logger.warning(
                "Rejecting booking for slot that has already started: %s",
                slot_id,
            )
            raise AppError(
                status_code=409,
                code=ErrorCode.SLOT_ALREADY_STARTED,
                message="Бронювання неможливе: час початку слота вже настав.",
            )

        # Додаткова перевірка активного бронювання.
        taken = session.exec(
            select(Booking.id)
            .where(
                Booking.slot_id == slot_id,
                col(Booking.status).in_(ACTIVE_STATUSES),
            )
            .limit(1)
        ).first()

        if taken is not None:
            raise SlotUnavailable(str(slot_id))

        # Перевірка перетину з іншими активними бронюваннями клієнта.
        client_active_slots = session.exec(
            select(TimeSlot)
            .join(Booking)
            .where(Booking.client_id == client_id)
            .where(col(Booking.status).in_(ACTIVE_STATUSES))
        ).all()

        for active_slot in client_active_slots:
            if slots_overlap(
                slot.start_time,
                slot.end_time,
                active_slot.start_time,
                active_slot.end_time,
            ):
                raise AppError(
                    status_code=409,
                    code=ErrorCode.CLIENT_SCHEDULE_CONFLICT,
                    message=("Ви вже маєте бронювання на час, " "що перетинається з цим слотом."),
                )

        booking = Booking(
            client_id=client_id,
            slot_id=slot_id,
            status=BookingStatus.PENDING,
            purpose=purpose,
        )
        session.add(booking)
        session.flush()

        reminder_time = compute_reminder_time(slot_start, current_time)

        if reminder_time is not None:
            session.add(
                Notification(
                    booking_id=booking.id,
                    scheduled_time=reminder_time.astimezone(timezone.utc),
                )
            )

        session.add(
            AuditLog(
                actor_type=ActorType.USER,
                user_id=client_id,
                action=AuditAction.BOOKING_CREATED,
                entity_type=EntityType.BOOKING,
                entity_id=booking.id,
            )
        )

        session.commit()

    except IntegrityError as exc:
        # Захист від конкурентного створення активного бронювання.
        session.rollback()
        raise SlotUnavailable(str(slot_id)) from exc
    except Exception:
        session.rollback()
        raise

    session.refresh(booking)
    return booking
