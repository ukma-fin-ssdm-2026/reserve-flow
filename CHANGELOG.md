# Журнал змін

Усі помітні зміни проєкту Reserve Flow записуються в цей файл.

Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версії — за [семантичним версіонуванням](https://semver.org/lang/uk/). Номер версії однаковий у `pyproject.toml`, `src/api/config.py` (`API_VERSION`, він же `info.version` в OpenAPI), цьому файлі й git-тегі `vX.Y.Z`.

## [Unreleased]

### Fixed

- Нагадування про бронювання плануються через `compute_reminder_time`: для слота, що починається менш ніж за 24 год, нагадування більше не потрапляє в минуле, а для слота, що вже почався, не створюється (#443, #421; знахідка R-06 з `docs/reliability/scavenger-hunt.md`).
- Заголовок `X-Correlation-ID` від клієнта перевіряється: приймається лише `[A-Za-z0-9-]{1,64}`, інакше генерується новий UUID, а в лог іде попередження без «сирого» значення — захист від підробки ID і log injection (#468, знахідка №11).
- `GET /api/v1/bookings`: фільтр доступу за роллю, підрахунок і пагінація виконуються в БД (`JOIN`, `COUNT`, `ORDER BY created_at, id`, `OFFSET`/`LIMIT`) замість завантаження всієї таблиці й фільтрації в Python; прибрано N+1 запитів для постачальника — 3 SQL-запити на сторінку незалежно від розміру БД. Формат відповіді не змінився (#467, знахідка №5).
- `GET /api/v1/health` перевіряє БД (`SELECT 1`): `200 {"status": "healthy", "db": "ok"}` або `503 {"status": "unhealthy", "db": "unavailable"}` без внутрішніх деталей — Render (`healthCheckPath`) бачить реальний стан сервісу. Маршрут перенесено в `routes/health.py` (раніше — мертвий модуль); `operationId` і шлях `/health` без змін (#458, знахідка №7).
- `services/bookings.py::create_booking` перехоплює `except Exception:` замість `BaseException`: системні сигнали завершення (`SystemExit`, `KeyboardInterrupt`) більше не викликають мережевий `session.rollback()` і не затримують graceful shutdown воркера (знахідка №12).

## [1.0.1] - 2026-11-09

Реліз рефакторингу (Лаб 8). Зовнішня поведінка API не змінилась: усі тести, що були до рефакторингу, зелені (235 → 258 passed, 0 failed). Метрики до/після — у [`docs/refactoring/sonarcloud-report.md`](docs/refactoring/sonarcloud-report.md).

### Refactoring

- `scripts/check_traceability.py`: **Extract Method** + **Decompose Conditional** — `main` і `scan_tests` розбито на малі функції, вкладену `visit` винесено на рівень модуля; Cognitive Complexity функцій 23 / 20 → 1 / 1, файлу 57 → 40 (#430, #402). Виконано з ШІ-агентом; спершу додано 4 тести на непокриті гілки.
- `src/api/routes/slots.py`: **Extract Method** + **Decompose Conditional** — з `search_slots` винесено `_validate_time_range`, `_build_slots_query`, `_matches_slot_filter`; Cognitive Complexity функції 19 → 3 (#438, #403).
- `src/api/services/notifications.py`, `src/api/services/bookings.py`: **Replace Magic Number with Constant** — одна константа `REMINDER_LEAD` замість двох копій `timedelta(hours=24)` (#423, #405).
- `src/api/mcp_server.py`: **Remove Dead Code** — прибрано ключ `get_health_api_v1_health_get` з `TOOL_NAMES` (такої операції в API немає); перед цим додано 9 характеризаційних тестів (#432, #413).

### Fixed

Виправлення надійності з Лаб 9, злиті в `main` між 1.0.0 і 1.0.1 (#437, `docs/reliability/scavenger-hunt.md`):

- Тайм-аути до бази даних (з'єднання, пул, запит, блокування `FOR UPDATE`); перевищення → `503 SERVICE_UNAVAILABLE` з `Retry-After` замість «зависання» API.
- Обробники з синхронною сесією БД більше не блокують цикл подій (`def` замість `async def`).
- Бронювання, нагадування й запис аудиту зберігаються в одній транзакції.
- Зміна статусу бронювання захищена від гонки (умовний `UPDATE … WHERE status = …`): конфлікт → `409` замість хибного `200`.

## [1.0.0] - 2026-11-05

Стан до Лаб 8 — гілка [`pre-refactor`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/pre-refactor) (`3cbd8ae`). REST API `/api/v1` на FastAPI + PostgreSQL: вхід з JWT і ролями (клієнт, постачальник, адмін), пошук вільних слотів з фільтрами, закриття слотів постачальником, повний цикл бронювання в БД (створення з транзакційним блокуванням, перегляд, підтвердження, скасування не пізніше ніж за 2 години), аудит змін статусу. Номер `1.0.0` раніше був лише в `API_VERSION`; git-тегу для нього немає.

[Unreleased]: https://github.com/ukma-fin-ssdm-2026/reserve-flow/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/ukma-fin-ssdm-2026/reserve-flow/compare/3cbd8ae...v1.0.1
[1.0.0]: https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/pre-refactor

---

Використання ШІ: журнал змін підготовано за допомогою Claude (Anthropic) на основі описів PR #423, #430, #432, #437, #438, #443; перевірено учасниками
команди.
