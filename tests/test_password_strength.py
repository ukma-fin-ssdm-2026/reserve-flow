"""TDD: перевірка надійності пароля (FR-001, SEC-001)."""

import pytest

from security import validate_password_strength


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        pytest.param("abc1", "too_short", id="shorter-than-8"),
        pytest.param("password", "no_digit", id="no-digit"),
        pytest.param("12345678", "no_letter", id="no-letter"),
        # 38 символів, але 74 байти в UTF-8: bcrypt такий пароль не прийме
        pytest.param("ї" * 36 + "a1", "too_long", id="over-72-bytes"),
    ],
)
def test_weak_password_is_rejected(password, problem):
    assert problem in validate_password_strength(password)


def test_strong_password_has_no_problems():
    assert validate_password_strength("correct1horse") == []
