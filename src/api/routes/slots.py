"""Кінцеві точки для роботи з часовими слотами."""

from datetime import date, datetime, time, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session, select

from config import API_PREFIX
from db import get_session
from deps import get_current_user, require_role
from errors import AppError, ErrorCode, ErrorDetail, error_responses
from mocks import KYIV
from models import Booking, BookingStatus, Room, TimeSlot
from schemas.auth import Role, UserOut
from schemas.common import Page, PaginationParams, paginate, pagination_params
from schemas.rooms import BuildingEnum
from schemas.slots import SlotOut, SlotPatchIn

# Усі кінцеві точки потребують токена (D-06, default deny): без нього -> 401.
router = APIRouter(
    prefix=f"{API_PREFIX}/slots",
    tags=["slots"],
    dependencies=[Depends(get_current_user)],
)


def _to_kyiv(dt: datetime) -> datetime:
    """Конвертує datetime з БД у часовий пояс Києва (враховує naive UTC з SQLite)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KYIV)


def _slot_to_out(slot: TimeSlot) -> SlotOut:
    return SlotOut(
        id=str(slot.id),
        room_id=str(slot.room_id),
        start_time=_to_kyiv(slot.start_time),
        end_time=_to_kyiv(slot.end_time),
        is_available=slot.is_available,
        closure_reason=slot.closure_reason,
    )


@router.get(
    "",
    response_model=Page[SlotOut],
    summary="Пошук вільних слотів",
    description=(
        "Повертає вільні слоти (FR-003): слот не закритий постачальником і не має активного "
        "бронювання (`Pending` / `Confirmed`). "
        "Усі фільтри необов'язкові й поєднуються через «і»:\n\n"
        "* `room_id` — слоти конкретного приміщення "
        "(D-02: плоска структура замість `/rooms/{id}/slots`);\n"
        "* `date` — слот у цей день;\n"
        "* `start` / `end` — слот повністю в інтервалі: "
        "починається не раніше `start` і закінчується не пізніше `end`;\n"
        "* `capacity` — місткість приміщення не менша;\n"
        "* `has_projector`, `is_shelter`, `building` — властивості приміщення.\n\n"
        "Час — за Києвом. Якщо `end <= start`, повертається `422`."
    ),
    responses=error_responses(401, 422, 500),
)
async def search_slots(
    session: Annotated[Session, Depends(get_session)],
    room_id: UUID | None = Query(None, description="ID приміщення"),
    search_date: date | None = Query(None, alias="date", description="Дата для пошуку"),
    start: time | None = Query(None, description="Початок інтервалу"),
    end: time | None = Query(None, description="Кінець інтервалу"),
    capacity: int | None = Query(None, ge=1, le=500, description="Мінімальна місткість"),
    has_projector: bool | None = Query(None, description="Проєктор"),
    is_shelter: bool | None = Query(None, description="Укриття"),
    building: BuildingEnum | None = Query(None, description="Корпус"),
    params: PaginationParams = Depends(pagination_params),
) -> Page[SlotOut]:
    """Фільтрує слоти в БД та повертає результат."""
    if start and end and end <= start:
        raise AppError(
            422,
            ErrorCode.VALIDATION_ERROR,
            "Некоректні дані запиту",
            [
                ErrorDetail(
                    field="end", issue="Час закінчення має бути строго пізніше за час початку"
                )
            ],
        )

    stmt = (
        select(TimeSlot, Room)
        .join(Room, TimeSlot.room_id == Room.id)
        .where(TimeSlot.is_available.is_(True))
    )

    if room_id is not None:
        stmt = stmt.where(TimeSlot.room_id == room_id)
    if capacity is not None:
        stmt = stmt.where(Room.capacity >= capacity)
    if has_projector is not None:
        stmt = stmt.where(Room.has_projector == has_projector)
    if is_shelter is not None:
        stmt = stmt.where(Room.is_shelter == is_shelter)
    if building is not None:
        stmt = stmt.where(Room.building_ua == building.value)

    rows = session.exec(stmt).all()

    booked_ids = set(
        session.exec(
            select(Booking.slot_id).where(
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            )
        ).all()
    )

    slots_out: list[SlotOut] = []
    for slot, _room in rows:
        if slot.id in booked_ids:
            continue

        starts = _to_kyiv(slot.start_time)
        ends = _to_kyiv(slot.end_time)

        if search_date and starts.date() != search_date:
            continue
        if start and starts.time().strftime("%H:%M:%S") < start.strftime("%H:%M:%S"):
            continue
        if end and ends.time().strftime("%H:%M:%S") > end.strftime("%H:%M:%S"):
            continue

        slots_out.append(_slot_to_out(slot))

    return paginate(slots_out, params)


@router.patch(
    "/{slot_id}",
    response_model=SlotOut,
    summary="Змінити статус слота",
    description=(
        "Дозволяє постачальнику закрити або відкрити слот (FR-008, FR-009). "
        "Під час закриття `closure_reason` обов'язковий, інакше `422`. "
        "Повертає `409`, якщо на слоті є активне бронювання."
    ),
    responses=error_responses(401, 403, 404, 409, 422, 500),
)
async def patch_slot(
    payload: SlotPatchIn,
    session: Annotated[Session, Depends(get_session)],
    # Лише постачальник; інша роль -> 403 (D-06)
    current_user: Annotated[UserOut, Depends(require_role(Role.PROVIDER))],
    slot_id: str = Path(..., description="ID слота"),
) -> SlotOut:
    """Оновлення статусу слота в БД (тільки для постачальника)."""
    try:
        slot_uuid = UUID(slot_id)
    except ValueError:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Слот не знайдено")

    # 1. Пошук слота в БД (404)
    slot = session.get(TimeSlot, slot_uuid)
    if not slot:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Слот не знайдено")

    # 2. Перевірка приналежності кімнати поточному постачальнику (403)
    room = session.get(Room, slot.room_id)
    if not room or str(room.provider_id) != str(current_user.id):
        raise AppError(
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            "Немає прав для редагування слотів чужої кімнати",
        )

    # 3. Перевірка активних бронювань у БД (409)
    if not payload.is_available:
        active_booking = session.exec(
            select(Booking).where(
                Booking.slot_id == slot.id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            )
        ).first()
        if active_booking:
            raise AppError(
                status.HTTP_409_CONFLICT,
                ErrorCode.ACTIVE_BOOKING_NEEDS_CONFIRMATION,
                "Слот має активне бронювання. Потрібне окреме підтвердження для скасування.",
            )

    # 4. Збереження змін у БД
    slot.is_available = payload.is_available
    slot.closure_reason = None if payload.is_available else payload.closure_reason
    session.add(slot)
    session.commit()
    session.refresh(slot)

    return _slot_to_out(slot)

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
