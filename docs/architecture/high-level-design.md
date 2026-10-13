# High-Level Design (HLD) — Система бронювання приміщень НаУКМА

---

## 1. Вступ та призначення документа

Цей документ описує високорівневу архітектуру (High-Level Design) вебсистеми онлайн-бронювання приміщень НаУКМА. Документ призначений для розробників, архітекторів та стейкхолдерів проєкту. Він фіксує основні архітектурні рішення, вибір технологічного стеку, підходи до розгортання та забезпечення нефункціональних вимог (NFR).

### 1.1 Межі системи (Scope)
* **Входить в обсяг:** Реєстрація/авторизація (RBAC), пошук і фільтрація доступних кімнат, створення та скасування бронювань, гарантування транзакційності від подвійного резервування, автоматичні сповіщення (Email), адмін-панель модерації та логування дій, локалізація інтерфейсу (UA/EN).
* **Поза межами:** Мобільні застосунки, онлайн-оплата, автоматична синхронізація з зовнішніми документами університету та інтеграція з зовнішніми календарями (Google Calendar тощо).

---

## 2. Архітектурний стиль та обґрунтування

Для проєкту обрано архітектурний стиль **Модульний моноліт (Modular Monolith)** із відокремленим **Single Page Application (SPA)** на фронтенді (чистий HTML + CSS + JS).

### Обґрунтування вибору (Rationale)
1. **Обмеження ресурсами та командою (C-001):** Команда з 4 розробників без виділеного DevOps-інженера не має накладних витрат на складну оркестрацію мікросервісів (Kubernetes, Service Discovery, API Gateway).
2. **Гарантії надійності та транзакційності (REL-001, FR-006):** Використання єдиної реляційної бази даних PostgreSQL дозволяє обробляти конкурентні запити за допомогою песимістичного блокування рядків (`with_for_update`) на рівні БД (ACID) без впровадження складних паттернів розподілених транзакцій (Saga, 2PC).
3. **Модульна чіткість:** Бізнес-логіка розбита на чіткі ізольовані модулі/сервіси (FastAPI APIRouters та Domain Services) у межах одного коду, що дозволяє паралельно працювати 4 розробникам без конфліктів.

---

## 3. Стек технологій

| Шар / Компонент | Технологія | Обґрунтування |
| :--- | :--- | :--- |
| **Frontend** | HTML + CSS + JS (Vanilla) | Легковагове рішення без інструментів збірки (без `npm` / Webpack). Багатомовність (FR-004) реалізується через легкий JS-модуль i18n (`ua.json` / `en.json`). |
| **Backend Framework** | Python 3.10+ / FastAPI | Сучасний асинхронний фреймворк для побудови REST API, автоматична генерація OpenAPI (Swagger UI), висока швидкість розробки. |
| **Security & Auth** | PyJWT + pwdlib (bcrypt) | Забезпечення вимог RBAC (FR-001, FR-002, SEC-001) з хешуванням паролів через `pwdlib` з алгоритмом bcrypt та перевіркою JWT-токена на кожному запиті. |
| **ORM / Data Access** | SQLModel / SQLAlchemy 2.0 | Зручне заповнення доменних моделей і DTO, повна підтримка асинхронності та песимістичних блокувань (`SELECT FOR UPDATE` через `.with_for_update()`). |
| **Database** | PostgreSQL | Вимоги C-003 та REL-001. Повна підтримка ACID, повноцінні песимістичні блокування рядків (`SELECT FOR UPDATE`). |
| **Async Tasks & Scheduling** | APScheduler + SQLAlchemyJobStore | Фоновий воркер у виділеному процесі (Standalone Process) для виконання нагадувань. |
| **External Mail** | SendGrid / SMTP Gateway | Вимога R-001 для запобігання потрапляння листів у спам при надсиланні сповіщень через SMTPS. |
| **CI/CD & Automation** | GitHub Actions | Вимога C-004. Автоматичний прогін лінтерів, юніт-тестів та інтеграційних тестів конкурентності у безкоштовному ліміті. |

---

## 4. Компонентна архітектура (Component View) та взаємодія

**Основні компоненти верхнього рівня:**
Web SPA → FastAPI Backend → Notification Scheduler → PostgreSQL (+ зовнішній SMTP). Детальну структуру показано на [діаграмі компонентів](uml/component.puml).

