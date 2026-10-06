# Архітектурна матриця простежуваності

Цей документ — архітектурний зріз вимог з Лабораторної 2: **вимога → компонент → проєктне рішення → метод верифікації**.
Реєстр вимог (історія → NFR → тест) залишається в [`docs/requirements/rtm.md`](../requirements/rtm.md); ідентифікатори тестів нижче (`TC-`, `PT-`, `ST-`, `RT-`) взято звідти.

Компоненти відповідають [`uml/component.puml`](uml/component.puml) і [`high-level-design.md`](high-level-design.md).

**Правило перевірки:** жодної вимоги без компонента, жодного компонента без вимоги (розділ 3).

---

## 1. Вимоги → компоненти

### 1.1 Функціональні вимоги

| Вимога | Суть | Компоненти | Проєктне рішення | Верифікація |
|---|---|---|---|---|
| FR-001 | Реєстрація та автентифікація з ролями | Web SPA, Auth APIRouter, User & Auth Service, PostgreSQL | JWT (PyJWT); паролі зберігаються як хеш `pwdlib (bcrypt)`; роль записується в підписаний payload токена | TC-019, TC-029 |
| FR-002 | RBAC на кожен запит, 401/403 | Auth APIRouter, Room / Booking / Admin APIRouter, User & Auth Service | FastAPI-залежність `Depends` перевіряє токен і роль у кожному роутері; роль береться лише з JWT, не з тіла запиту | TC-003, TC-006, TC-009, TC-012, TC-018, TC-029, ST-002 |
| FR-003 | Пошук і фільтрація приміщень | Web SPA, Room APIRouter, Room Management Service, PostgreSQL | Фільтрація виконується SQL-запитом на сервері; складені індекси на `TimeSlot(room_id, start_time)` | TC-020, TC-024, TC-025, TC-026, PT-001 |
| FR-004 | Інтерфейс UA / EN | Web SPA, PostgreSQL | JS-модуль i18n (`ua.json` / `en.json`); назви приміщень і корпусів зберігаються двома мовами (`name_ua` / `name_en`, `building_ua` / `building_en`) | TC-021 |
| FR-005 | Створення бронювання вільного слота | Web SPA, Booking APIRouter, Booking Engine Service, Room Management Service, PostgreSQL | Booking Engine перевіряє слот через Room Management Service; нове бронювання отримує статус `Pending` | TC-022 |
| FR-006 | Транзакційність, без подвійного резервування | Booking Engine Service, PostgreSQL | `SELECT … FOR UPDATE` (`with_for_update`) і `INSERT` в одній транзакції; при конфлікті — `409 Conflict` | RT-001 |
| FR-007 | Скасування не пізніше ніж за 2 год | Booking APIRouter, Booking Engine Service, Audit Log Service, PostgreSQL | Ліміт 2 год перевіряється на сервері за `TimeSlot.start_time`; статус `Cancelled`, слот знову доступний | TC-016, TC-017, TC-018 |
| FR-008 | Постачальник змінює статус слотів із причиною | Room APIRouter, Room Management Service, PostgreSQL | Поля `TimeSlot.is_available` і `closure_reason` | TC-007, TC-009 |
| FR-009 | Підтвердження перед закриттям слота з активним бронюванням | Room APIRouter, Room Management Service, PostgreSQL | Перед закриттям сервіс перевіряє активні бронювання слота і вимагає повторного підтвердження | TC-008 |
| FR-010 | Підтвердження / відхилення заявок з причиною | Booking APIRouter, Booking Engine Service, PostgreSQL | Статуси `Confirmed` / `Rejected`; `rejection_reason` обов'язкове при відхиленні | TC-010, TC-011, TC-012 |
| FR-011 | Модерація запитів постачальника | Room APIRouter, Admin APIRouter, Room Management Service, PostgreSQL | Нове приміщення має `moderation_status = Pending` і не видно в пошуку до погодження; `approved_by` фіксує адміністратора | TC-001, TC-002, TC-003 |
| FR-012 | Адмін-панель: користувачі, бронювання, довідник | Admin APIRouter, User & Auth Service, Room Management Service, PostgreSQL | Поле `User.is_blocked`; заблокований користувач отримує `403` на будь-який запит | TC-023, TC-027, TC-028 |
| FR-013 | Системні логи з часовими мітками | Audit Log Service, Admin APIRouter, Booking Engine Service, Room Management Service, PostgreSQL | Сервіси пишуть дії в таблицю `AuditLog`; записи лише додаються, не змінюються | TC-004, TC-005, TC-006 |
| FR-014 | Нагадування за N годин | Notification Scheduler, PostgreSQL, External Email Gateway | Окремий процес APScheduler опитує таблицю `Notification` кожні 30 с; пропускає користувачів з `notifications_enabled = false` | TC-013, TC-015, PT-002 |
| FR-015 | Логування помилок доставки та retry | Notification Scheduler, Audit Log Service, External Email Gateway, PostgreSQL | `Notification.status` і `retry_count`; кожна помилка записується в `AuditLog` | TC-014, RT-002 |

