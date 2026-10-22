"""TDD: перевірка надійності пароля (FR-001, SEC-001)."""

from security import validate_password_strength


def test_password_shorter_than_8_chars_is_too_short():
    assert "too_short" in validate_password_strength("abc1")
