"""Кінцеві точки для роботи з приміщеннями."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from sqlmodel import Session

from config import API_PREFIX
from db import get_session
from deps import get_current_user
from errors import AppError, ErrorCode, error_responses
from models import Room
from schemas.rooms import RoomOut

# Усі кінцеві точки потребують токена (D-06, default deny): без нього -> 401.
router = APIRouter(
    prefix=f"{API_PREFIX}/rooms",
    tags=["rooms"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/{room_id}",
    response_model=RoomOut,
    summary="Деталі кімнати",
    description="Повертає детальну інформацію про кімнату за її ідентифікатором.",
    responses=error_responses(401, 404, 422, 500),
)
async def get_room(
    session: Annotated[Session, Depends(get_session)],
    room_id: str = Path(..., description="ID кімнати"),
) -> RoomOut:
    """Отримання деталей кімнати з БД."""
    try:
        room_uuid = UUID(room_id)
    except ValueError:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Кімнату не знайдено")

    room = session.get(Room, room_uuid)
    if not room:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Кімнату не знайдено")

    return RoomOut(
        id=room.id,
        provider_id=room.provider_id,
        name_ua=room.name_ua,
        name_en=room.name_en,
        capacity=room.capacity,
        has_projector=room.has_projector,
        is_shelter=room.is_shelter,
        building_ua=room.building_ua.value,
        building_en=room.building_en.value,
        room_number=room.room_number,
        moderation_status=room.moderation_status.value,
        approved_by=str(room.approved_by) if room.approved_by else None,
    )

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude.
    # Код вичитано, відредаговано та затверджено учасниками команди
