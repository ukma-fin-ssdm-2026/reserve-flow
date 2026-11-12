"""Booking Engine Service: створення бронювання в одній транзакції (FR-005, FR-006, FR-013)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

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
from services.exceptions import SlotUnavailable, SlotNotFound
from services.rooms import lock_slot

from services.validators import slots_overlap
from errors import AppError, ErrorCode
from services.notifications import compute_reminder_time

ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def _as_utc(dt: datetime) -> datetime:
    """SQLite повертає naive-час; у БД він зберігається в UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def create_booking(
    session: Session,
    client_id: UUID,
    slot_id: UUID,
    purpose: str,
    now: datetime | None = None,
) -> Booking:
    """Блокує слот, перевіряє доступність, створює Booking (Pending), Notification і AuditLog.

    Усе в одній транзакції (Лаб 9, знахідка #4): або є і бронювання, і запис аудиту,
    або немає нічого — клієнт ніколи не отримає 500 на бронювання, яке вже збережено.

    Паралельний запит на той самий слот чекає на
    SELECT ... FOR UPDATE, а після COMMIT першої транзакції бачить її бронювання
    і отримує SlotUnavailable. Будь-який виняток -> ROLLBACK (знімає блокування).

    Час нагадування — за compute_reminder_time (#421): не раніше за `now`; для слота,
    що вже почався, нагадування не створюється.
    """
    try:
        slot = lock_slot(session, slot_id)
        if not slot:
            raise SlotNotFound()
        if not slot.is_available:
            raise SlotUnavailable(str(slot_id))

        taken = session.exec(
            select(Booking.id)
            .where(Booking.slot_id == slot_id, col(Booking.status).in_(ACTIVE_STATUSES))
            .limit(1)
        ).first()
        if taken is not None:
            raise SlotUnavailable(str(slot_id))

        client_active_slots = session.exec(
            select(TimeSlot)
            .join(Booking)
            .where(Booking.client_id == client_id)
            .where(col(Booking.status).in_(ACTIVE_STATUSES))
        ).all()

        # Перевіряємо, чи немає перетину з новим слотом
        for active_slot in client_active_slots:
            if slots_overlap(
                slot.start_time, slot.end_time, active_slot.start_time, active_slot.end_time
            ):
                raise AppError(
                    status_code=409,
                    code=ErrorCode.CLIENT_SCHEDULE_CONFLICT,
                    message="Ви вже маєте бронювання на час, що перетинається з цим слотом.",
                )

        booking = Booking(
            client_id=client_id,
            slot_id=slot_id,
            status=BookingStatus.PENDING,
            purpose=purpose,
        )
        session.add(booking)
        session.flush()  # потрібен booking.id для Notification
        reminder_time = compute_reminder_time(
            _as_utc(slot.start_time), now or datetime.now(timezone.utc)
        )
        if reminder_time is not None:
            # UTC, як і решта часу в БД: SQLite відкидає часовий пояс
            session.add(
                Notification(
                    booking_id=booking.id, scheduled_time=reminder_time.astimezone(timezone.utc)
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
        # Страховка: часткове UNIQUE-обмеження uq_bookings_active_slot спрацювало
        # (напр. на СУБД без row-lock) — це теж конфлікт, а не 500.
        session.rollback()
        raise SlotUnavailable(str(slot_id)) from exc
    except Exception:
        session.rollback()
        raise

    session.refresh(booking)
    return booking
