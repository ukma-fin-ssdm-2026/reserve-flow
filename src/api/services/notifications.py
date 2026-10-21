from datetime import datetime, timedelta

def compute_reminder_time(slot_start: datetime, now: datetime) -> datetime:
    return slot_start - timedelta(hours=24)