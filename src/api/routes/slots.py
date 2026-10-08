"""Кінцеві точки для роботи з часовими слотами."""
from datetime import date, time
from fastapi import APIRouter, Depends, Path, Query, status

from config import API_PREFIX
from errors import AppError, error_responses
from mocks import SLOTS, find_by_id
from schemas.common import Page, PaginationParams, paginate, pagination_params
from schemas.slots import SlotOut, SlotPatchIn
from schemas.rooms import BuildingEnumEn, BuildingEnum
from deps import CurrentUser, get_current_user

router = APIRouter(prefix=f"{API_PREFIX}/slots", tags=["slots"])

@router.get(
    "",
    response_model=Page[SlotOut],
    summary="Пошук вільних слотів",
    description="Повертає список слотів за фільтрами з пагінацією. Якщо end <= start, повертається статус 422.",
    responses=error_responses(422, 500),
)
async def search_slots(
    # Фільтри
    search_date: date | None = Query(None, description="Дата для пошуку (YYYY-MM-DD)"),
    start: time | None = Query(None, description="Початок інтервалу (HH:MM:SS)"),
    end: time | None = Query(None, description="Кінець інтервалу (HH:MM:SS)"),
    capacity: int | None = Query(None, ge=1, le=500, description="Мінімальна місткість (1-500)"),
    has_projector: bool | None = Query(None, description="Чи потрібен проєктор"),
    is_shelter: bool | None = Query(None, description="Чи потрібне укриття"),
    building: BuildingEnum | None = Query(None, description="Корпус"),
    # Пагінація з common.py
    params: PaginationParams = Depends(pagination_params)
) -> Page[SlotOut]:
    """Фільтрує слоти та повертає результат у форматі Page."""
    # Бізнес-валідація 422
    if start and end and end <= start:
        raise AppError(
            message="Час закінчення має бути строго пізніше за час початку",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_TIME_RANGE"
        )
    
    #зашлушка: повертаємо всі слоти без фільтрації
    slots_out = [SlotOut(**slot) for slot in SLOTS]
    return paginate(slots_out, params)


@router.patch(
    "/{slot_id}",
    response_model=SlotOut,
    summary="Змінити статус слота",
    description="Дозволяє постачальнику закрити або відкрити слот. Повертає 409, якщо є активне бронювання.",
    responses=error_responses(401, 403, 404, 409, 422, 500),
)
async def patch_slot(
    slot_id: str = Path(..., description="ID слота"),
    payload: SlotPatchIn = None,
    current_user: CurrentUser = Depends(get_current_user)
) -> SlotOut:
    """Оновлення статусу слота (тільки для постачальника)."""
    # 1. Перевірка ролі (403)
    if current_user.role != "Provider":
         raise AppError(
            message="Лише постачальник може змінювати статус слота",
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN"
        )
    
    # 2. Пошук слота (404)
    slot = find_by_id(SLOTS, slot_id)
    if not slot:
        raise AppError(
            message="Слот не знайдено",
            status_code=status.HTTP_404_NOT_FOUND,
            code="SLOT_NOT_FOUND"
        )
        
    # 3. Імітація 409 помилки (ACTIVE_BOOKING_NEEDS_CONFIRMATION)
    #Якщо слот - це SLOT_2_ID (на нього є тестове бронювання BOOKING_1_ID), і ми намагаємося його закрити
    if slot_id == "b2000000-0000-4000-8000-000000000002" and not payload.is_available:
        raise AppError(
            message="Слот має активне бронювання. Потрібне окреме підтвердження для скасування.",
            status_code=status.HTTP_409_CONFLICT,
            code="ACTIVE_BOOKING_NEEDS_CONFIRMATION"
        )

    #Заглушка успіху (повертає знайдений слот зі зміненим статусом)
    updated_slot = slot.copy()
    updated_slot["is_available"] = payload.is_available
    updated_slot["closure_reason"] = payload.closure_reason
    return SlotOut(**updated_slot)

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini. 
    # Код вичитано, відредаговано та затверджено учасниками команди