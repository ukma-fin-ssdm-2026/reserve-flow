# Звіт про надійність — Reserve Flow (Лаб 9)

**Код:** `main` після #437, #443, #471, #474–#476, #478–#481 · знахідки — [`scavenger-hunt.md`](scavenger-hunt.md) · авторство знахідок — #453.

> Номери знахідок — як **№1–№14** (за `scavenger-hunt.md`), щоб GitHub не перетворював їх на посилання на issues.
> Місця з `<…>` заповнюються, коли буде злито відповідний PR (тести — #456, бонуси — #459, #460) і відомо, хто презентував на парі.

## 1. Усі знайдені проблеми

| № | Проблема | Кат. | Пріоритет | Статус | Помітив(ла) на парі |
|---|---|---|---|---|---|
| 1 | Синхронні запити до БД у `async def` блокують event loop | E | 🔴 критичний | ✅ виправлено, #437 | — |
| 2 | Немає тайм-аутів на підключення і запити до PostgreSQL | B / E | 🔴 критичний | ✅ виправлено, #437 | — |
| 3 | `SELECT … FOR UPDATE` без `lock_timeout` | E | 🔴 критичний | ✅ виправлено, #437 | — |
| 4 | Бронювання й аудит комітяться в різних транзакціях | A / D | 🔴 критичний | ✅ виправлено, #437 | — |
| 5 | `GET /bookings`: уся таблиця + N+1 запитів | E | 🟠 високий | ✅ виправлено, #475 (#467) | Лавришин |
| 6 | Гонка при зміні статусу бронювання (lost update) | D | 🟠 високий | ✅ виправлено, #437 | — |
| 7 | Health check «healthy», навіть коли БД лежить | B / D | 🟠 високий | ✅ виправлено, #476 (бонус, #458) | — |
| 8 | Конфігурація перевіряється лише під час запиту | C / D | 🟠 високий | ✅ виправлено, #471 | Покормяк |
| 9a | Можна забронювати слот, що вже почався / минув | C | 🟠 високий | ✅ виправлено, #478 (#454) | Балабанов |
| 9b | Нагадування для слота < 24 год планується в минулому | C / D | 🟠 високий | ✅ виправлено, #443 | Покормяк (додатково) |
| 10 | Запис файлів OpenAPI на старті, помилка ховається | A / B / D | 🟡 середній | ✅ виправлено, #481 | Ромах |
| 11 | Неперевірений заголовок `X-Correlation-ID` | C / B | 🟡 середній | ✅ виправлено, #474 (#468) | Лавришин |
| 12 | `except BaseException` у сервісі бронювання | A | 🟡 середній | ✅ виправлено, #479 | Ромах |
| 13 | Слабка валідація `purpose` / `reason` | C | 🟡 середній | ✅ виправлено, #478 (#455) | Балабанов |
| 14 | Невідомі HTTP-коди маркуються як `INTERNAL_ERROR` | A | 🟢 низький | ✅ виправлено, #480 | Ромах |

**Підсумок:** виправлено 15 із 15 (№1, №2, №3, №4, №6 — #437; №5 — #475; №7 — #476; №8 — #471; №9a, №13 — #478; №9b — #443; №10 — #481; №11 — #474; №12 — #479; №14 — #480); відкритих немає.

## 2. Виправлення: до / після, патерн, режим відмови

### №1. Блокувальний I/O в асинхронних обробниках — #437 (`6d097ea`)

```python
# До: синхронна Session усередині async def — блокує event loop усього воркера
@router.get("")
async def get_bookings(..., session: Annotated[Session, Depends(get_session)]): ...

# Після: def — FastAPI виконує обробник у пулі потоків
@router.get("")
def get_bookings(..., session: Annotated[Session, Depends(get_session)]): ...
```

- **Патерн:** ізоляція (повільна операція не займає спільний ресурс — event loop). Так зроблено для 6 обробників у `bookings`, `slots`, `rooms`.
- **Режим відмови:** ізоляція, а не відмова: повільний запит до БД гальмує лише свій запит.
- **Що бачить користувач:** інші запити відповідають як завжди.
- **Відновлення:** автоматичне — потік звільняється, щойно БД відповіла або спрацював тайм-аут (№2).
- **Тест:** `tests/test_no_blocking_in_async.py` — падає, якщо обробник з `Depends(get_session)` знову стане `async`.

### №2, №3. Тайм-аути до БД і на блокування рядка — #437 (`a71fed2`)

```python
# До: жодних меж часу
return create_engine(url, pool_pre_ping=True, **kwargs)

# Після (db.py): кожен виклик до БД обмежений у часі
DB_CONNECT_TIMEOUT_S = 5       # TCP-з'єднання
DB_POOL_TIMEOUT_S = 5          # вільне з'єднання в пулі
DB_STATEMENT_TIMEOUT_MS = 5000 # один SQL-запит
DB_LOCK_TIMEOUT_MS = 3000      # SELECT ... FOR UPDATE
# errors.py: OperationalError / pool TimeoutError -> 503 SERVICE_UNAVAILABLE + Retry-After: 5
```

- **Патерни:** тайм-аути; вузькі обробники (`OperationalError`, pool `TimeoutError`, а не `Exception`); логування з `correlation_id`.
- **Режим відмови:** **швидка** — зависання гірше за чітку помилку: без тайм-ауту один завислий запит займає з'єднання з пулу, і відмова каскадом поширюється на весь API.
- **Що бачить користувач:** через ≤ 5 с — `503` «Сервіс тимчасово недоступний. Спробуйте ще раз за кілька секунд», заголовок `Retry-After: 5`.
- **Відновлення:** клієнт повторює запит після `Retry-After`; щойно БД відповідає вчасно — звичайна робота.
- **Тест:** `tests/test_db_timeouts.py` — lock / pool timeout → `503` з `Retry-After`, без внутрішніх деталей; engine отримує тайм-аути.

### №4. Бронювання й аудит в одній транзакції — #437 (`a6a42db`)

```python
# До: два коміти — бронювання вже збережене, коли пишемо аудит
booking = booking_engine.create_booking(...)   # усередині session.commit()
session.add(AuditLog(...))
session.commit()                               # окрема транзакція

# Після (services/bookings.py): Booking, Notification і AuditLog — перед єдиним commit
session.add(Notification(...))
session.add(AuditLog(actor_type=ActorType.USER, user_id=client_id,
                     action=AuditAction.BOOKING_CREATED, ...))
session.commit()
```

- **Патерн:** атомарна транзакція (усе або нічого).
- **Режим відмови:** **швидка** — це запис даних: неправильна відповідь («напівстворене» бронювання) гірша за відсутність.
- **Що бачить користувач:** `500` з `correlation_id`; у БД **нічого** не лишається (до виправлення: бронювання є, а повтор дає `409` на власне бронювання).
- **Відновлення:** клієнт повторює запит після усунення збою → `201`.
- **Тест:** `tests/test_booking_atomic_audit.py` — зламаний аудит → `500`, немає ні бронювання, ні нагадування; повтор → `201`.

### №6. Гонка при зміні статусу — #437 (`c2a4ada`)

```python
# До: перевірка на прочитаних даних, запис без умови — перемагає останній коміт
booking.status = booking_in.status
session.add(booking)

# Після (routes/bookings.py): compare-and-set
changed = session.exec(
    update(Booking)
    .where(Booking.id == booking_id, Booking.status == expected_status)
    .values(**new_values)
).rowcount
if changed != 1:
    logger.warning("Concurrent status change of booking %s ...", booking_id, ...)
    raise AppError(409, ErrorCode.INVALID_STATUS_TRANSITION, "Статус бронювання щойно змінив інший запит...")
```

- **Патерни:** compare-and-set (умовний `UPDATE`); логування конфлікту.
- **Режим відмови:** **швидка** — `409` замість хибного `200`, після якого журнал суперечить стану.
- **Що бачить користувач:** «Статус бронювання щойно змінив інший запит. Оновіть дані й спробуйте ще раз».
- **Відновлення:** ручне — користувач оновлює дані й вирішує знову (сервер не може вирішити за нього, чия дія важливіша).
- **Тест:** `tests/test_booking_status_race.py` — інша сесія змінює статус між перевіркою і записом → `409`, у журналі немає суперечливого `CONFIRMED`.

### №9b. Нагадування в минулому — #443

```python
# До: для слота < 24 год час нагадування вже в минулому
Notification(booking_id=booking.id, scheduled_time=slot.start_time - REMINDER_LEAD)

# Після (services/bookings.py): правило з notifications.compute_reminder_time
reminder_time = compute_reminder_time(_as_utc(slot.start_time), now or datetime.now(timezone.utc))
if reminder_time is not None:
    session.add(Notification(booking_id=booking.id,
                             scheduled_time=reminder_time.astimezone(timezone.utc)))
```

- **Патерни:** граничне значення (`max(start − 24 год, now)`); нормалізація часу до UTC (SQLite відкидає часовий пояс — без цього нагадування зсувалося на 3 год, це зловив тест).
- **Режим відмови:** **безпечна / контрольована деградація** — нагадати пізніше, ніж за 24 год, але одразу, краще, ніж не нагадати; для слота, що вже почався, нагадування не створюється.
- **Що бачить користувач:** нагадування приходить одразу після бронювання, а не «губиться» в минулому.
- **Відновлення:** не потрібне — поведінка коректна за будь-якого часу до початку.
- **Тест:** `tests/test_booking_reminder_time.py` — слот через 2 год → нагадування «зараз» (на старому коді падає); слот через 48 год → `start − 24 год`.

### №8. Перевірка конфігурації на старті — #471

```python
# До: змінні читаються лише під час запиту
return timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))  # "30m" -> 500 на вході

# Після: config_check.validate_config() — першим кроком у main.lifespan
try:
    validate_config()   # JWT_SECRET >= 32; TTL — ціле 5–1440; DATABASE_URL або POSTGRES_PASSWORD
except ConfigError as exc:
    logging.critical("%s. Сервер не запущено.", exc)
    raise
```

- **Патерни:** перевірка входу (guard на старті); усі порушення одним повідомленням; логування без значень секретів.
- **Режим відмови:** **швидка** — некоректна конфігурація гірша за відсутність сервера: інакше він «здоровий», а користувачі отримують `500` на вході або `401` на кожен запит.
- **Що бачить користувач:** новий деплой не стартує; в лозі — `CRITICAL Некоректна конфігурація: ACCESS_TOKEN_EXPIRE_MINUTES має бути цілим числом хвилин. Сервер не запущено.` і `Application startup failed`.
- **Відновлення:** ручне — виправити змінну оточення й перезапустити.
- **Тест:** `tests/reliability/test_config_validation.py` (16 тестів) — недопустимі TTL (`30m`, `0`, `-5`, порожній), межі 4/5/1440/1441, слабкий `JWT_SECRET`, немає змінних БД, секрет не потрапляє в повідомлення, `lifespan` не стартує.

### №9a. Бронювання слота, що вже почався — #478 (#454, Балабанов)

```python
# До: перевірялось лише закриття слота постачальником, а не час початку
slot = lock_slot(session, slot_id)
if not slot.is_available:
    raise SlotUnavailable(str(slot_id))

# Після (services/bookings.py): guard clause до створення Booking / Notification / AuditLog
current_time = _as_utc(now or datetime.now(timezone.utc))
...
slot_start = _as_utc(slot.start_time)
if slot_start <= current_time:
    logger.warning("Rejecting booking for slot that has already started: %s", slot_id)
    raise AppError(status_code=409, code=ErrorCode.SLOT_ALREADY_STARTED,
                   message="Бронювання неможливе: час початку слота вже настав.")
```

- **Патерни:** guard clause; нормалізація часу до UTC (`_as_utc`); логування.
- **Режим відмови:** **швидка** — бронювання минулого слота неприпустиме: `201` на неможливу дію гірший за чітку помилку.
- **Що бачить користувач:** `409 SLOT_ALREADY_STARTED` «Бронювання неможливе: час початку слота вже настав»; у БД нічого не створюється.
- **Відновлення:** ручне — користувач обирає інший слот.
- **Тест:** `tests/reliability/test_booking_time_boundaries.py` — межа відносно `now`: −1 с → `409`, рівно `now` → `409`, +1 с → `201`; для відхилених — немає бронювання і є попередження в лозі.

### №13. Валідація `purpose` / `reason` — #478 (#455, Балабанов)

```python
# До: пробіли не обрізались ("   " проходило min_length=3), reason без межі довжини
purpose: str = Field(..., min_length=3, max_length=200)
reason: str | None = Field(None, ...)

# Після (schemas/bookings.py): пробіли обрізаються до перевірки довжини
class BookingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    purpose: str = Field(..., min_length=1, max_length=200)

class BookingUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str | None = Field(None, max_length=500)
```

- **Патерн:** перевірка входу на межі системи — до бізнес-логіки й запису в БД.
- **Режим відмови:** **швидка** — `422 VALIDATION_ERROR` замість порожнього за змістом запису чи `500` на обмеженні колонки.
- **Що бачить користувач:** `422` з полем і причиною: `purpose` порожній після обрізання або > 200 символів; `reason` > 500 символів; для `Rejected` — порожня причина.
- **Відновлення:** ручне — виправити поле й надіслати знову.
- **Тест:** `tests/reliability/test_booking_input_validation.py` — `purpose` з пробілів, рівно 200 / 201 символ; `reason` з пробілів, рівно 500 / 501; значення на межі зберігається без крайових пробілів.

### №5. `GET /bookings`: уся таблиця + N+1 — #475 (#467, Лавришин)

```python
# До: усі бронювання в пам'ять, +2 запити на кожне, сторінка ріжеться в Python
all_bookings = session.exec(select(Booking)).all()
filtered = [b for b in all_bookings if _can_view(session, current_user, b)]
return paginate([_to_out(b) for b in filtered], params)

# Після (routes/bookings.py): фільтр доступу, COUNT і OFFSET/LIMIT — у SQL
stmt = _visible_bookings(current_user)            # WHERE за роллю, JOIN TimeSlot/Room для постачальника
total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
rows = session.exec(stmt.order_by(Booking.created_at, Booking.id)
                        .offset(params.offset).limit(params.limit)).all()
return page_of([_to_out(b) for b in rows], params, total)
```

- **Патерн:** обмеження обсягу роботи на запит (сторінка й фільтр у БД, сталий порядок сортування).
- **Режим відмови:** профілактика — час відповіді залежить від розміру сторінки (`limit ≤ 100`), а не від усієї таблиці, тож запит не впирається в тайм-аути з №2.
- **Що бачить користувач:** та сама сторінка, що й раніше, але швидко за будь-якого розміру БД.
- **Відновлення:** не потрібне.
- **Тест:** `tests/reliability/test_bookings_list_query.py` — клієнт бачить лише свої, постачальник — лише у своїх кімнатах; пагінація й кількість запитів.

### №11. Перевірка `X-Correlation-ID` — #474 (#468, Лавришин)

```python
# До: будь-яке значення від клієнта — у логи, тіло помилок і заголовок відповіді
correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

# Після (main.py): лише [A-Za-z0-9-]{1,64}, інакше — новий UUID
def safe_correlation_id(raw: str | None) -> str:
    if raw is None:
        return str(uuid.uuid4())
    if _CORRELATION_ID.fullmatch(raw):
        return raw
    logger.warning("Невалідний X-Correlation-ID (довжина %d) — замінено новим", len(raw))
    return str(uuid.uuid4())
```

- **Патерни:** перевірка входу; резервне значення (новий UUID); логування без самого значення.
- **Режим відмови:** **безпечна** — невалідний заголовок не причина відмовляти в запиті, але й не потрапляє в логи (log injection, підробка, надто довгий рядок).
- **Що бачить користувач:** запит обробляється як завжди; у відповіді — новий `X-Correlation-ID`.
- **Відновлення:** автоматичне — новий ID на кожен такий запит.
- **Тест:** `tests/reliability/test_correlation_id.py` — валідний UUID проходить, межі довжини 64 / 65, небезпечні символи й перенос рядка замінюються, у лозі немає сирого значення.

### №7. Health check з перевіркою БД — #476 (бонус, #458, Лавришин)

```python
# До (main.py): завжди «healthy», БД не перевірялась
def health_check():
    return {"status": "healthy"}

# Після (routes/health.py): SELECT 1 з тайм-аутами з db.py; 503, якщо БД недоступна
try:
    session.execute(text("SELECT 1"))
except SQLAlchemyError as exc:
    logger.warning("Health check: БД недоступна (%s)", type(exc).__name__)
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(status="unhealthy", db="unavailable")
return HealthOut(status="healthy", db="ok")
```

- **Патерни:** перевірка критичної залежності; вузький `except SQLAlchemyError`; логування лише типу помилки (без хоста й параметрів з'єднання).
- **Режим відмови:** **швидка** для платформи — `render.yaml` використовує `/api/v1/health` як `healthCheckPath`, тож Render бачить реальний стан, а не «healthy» за будь-яких умов.
- **Що бачить користувач / платформа:** `503 {"status": "unhealthy", "db": "unavailable"}`.
- **Відновлення:** автоматичне — щойно БД відповідає, health знову `200`.
- **Тест:** `tests/reliability/test_health_db.py` — ін'єкція збою (зламана сесія, недоступна БД) → `503`; БД відповідає → `200`; автентифікація не потрібна.

### №12. `except BaseException` у сервісі бронювання — #479 (Ромах)

```python
# До: перехоплювались і сигнали завершення процесу (SystemExit, KeyboardInterrupt)
except BaseException:
    session.rollback()   # мережевий виклик до БД під час зупинки воркера
    raise

# Після (services/bookings.py): лише помилки застосунку
except Exception:
    session.rollback()
    raise
```

- **Патерн:** вузьке перехоплення.
- **Режим відмови:** **швидка** для сигналів завершення — `SystemExit` / `KeyboardInterrupt` проходять одразу, без мережевого `rollback()`, тож graceful shutdown воркера не затримується; для помилок застосунку поведінка та сама — відкат і повторне кидання.
- **Що бачить користувач:** нічого нового — для звичайних збоїв, як і раніше, `500` / `409`, транзакція відкочена.
- **Відновлення:** автоматичне — незакомічену транзакцію відкочує сама БД, коли з'єднання закривається.
- **Тест:** `tests/reliability/test_booking_exception_scope.py` — сигнал завершення проходить без `rollback`; помилка застосунку відкочує транзакцію, і слот лишається доступним; `IntegrityError` → відкат і `SlotUnavailable`.

### №10. Експорт OpenAPI на старті — #481 (Ромах)

```python
# До (main.lifespan): сервер на кожному старті пише docs/api/* у свою папку;
# будь-яка помилка — один рядок у лозі без стеку, відсутній yaml маскувався під «модуль не знайдено»
except ImportError:
    logging.warning("Модуль export_openapi не знайдено. Експорт пропущено.")
except Exception as e:
    logging.error(f"Помилка експорту OpenAPI: {e}")

# Після (main.py): експорт можна вимкнути, помилки — зі стеком
def _export_openapi_on_startup(app: FastAPI) -> None:
    if os.getenv("EXPORT_OPENAPI", "1").strip().lower() in _DISABLE_VALUES:
        logging.info("Експорт OpenAPI пропущено (EXPORT_OPENAPI вимкнено).")
        return
    try:
        from export_openapi import export_openapi
    except ImportError as exc:
        if getattr(exc, "name", None) in (None, "export_openapi"):
            logging.warning("Модуль export_openapi не знайдено. Експорт пропущено.")
        else:
            logging.exception("Помилка експорту OpenAPI (відсутня залежність): %s", exc)
        return
    try:
        export_openapi(app)
    except Exception as exc:
        logging.exception("Помилка експорту OpenAPI: %s", exc)
```

- **Патерни:** вимикач для необов'язкової операції (`EXPORT_OPENAPI=0` у `Dockerfile` і `render.yaml`); розрізнення причин `ImportError`; логування зі стеком (`logging.exception`).
- **Режим відмови:** **безпечна / контрольована деградація** — експорт специфікації не потрібен для роботи API, тож його збій не зупиняє сервер; на продакшені запис на диск узагалі вимкнено.
- **Що бачить користувач:** нічого — API працює; розробник бачить у лозі повний стек і справжню причину.
- **Відновлення:** ручне — виправити причину за стеком; специфікацію генерує й перевіряє CI (job `api`).
- **Тест:** `tests/reliability/test_openapi_export_resilience.py` — `EXPORT_OPENAPI=0` пропускає експорт; помилка файлової системи логується зі стеком, а сервер стартує; відсутній `yaml` не маскується під відсутній модуль.

### №14. Невідомі 4xx позначались як `INTERNAL_ERROR` — #480 (Ромах)

```python
# До (errors.py): будь-який код поза 401/403/404/405 -> INTERNAL_ERROR, навіть 400 чи 409
code, default_message = _DEFAULT_ERRORS.get(
    exc.status_code, (ErrorCode.INTERNAL_ERROR, "Помилка обробки запиту")
)

# Після: невідомі 4xx -> BAD_REQUEST, INTERNAL_ERROR лише для 5xx
def _default_http_error(status_code: int) -> tuple[ErrorCode, str]:
    if status_code in _DEFAULT_ERRORS:
        return _DEFAULT_ERRORS[status_code]
    if 400 <= status_code < 500:
        return ErrorCode.BAD_REQUEST, "Некоректний запит"
    return ErrorCode.INTERNAL_ERROR, "Помилка обробки запиту"
```

- **Патерн:** коректна класифікація помилок (код відповідає причині).
- **Режим відмови:** **швидка** — клієнт отримує чітку помилку зі своєю причиною, а не «збій сервера».
- **Що бачить користувач:** для 400 / 409 / 413 / 415 / 429 — `code = "BAD_REQUEST"`; моніторинг більше не рахує помилки клієнта як збої сервера, клієнт не повторює запит, який ніколи не вдасться.
- **Відновлення:** ручне — клієнт виправляє запит.
- **Тест:** `tests/reliability/test_http_exception_codes.py` — невідомі 4xx → `BAD_REQUEST`; 401 / 403 / 404 / 405 зберігають свої коди; 5xx → `INTERNAL_ERROR`; 404 не віддає текст фреймворку.

## 3. Застосовані патерни і їх порядок (§3.5)

| Патерн | Де |
|---|---|
| Тайм-аути | №2, №3 — з'єднання, пул, запит, блокування |
| Вузькі `except` | №2, №3 — `OperationalError`, pool `TimeoutError`; №7 — `SQLAlchemyError`; №12 — `Exception` замість `BaseException` |
| Guard clauses / перевірка входу | №8 (конфігурація на старті), №9a (слот уже почався), №11 (`X-Correlation-ID`), №13 (`purpose` / `reason`) |
| Логування | №2, №3 (`correlation_id`), №6 (конфлікт), №7, №8 (`CRITICAL`), №9a, №11 (без сирого значення) |
| Атомарна транзакція | №4 |
| Compare-and-set | №6 |
| Ізоляція | №1 — `def` замість `async def` |
| Контрольована деградація / резервне значення | №10 — збій експорту OpenAPI не зупиняє сервер; №9b — нагадування «зараз» замість «в минулому»; №11 — новий UUID замість невалідного ID |
| Перевірка залежностей | №7 — health check з `SELECT 1` |
| Коректна класифікація помилок | №14 — невідомі 4xx → `BAD_REQUEST`, `INTERNAL_ERROR` лише для 5xx |
| Обмеження обсягу роботи | №5 — фільтр і пагінація в SQL |

**Порядок (§3.5).** Тайм-аут — найглибший шар: кожен виклик до БД обмежений у часі. **Повтору на сервері немає свідомо:** `POST /bookings` не ідемпотентний — автоматичний повтор після тайм-ауту міг би створити друге бронювання, тож повторює клієнт за `Retry-After`. **Резервного значення немає:** вигадана відповідь про бронювання гірша за чесну `503`.

## 4. Відкриті проблеми

Відкритих знахідок немає: усі 15 виправлено (останню, №10, — у #481). Нові знахідки учасників нумеруються з №15 у `scavenger-hunt.md`.

## 5. Тести надійності

| Тип (за завданням) | Файл | Що перевіряє |
|---|---|---|
| Обробка помилки | `tests/test_booking_atomic_audit.py` | збій аудиту → `500`, у БД нічого, повтор → `201` |
| Зовнішня відмова (ін'єкція збою) | `tests/test_db_timeouts.py` | lock / pool timeout → `503` + `Retry-After` |
| Зовнішня відмова (ін'єкція збою) | `tests/reliability/test_config_validation.py` | некоректна конфігурація → сервер не стартує |
| Граничний | `tests/reliability/test_config_validation.py` | TTL 4 / 5 / 1440 / 1441, `JWT_SECRET` 31 символ |
| Граничний | `tests/test_booking_reminder_time.py` | слот через 2 год і через 48 год |
| Конкурентність | `tests/test_booking_status_race.py` | гонка статусів → `409` |
| Регресія | `tests/test_no_blocking_in_async.py` | жоден обробник з БД не `async` |
| Граничний | `tests/reliability/test_booking_time_boundaries.py` | слот −1 с / рівно зараз / +1 с → `409` / `409` / `201` |
| Граничний | `tests/reliability/test_booking_input_validation.py` | `purpose` 200 / 201, `reason` 500 / 501, пробіли |
| Зовнішня відмова (ін'єкція збою) | `tests/reliability/test_health_db.py` | зламана / недоступна БД → health `503` |
| Обробка помилки | `tests/reliability/test_correlation_id.py` | невалідний заголовок → новий UUID, запит не падає |
| Регресія | `tests/reliability/test_bookings_list_query.py` | фільтр доступу й пагінація в SQL |
| Обробка помилки | `tests/reliability/test_booking_exception_scope.py` | сигнал завершення — без `rollback`; помилка застосунку — відкат, слот доступний |
| Обробка помилки | `tests/reliability/test_http_exception_codes.py` | невідомі 4xx → `BAD_REQUEST`, 5xx → `INTERNAL_ERROR` |
| Зовнішня відмова (ін'єкція збою) | `tests/reliability/test_openapi_export_resilience.py` | помилка запису / відсутній `yaml` → лог зі стеком, сервер стартує |

`<тести з #456 (Ромах) — після злиття>`

## 6. Презентація на парі (Етап 4)

Показали знахідку **№4** (бронювання й аудит у різних транзакціях): ланцюг несправність → помилка → відмова, вибір швидкої відмови, виправлення в #437 і тест. Презентував(ла): `<хто>`.

## 7. Бонуси

| Бонус | Хто пояснює у відео | Що зроблено | Докази | Стан |
|---|---|---|---|---|
| Health check з перевіркою БД (#458) | Лавришин | `/api/v1/health` виконує `SELECT 1`: `200 healthy` або `503 unhealthy`; старий маршрут без перевірки прибрано | PR #476; тест з ін'єкцією збою `tests/reliability/test_health_db.py` | ✅ виконано |
| Тести надійності — обов'язкова перевірка PR (#459) | Ромах | `<…>` | `<посилання на прогін>` | у роботі |
| Повтори з експоненційним відступом і full jitter (#460, за бажанням) | Балабанов | `<…>` | `<PR, тест>` | не розпочато |

---

*Використання ШІ: структуру звіту, фрагменти «до/після» та опис режимів відмов підготовано за допомогою Claude (Anthropic) на основі `scavenger-hunt.md`, PR #437, #443, #471, #474–#476, #478–#481 і коду репозиторію; розділи №9a і №13 — на основі звіту Балабанова з #478, звірені з кодом; перевірено та затверджено учасниками команди.*
