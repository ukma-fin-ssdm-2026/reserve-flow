"""Booking Engine Service: створення бронювання в одній транзакції (FR-005, FR-006)."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from models import Booking, BookingStatus, Notification, TimeSlot
from services.exceptions import SlotUnavailable, SlotNotFound
from services.rooms import lock_slot

from services.validators import slots_overlap
from errors import AppError, ErrorCode

ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)

# FR-014: нагадування за N годин до початку. N у вимогах не визначено — тимчасово 24 год.
REMINDER_LEAD = timedelta(hours=24)


def create_booking(session: Session, client_id: UUID, slot_id: UUID, purpose: str) -> Booking:
    """Блокує слот, перевіряє доступність, створює Booking (Pending) і Notification.

    Усе в одній транзакції. Паралельний запит на той самий слот чекає на
    SELECT ... FOR UPDATE, а після COMMIT першої транзакції бачить її бронювання
    і отримує SlotUnavailable. Будь-який виняток -> ROLLBACK (знімає блокування).
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
        session.add(
            Notification(booking_id=booking.id, scheduled_time=slot.start_time - REMINDER_LEAD)
        )
        session.commit()
    except IntegrityError as exc:
        # Страховка: часткове UNIQUE-обмеження uq_bookings_active_slot спрацювало
        # (напр. на СУБД без row-lock) — це теж конфлікт, а не 500.
        session.rollback()
        raise SlotUnavailable(str(slot_id)) from exc
    except BaseException:
        session.rollback()
        raise

    session.refresh(booking)
    return booking
