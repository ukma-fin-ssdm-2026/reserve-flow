import pytest
from hypothesis import given, settings
from hypothesis.strategies import text
from security import hash_password, verify_password

pytestmark = pytest.mark.req("FR-001", "SEC-001")


@settings(max_examples=10, deadline=None)
# bcrypt приймає до 72 БАЙТІВ; text(max_size=72) рахує символи (кирилиця — 2 байти)
@given(text(max_size=72).filter(lambda s: len(s.encode()) <= 72))
def test_password_hashing_property(password):
    """
    Властивість: Будь-який згенерований пароль до 72 байтів після хешування
    має успішно верифікуватися.
    """
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
