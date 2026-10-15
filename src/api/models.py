"""SQLModel-моделі за data-model.md."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, Index, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


def _enum(enum_cls: type[Enum], *, nullable: bool = False) -> Column:
    """VARCHAR (а не native ENUM), зберігає значення, а не імена членів:
    однаково працює в PostgreSQL і SQLite, зміна переліку не потребує ALTER TYPE."""
    return Column(
        SAEnum(
            enum_cls,
            native_enum=False,
            length=64,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=nullable,
    )


def _ts(*, nullable: bool = False) -> Column:
    return Column(DateTime(timezone=True), nullable=nullable)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums ---------------------------------------------------------------------


class Role(str, Enum):
    CLIENT = "Client"
    PROVIDER = "Provider"
    ADMIN = "Admin"


class ModerationStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class BookingStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class NotificationStatus(str, Enum):
    PENDING = "Pending"
    SENT = "Sent"
    FAILED = "Failed"


class ActorType(str, Enum):
    USER = "User"
    SYSTEM = "System"


class AuditAction(str, Enum):
    BOOKING_CREATED = "BookingCreated"
    BOOKING_CANCELLED = "BookingCancelled"
    BOOKING_CONFIRMED = "BookingConfirmed"
    BOOKING_REJECTED = "BookingRejected"
    SLOT_STATUS_CHANGED = "SlotStatusChanged"
    ROOM_REQUEST_SUBMITTED = "RoomRequestSubmitted"
    ROOM_APPROVED = "RoomApproved"
    ROOM_REJECTED = "RoomRejected"
    USER_BLOCKED = "UserBlocked"
    USER_UNBLOCKED = "UserUnblocked"
    NOTIFICATION_FAILED = "NotificationFailed"


class EntityType(str, Enum):
    USER = "User"
    ROOM = "Room"
    TIME_SLOT = "TimeSlot"
    BOOKING = "Booking"
    NOTIFICATION = "Notification"


class BuildingUA(str, Enum):
    B1 = "Корпус 1"
    B2 = "Корпус 2"
    B3 = "Корпус 3"
    B4 = "Корпус 4"
    B5 = "Корпус 5"
    B6 = "Корпус 6"
    B7 = "Корпус 7"
    B8 = "Корпус 8"
    B9 = "Корпус 9"
    B10 = "Корпус 10"
    KMC = "КМЦ"
    LIBRARY = "Наукова бібліотека"
    MUSEUM = "Історико-музейний комплекс НаУКМА"


class BuildingEN(str, Enum):
    B1 = "Building 1"
    B2 = "Building 2"
    B3 = "Building 3"
    B4 = "Building 4"
    B5 = "Building 5"
    B6 = "Building 6"
    B7 = "Building 7"
    B8 = "Building 8"
    B9 = "Building 9"
    B10 = "Building 10"
    KMC = "Cultural and Art Center (KMC)"
    LIBRARY = "Research Library"
    MUSEUM = "Historical and Museum Complex of NaUKMA"


# --- Tables --------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)  # <<зашифровано>>: pgcrypto / шифрований том
    full_name: str  # <<зашифровано>>
    password_hash: str
    role: Role = Field(sa_column=_enum(Role))
    notifications_enabled: bool = Field(default=True)
    is_blocked: bool = Field(default=False)


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    name_ua: str
    name_en: str
    capacity: int
    has_projector: bool = Field(default=False)
    is_shelter: bool = Field(default=False)
    building_ua: BuildingUA = Field(sa_column=_enum(BuildingUA))
    building_en: BuildingEN = Field(sa_column=_enum(BuildingEN))
    room_number: str
    moderation_status: ModerationStatus = Field(
        default=ModerationStatus.PENDING, sa_column=_enum(ModerationStatus)
    )
    approved_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")


class TimeSlot(SQLModel, table=True):
    __tablename__ = "time_slots"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_time_slots_interval"),
        Index("ix_time_slots_room_start", "room_id", "start_time"),  # PERF-001
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    start_time: datetime = Field(sa_column=_ts())
    end_time: datetime = Field(sa_column=_ts())
    is_available: bool = Field(default=True)
    closure_reason: str | None = Field(default=None)


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        # A-002 / REL-001: на слот — щонайбільше одне активне бронювання;
        # скасовані/відхилені залишаються як історія.
        Index(
            "uq_bookings_active_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status IN ('Pending', 'Confirmed')"),
            sqlite_where=text("status IN ('Pending', 'Confirmed')"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    slot_id: uuid.UUID = Field(foreign_key="time_slots.id")
    status: BookingStatus = Field(default=BookingStatus.PENDING, sa_column=_enum(BookingStatus))
    purpose: str | None = Field(default=None)  # немає в data-model.md, але є в API/mocks
    rejection_reason: str | None = Field(default=None)  # обов'язкове лише для Rejected (FR-010)
    created_at: datetime = Field(default_factory=_now, sa_column=_ts())


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(
        foreign_key="bookings.id", unique=True
    )  # Booking ||--o| Notification
    scheduled_time: datetime = Field(sa_column=_ts())
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING, sa_column=_enum(NotificationStatus)
    )
    retry_count: int = Field(default=0)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    __table_args__ = (
        # actor_type = User  ⇔  user_id заповнене
        CheckConstraint(
            "(actor_type = 'User') = (user_id IS NOT NULL)", name="ck_audit_logs_actor"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_type: ActorType = Field(sa_column=_enum(ActorType))
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    action: AuditAction = Field(sa_column=_enum(AuditAction))
    entity_type: EntityType = Field(sa_column=_enum(EntityType))
    entity_id: uuid.UUID  # без FK: тип об'єкта різний
    details: str | None = Field(default=None)  # без персональних даних
    timestamp: datetime = Field(default_factory=_now, sa_column=_ts())
    # Append-only (захист від Repudiation) забезпечується на рівні сервісу
    # AuditLog; у БД можна додатково заборонити UPDATE/DELETE тригером.
