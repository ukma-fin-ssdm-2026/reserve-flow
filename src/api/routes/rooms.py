"""Кінцеві точки для роботи з приміщеннями."""
from fastapi import APIRouter, Path, status

from config import API_PREFIX
from errors import AppError, error_responses
from mocks import ROOMS, find_by_id
from schemas.rooms import RoomOut

router = APIRouter(prefix=f"{API_PREFIX}/rooms", tags=["rooms"])

@router.get(
    "/{room_id}",
    response_model=RoomOut,
    summary="Деталі кімнати",
    description="Повертає детальну інформацію про кімнату за її ідентифікатором.",
    responses=error_responses(404, 422, 500),
)
async def get_room(
    room_id: str = Path(..., description="ID кімнати")
) -> RoomOut:
    """Отримання деталей кімнати."""
    room = find_by_id(ROOMS, room_id)
    if not room:
        raise AppError(
            message="Кімнату не знайдено",
            status_code=status.HTTP_404_NOT_FOUND,
            code="ROOM_NOT_FOUND"
        )
        
    return RoomOut(**room)