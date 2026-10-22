from hypothesis import given, settings
from hypothesis.strategies import text
from security import hash_password, verify_password

@settings(max_examples=10)  
@given(text(max_size=72))  
def test_password_hashing_property(password):
    """
    Властивість: Будь-який згенерований пароль після хешування має успішно верифікуватися.
    """
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True