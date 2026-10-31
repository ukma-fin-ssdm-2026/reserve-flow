# Code Review Report

Команда, що оглядала: Team 3

Репозиторій, що оглядався: <https://github.com/ukma-fin-ssdm-2026/vibecoders>

Рецензований код: коміт [`a22dc1a`](https://github.com/ukma-fin-ssdm-2026/vibecoders/tree/a22dc1a210e1e0802c45daf17f62e30e687cd3a0) (`a22dc1a210e1e0802c45daf17f62e30e687cd3a0`, `main` станом на 08.10.2026 — останній коміт коду перед оглядом на парі 09.10). Усі посилання на рядки нижче — на цей коміт.


## Сильні сторони
1. **Розділення автентифікації та авторизації**: У файлі `security.py` за ці процеси відповідають різні функції (`get_current_user` та `require_roles`), що є гарною практикою.
   *Де:* [`security.py:16`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/security.py#L16) (`get_current_user`), [`security.py:27`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/security.py#L27) (`require_roles`).
2. **Чітке розділення відповідальностей**: На базовому рівні API-роути та схеми запитів/відповідей добре структуровані. Крім того, наявна перевірка прав доступу для PATCH-запитів.
   *Де:* [`routes/games.py:44`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L44) (`ensure_can_manage`), виклик у [`routes/games.py:146`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L146) (`patch_game`); [`routes/rooms.py:92`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/rooms.py#L92) (`patch_room`).
3. **Безпека логування**: Користувачу не показують детальні системні логи помилок, що запобігає витоку чутливої інформації. Також присутня централізована обробка помилок.
   *Де:* [`errors.py:51`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/errors.py#L51) (`register_error_handlers`), [`errors.py:71`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/errors.py#L71) (`unexpected_error_handler` повертає лише «Внутрішня помилка сервера»).

## Пропозиції щодо покращення
1. **Запобігання брутфорсу**: Рекомендується логувати спроби входу користувачів при виклику ендпоінту `login`, а також додати механізм таймаутів (тимчасове блокування доступу) після певної кількості невдалих спроб. Це допоможе відстежувати підозрілу активність та ефективно запобігати спробам підбору паролів.
   *Де:* [`routes/auth.py:21`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/auth.py#L21) (`login`): невдала спроба одразу повертає 401 без логування й лічильника спроб.
2. **Трасування запитів та логування**: Рекомендується додати глобальне логування помилок із використанням `correlation_id` для кращого відстеження запитів між компонентами.
   *Де:* [`errors.py:71`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/errors.py#L71): непередбачена помилка не логується взагалі, тож причину 500 не знайти.
3. **Транзакційна межа**: Відсутня чітка транзакційна межа між пов'язаними операціями, що наразі розмиває межу (separation) між бізнес-логікою та інфраструктурою фреймворку.
   *Де:* [`routes/games.py:100`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L100) (`create_game`): перевірка розкладу, запис у `GAMES` і `ENROLLMENTS` виконуються прямо в роутері.

## Потенційна вразливість / ризик
- **Опис**: Складність контролю конкурентного доступу до даних при багатопотоковості.
- **Де знайдено**: В ендпоінтах, що модифікують стан ресурсів (наприклад, PATCH-запити для оновлення).
  Конкретно: [`routes/games.py:102`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L102) і [`routes/games.py:152`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L152) — спершу `ensure_schedule_is_valid` перевіряє, що кімната й майстер вільні ([`routes/games.py:49`](https://github.com/ukma-fin-ssdm-2026/vibecoders/blob/a22dc1a210e1e0802c45daf17f62e30e687cd3a0/src/api/routes/games.py#L49)), і лише потім гра записується в `GAMES`. Між перевіркою і записом немає блокування (check-then-act); у прототипі зі сховищем у пам'яті це малоймовірно, але при переході на БД два одночасні запити можуть обидва пройти перевірку `ROOM_BUSY`.
- **Можливі наслідки**: Якщо кілька користувачів одночасно спробують змінити стан одного й того ж ресурсу (наприклад, забронювати один слот або змінити його статус), це може призвести до стану гонитви (race condition). Як наслідок, система може зберегти некоректні дані, наприклад, дозволити подвійне бронювання.
- **Як виправити**: Додати механізми блокування ресурсів на рівні додатка або реалізувати оптимістичне/песимістичне блокування (locking) перед модифікацією стану, особливо коли буде підключена реальна база даних.

---

## Відгук на наш код (команда ctrl-alt-defeat)

Рецензенти: команда **ctrl-alt-defeat**, звіт — [`docs/code-quality/review-report.md`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/blob/7dbbff6/docs/code-quality/review-report.md) у їхньому репозиторії. Рецензований код Reserve Flow: коміт [`57396f8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/57396f8) (`main` станом на 08.10.2026).

**Сильні сторони, які відзначили:** модульна структура (роутери, схеми, автентифікація, помилки, конфігурація), валідація через Pydantic (Enum, UUID, EmailStr, `model_validator`), документування API й централізований формат помилок з correlation ID.

| Зауваження | Що зробили | Статус |
|---|---|---|
| **BOLA / IDOR у `patch_slot()`** — перевіряється лише роль `PROVIDER`, а не те, що кімната слота належить саме цьому постачальнику | Додано перевірку власника кімнати → `403 FORBIDDEN` ([`routes/slots.py`](../../src/api/routes/slots.py), `patch_slot`); регресійний тест `test_provider_cannot_patch_foreign_room_slot` у [`tests/api/test_slots_rooms.py`](../../tests/api/test_slots_rooms.py) | ✅ виправлено, PR [#235](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/235) |
| Винести бізнес-логіку з роутерів у service layer | Створено `services/bookings.py` (Booking Engine, транзакція з `SELECT … FOR UPDATE`) і `services/rooms.py`; роутер `POST /bookings` лише викликає сервіс | ✅ виправлено, PR [#223](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/223), [#238](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/238) |
| Уніфікувати типи ідентифікаторів (`BookingOut` — `UUID`, `RoomOut` / `SlotOut` — `str`) | `RoomOut.id` / `provider_id` і `SlotOut.id` / `room_id` переведено на `UUID` — у контракті API всі id тепер `string, format: uuid`; регресійний тест `test_ids_have_uuid_format_in_openapi` у [`tests/api/test_schemas_consistency.py`](../../tests/api/test_schemas_consistency.py) | ✅ виправлено, PR [#273](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/273) |
| `datetime.utcnow()` у `BookingOut` дає naive-дату, решта коду — timezone-aware | `BookingOut.created_at` тепер `datetime.now(timezone.utc)`, як у `models.py` і `security.py`; регресійний тест `test_booking_created_at_is_timezone_aware_utc` у [`tests/api/test_schemas_consistency.py`](../../tests/api/test_schemas_consistency.py) | ✅ виправлено, PR [#273](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/273) |

**Висновок.** Усі чотири зауваження прийнято й виправлено, три з них — з регресійними тестами. Найважливіше — BOLA — підтвердилося. Наш власний огляд vibecoders шукав ризики на рівні архітектури (конкурентність), а рецензенти знайшли конкретну помилку авторизації на рівні об'єкта: це ще раз показує, що огляд колеги знаходить те, чого не бачать ні автор, ні статичний аналіз (bandit цю помилку не позначав).

---

## Використання ШІ

- **Первинний огляд** (сильні сторони, пропозиції, потенційний ризик; 09.10.2026) — Анастасія Покормяк. ШІ: формулювання пропозицій.
- **Доповнення 21.10.2026** (SHA рецензованого коміту, посилання на конкретні рядки коду vibecoders, розділ «Відгук на наш код» з таблицею виправлень) — Анастасія Лавришин за допомогою Claude (Anthropic): пошук рядків у коді за SHA, формулювання і структура таблиці.
- **Перевірено вручну:** кожне посилання відкрито на коміті `a22dc1a`; кожне виправлення з розділу «Відгук на наш код» звірено з кодом і тестами нашого репозиторію.
