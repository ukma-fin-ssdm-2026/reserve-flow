from datetime import datetime, timedelta, timezone

KYIV = timezone(timedelta(hours=3))  # A-001: одна часова зона, Київ (EEST)

# --- Користувачі (заглушка для D-06; токени — у deps.py) -------------------
USER_CLIENT_ID = "11111111-1111-4111-8111-111111111111"
USER_PROVIDER_ID = "22222222-2222-4222-8222-222222222222"
USER_ADMIN_ID = "33333333-3333-4333-8333-333333333333"

# --- Приміщення ------------------------------------------------------------
ROOM_1_ID = "a1000000-0000-4000-8000-000000000001"
ROOM_2_ID = "a1000000-0000-4000-8000-000000000002"

ROOMS: list[dict] = [
    {
        "id": ROOM_1_ID,
        "provider_id": USER_PROVIDER_ID,
        "name_ua": "Аудиторія 1-225",
        "name_en": "Room 1-225",
        "building_ua": "Корпус 1",
        "building_en": "Building 1",
        "room_number": "225",
        "capacity": 40,
        "has_projector": True,
        "is_shelter": False,
        "moderation_status": "Approved",
    },
    {
        "id": ROOM_2_ID,
        "provider_id": USER_PROVIDER_ID,
        "name_ua": "Аудиторія 3-101",
        "name_en": "Room 3-101",
        "building_ua": "Корпус 3",
        "building_en": "Building 3",
        "room_number": "101",
        "capacity": 25,
        "has_projector": False,
        "is_shelter": True,
        "moderation_status": "Approved",
    },
]

# --- Часові слоти ------------------------------------------------------------
SLOT_1_ID = "b2000000-0000-4000-8000-000000000001"
SLOT_2_ID = "b2000000-0000-4000-8000-000000000002"
SLOT_3_ID = "b2000000-0000-4000-8000-000000000003"

SLOTS: list[dict] = [
    {
        "id": SLOT_1_ID,
        "room_id": ROOM_1_ID,
        "start_time": datetime(2026, 10, 15, 14, 0, tzinfo=KYIV),
        "end_time": datetime(2026, 10, 15, 15, 20, tzinfo=KYIV),
        "is_available": True,
        "closure_reason": None,
    },
    {
        "id": SLOT_2_ID,
        "room_id": ROOM_1_ID,
        "start_time": datetime(2026, 10, 15, 15, 40, tzinfo=KYIV),
        "end_time": datetime(2026, 10, 15, 17, 0, tzinfo=KYIV),
        "is_available": True,
        "closure_reason": None,
    },
    {
        "id": SLOT_3_ID,
        "room_id": ROOM_2_ID,
        "start_time": datetime(2026, 10, 15, 14, 0, tzinfo=KYIV),
        "end_time": datetime(2026, 10, 15, 15, 20, tzinfo=KYIV),
        "is_available": False,
        "closure_reason": "Ремонт проєктора",
    },
]

# --- Бронювання -------------------------------------------------------------
BOOKING_1_ID = "c3000000-0000-4000-8000-000000000001"

BOOKINGS: list[dict] = [
    {
        "id": BOOKING_1_ID,
        "client_id": USER_CLIENT_ID,
        "slot_id": SLOT_2_ID,
        "status": "Pending",
        "rejection_reason": None,
        "created_at": datetime(2026, 10, 7, 10, 0, tzinfo=KYIV),
    },
]


def find_by_id(items: list[dict], item_id: str) -> dict | None:
    """Пошук заглушки за id; None, якщо не знайдено (роутер повертає 404)."""
    return next((item for item in items if item["id"] == item_id), None)


    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini та Claude. 
    # Код вичитано, відредаговано та затверджено учасниками команди