from datetime import datetime, timedelta

# FR-014: нагадування за N годин до початку. N у вимогах не визначено — тимчасово 24 год.
REMINDER_LEAD = timedelta(hours=24)


def compute_reminder_time(slot_start: datetime, now: datetime) -> datetime | None:
    """Обчислює час нагадування (за 24 год до початку).
    Якщо 24 год уже минули, повертає поточний час. Якщо слот почався — None."""
    if now >= slot_start:
        return None
    reminder = slot_start - REMINDER_LEAD
    return max(reminder, now)
