"""Демо для перевірки воріт покриття: функція без тестів. НЕ ЗЛИВАТИ."""


def untested_discount(price: float, percent: float) -> float:
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")
    if price < 0:
        raise ValueError("price must be non-negative")
    return round(price * (1 - percent / 100), 2)
