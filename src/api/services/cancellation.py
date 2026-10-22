"""Правило скасування бронювання (FR-007)."""

from datetime import datetime, timedelta

# FR-007: скасувати можна не пізніше ніж за 2 години до початку.
CANCELLATION_DEADLINE = timedelta(hours=2)


def can_cancel(slot_start: datetime, now: datetime) -> bool:
    """True, якщо бронювання ще можна скасувати.

    Скасування дозволене, поки до початку слота лишається не менше
    CANCELLATION_DEADLINE; рівно 2 год — ще можна. Обидва моменти мають бути
    aware (з часовою зоною), інакше ValueError.
    """
    if slot_start.tzinfo is None or now.tzinfo is None:
        raise ValueError("slot_start і now мають бути aware datetime (з часовою зоною)")
    return slot_start - now >= CANCELLATION_DEADLINE
