from datetime import datetime, timedelta
from services.notifications import compute_reminder_time

def test_reminder_24h_before():
    now = datetime(2026, 10, 10, 12, 0)
    slot_start = datetime(2026, 10, 15, 12, 0)
    expected = slot_start - timedelta(hours=24)
    assert compute_reminder_time(slot_start, now) == expected 

def test_reminder_less_than_24h():
    now = datetime(2026, 10, 15, 10, 0)
    slot_start = datetime(2026, 10, 15, 12, 0)
    assert compute_reminder_time(slot_start, now) == now

def test_reminder_for_past_slot_returns_none():
    now = datetime(2026, 10, 15, 13, 0)
    slot_start = datetime(2026, 10, 15, 12, 0)
    assert compute_reminder_time(slot_start, now) is None