"""Регресійні тести на зауваження ctrl-alt-defeat з огляду коду Lab 5 (#245)."""

from datetime import timedelta
from uuid import uuid4

import pytest

from schemas.bookings import BookingOut, BookingStatus


def test_booking_created_at_is_timezone_aware_utc():
    # Arrange / Act: created_at не передаємо — спрацьовує default_factory
    booking = BookingOut(
        id=uuid4(),
        slot_id=uuid4(),
        user_id=uuid4(),
        status=BookingStatus.PENDING,
        purpose="Семінар",
    )

    # Assert: не naive-дата (як було з datetime.utcnow()), а саме UTC
    assert booking.created_at.tzinfo is not None
    assert booking.created_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("schema", "field"),
    [
        ("BookingOut", "id"),
        ("BookingOut", "slot_id"),
        ("RoomOut", "id"),
        ("RoomOut", "provider_id"),
        ("SlotOut", "id"),
        ("SlotOut", "room_id"),
    ],
)
def test_ids_have_uuid_format_in_openapi(client, schema, field):
    # Act
    spec = client.get("/openapi.json").json()

    # Assert: усі ідентифікатори в контракті API — один тип (string, format: uuid)
    prop = spec["components"]["schemas"][schema]["properties"][field]
    assert prop["type"] == "string"
    assert prop["format"] == "uuid"