**Взаємодія компонентів:**
SPA звертається до API через HTTPS/REST з використанням JWT-токена. Роутери (FastAPI) викликають доменні сервіси, які працюють з базою даних через SQLModel у межах транзакцій. Notification Scheduler кожні 30 секунд читає БД і надсилає листи через зовнішній SMTP, а всі помилки доставки пишуться в Audit Log.

Серверна частина поділена на 3 внутрішні шари (Layered Architecture):

1. **API & Security Layer (FastAPI APIRouters):**
   * `Auth APIRouter`: обробка автентифікації, видача JWT, реєстрація (FR-001, FR-002).
   * `Room APIRouter`: пошук, фільтрація приміщень, подача запитів на додавання кімнат та керування статусом слотів (FR-003, FR-008, FR-009, FR-011).
   * `Booking APIRouter`: створення, перегляд, скасування бронювань, а також підтвердження / відхилення заявок постачальником (FR-005, FR-007, FR-010).
   * `Admin APIRouter`: панель управління користувачами, модерація кімнат, перегляд системних логів (FR-011, FR-012, FR-013).
2. **Business Domain Layer:**
   * `User & Auth Service`: бізнес-логіка керування акаунтами та ролями (FR-001, FR-002, FR-012).
   * `Room Management Service`: ведення довідників кімнат, перевірка статусу доступності слотів і наявності активних бронювань перед закриттям слота (FR-003, FR-008, FR-009, FR-011).
   * `Booking Engine Service`: центральний модуль перевірки колізій та резервування слотів із використанням песимістичних блокувань (`with_for_update`) для забезпечення FR-006 / REL-001. У тій самій транзакції створює запис `Notification`, з якого Notification Scheduler потім надсилає нагадування (FR-014).
   * `Audit Log Service`: фіксація дій користувачів у логах з часовими мітками (FR-013, FR-015).
3. **Background Processing Layer (Standalone Process):**
   * `Notification Scheduler`: фоновий воркер на базі **APScheduler** із збереженням задач у **SQLAlchemyJobStore**, який працює в окремому процесі. Він регулярно (кожні 30 секунд) вичитує з БД майбутні бронювання та надсилає листи, **не надсилаючи нагадування тим, хто вимкнув сповіщення** (FR-014). Статус і кількість спроб зберігаються безпосередньо в записі нагадування. У разі помилки відправки виконується **≥ 3 повтори з експоненційною затримкою** (REL-002), а всі помилки фіксуються в `Audit Log Service` (FR-015).

### 4.1 Діаграми

| Діаграма | Що показує |
|---|---|
| [Компонентна](uml/component.puml) | Компоненти, шари та їхні залежності з прив'язкою до FR |
| [Послідовності: створення бронювання](uml/sequence-booking.puml) | Критичний сценарій FR-005 / FR-006: перевірка JWT, блокування слота, `201` / `401` / `403` / `409` |
| [Діяльності: алгоритм бронювання](uml/activity-booking.puml) | Той самий сценарій як алгоритм з межами транзакції |
| [Розгортання](uml/deployment.puml) | Вузли, процеси, reverse proxy і межі довіри TB1–TB4 (див. розділ 6) |
| [ER-модель](uml/er.puml) | Сутності та зв'язки, описані в [data-model.md](data-model.md) |

### 4.2 Інтерфейси між компонентами

Компоненти взаємодіють через три види інтерфейсів:

1. **Зовнішній REST API** — Web SPA → APIRouter (HTTPS, JSON, JWT у заголовку `Authorization: Bearer`).
2. **Внутрішні операції сервісів** — APIRouter → доменний сервіс і сервіс → сервіс (виклики Python-методів у межах одного процесу).
3. **Інтерфейси даних та інфраструктури** — сервіси → PostgreSQL, Notification Scheduler → SMTP, reverse proxy → Uvicorn.

Шляхи REST API нижче — базова версія для Лабораторної 4, де API деталізується. `POST /api/bookings` і операції `create_booking` / `lock_slot` показано на [діаграмі послідовності](uml/sequence-booking.puml).

#### 4.2.1 Зовнішній REST API (Web SPA → APIRouter)

Посилання на [api-design.md](https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/main/docs/api)

Загальні правила:

