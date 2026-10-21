"""Схеми для приміщень."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class BuildingEnum(str, Enum):
    CORP_1 = "Корпус 1"
    CORP_2 = "Корпус 2"
    CORP_3 = "Корпус 3"
    CORP_4 = "Корпус 4"
    CORP_5 = "Корпус 5"
    CORP_6 = "Корпус 6"
    CORP_7 = "Корпус 7"
    CORP_8 = "Корпус 8"
    CORP_9 = "Корпус 9"
    CORP_10 = "Корпус 10"
    CORP_KMC = "КМЦ"
    CORP_LIBRARY = "Наукова бібліотека"
    CORP_MUSEUM = "Історико-музейний комплекс НаУКМА"


class BuildingEnumEn(str, Enum):
    CORP_1 = "Building 1"
    CORP_2 = "Building 2"
    CORP_3 = "Building 3"
    CORP_4 = "Building 4"
    CORP_5 = "Building 5"
    CORP_6 = "Building 6"
    CORP_7 = "Building 7"
    CORP_8 = "Building 8"
    CORP_9 = "Building 9"
    CORP_10 = "Building 10"
    CORP_KMC = "Cultural and Art Center (KMC)"
    CORP_LIBRARY = "Research Library"
    CORP_MUSEUM = "Historical and Museum Complex of NaUKMA"


class ModerationStatusEnum(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class RoomOut(BaseModel):
    """Схема виводу для приміщення."""

    id: UUID = Field(..., description="UUID приміщення")
    provider_id: UUID = Field(..., description="UUID постачальника (відповідального)")
    name_ua: str = Field(..., examples=["Аудиторія 1-225"])
    name_en: str = Field(..., examples=["Room 1-225"])
    building_ua: BuildingEnum = Field(..., description="Корпус (українською)")
    building_en: BuildingEnumEn = Field(..., description="Building (English)")
    room_number: str = Field(..., examples=["225"])
    capacity: int = Field(..., ge=1, examples=[40])
    has_projector: bool = Field(..., description="Наявність проєктора")
    is_shelter: bool = Field(..., description="Чи є укриттям")
    moderation_status: ModerationStatusEnum = Field(..., description="Статус модерації")

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini.
    # Код вичитано, відредаговано та затверджено учасниками команди
