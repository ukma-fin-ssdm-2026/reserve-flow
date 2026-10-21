from datetime import datetime, timedelta

def compute_reminder_time(slot_start: datetime, now: datetime) -> datetime:
    reminder = slot_start - timedelta(hours=24)
    return max(reminder, now)