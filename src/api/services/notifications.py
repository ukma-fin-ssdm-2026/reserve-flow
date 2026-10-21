from datetime import timedelta

def compute_reminder_time(slot_start, now):
    return slot_start - timedelta(hours=24)