"""Кінцеві точки для роботи з бронюваннями.

POST створює бронювання в БД (services/bookings.py, одна транзакція з FOR UPDATE).
GET і PATCH поки працюють із заглушками mocks.py (BOOKINGS, SLOTS, ROOMS) і
переходять на БД в окремих задачах.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlmodel import Session

from services.cancellation import can_cancel

from config import API_PREFIX
from db import get_session
from deps import get_current_user, require_role
from errors import AppError, ErrorCode, error_responses
from mocks import BOOKINGS, KYIV, ROOMS, SLOTS, find_by_id
from models import ActorType, AuditAction, AuditLog, EntityType
from schemas.auth import Role, UserOut
from schemas.bookings import BookingCreate, BookingOut, BookingStatus, BookingUpdate
from schemas.common import Page, PaginationParams, paginate, pagination_params
from services import bookings as booking_engine
from services.exceptions import SlotNotFound, SlotUnavailable

# Усі кінцеві точки bookings потребують токена (D-06): без нього -> 401.
router = APIRouter(
    prefix=f"{API_PREFIX}/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_current_user)],
)

# Статуси, за яких бронювання займає слот.
_ACTIVE_STATUSES = {BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value}


def _now() -> datetime:
    """Поточний час у часовій зоні Києва (окрема функція, щоб підміняти в тестах)."""
    return datetime.now(KYIV)


def _to_out(booking: dict) -> BookingOut:
    return BookingOut(
        id=booking["id"],
        slot_id=booking["slot_id"],
        user_id=booking["client_id"],
        status=booking["status"],
        purpose=booking["purpose"],
        reason=booking["rejection_reason"],
        created_at=booking["created_at"],
    )


def _room_provider_id(slot_id: str) -> str | None:
    """Постачальник кімнати, до якої належить слот."""
    slot = find_by_id(SLOTS, slot_id)
    room = find_by_id(ROOMS, slot["room_id"]) if slot else None
    return room["provider_id"] if room else None


def _can_view(user: UserOut, booking: dict) -> bool:
    """Клієнт бачить свої бронювання, постачальник — на свої кімнати, адмін — усі."""
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.CLIENT:
        return booking["client_id"] == user.id
    return _room_provider_id(booking["slot_id"]) == user.id


def _get_booking_or_404(booking_id: UUID) -> dict:
    booking = find_by_id(BOOKINGS, str(booking_id))
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
    # Бронювати може лише клієнт; постачальник чи адмін -> 403.
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

        # --- Notification Scheduler (Stub) ---
        print(
            f"[{_now()}] Notification Scheduler: Нагадування сплановано для бронювання {booking.id}"
        )

    except SlotNotFound:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Слот не знайдено") from None
    except SlotUnavailable:
        raise AppError(
            status.HTTP_409_CONFLICT, ErrorCode.SLOT_UNAVAILABLE, "Обраний час уже зайнято"
        ) from None

    response.headers["Location"] = f"{API_PREFIX}/bookings/{booking.id}"
    return BookingOut(
        id=booking.id,
        slot_id=booking.slot_id,
        user_id=booking.client_id,
        status=booking.status.value,
        purpose=booking.purpose,
        reason=booking.rejection_reason,
        created_at=booking.created_at,
    )


@router.get(
    "",
    response_model=Page[BookingOut],
    summary="Отримати список бронювань",
    description=(
        "Повертає сторінку бронювань з фільтром за статусом. Клієнт бачить свої бронювання, "
        "постачальник — бронювання на свої кімнати, адміністратор — усі."
    ),
    responses=error_responses(401, 422),
)
async def get_bookings(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    params: Annotated[PaginationParams, Depends(pagination_params)],
    status_filter: Annotated[
        BookingStatus | None,
        Query(alias="status", description="Фільтр за статусом"),
    ] = None,
) -> Page[BookingOut]:
    items = [_to_out(b) for b in BOOKINGS if _can_view(current_user, b)]
    if status_filter:
        items = [b for b in items if b.status == status_filter]
    return paginate(items, params)


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Отримати бронювання за ID",
    description="Повертає деталі бронювання. Чуже бронювання → `403`, неіснуюче → `404`.",
    responses=error_responses(401, 403, 404, 422),
)
async def get_booking(
    booking_id: Annotated[UUID, Path(description="ID бронювання")],
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> BookingOut:
    booking = _get_booking_or_404(booking_id)
    if not _can_view(current_user, booking):
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

PATCH_DESCRIPTION = """Змінює статус бронювання (D-03).
Замість окремих `/cancel`, `/confirm`, `/decision`.

| З | В | Хто | Умова | Помилка |
|---|---|---|---|---|
| `Pending` | `Confirmed` | Постачальник | — | `403` чужа кімната або інша роль |
| `Pending` | `Rejected` | Постачальник | `reason` обов'язковий (FR-010) | `422` без причини |
| `Pending`, `Confirmed` | `Cancelled` | Клієнт-власник | за ≥ 2 год | `409` CANCELLATION_TOO_LATE |

Будь-який інший перехід (зокрема в `Pending` або з `Rejected` / `Cancelled`)
-> `409 INVALID_STATUS_TRANSITION`.
Неіснуюче бронювання -> `404`.
"""


@router.patch(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Змінити статус бронювання",
    description=PATCH_DESCRIPTION,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def update_booking(
    booking_id: Annotated[UUID, Path(description="ID бронювання")],
    booking_in: BookingUpdate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> BookingOut:
    booking = _get_booking_or_404(booking_id)

    allowed_role = _ALLOWED_ROLE_FOR_STATUS.get(booking_in.status)
    if allowed_role is None:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Неможливо перевести бронювання в статус {booking_in.status.value}",
        )
    # Роль не та або бронювання/кімната чужі -> 403
    if current_user.role != allowed_role or not _can_view(current_user, booking):
        raise AppError(
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            "Недостатньо прав для цієї зміни статусу",
        )
    if booking["status"] not in _ALLOWED_FROM[booking_in.status]:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Перехід {booking['status']} → {booking_in.status.value} не дозволений",
        )
    if booking_in.status == BookingStatus.CANCELLED:
        slot = find_by_id(SLOTS, booking["slot_id"])
        if slot and not can_cancel(slot["start_time"], _now()):
            raise AppError(
                status.HTTP_409_CONFLICT,
                ErrorCode.CANCELLATION_TOO_LATE,
                "Скасувати можна не пізніше ніж за 2 години до початку",
            )

    # --- AuditLog (FR-013) ---
    audit_action = None
    if booking_in.status == BookingStatus.CONFIRMED:
        audit_action = AuditAction.BOOKING_CONFIRMED
    elif booking_in.status == BookingStatus.REJECTED:
        audit_action = AuditAction.BOOKING_REJECTED
    elif booking_in.status == BookingStatus.CANCELLED:
        audit_action = AuditAction.BOOKING_CANCELLED

    if audit_action:
        audit = AuditLog(
            actor_type=ActorType.USER,
            user_id=UUID(str(current_user.id)),
            action=audit_action,
            entity_type=EntityType.BOOKING,
            entity_id=booking_id,
            details=booking_in.reason,
        )
        session.add(audit)
        session.commit()

    # Заглушка: повертаємо бронювання з новим статусом, не змінюючи mocks.py
    return _to_out(booking).model_copy(
        update={"status": booking_in.status, "reason": booking_in.reason}
    )

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
