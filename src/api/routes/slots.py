"""Кінцеві точки для роботи з часовими слотами."""

from datetime import date, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from config import API_PREFIX
from deps import get_current_user, require_role
from errors import AppError, ErrorCode, ErrorDetail, error_responses
from mocks import BOOKINGS, KYIV, ROOMS, SLOTS, find_by_id
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

# Слот із тестовим активним бронюванням (BOOKING_1_ID у mocks.py) — для демонстрації 409.
_SLOT_WITH_ACTIVE_BOOKING = "b2000000-0000-4000-8000-000000000002"


@router.get(
    "",
    response_model=Page[SlotOut],
    summary="Пошук вільних слотів",
    description=(
        "Повертає вільні слоти (FR-003): слот не закритий постачальником і не має активного "
        "бронювання (`Pending` / `Confirmed`). Усі фільтри необов'язкові й поєднуються через «і»:\n\n"
        "* `room_id` — слоти конкретного приміщення (D-02: плоска структура замість `/rooms/{id}/slots`);\n"
        "* `date` — слот у цей день;\n"
        "* `start` / `end` — слот повністю в інтервалі: починається не раніше `start` і закінчується не пізніше `end`;\n"
        "* `capacity` — місткість приміщення не менша;\n"
        "* `has_projector`, `is_shelter`, `building` — властивості приміщення.\n\n"
        "Час — за Києвом. Якщо `end <= start`, повертається `422`."
    ),
    responses=error_responses(401, 422, 500),
)
async def search_slots(
    # Фільтри
    room_id: UUID | None = Query(None, description="ID приміщення: лише слоти цієї кімнати (D-02)"),
    search_date: date | None = Query(
        None, alias="date", description="Дата для пошуку (YYYY-MM-DD)"
    ),
    start: time | None = Query(None, description="Початок інтервалу (HH:MM:SS)"),
    end: time | None = Query(None, description="Кінець інтервалу (HH:MM:SS)"),
    capacity: int | None = Query(None, ge=1, le=500, description="Мінімальна місткість (1-500)"),
    has_projector: bool | None = Query(None, description="Чи потрібен проєктор"),
    is_shelter: bool | None = Query(None, description="Чи потрібне укриття"),
    building: BuildingEnum | None = Query(None, description="Корпус"),
    # Пагінація з common.py
    params: PaginationParams = Depends(pagination_params),
) -> Page[SlotOut]:
    """Фільтрує слоти та повертає результат у форматі Page."""
    # Бізнес-валідація 422 (формат D-04: поле і що не так)
    if start and end and end <= start:
        raise AppError(
            422,  # HTTP_422_UNPROCESSABLE_CONTENT (назва константи різна у версіях Starlette)
            ErrorCode.VALIDATION_ERROR,
            "Некоректні дані запиту",
            [
                ErrorDetail(
                    field="end", issue="Час закінчення має бути строго пізніше за час початку"
                )
            ],
        )

    booked = {b["slot_id"] for b in BOOKINGS if b["status"] in ("Pending", "Confirmed")}

    def matches(slot: dict) -> bool:
        if not slot["is_available"] or slot["id"] in booked:
            return False
        if room_id and slot["room_id"] != str(room_id):
            return False
        starts = slot["start_time"].astimezone(KYIV)
        ends = slot["end_time"].astimezone(KYIV)
        if search_date and starts.date() != search_date:
            return False
        if start and starts.time() < start:
            return False
        if end and ends.time() > end:
            return False
        room = find_by_id(ROOMS, slot["room_id"])
        if room is None:
            return False
        if capacity and room["capacity"] < capacity:
            return False
        if has_projector is not None and room["has_projector"] != has_projector:
            return False
        if is_shelter is not None and room["is_shelter"] != is_shelter:
            return False
        if building and room["building_ua"] != building.value:
            return False
        return True

    slots_out = [SlotOut(**slot) for slot in SLOTS if matches(slot)]
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
    # Лише постачальник; інша роль -> 403 (D-06)
    current_user: Annotated[UserOut, Depends(require_role(Role.PROVIDER))],
    slot_id: str = Path(..., description="ID слота"),
) -> SlotOut:
    """Оновлення статусу слота (тільки для постачальника)."""
    # 1. Пошук слота (404)
    slot = find_by_id(SLOTS, slot_id)
    if not slot:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Слот не знайдено")

    # 2. Імітація 409: на SLOT_2_ID є тестове бронювання BOOKING_1_ID, і ми намагаємося його закрити
    if slot_id == _SLOT_WITH_ACTIVE_BOOKING and not payload.is_available:
        raise AppError(
            status.HTTP_409_CONFLICT,
            ErrorCode.ACTIVE_BOOKING_NEEDS_CONFIRMATION,
            "Слот має активне бронювання. Потрібне окреме підтвердження для скасування.",
        )

    # Заглушка успіху (повертає знайдений слот зі зміненим статусом)
    updated_slot = slot.copy()
    updated_slot["is_available"] = payload.is_available
    updated_slot["closure_reason"] = None if payload.is_available else payload.closure_reason
    return SlotOut(**updated_slot)

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
