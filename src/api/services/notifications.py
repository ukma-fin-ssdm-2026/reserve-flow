from datetime import datetime, timedelta

_REMINDER_LEAD_TIME = timedelta(hours=24)


def compute_reminder_time(slot_start: datetime, now: datetime) -> datetime | None:
    """Обчислює час нагадування (за 24 год до початку).
    Якщо 24 год уже минули, повертає поточний час. Якщо слот почався — None."""
    if now >= slot_start:
        return None
    reminder = slot_start - _REMINDER_LEAD_TIME
    return max(reminder, now)
