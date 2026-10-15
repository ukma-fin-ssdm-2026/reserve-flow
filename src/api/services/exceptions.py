"""Доменні винятки сервісів. Роутер перетворює їх на AppError / HTTP-відповідь."""


class SlotNotFound(Exception):
    """Слота з таким id не існує (-> 404 NOT_FOUND)."""


class SlotUnavailable(Exception):
    """Слот закрито постачальником або він має активне бронювання (-> 409 SLOT_UNAVAILABLE)."""