- Усі кінцеві точки починаються з префіксу `/api/v1` (D-01); правила зміни версії — у `api-design.md`.
- Права перевіряє залежність FastAPI `Depends(get_current_user)` у кожному роутері (FR-002, D-06); роль береться лише з JWT-токена.
- Помилки повертаються в єдиному форматі `ErrorResponse` (D-04) з обов'язковими полями `code`, `message`, `details` та `correlation_id`:
  - `401` — `UNAUTHORIZED` (немає або недійсний токен);
  - `403` — `FORBIDDEN` (недостатньо прав, чужий ресурс або акаунт заблоковано);
  - `404` — `NOT_FOUND` (об'єкт не знайдено);
  - `409` — `SLOT_UNAVAILABLE` / `CANCELLATION_TOO_LATE` / `INVALID_STATUS_TRANSITION` / `ACTIVE_BOOKING_NEEDS_CONFIRMATION` (конфлікт стану);
  - `422` — `VALIDATION_ERROR` (некоректні вхідні дані, зокрема відхилення бронювання без причини чи закриття слота без `closure_reason`).

| Роутер | Операція | Роль | Вхід | Успіх | Помилки | Вимоги |
|---|---|---|---|---|---|---|
| Auth | `POST /api/v1/auth/token` <!-- раніше: POST /api/auth/login --> | — | `email`, `password` | `200` + `access_token` (JWT) | `401` невірні дані, `403` акаунт заблоковано | FR-001, FR-012, D-06 |
<!-- | Auth | POST /api/auth/register | — | email, full_name, password, role | 201 + профіль | 409 email зайнятий, 422 | FR-001 | -->
| Room | `GET /api/v1/slots` <!-- раніше: GET /api/rooms/search --> | Будь-яка (з токеном) | `room_id`, `date`, `start`, `end`, `capacity`, `has_projector`, `is_shelter`, `building`, `limit`, `offset` | `200` + `Page[SlotOut]` (список вільних слотів) | `401`, `422` (напр., кінець раніше за початок) | FR-003, PERF-001, D-02, D-05 |
| Room | `GET /api/v1/rooms/{room_id}` | Будь-яка (з токеном) | `room_id` (Path) | `200` + `RoomOut` (деталі приміщення) | `401`, `404` приміщення не знайдено | FR-003, D-02 |
| Room | `PATCH /api/v1/slots/{slot_id}` <!-- раніше: PATCH /api/slots/{slot_id} --> | Постачальник | `is_available`, `closure_reason` (обов'язкова при закритті) | `200` + `SlotOut` | `401`, `403` інша роль, `404` слот не знайдено, `409` ACTIVE_BOOKING_NEEDS_CONFIRMATION (на слоті є активне бронювання), `422` закриття без причини | FR-008, FR-009, D-02 |
<!-- | Room | POST /api/rooms/requests | Постачальник | дані приміщення | 201 + запит (Pending) | 422 | FR-011 | -->
| Booking | `POST /api/v1/bookings` <!-- раніше: POST /api/bookings --> | Клієнт | `slot_id`, `purpose` | `201` + `BookingOut` (`Pending`) + заголовок `Location` | `401`, `403` не клієнт, `404` слот не знайдено, `409` SLOT_UNAVAILABLE (слот закрито або вже заброньовано), `422` | FR-005, FR-006, REL-001, D-02 |
| Booking | `GET /api/v1/bookings` <!-- раніше: GET /api/bookings/my --> | Клієнт / Постачальник / Адмін | `status`, `limit`, `offset` | `200` + `Page[BookingOut]` (свої бронювання, бронювання на свої кімнати або всі — для адміністратора) | `401`, `422` | FR-005, D-02, D-05 |
| Booking | `GET /api/v1/bookings/{booking_id}` | Клієнт / Постачальник | `booking_id` (Path) | `200` + `BookingOut` | `401`, `403` чуже бронювання, `404` не знайдено | FR-005, D-02 |
| Booking | `PATCH /api/v1/bookings/{booking_id}` <!-- раніше: POST /api/bookings/{id}/cancel та POST /api/bookings/{id}/decision --> | Клієнт / Постачальник | `status` (`Cancelled` / `Confirmed` / `Rejected`), `reason` | `200` + `BookingOut` з оновленим статусом | `401`, `403` чуже бронювання чи кімната, `404`, `409` CANCELLATION_TOO_LATE (до початку менше 2 год), `409` INVALID_STATUS_TRANSITION, `422` відхилення без причини | FR-007, FR-010, D-03 |
<!-- | Admin | POST /api/admin/rooms/requests/{id}/decision | Адмін | decision, reason | 200 + приміщення | 403, 404 | FR-011 | -->
<!-- | Admin | PATCH /api/admin/users/{id} | Адмін | is_blocked | 200 + профіль | 403 спроба заблокувати адміністратора | FR-012 | -->
<!-- | Admin | GET /api/admin/bookings | Адмін | фільтри (дата, кімната, статус) | 200 + список | 403 | FR-012 | -->
<!-- | Admin | GET /api/admin/audit-log | Адмін | user_id, from, to, entity_type | 200 + записи журналу | 403 | FR-013 | -->

<!-- Commented are those that might be used later -->

#### 4.2.2 Внутрішні операції доменних сервісів

APIRouter не працює з БД напряму: він викликає операції сервісу і перетворює результат або виняток на HTTP-відповідь.

| Сервіс | Операція | Викликає | Результат / виняток | Вимоги |
|---|---|---|---|---|
| User & Auth Service | `register(email, full_name, password, role)` | Auth APIRouter | `User` / `EmailAlreadyUsed` | FR-001 |
| User & Auth Service | `authenticate(email, password)` | Auth APIRouter | JWT / `InvalidCredentials`, `UserBlocked` | FR-001, FR-012 |
| User & Auth Service | `get_current_user(token)` | усі APIRouter (`Depends`) | `User` / `Unauthorized`, `UserBlocked` | FR-002, SEC-001 |
| User & Auth Service | `set_blocked(user_id, blocked, admin)` | Admin APIRouter | `User` / `CannotBlockAdmin` | FR-012 |
| Room Management Service | `search_available(filters)` | Room APIRouter | список слотів | FR-003 |
| Room Management Service | `lock_slot(slot_id, session)` | Booking Engine Service | `TimeSlot`, заблокований до кінця транзакції (`SELECT … FOR UPDATE`) | FR-006, REL-001 |
| Room Management Service | `set_slot_status(slot_id, available, reason, confirm, provider)` | Room APIRouter | `TimeSlot` / `NotRoomOwner`, `ActiveBookingNeedsConfirmation`; активні бронювання слота читає запитом до таблиці `Booking` (лише читання) | FR-008, FR-009 |
| Room Management Service | `submit_room_request(data, provider)`, `moderate_room(room_id, decision, admin)` | Room APIRouter, Admin APIRouter | `Room` | FR-011 |
| Booking Engine Service | `create_booking(client_id, slot_id)` | Booking APIRouter | `Booking (Pending)` / `SlotUnavailable` | FR-005, FR-006 |
| Booking Engine Service | `cancel_booking(booking_id, user)` | Booking APIRouter | `Booking (Cancelled)` / `NotBookingOwner`, `CancellationTooLate` | FR-007 |
| Booking Engine Service | `decide_booking(booking_id, decision, reason, provider)` | Booking APIRouter | `Booking` / `NotRoomOwner`, `ReasonRequired` | FR-010 |
| Audit Log Service | `log(actor_type, user_id, action, entity_type, entity_id, details)` | Booking Engine, Room Management, User & Auth, Notification Scheduler | — | FR-013, FR-015 |
| Audit Log Service | `query(filters)` | Admin APIRouter | список записів | FR-013 |

**Правила:**

- `create_booking` відкриває одну транзакцію і передає ту саму сесію в `lock_slot`. Блокування, перевірка активних бронювань, запис `Booking` і запис `Notification` виконуються в ній; помилка на будь-якому кроці — `ROLLBACK` (див. [діаграму послідовності](uml/sequence-booking.puml)).
- Залежність між доменними сервісами одностороння: Booking Engine Service викликає Room Management Service (`lock_slot`), але не навпаки. Для FR-009 Room Management Service лише читає таблицю `Booking`, не викликаючи Booking Engine, тож циклічної залежності немає.
- Для дій планувальника `actor_type = System`, а `user_id` порожнє (див. `AuditLog` у [data-model.md](data-model.md)).

#### 4.2.3 Інтерфейси даних та інфраструктури

| Звідки → куди | Протокол / технологія | Що передається | Вимоги |
|---|---|---|---|
| Браузер → Reverse proxy (Nginx) | HTTPS | REST-запити SPA; TLS завершується на proxy | SEC-001 |
| Reverse proxy → Uvicorn (FastAPI) | HTTP у внутрішній мережі | ті самі запити | SEC-001 |
| Доменні сервіси → PostgreSQL | SQLModel / SQLAlchemy 2.0 (async), TCP 5432 | читання й запис сутностей з `data-model.md`; одна транзакція на запит | FR-006, REL-001 |
| Notification Scheduler → PostgreSQL | SQLAlchemy, TCP 5432 | кожні 30 с вибирає `Notification` зі `status = Pending` і `scheduled_time ≤ now`; оновлює `status`, `retry_count`; задачі APScheduler у SQLAlchemyJobStore | FR-014, PERF-002, REL-002 |
| Notification Scheduler → SMTP-шлюз | SMTPS (SendGrid / SMTP) | лист-нагадування; тайм-аут 5 с, ≥ 3 повтори з експоненційною затримкою | FR-014, FR-015, REL-002 |
| Notification Scheduler → Audit Log Service | виклик `log(...)` | помилки доставки | FR-015 |

---

## 5. Забезпечення нефункціональних вимог (NFR)

* **Продуктивність (PERF-001):** Для швидкого пошуку та запобігання деградації продуктивності у PostgreSQL створюються складені індекси (наприклад, на дату, кімнату й слот), а також індекси на зовнішні ключі (user_id, room_id).
* **Безпека (SEC-001):** Персональні та контактні дані користувачів шифруються at rest за допомогою розширення `pgcrypto` (або через використання шифрованого тому БД). Усі запити між клієнтом і сервером відбуваються виключно через HTTPS (налаштовується на рівні reverse proxy). Паролі надійно хешуються (pwdlib/bcrypt), а авторизація виконується за допомогою JWT.
* **Доступність (DoS, `threat-model.md`):** Reverse proxy обмежує частоту запитів (`limit_req` у Nginx) для ендпоінтів входу та бронювання. Блокування `SELECT FOR UPDATE` захищає цілісність даних, а не доступність, тому не розглядається як захист від флуду.
* **Надійність та транзакційність (REL-001):** Система використовує ACID-транзакції PostgreSQL з песимістичним блокуванням (`SELECT FOR UPDATE`), що повністю виключає можливість подвійного бронювання одного слота при паралельних запитах.

---

## 6. Розгортання (Deployment)

Діаграма: [deployment.puml](uml/deployment.puml) (з межами довіри TB1–TB4, які аналізуються в [threat-model.md](threat-model.md)).

Система розгортається на **одному хості** (Ubuntu) за допомогою `docker-compose` — це відповідає обмеженню C-001 (без виділеного DevOps). Запускаються **чотири контейнери**:

| Контейнер | Процес | Мережа | Назовні |
| :--- | :--- | :--- | :--- |
| `nginx` | Reverse proxy: термінація HTTPS, обмеження частоти запитів (`limit_req`) | `app_net` | порт 443 |
| `api` | `uvicorn` з FastAPI-бекендом | `app_net`, `db_net` | не публікується |
| `scheduler` | Окремий Python-процес з APScheduler (нагадування) | `app_net` (вихід до SMTP), `db_net` | не публікується |
| `postgres` | PostgreSQL з томом для даних | `db_net` | не публікується |

* `app_net` — зона застосунку (TB2): лише `nginx` приймає зовнішні з'єднання.
* `db_net` — ізольована внутрішня мережа Docker (`internal: true`, зона TB3): до PostgreSQL мають доступ лише контейнери `api` і `scheduler`, порт 5432 назовні не відкривається.
* Зовнішній SMTP-шлюз (TB4) викликає лише `scheduler`.

---

Використання ШІ: у структуруванні документа та при додатковій перевірці відповідності стандартам завдання було використано ШІ Gemini (відповідно до  ідей команди). Документ перевірено, відредаговано та затверджено учасниками команди

Розділи 4.1, 4.2 та оновлення розділів 5–6 підготовлено за допомогою ШІ Claude на основі діаграм і зауважень рецензента. Перевірено й вичитано учасниками команди.
