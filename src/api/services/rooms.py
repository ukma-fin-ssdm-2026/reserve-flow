"""Room Management Service (частина, потрібна для бронювання)."""

from uuid import UUID

from sqlmodel import Session, select

from models import TimeSlot
from services.exceptions import SlotNotFound


def lock_slot(session: Session, slot_id: UUID) -> TimeSlot:
    """SELECT ... FOR UPDATE по слоту. Блокування тримається до COMMIT/ROLLBACK
    поточної транзакції (REL-001). У SQLite FOR UPDATE ігнорується."""
    statement = (
        select(TimeSlot)
        .where(TimeSlot.id == slot_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    slot = session.exec(statement).one_or_none()
    if slot is None:
        raise SlotNotFound(str(slot_id))
    return slot
