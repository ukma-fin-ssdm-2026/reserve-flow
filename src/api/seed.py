"""Перенос даних з mocks.py в БД. Ідемпотентний: повторний запуск оновлює ті самі рядки.

cd src/api && python seed.py            # create_all + seed
cd src/api && python seed.py --reset    # спочатку drop_all
"""

import argparse
import uuid

from sqlmodel import Session, SQLModel

import mocks
from db import get_engine, init_db
from models import (
    Booking,
    BookingStatus,
    BuildingEN,
    BuildingUA,
    ModerationStatus,
    Role,
    Room,
    TimeSlot,
    User,
)

# mocks.py містить лише ID користувачів; решта — з тестів автентифікації (L4-05)
MOCK_USERS = [
    (mocks.USER_CLIENT_ID, "client@ukma.edu.ua", "Тестовий Клієнт", Role.CLIENT),
    (mocks.USER_PROVIDER_ID, "provider@ukma.edu.ua", "Тестовий Постачальник", Role.PROVIDER),
    (mocks.USER_ADMIN_ID, "admin@ukma.edu.ua", "Тестовий Адміністратор", Role.ADMIN),
]


def build_objects() -> list[SQLModel]:
    objs: list[SQLModel] = [
        User(
            id=uuid.UUID(uid),
            email=email,
            full_name=name,
            role=role,
            password_hash="!mock-no-login",  # реальний bcrypt-хеш з'явиться разом з auth
        )
        for uid, email, name, role in MOCK_USERS
    ]
    objs += [
        Room(
            id=uuid.UUID(r["id"]),
            provider_id=uuid.UUID(r["provider_id"]),
            name_ua=r["name_ua"],
            name_en=r["name_en"],
            building_ua=BuildingUA(r["building_ua"]),
            building_en=BuildingEN(r["building_en"]),
            room_number=r["room_number"],
            capacity=r["capacity"],
            has_projector=r["has_projector"],
            is_shelter=r["is_shelter"],
            moderation_status=ModerationStatus(r["moderation_status"]),
            approved_by=(
                uuid.UUID(mocks.USER_ADMIN_ID) if r["moderation_status"] == "Approved" else None
            ),
        )
        for r in mocks.ROOMS
    ]
    objs += [
        TimeSlot(
            id=uuid.UUID(s["id"]),
            room_id=uuid.UUID(s["room_id"]),
            start_time=s["start_time"],
            end_time=s["end_time"],
            is_available=s["is_available"],
            closure_reason=s["closure_reason"],
        )
        for s in mocks.SLOTS
    ]
    objs += [
        Booking(
            id=uuid.UUID(b["id"]),
            client_id=uuid.UUID(b["client_id"]),
            slot_id=uuid.UUID(b["slot_id"]),
            status=BookingStatus(b["status"]),
            purpose=b["purpose"],
            rejection_reason=b["rejection_reason"],
            created_at=b["created_at"],
        )
        for b in mocks.BOOKINGS
    ]
    return objs


def seed(session: Session) -> None:
    for obj in build_objects():  # порядок = порядок залежностей FK
        session.merge(obj)
    session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop_all перед створенням")
    args = parser.parse_args()
    engine = get_engine()
    if args.reset:
        SQLModel.metadata.drop_all(engine)
    init_db(engine)
    with Session(engine) as session:
        seed(session)
    print("Seed виконано.")
