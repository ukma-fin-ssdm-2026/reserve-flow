# Звіт про надійність — виправлення знахідок №9a та №13

**Проєкт:** Reserve Flow  
**Обсяг:** гранична перевірка часу слота та валідація текстових полів бронювання.  
**Пов'язані завдання:** #456, #457.  
**Реалізація:** `src/api/services/bookings.py`, `src/api/schemas/bookings.py`, `src/api/errors.py`.

## №9a. Бронювання слота, що вже почався — #456

### До

`create_booking` перевіряв існування й доступність слота, але не порівнював час його початку з поточним часом. Тому запит міг створити бронювання на слот, який уже почався або минув.

```python
slot = lock_slot(session, slot_id)
if not slot.is_available:
    raise SlotUnavailable(str(slot_id))
# Перевірки slot.start_time <= now не було.
```

### Після

Перед перевіркою доступності сервіс нормалізує час до UTC та відхиляє слот, якщо його початок настав:

```python
slot_start = _as_utc(slot.start_time)
current_time = _as_utc(now or datetime.now(timezone.utc))
if slot_start <= current_time:
    logger.warning(
        "Rejecting booking for slot that has already started: slot_id=%s "
        "slot_start=%s now=%s",
        slot_id,
        slot_start.isoformat(),
        current_time.isoformat(),
    )
    raise AppError(
        status_code=409,
        code=ErrorCode.SLOT_ALREADY_STARTED,
        message="Не можна забронювати слот, час початку якого вже настав.",
    )
```

**Патерн:** guard clause / fail fast. Некоректне з погляду часу бронювання відхиляється до створення `Booking`, `Notification` та `AuditLog`.

**Режим відмови:** швидка відмова. Клієнт одразу отримує `409 SLOT_ALREADY_STARTED` з повідомленням; операція не залишає бронювання в БД. У журналі застосунку фіксуються ID слота, час початку та час перевірки.

**Граничні тести:** `tests/reliability/test_booking_time_boundaries.py` перевіряє три значення відносно `now`:

- `now - 1 секунда` → `409 SLOT_ALREADY_STARTED`;
- `now` → `409 SLOT_ALREADY_STARTED`;
- `now + 1 секунда` → `201 Created`.

Для відхилених запитів також перевіряється відсутність запису бронювання та наявність попередження в логах.

## №13. Валідація `purpose` та `reason` — #457

### До

`purpose` мав `min_length=3` і `max_length=200`, але пробіли не обрізалися. Значення з пробілів могло пройти перевірку мінімальної довжини. `reason` не мав верхньої межі довжини.

```python
purpose: str = Field(..., min_length=3, max_length=200)
reason: str | None = Field(None, ...)
```

### Після

Для `BookingCreate` і `BookingUpdate` встановлено `str_strip_whitespace=True`. Pydantic обрізає пробіли до перевірки обмежень. Для `purpose` збережено діапазон 3–200 символів, а для `reason` встановлено максимум 500 символів:

```python
class BookingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    purpose: str = Field(..., min_length=3, max_length=200)

class BookingUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str | None = Field(None, max_length=500)
```

**Патерн:** валідація на межі системи. Некоректні значення відхиляються до виконання бізнес-логіки й запису в БД.

**Режим відмови:** швидка відмова з `422 VALIDATION_ERROR`. Значення з порожнім після обрізання `purpose`, коротшим за 3 символи або довшим за 200 символів не приймається. `reason` довший за 500 символів також відхиляється; для статусу `Rejected` порожня після обрізання причина залишається невалідною.

**Граничні тести:** `tests/reliability/test_booking_input_validation.py` перевіряє порожній і пробільний `purpose`, рівно 200 та 201 символ; для `reason` — пробільне значення, рівно 500 та 501 символ. Окремо перевіряється, що значення на межі після обрізання зберігається без зовнішніх пробілів.

## Оновлення API-документації

У схемі OpenAPI відображено новий код `SLOT_ALREADY_STARTED`, опис відповіді `409` для `POST /bookings` та обмеження `maxLength: 500` для `BookingUpdate.reason`. Опис полів також повідомляє про обрізання крайових пробілів. Актуальні експорти: `docs/api/openapi-generated.json` і `docs/api/openapi-generated.yaml`.

---

*Звіт описує лише виправлення знахідок №9a та №13 і не змінює статус інших знахідок у `scavenger-hunt.md`.*
