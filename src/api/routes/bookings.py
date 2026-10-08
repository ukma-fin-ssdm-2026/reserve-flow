"""Кінцеві точки для роботи з бронюваннями."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Path, Query, Response, status

from config import API_PREFIX
from deps import get_current_user, require_role
from errors import AppError, ErrorCode, error_responses
from schemas.auth import Role, UserOut
from schemas.bookings import BookingCreate, BookingOut, BookingStatus, BookingUpdate
from schemas.common import Page, PaginationParams, paginate

# Усі кінцеві точки bookings потребують токена (D-06): без нього -> 401.
router = APIRouter(
    prefix=f"{API_PREFIX}/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_current_user)],
)

# --- Заглушки (Mocks) ---
MOCK_USER_ID = uuid4()
MOCK_SLOT_ID = uuid4()
MOCK_BOOKING_ID = uuid4()

MOCK_BOOKING = BookingOut(
    id=MOCK_BOOKING_ID,
    slot_id=MOCK_SLOT_ID,
    user_id=MOCK_USER_ID,
    status=BookingStatus.PENDING,
    purpose="Зустріч клубу настільних ігор",
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BookingOut,
    summary="Створити нове бронювання",
    description="Бронює вільний слот. У разі успіху повертає 201 та заголовок `Location`.",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def create_booking(
    booking_in: BookingCreate,
    response: Response,
    # Бронювати може лише клієнт; постачальник чи адмін -> 403.
    current_user: Annotated[UserOut, Depends(require_role(Role.CLIENT))],
) -> BookingOut:
    # Формуємо заглушку-відповідь на основі вхідних даних
    new_booking = BookingOut(
        id=uuid4(),
        slot_id=booking_in.slot_id,
        user_id=current_user.id,
        status=BookingStatus.PENDING,
        purpose=booking_in.purpose,
    )
    
    # Додаємо Location header
    response.headers["Location"] = f"{API_PREFIX}/bookings/{new_booking.id}"
    return new_booking


@router.get(
    "",
    response_model=Page[BookingOut],
    summary="Отримати список бронювань",
    description="Повертає сторінку бронювань. Підтримує пагінацію та фільтрацію за статусом.",
    responses=error_responses(401, 422),
)
async def get_bookings(
    params: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[
        BookingStatus | None, 
        Query(alias="status", description="Фільтр за статусом")
    ] = None,
) -> Page[BookingOut]:
    # Заглушка: генеруємо масив з 3 елементів
    items = [MOCK_BOOKING, MOCK_BOOKING.model_copy(update={"id": uuid4()}), MOCK_BOOKING.model_copy(update={"id": uuid4()})]
    
    # Імітація фільтрації (якщо б статуси відрізнялись)
    if status_filter:
        items = [b for b in items if b.status == status_filter]
        
    return paginate(items, params)


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Отримати бронювання за ID",
    description="Повертає деталі конкретного бронювання.",
    responses=error_responses(401, 403, 404, 422),
)
async def get_booking(
    booking_id: Annotated[UUID, Path(description="ID бронювання")],
) -> BookingOut:
    return MOCK_BOOKING.model_copy(update={"id": booking_id})


# Хто може перевести бронювання в кожен зі статусів (D-03).
# Pending — лише початковий статус, перейти в нього не можна.
_ALLOWED_ROLE_FOR_STATUS: dict[BookingStatus, Role] = {
    BookingStatus.CONFIRMED: Role.PROVIDER,
    BookingStatus.REJECTED: Role.PROVIDER,
    BookingStatus.CANCELLED: Role.CLIENT,
}

PATCH_DESCRIPTION = """Змінює статус бронювання (D-03). Замість окремих `/cancel`, `/confirm`, `/decision`.

| З | В | Хто | Умова | Помилка |
|---|---|---|---|---|
| `Pending` | `Confirmed` | Постачальник цієї кімнати | — | `403` чужа кімната або інша роль |
| `Pending` | `Rejected` | Постачальник цієї кімнати | `reason` обов'язковий (FR-010) | `422` без причини |
| `Pending`, `Confirmed` | `Cancelled` | Клієнт-власник | до початку ≥ 2 год (FR-007) | `409 CANCELLATION_TOO_LATE` |

Будь-який інший перехід (зокрема в `Pending` або з `Rejected` / `Cancelled`) → `409 INVALID_STATUS_TRANSITION`.

Lab 4: перевіряється роль і правило для `reason`; власник ресурсу й 2 години перевірятимуться, коли з'явиться БД.
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
) -> BookingOut:
    allowed_role = _ALLOWED_ROLE_FOR_STATUS.get(booking_in.status)
    if allowed_role is None:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Неможливо перевести бронювання в статус {booking_in.status.value}",
        )
    if current_user.role != allowed_role:
        raise AppError(
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            "Недостатньо прав для цієї зміни статусу",
        )
    # Повертаємо заглушку з оновленими даними
    return MOCK_BOOKING.model_copy(
        update={
            "id": booking_id,
            "status": booking_in.status,
            "reason": booking_in.reason,
        }
    )


    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini. 
    # Код вичитано, відредаговано та затверджено учасниками команди