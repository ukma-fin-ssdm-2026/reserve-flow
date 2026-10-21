from datetime import datetime, timedelta

_REMINDER_LEAD_TIME = timedelta(hours=24)

def compute_reminder_time(slot_start: datetime, now: datetime) -> datetime:
    reminder = slot_start - _REMINDER_LEAD_TIME
    return max(reminder, now)