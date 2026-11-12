"""Лаб 9, №5 (#467): GET /bookings — фільтр доступу й пагінація на боці БД.

Перші тести фіксують поведінку, яку треба зберегти (видимість за роллю, фільтр статусу,
пагінація, порядок). Останні доводять проблему: сторінку має вибирати БД (LIMIT), а кількість
SQL-запитів на одну сторінку не має залежати від кількості бронювань у БД.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event
from sqlmodel import Session

from conftest import auth
from mocks import USER_CLIENT_ID as _SEED_CLIENT
from mocks import USER_PROVIDER_ID as _SEED_PROVIDER
from models import Booking, BookingStatus, BuildingEN, BuildingUA, Role, Room, TimeSlot, User
from security import create_access_token

pytestmark = pytest.mark.req("FR-002")

URL = "/api/v1/bookings"
SEED_CLIENT_ID = uuid.UUID(str(_SEED_CLIENT))
SEED_PROVIDER_ID = uuid.UUID(str(_SEED_PROVIDER))
OTHER_CLIENT_ID = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
OTHER_PROVIDER_ID = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000002")
STATUSES = [BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CANCELLED]


def _headers(user_id: uuid.UUID, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id), role)}"}


OTHER_CLIENT = _headers(OTHER_CLIENT_ID, "Client")
OTHER_PROVIDER = _headers(OTHER_PROVIDER_ID, "Provider")


def _add_users_and_rooms(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    """Другий клієнт і другий постачальник; по одній кімнаті кожному постачальнику."""
    for user_id, role in ((OTHER_CLIENT_ID, Role.CLIENT), (OTHER_PROVIDER_ID, Role.PROVIDER)):
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@test.ukma.edu.ua",
                full_name="Test",
                password_hash="x",
                role=role,
            )
        )
    session.flush()  # користувачі — до кімнат (FK без relationship)
    rooms = []
    for provider_id in (SEED_PROVIDER_ID, OTHER_PROVIDER_ID):
        room = Room(
            provider_id=provider_id,
            name_ua="Тест",
            name_en="Test",
            capacity=10,
            building_ua=BuildingUA.B1,
            building_en=BuildingEN.B1,
            room_number=str(uuid.uuid4())[:6],
        )
        session.add(room)
        rooms.append(room.id)
    session.commit()
    return rooms[0], rooms[1]


def _add_bookings(session: Session, rooms: tuple[uuid.UUID, uuid.UUID], start: int, count: int):
    """`count` бронювань по черзі в обох кімнатах, від обох клієнтів, з різними статусами.

    created_at зростає — порядок створення збігається з порядком вставки.
    """
    base = datetime.now(timezone.utc) + timedelta(days=30)
    for i in range(start, start + count):
        slot = TimeSlot(
            room_id=rooms[i % 2],
            start_time=base + timedelta(hours=2 * i),
            end_time=base + timedelta(hours=2 * i + 1),
        )
        session.add(slot)
        session.flush()  # слот — до бронювання (FK без relationship)
        session.add(
            Booking(
                client_id=(SEED_CLIENT_ID, OTHER_CLIENT_ID)[(i // 2) % 2],
                slot_id=slot.id,
                status=STATUSES[i % 3],
                purpose=f"#{i}",
                created_at=datetime.now(timezone.utc) + timedelta(minutes=i + 1),
            )
        )
    session.commit()


@pytest.fixture
def many(db_engine):
    """БД із seed + 12 додаткових бронювань (2 клієнти, 2 постачальники)."""
    with Session(db_engine) as session:
        rooms = _add_users_and_rooms(session)
        _add_bookings(session, rooms, 0, 12)
    return db_engine, rooms


def _all_bookings(engine) -> list[Booking]:
    with Session(engine) as session:
        rows = session.query(Booking).order_by(Booking.created_at).all()
        session.expunge_all()
        return rows


def _room_of(engine, slot_id) -> uuid.UUID:
    with Session(engine) as session:
        return session.get(TimeSlot, slot_id).room_id


def _ids(response) -> list[str]:
    assert response.status_code == 200
    return [item["id"] for item in response.json()["items"]]


# --- Поведінка, яку треба зберегти -------------------------------------------------------


def test_client_sees_only_own(client, many):
    engine, _ = many
    expected = {str(b.id) for b in _all_bookings(engine) if b.client_id == OTHER_CLIENT_ID}

    ids = _ids(client.get(URL, headers=OTHER_CLIENT, params={"limit": 100}))

    assert set(ids) == expected and len(ids) == len(expected) == 6


def test_provider_sees_only_bookings_in_own_rooms(client, many):
    engine, rooms = many
    expected = {str(b.id) for b in _all_bookings(engine) if _room_of(engine, b.slot_id) == rooms[1]}

    ids = _ids(client.get(URL, headers=OTHER_PROVIDER, params={"limit": 100}))

    assert set(ids) == expected and len(expected) == 6


def test_admin_sees_all(client, many):
    engine, _ = many
    expected = {str(b.id) for b in _all_bookings(engine)}

    ids = _ids(client.get(URL, headers=auth("admin"), params={"limit": 100}))

    assert set(ids) == expected and len(expected) == 13  # 1 із seed + 12


def test_status_filter_combines_with_role(client, many):
    engine, _ = many
    expected = {
        str(b.id)
        for b in _all_bookings(engine)
        if b.client_id == OTHER_CLIENT_ID and b.status == BookingStatus.CONFIRMED
    }

    ids = _ids(client.get(URL, headers=OTHER_CLIENT, params={"status": "Confirmed"}))

    assert set(ids) == expected and expected


def test_order_is_creation_order(client, many):
    engine, _ = many
    expected = [str(b.id) for b in _all_bookings(engine)]

    assert _ids(client.get(URL, headers=auth("admin"), params={"limit": 100})) == expected


def test_pages_join_into_full_list(client, many):
    full = _ids(client.get(URL, headers=auth("admin"), params={"limit": 100}))
    pages = []
    for offset in range(0, len(full), 5):
        response = client.get(URL, headers=auth("admin"), params={"limit": 5, "offset": offset})
        info = response.json()["pagination"]
        assert info["total"] == len(full)
        assert info["has_more"] == (offset + 5 < len(full))
        pages += _ids(response)

    assert pages == full


@pytest.mark.parametrize(("offset", "count"), [(12, 1), (13, 0), (50, 0)])
def test_offset_boundaries(client, many, offset, count):
    response = client.get(URL, headers=auth("admin"), params={"limit": 5, "offset": offset})

    assert len(_ids(response)) == count
    assert response.json()["pagination"] == {
        "limit": 5,
        "offset": offset,
        "total": 13,
        "has_more": False,
    }


# --- Проблема №5: уся таблиця в пам'ять і N+1 запитів -----------------------------------


def _statements(client, engine, headers) -> list[str]:
    """SQL-запити, виконані під час `GET /bookings?limit=5`."""
    statements = []

    def _on_execute(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        assert client.get(URL, headers=headers, params={"limit": 5}).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)
    return statements


@pytest.mark.parametrize(
    "headers", [OTHER_CLIENT, OTHER_PROVIDER, auth("admin")], ids=["client", "provider", "admin"]
)
def test_page_is_selected_by_database(client, many, headers):
    """Бронювання вибираються з LIMIT, а не вся таблиця в пам'ять (для кожної ролі)."""
    engine, _ = many
    selects = [
        s
        for s in _statements(client, engine, headers)
        if "FROM bookings" in s and "count(" not in s
    ]

    assert selects and all("LIMIT" in s for s in selects), selects


def test_query_count_does_not_grow_with_bookings(client, many):
    engine, rooms = many
    before = len(_statements(client, engine, OTHER_PROVIDER))

    with Session(engine) as session:
        _add_bookings(session, rooms, 12, 40)
    after = len(_statements(client, engine, OTHER_PROVIDER))

    assert after == before, f"{before} SQL-запитів на 12 бронюваннях, {after} — на 52"
