"""Модульні тести правила скасування (FR-007), TDD."""

from datetime import datetime, timedelta, timezone

import pytest

from services.cancellation import can_cancel

pytestmark = pytest.mark.req("FR-007")

KYIV = timezone(timedelta(hours=3))
SLOT_START = datetime(2026, 10, 15, 14, 0, tzinfo=KYIV)


@pytest.mark.parametrize(
    ("time_before_start", "expected"),
    [
        (timedelta(hours=3), True),
        (timedelta(hours=2, seconds=1), True),
        (timedelta(hours=2), True),
        (timedelta(hours=1, minutes=59, seconds=59), False),
        (timedelta(0), False),
        (timedelta(hours=-1), False),
    ],
    ids=["3h", "2h+1s", "exactly-2h", "2h-1s", "at-start", "already-started"],
)
def test_can_cancel_deadline(time_before_start, expected):
    # Arrange
    now = SLOT_START - time_before_start

    # Act
    result = can_cancel(SLOT_START, now)

    # Assert
    assert result is expected


def test_naive_datetime_is_rejected():
    # Arrange
    naive_now = datetime(2026, 10, 15, 10, 0)

    # Act / Assert
    with pytest.raises(ValueError, match="aware"):
        can_cancel(SLOT_START, naive_now)
