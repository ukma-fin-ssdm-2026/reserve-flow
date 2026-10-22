"""TDD: перевірка надійності пароля (FR-001, SEC-001)."""

from security import validate_password_strength


def test_password_shorter_than_8_chars_is_too_short():
    assert "too_short" in validate_password_strength("abc1")


def test_password_without_digit_is_rejected():
    assert "no_digit" in validate_password_strength("password")


def test_password_without_letter_is_rejected():
    assert "no_letter" in validate_password_strength("12345678")


def test_password_over_72_bytes_is_rejected():
    # 38 символів, але 74 байти в UTF-8: bcrypt такий пароль не прийме
    assert "too_long" in validate_password_strength("ї" * 36 + "a1")
