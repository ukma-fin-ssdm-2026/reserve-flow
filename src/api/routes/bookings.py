"""Кінцеві точки для роботи з бронюваннями (робота з БД для POST, GET, PATCH).


POST створює бронювання в БД (services/bookings.py, одна транзакція з FOR UPDATE).
GET і PATCH поки працюють із заглушками mocks.py (BOOKINGS, SLOTS, ROOMS) і
переходять на БД в окремих задачах.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlmodel import Session, select

from config import API_PREFIX
from db import get_session
from deps import get_current_user, require_role
from errors import AppError, ErrorCode, error_responses
from models import ActorType, AuditAction, AuditLog, EntityType, Booking, TimeSlot, Room
from schemas.auth import Role, UserOut
from schemas.bookings import BookingCreate, BookingOut, BookingStatus, BookingUpdate
from schemas.common import Page, PaginationParams, paginate, pagination_params
from services import bookings as booking_engine
from services.cancellation import can_cancel
from services.exceptions import SlotNotFound, SlotUnavailable

# Усі кінцеві точки bookings потребують токена (D-06): без нього -> 401.
router = APIRouter(
    prefix=f"{API_PREFIX}/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_current_user)],
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_out(booking: Booking) -> BookingOut:
    return BookingOut(
        id=booking.id,
        slot_id=booking.slot_id,
        user_id=booking.client_id,
        status=booking.status.value,
        purpose=booking.purpose,
        reason=booking.rejection_reason,
        created_at=booking.created_at,
    )


def _can_view(session: Session, user: UserOut, booking: Booking) -> bool:
    """Клієнт бачить свої бронювання, постачальник — на свої кімнати, адмін — усі."""
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.CLIENT:
        return str(booking.client_id) == str(user.id)

    # Перевірка для постачальника: чи належить кімната слота цього постачальника
    slot = session.get(TimeSlot, booking.slot_id)
    if not slot:
        return False
    room = session.get(Room, slot.room_id)
    if not room:
        return False
    return str(room.provider_id) == str(user.id)


def _get_booking_or_404(session: Session, booking_id: UUID) -> Booking:
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Бронювання не знайдено")
    return booking


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BookingOut,
    summary="Створити нове бронювання",
    description=(
        "Бронює вільний слот (FR-005). Нове бронювання має статус `Pending`. "
        "У разі успіху повертає `201` та заголовок `Location`.\n\n"
        "* `404` — слота не існує;\n"
        "* `409 SLOT_UNAVAILABLE` — слот закрито постачальником або він уже має активне бронювання."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def create_booking(
    booking_in: BookingCreate,
    response: Response,
    current_user: Annotated[UserOut, Depends(require_role(Role.CLIENT))],
    session: Annotated[Session, Depends(get_session)],
) -> BookingOut:
    try:
        booking = booking_engine.create_booking(
            session,
            client_id=UUID(str(current_user.id)),
            slot_id=booking_in.slot_id,
            purpose=booking_in.purpose,
        )

        # --- AuditLog (FR-013) ---
        audit = AuditLog(
            actor_type=ActorType.USER,
            user_id=UUID(str(current_user.id)),
            action=AuditAction.BOOKING_CREATED,
            entity_type=EntityType.BOOKING,
            entity_id=booking.id,
        )
        session.add(audit)
        session.commit()

    except SlotNotFound:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Слот не знайдено") from None
    except SlotUnavailable:
        raise AppError(
            status.HTTP_409_CONFLICT, ErrorCode.SLOT_UNAVAILABLE, "Обраний час уже зайнято"
        ) from None

    response.headers["Location"] = f"{API_PREFIX}/bookings/{booking.id}"
    return _to_out(booking)


@router.get(
    "",
    response_model=Page[BookingOut],
    summary="Отримати список бронювань",
    description=(
        "Повертає сторінку бронювань з фільтром за статусом із БД. Клієнт бачить свої бронювання, "
        "постачальник — бронювання на свої кімнати, адміністратор — усі."
    ),
    responses=error_responses(401, 422),
)
async def get_bookings(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    params: Annotated[PaginationParams, Depends(pagination_params)],
    status_filter: Annotated[
        BookingStatus | None,
        Query(alias="status", description="Фільтр за статусом"),
    ] = None,
) -> Page[BookingOut]:
    stmt = select(Booking)
    if status_filter:
        stmt = stmt.where(Booking.status == status_filter)

    all_bookings = session.exec(stmt).all()
    filtered = [b for b in all_bookings if _can_view(session, current_user, b)]

    items = [_to_out(b) for b in filtered]
    return paginate(items, params)


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Отримати бронювання за ID",
    description="Повертає деталі бронювання з БД. Чуже бронювання → `403`, неіснуюче → `404`.",
    responses=error_responses(401, 403, 404, 422),
)
async def get_booking(
    booking_id: Annotated[UUID, Path(description="ID бронювання")],
    current_user: Annotated[UserOut, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> BookingOut:
    booking = _get_booking_or_404(session, booking_id)
    if not _can_view(session, current_user, booking):
        raise AppError(
            status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN, "Немає доступу до цього бронювання"
        )
    return _to_out(booking)


# Хто може перевести бронювання в кожен зі статусів і з яких статусів (D-03).
_ALLOWED_ROLE_FOR_STATUS: dict[BookingStatus, Role] = {
    BookingStatus.CONFIRMED: Role.PROVIDER,
    BookingStatus.REJECTED: Role.PROVIDER,
    BookingStatus.CANCELLED: Role.CLIENT,
}
_ALLOWED_FROM: dict[BookingStatus, set[str]] = {
    BookingStatus.CONFIRMED: {BookingStatus.PENDING.value},
    BookingStatus.REJECTED: {BookingStatus.PENDING.value},
    BookingStatus.CANCELLED: {BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value},
}


@router.patch(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Змінити статус бронювання в БД",
    description="Змінює статус бронювання та оновлює стан слота в БД (D-03, FR-007).",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def update_booking(
    booking_id: Annotated[UUID, Path(description="ID бронювання")],
    booking_in: BookingUpdate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> BookingOut:
    booking = _get_booking_or_404(session, booking_id)

    allowed_role = _ALLOWED_ROLE_FOR_STATUS.get(booking_in.status)
    if allowed_role is None:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Неможливо перевести бронювання в статус {booking_in.status.value}",
        )

    if current_user.role != allowed_role or not _can_view(session, current_user, booking):
        raise AppError(
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            "Недостатньо прав для цієї зміни статусу",
        )

    if booking.status.value not in _ALLOWED_FROM[booking_in.status]:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Перехід {booking.status.value} → {booking_in.status.value} не дозволений",
        )

    slot_to_release = None

    if booking_in.status == BookingStatus.CANCELLED:
        slot = session.get(TimeSlot, booking.slot_id)

        if slot is None:
            raise AppError(
                status.HTTP_409_CONFLICT,
                ErrorCode.INVALID_STATUS_TRANSITION,
                "Слот бронювання не знайдено",
            )

        slot_start = slot.start_time

        # SQLite може повертати datetime без tzinfo.
        # Це коректно лише за умови, що naive-час у БД зберігається в UTC.
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)

        if not can_cancel(slot_start, _now()):
            raise AppError(
                status.HTTP_409_CONFLICT,
                ErrorCode.CANCELLATION_TOO_LATE,
                "Скасувати можна не пізніше ніж за 2 години до початку",
            )

        slot_to_release = slot

    # Змінюємо статус бронювання.
    booking.status = booking_in.status
    if booking_in.reason:
        booking.rejection_reason = booking_in.reason

    audit_action = {
        BookingStatus.CONFIRMED: AuditAction.BOOKING_CONFIRMED,
        BookingStatus.REJECTED: AuditAction.BOOKING_REJECTED,
        BookingStatus.CANCELLED: AuditAction.BOOKING_CANCELLED,
    }.get(booking_in.status)

    try:
        session.add(booking)

        # Скасування звільняє слот у тій самій транзакції.
        if slot_to_release is not None:
            slot_to_release.is_available = True
            session.add(slot_to_release)

        # Один запис аудиту на одну зміну статусу.
        if audit_action is not None:
            session.add(
                AuditLog(
                    actor_type=ActorType.USER,
                    user_id=UUID(str(current_user.id)),
                    action=audit_action,
                    entity_type=EntityType.BOOKING,
                    entity_id=booking_id,
                    details=booking_in.reason,
                )
            )

        session.commit()
        session.refresh(booking)

    except Exception:
        session.rollback()
        raise

    return _to_out(booking)


# Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
# Код вичитано, відредаговано та затверджено учасниками команди
