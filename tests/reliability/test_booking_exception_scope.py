"""Лаб 9, №12: вузьке перехоплення винятків у сервісі бронювання (`except Exception`).

Системні сигнали завершення (`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`) успадковуються
від `BaseException`, а не `Exception`. Вони не повинні перехоплюватися у `create_booking` і
викликати мережевий `session.rollback()` під час зупинки воркера. Натомість будь-який прикладний
`Exception` має відкочувати транзакцію, не залишаючи часткових даних у БД.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from mocks import SLOT_1_ID, USER_CLIENT_ID
from models import AuditLog, Booking, Notification
from services import bookings as booking_engine
from services.exceptions import SlotUnavailable

pytestmark = pytest.mark.req("FR-005", "FR-006", "REL-001")

CLIENT_ID = uuid.UUID(USER_CLIENT_ID)
SLOT_FREE = uuid.UUID(SLOT_1_ID)


@pytest.fixture
def session(db_engine):
    with Session(db_engine) as s:
        yield s


def _count(session: Session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


@pytest.mark.parametrize(
    "signal_exc",
    [KeyboardInterrupt("SIGINT"), SystemExit(1), GeneratorExit()],
    ids=["KeyboardInterrupt", "SystemExit", "GeneratorExit"],
)
def test_base_exception_propagates_without_db_rollback(session, monkeypatch, signal_exc):
    """Лаб 9, №12: сигнали завершення воркера не викликають мережевий session.rollback()."""

    def interrupt(*_args, **_kwargs):
        raise signal_exc

    monkeypatch.setattr(booking_engine, "AuditLog", interrupt)
    rollback_spy = MagicMock(wraps=session.rollback)
    monkeypatch.setattr(session, "rollback", rollback_spy)

    with pytest.raises(type(signal_exc)):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Переривання воркера")

    rollback_spy.assert_not_called()


@pytest.mark.parametrize(
    "app_exc",
    [RuntimeError("db error"), ValueError("invalid state"), LookupError("missing key")],
    ids=["RuntimeError", "ValueError", "LookupError"],
)
def test_application_exception_rolls_back_and_leaves_slot_bookable(session, monkeypatch, app_exc):
    """Будь-який прикладний Exception викликає rollback, залишаючи БД чистою для повтору."""
    bookings_before = _count(session, Booking)
    notifications_before = _count(session, Notification)
    audits_before = _count(session, AuditLog)

    real_audit_log = booking_engine.AuditLog
    should_fail = True

    def flaky_audit(**kwargs):
        if should_fail:
            raise app_exc
        return real_audit_log(**kwargs)

    monkeypatch.setattr(booking_engine, "AuditLog", flaky_audit)
    rollback_spy = MagicMock(wraps=session.rollback)
    monkeypatch.setattr(session, "rollback", rollback_spy)

    with pytest.raises(type(app_exc)):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Збій на аудиті")

    rollback_spy.assert_called_once()
    assert _count(session, Booking) == bookings_before
    assert _count(session, Notification) == notifications_before
    assert _count(session, AuditLog) == audits_before

    # Після відновлення повторний запит на той самий слот успішно створює бронювання
    should_fail = False
    created = booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Повтор після збою")
    assert created.slot_id == SLOT_FREE
    assert _count(session, Booking) == bookings_before + 1


def test_integrity_error_rolls_back_and_raises_slot_unavailable(session, monkeypatch):
    """Конфлікт унікального індексу під час commit відкочує транзакцію й кидає SlotUnavailable."""
    rollback_spy = MagicMock(wraps=session.rollback)
    monkeypatch.setattr(session, "rollback", rollback_spy)
    monkeypatch.setattr(
        session,
        "commit",
        MagicMock(side_effect=IntegrityError("INSERT", {}, Exception("uq_bookings_active_slot"))),
    )

    with pytest.raises(SlotUnavailable):
        booking_engine.create_booking(session, CLIENT_ID, SLOT_FREE, "Конфлікт індексу")

    rollback_spy.assert_called_once()


# Використання ШІ: тести згенеровано ШІ Gemini та перевірено й затверджено учасником команди.
