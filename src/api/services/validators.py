from datetime import datetime


def slots_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Перевіряє, чи перетинаються два часові інтервали."""
    return a_start < b_end and a_end > b_start