### 1.2 Нефункціональні вимоги

| Вимога | Суть | Компоненти | Проєктне рішення | Верифікація |
|---|---|---|---|---|
| PERF-001 | Пошук ≤ 5 с при 10 одночасних користувачах | Room APIRouter, Room Management Service, PostgreSQL | Асинхронний FastAPI; фільтрація в SQL; складені індекси | PT-001 (сценарій QAS-1) |
| PERF-002 | Нагадування ініціюється ≤ 60 с після тригера | Notification Scheduler, PostgreSQL | Інтервал опитування 30 с — удвічі менший за ліміт; індекс на `Notification(status, scheduled_time)` | PT-002 |
| SEC-001 | Шифрування персональних даних, лише HTTPS, 0% доступу до чужих даних | Web SPA, усі APIRouter, User & Auth Service, PostgreSQL | HTTPS через reverse proxy (Nginx / Traefik); `pgcrypto` для `email` і `full_name`; RBAC (FR-002) | ST-001, ST-002 (сценарій QAS-3) |
| REL-001 | 0 подвійних бронювань при ≥ 10 одночасних запитах | Booking Engine Service, PostgreSQL | Песимістичне блокування рядка в одній транзакції | RT-001 (сценарій QAS-2) |
| REL-002 | ≥ 99% нагадувань відправлено, ≥ 3 retry з експоненційною затримкою | Notification Scheduler, External Email Gateway, PostgreSQL, Audit Log Service | Стан спроб у записі `Notification`; задачі в SQLAlchemyJobStore переживають перезапуск; окремий процес | RT-002 |

---

## 2. Компоненти → вимоги

| Компонент | Шар | Вимоги |
|---|---|---|
| Web SPA | Клієнт | FR-001, FR-003, FR-004, FR-005, SEC-001 |
| Auth APIRouter | API | FR-001, FR-002, SEC-001 |
| Room APIRouter | API | FR-002, FR-003, FR-008, FR-009, FR-011, PERF-001, SEC-001 |
| Booking APIRouter | API | FR-002, FR-005, FR-007, FR-010, SEC-001 |
| Admin APIRouter | API | FR-002, FR-011, FR-012, FR-013, SEC-001 |
| User & Auth Service | Домен | FR-001, FR-002, FR-012, SEC-001 |
| Room Management Service | Домен | FR-003, FR-005, FR-008, FR-009, FR-011, FR-012, FR-013, PERF-001 |
| Booking Engine Service | Домен | FR-005, FR-006, FR-007, FR-010, FR-013, REL-001 |
| Audit Log Service | Домен | FR-007, FR-013, FR-015, REL-002 |
| Notification Scheduler | Фоновий процес | FR-014, FR-015, PERF-002, REL-002 |
| PostgreSQL | Дані | FR-001, FR-003–FR-015, PERF-001, PERF-002, SEC-001, REL-001, REL-002 |
| External Email Gateway | Зовнішній | FR-014, FR-015, REL-002 |

