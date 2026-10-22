from datetime import datetime
import pytest
from services.validators import slots_overlap


@pytest.mark.parametrize(
    ("a_start", "a_end", "b_start", "b_end", "expected"),
    [
        # 1. Окремі інтервали
        (
            datetime(2026, 10, 15, 10, 0),
            datetime(2026, 10, 15, 11, 0),
            datetime(2026, 10, 15, 12, 0),
            datetime(2026, 10, 15, 13, 0),
            False,
        ),
        # 2. Частковий перетин
        (
            datetime(2026, 10, 15, 10, 0),
            datetime(2026, 10, 15, 12, 0),
            datetime(2026, 10, 15, 11, 0),
            datetime(2026, 10, 15, 13, 0),
            True,
        ),
        # 3. Граничний випадок: впритул
        (
            datetime(2026, 10, 15, 14, 0),
            datetime(2026, 10, 15, 15, 20),
            datetime(2026, 10, 15, 15, 20),
            datetime(2026, 10, 15, 16, 40),
            False,
        ),
        # 4. Один інтервал повністю всередині іншого
        (
            datetime(2026, 10, 15, 10, 0),
            datetime(2026, 10, 15, 14, 0),
            datetime(2026, 10, 15, 11, 0),
            datetime(2026, 10, 15, 12, 0),
            True,
        ),
    ],
    ids=["separate", "partial-overlap", "adjacent-boundary", "nested"],
)
def test_slots_overlap(a_start, a_end, b_start, b_end, expected):
    assert slots_overlap(a_start, a_end, b_start, b_end) is expected
