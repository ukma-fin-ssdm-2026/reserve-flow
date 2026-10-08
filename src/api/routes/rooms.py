"""Кінцеві точки для роботи з приміщеннями."""
from fastapi import APIRouter, Depends, Path, status

from config import API_PREFIX
from deps import get_current_user
from errors import AppError, ErrorCode, error_responses
from mocks import ROOMS, find_by_id
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
    room_id: str = Path(..., description="ID кімнати"),
) -> RoomOut:
    """Отримання деталей кімнати."""
    room = find_by_id(ROOMS, room_id)
    if not room:
        raise AppError(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Кімнату не знайдено")

    return RoomOut(**room)