---

## 3. Перевірка покриття

- **Вимоги без компонента:** немає — усі 15 FR і 5 NFR мають щонайменше один компонент і метод верифікації.
- **Компоненти без вимоги:** немає — усі 12 компонентів з `component.puml` покривають щонайменше одну вимогу.

**Знайдені розбіжності між вимогами й діаграмами (виправлено):**

| ✓ | # | Що | Де | Пропозиція |
|---|---|----|----|------------|
| ✓ | 1 | SEC-001 покладається на HTTPS через reverse proxy, але proxy немає ні на діаграмі компонентів, ні на діаграмі розгортання | `deployment.puml`, HLD §6 | Додати вузол Nginx / Traefik між браузером і Uvicorn |
| ✓ | 2 | FR-009: Room Management Service має знати про активні бронювання слота, але зв'язку з бронюваннями на діаграмі немає | `component.puml` | Або дописати в HLD, що сервіс читає таблицю `Booking` напряму |
| ✓ | 3 | FR-014: хто створює запис `Notification` при новому бронюванні — не показано | `component.puml`, HLD §4 | Дописати: Booking Engine створює запис `Notification` у тій самій транзакції, що й бронювання |
| ✓ | 4 | FR-012: `is_blocked` у `data-model.md` належить `User`, а в `er.puml` — `Room` | `er.puml` | Перенести поле в `User` |

---

## 4. Сценарії атрибутів якості

Формат: джерело → стимул → артефакт → середовище → реакція → метрика.

### QAS-1. Продуктивність пошуку (PERF-001)

| Елемент | Значення |
|---|---|
| Джерело | 10 клієнтів одночасно |
| Стимул | Пошук вільних приміщень за датою, часом і фільтрами (місткість, проєктор, укриття) |
| Артефакт | Room APIRouter → Room Management Service → PostgreSQL |
| Середовище | Звичайна робота; синтетичні тестові дані (A-003) |
| Реакція | Система повертає список приміщень, що відповідають усім фільтрам і вільні на обраний час |
| Метрика | Відповідь на кожен із 10 запитів ≤ 5 с |
| Верифікація | PT-001 — навантажувальний тест на 10 віртуальних користувачів |

### QAS-2. Надійність бронювання (REL-001)

| Елемент | Значення |
|---|---|
| Джерело | 10 клієнтів |
| Стимул | Одночасні запити на бронювання одного й того самого слота |
| Артефакт | Booking Engine Service → PostgreSQL |
| Середовище | Звичайна робота |
| Реакція | Один запит отримує `201 Created`, решта — `409 Conflict` з повідомленням «Обраний час уже зайнято» |
| Метрика | Рівно 1 бронювання для слота; 0 дублікатів |
| Верифікація | RT-001 — інтеграційний тест із 10 паралельними запитами і перевіркою таблиці `Booking` |

### QAS-3. Безпека доступу до чужих даних (SEC-001, FR-002)

| Елемент | Значення |
|---|---|
| Джерело | Автентифікований клієнт з дійсним JWT |
| Стимул | Спроба скасувати чуже бронювання або відкрити ендпоінт адміністратора |
| Артефакт | Booking APIRouter / Admin APIRouter → перевірка ролі та власника → Booking Engine Service |
| Середовище | Звичайна робота |
| Реакція | Запит відхиляється з `403 Forbidden`; дані не змінюються |
| Метрика | 100% таких запитів отримують `403`; 0 змінених записів |
| Верифікація | ST-002, TC-018 — API-тест з токеном іншого користувача |

---

Використання ШІ: Структуру матриці, зіставлення вимог з компонентами та чернетки сценаріїв атрибутів якості підготовлено за допомогою ШІ Claude на основі `requirements.md`, `rtm.md`, `component.puml`, `data-model.md` і `high-level-design.md` команди. Усе вичитано й перевірено учасником команди.
