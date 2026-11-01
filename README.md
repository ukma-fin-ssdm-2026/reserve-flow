![CI Status](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/workflows/ci.yml/badge.svg)

# Reserve Flow
Вебсервіс для бронювання приміщень у НаУКМА в онлайн-форматі.

## Команда Team 3
  - Анастасія Покормяк (GitHub: @zarizanakulbabka, електронна пошта НаУКМА: a.pokormiak@ukma.edu.ua)
  - Анастасія Лавришин (GitHub: @magicteamwinx, електронна пошта НаУКМА: a.lavryshyn@ukma.edu.ua)
  - Марія Ромах (GitHub: @regjine, електронна пошта НаУКМА: m.romakh@ukma.edu.ua)
  - Іван Балабанов (GitHub: @Ivan-Balabanov, електронна пошта НаУКМА: i.balabanov@ukma.edu.ua)

## Структура проєкту

* `.github/` — шаблони та конфігурації CI/CD workflows
* `docs/` — проєктна документація:
  * `docs/requirements/` — вимоги, історії, варіанти використання, матриця простежуваності (Лаб 2)
  * `docs/architecture/` — HLD, UML, модель даних, модель загроз, ADR (Лаб 3)
  * `docs/api/` — дизайн API, OpenAPI, атрибути якості, Swagger для GitHub Pages (Лаб 4)
  * `docs/code-quality/` — огляд коду, статичний аналіз, прогрес розробки (Лаб 5)
  * `docs/testing/` — стратегія тестування, журнал налагодження (Лаб 6)
  * `docs/validation/` — план тестування, журнал взаємного огляду (Лаб 7)
  * `docs/refactoring/` — звіт SonarQube Cloud (Лаб 8)
* `scripts/` — службові скрипти (перевірка простежуваності «вимога ↔ тест» у CI)
* `htmlcov/` — HTML-звіт покриття тестами
* `src/` — вихідний код проєкту
* `tests/` — модульні та інтеграційні тести
* `Labs/` — посилання на Loom-відео до лабораторних і проміжної презентації у txt-файлах

## Публічне розгортання API (Render / Docker)

Система налаштована для публічного хмарного розгортання (FastAPI + PostgreSQL 16) за допомогою конфігурації [`render.yaml`](render.yaml) (Render Blueprint) або контейнера [`Dockerfile`](Dockerfile).

* **Публічна адреса Swagger UI (Render):** [https://reserve-flow.onrender.com/api-docs](https://reserve-flow.onrender.com/api-docs)
* **Перевірка стану (Healthcheck):** [https://reserve-flow.onrender.com/api/v1/health](https://reserve-flow.onrender.com/api/v1/health)
* **Статична документація OpenAPI (GitHub Pages):** [https://ukma-fin-ssdm-2026.github.io/reserve-flow/](https://ukma-fin-ssdm-2026.github.io/reserve-flow/)

## Запуск API (Локальна розробка)

Потрібен **Python 3.11+** (у CI використовується Python 3.11) та Docker. Щоб запустити бекенд локально з кореня репозиторію:
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env          # і заповніть POSTGRES_PASSWORD, JWT_SECRET, SEED_USER_PASSWORD
docker compose up -d db      # PostgreSQL 16 на 127.0.0.1:5432
python src/api/seed.py       # таблиці й тестові дані (повторний запуск безпечний)
uvicorn main:app --app-dir src/api --reload --port 3000
```
`.env` є в `.gitignore`, у git він не потрапляє. Секрет для JWT (не коротший за 32 символи) згенеруйте так:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Вхід** (ADR-003): `POST /api/v1/auth/token` з email і паролем повертає JWT (строк дії — `ACCESS_TOKEN_EXPIRE_MINUTES`, 30 хв). Тестові користувачі після seed: `client@ukma.edu.ua`, `provider@ukma.edu.ua`, `admin@ukma.edu.ua`; пароль — ваш `SEED_USER_PASSWORD`. У Swagger UI вставте `access_token` у **Authorize**.

Адреса Swagger UI після локального запуску: [http://localhost:3000/api-docs](http://localhost:3000/api-docs)

**Команда генерації OpenAPI:**
```bash
python src/api/export_openapi.py
```
Файли специфікації зберігаються у: [`docs/api/`](docs/api/)

## Перевірка якості коду та статичний аналіз

Для підтримки стандартів кодування (PEP 8) та безпеки в проєкті використовуються `black`, `flake8`, `bandit` та `pip-audit`.

**Встановлення залежностей**
```bash
pip install -r requirements-dev.txt
```

**Команди запуску**

1. **Форматування коду (Black):**
   * Перевірка без внесення змін:
     ```bash
     python -m black --check src/ tests/
     ```
   * Автоматичне форматування:
     ```bash
     python -m black src/ tests/
     ```

2. **Перевірка стилю та конвенцій (Flake8):**
   ```bash
   python -m flake8 src/ tests/
   ```

3. **Статичний аналіз безпеки (Bandit):**
   * Повне сканування вихідного коду:
     ```bash
     python -m bandit -c pyproject.toml -r src/
     ```
   * Сканування лише на вразливості середнього та високого рівня:
     ```bash
     python -m bandit -c pyproject.toml -r src/ -ll
     ```

4. **Аудит вразливостей у залежностях (pip-audit):**
   ```bash
   python -m pip_audit -r requirements.txt
   ```

**Документація API (GitHub Pages):**
[Reserve Flow API Reference](https://ukma-fin-ssdm-2026.github.io/reserve-flow/)

## MCP-сервер (бонус)

[`src/api/mcp_server.py`](src/api/mcp_server.py) генерує MCP-сервер з нашого FastAPI-застосунку через `FastMCP.from_fastapi`: кожна кінцева точка стає інструментом агента з тими самими назвою, описом і схемою параметрів, що й у Swagger UI. Окремо запускати API не потрібно.

**Встановлення і запуск** (з кореня репозиторію):
```bash
pip install -r requirements-mcp.txt
python src/api/mcp_server.py
```

**Перевірка в MCP Inspector** (потрібен Node.js):
```bash
npx @modelcontextprotocol/inspector python src/api/mcp_server.py
```

**Інструменти:** `search_slots`, `get_room`, `create_booking`, `list_bookings`, `get_booking`, `change_booking_status`, `update_slot_availability`, `who_am_i`, `issue_token`, `check_health`.

**Роль агента.** Агент викликає API від імені тестового користувача з seed (потрібні запущена БД і `JWT_SECRET` у `.env`, див. «Запуск API»). Перед кожним викликом інструмента сервер видає свіжий JWT, тож сесія агента не обривається через строк дії токена. За замовчуванням це клієнт; іншу роль задає змінна середовища:
```bash
RESERVE_FLOW_ROLE=provider python src/api/mcp_server.py
```

**Підключення до агента** (Claude Desktop, Cursor та інші). Додайте сервер у конфігурацію MCP агента, вказавши абсолютні шляхи:
```json
{
  "mcpServers": {
    "reserve-flow": {
      "command": "/абсолютний/шлях/до/.venv/bin/python",
      "args": ["/абсолютний/шлях/до/reserve-flow/src/api/mcp_server.py"],
      "env": { "RESERVE_FLOW_ROLE": "client" }
    }
  }
}
```
Приклад завдання для агента: «Які аудиторії вільні 15 жовтня о 14:00?» — агент має обрати `search_slots`.

## Артефакти вимог (Requirements Artifacts)

Уся документація з інженерії вимог зберігається в каталозі `docs/requirements/`. Ключові документи проєкту:

* [Опис проєкту / Міні-ТЗ (Project Description)](Project-Description.md)
* [Користувацькі історії (User Stories)](docs/requirements/user-stories.md)
* [Функціональні та нефункціональні вимоги (FR & NFR)](docs/requirements/requirements.md)
* [Матриця простежуваності (Requirements Traceability Matrix)](docs/requirements/rtm.md)
* [Варіанти використання (Use Cases)](docs/requirements/use-cases.md)

## Тестування та валідація (Testing & Validation)

Тести — у каталозі `tests/`, документація — у `docs/testing/` і `docs/validation/`:

* [Стратегія тестування (Testing Strategy)](docs/testing/testing-strategy.md)
* [Журнал налагодження (Debugging Log)](docs/testing/debugging-log.md)
* [Звіт про покриття тестами (Coverage Report)](htmlcov/index.html)
* [План тестування (Test Plan)](docs/validation/test-plan.md)
* [Журнал взаємного огляду (Review Log)](docs/validation/review-log.md)
* Перевірка простежуваності «вимога ↔ тест» у CI: [`scripts/check_traceability.py`](scripts/check_traceability.py)

## Архітектурні та API артефакти (Architecture & Code Quality Artifacts)

Усі архітектурні рішення, діаграми, специфікації API та звіти якості коду зберігаються в каталогах `docs/architecture/`, `docs/api/` та `docs/code-quality/`:

* [Високорівневий дизайн (High-Level Design)](docs/architecture/high-level-design.md) — опис архітектурного стилю (модульний моноліт + SPA), компонентна архітектура та зведені UML-діаграми.
* [Матриця простежуваності (Traceability Matrix)](docs/architecture/traceability-matrix.md) — відображення функціональних та нефункціональних вимог на конкретні архітектурні компоненти.
* [Модель даних (Data Model)](docs/architecture/data-model.md) — ER-модель бази даних із позначеними чутливими даними.
* [Модель загроз (Threat Model)](docs/architecture/threat-model.md) — аналіз безпекових ризиків за методологією STRIDE на основі діаграми розгортання.
* [Журнал архітектурних рішень (ADR)](docs/architecture/decisions/) — реєстр ключових технічних рішень (вибір стилю, перехід на FastAPI тощо).
* [UML-діаграми (UML Diagrams)](docs/architecture/uml/) — вихідні файли діаграм компонентів, розгортання, послідовності та діяльності у форматі PlantUML.
* [Проєктування API (API Design)](docs/api/api-design.md), [Атрибути якості API](docs/api/quality-attributes.md) та [OpenAPI специфікація](docs/api/openapi-generated.yaml).
* [Звіт огляду коду (Review Report)](docs/code-quality/review-report.md), [Статичний аналіз (Static Analysis)](docs/code-quality/static-analysis.md) та [Прогрес розробки (Progress)](docs/code-quality/progress.md).

## Артефакти за лабораторними

| Лаб | Тема | Артефакти | Відео Loom |
|---|---|---|---|
| 1 | Команда та інструменти | [Статут команди](TeamCharter.md) (зокрема «Використання ШІ»), [README](README.md), [CI](.github/workflows/) | [`Labs/Lab01/`](Labs/Lab01/) |
| 2 | Вимоги | [Міні-ТЗ](Project-Description.md), [історії](docs/requirements/user-stories.md), [вимоги FR/NFR](docs/requirements/requirements.md), [варіанти використання](docs/requirements/use-cases.md), [RTM](docs/requirements/rtm.md) | [`Labs/Lab02/`](Labs/Lab02/) |
| 3 | Архітектура | [HLD](docs/architecture/high-level-design.md), [матриця простежуваності](docs/architecture/traceability-matrix.md), [UML](docs/architecture/uml/), [модель даних](docs/architecture/data-model.md), [модель загроз](docs/architecture/threat-model.md), [ADR](docs/architecture/decisions/) | [`Labs/Lab03/`](Labs/Lab03/) |
| 4 | API | [дизайн API](docs/api/api-design.md), [OpenAPI](docs/api/openapi-generated.yaml), [атрибути якості](docs/api/quality-attributes.md), [Swagger на GitHub Pages](https://ukma-fin-ssdm-2026.github.io/reserve-flow/) | [`Labs/Lab04/`](Labs/Lab04/) |
| 5 | Якість коду | [огляд коду](docs/code-quality/review-report.md), [статичний аналіз](docs/code-quality/static-analysis.md), [прогрес](docs/code-quality/progress.md) | [`Labs/Lab05/`](Labs/Lab05/) |
| 6 | Тестування | [стратегія](docs/testing/testing-strategy.md), [журнал налагодження](docs/testing/debugging-log.md), [покриття](htmlcov/index.html) | [`Labs/Lab06/`](Labs/Lab06/) |
| 7 | Планування тестування | [план тестування](docs/validation/test-plan.md), [журнал огляду](docs/validation/review-log.md) | [`Labs/Lab07/`](Labs/Lab07/) |
| 8 | Рефакторинг | [звіт SonarQube Cloud](docs/refactoring/sonarcloud-report.md) | — |
| — | Проміжне оцінювання | [розгортання і демо](Labs/midterm-presentation.txt) | — |

## Робочий процес

Команда відстежує всю роботу через GitHub Issues і дошку Project з чотирма колонками:

- **Todo** — задача відкрита і ще не розпочата
- **In Progress** — задача призначена і над нею активно працюють
- **In Review** — робота завершена й очікує на перевірку чи затвердження (через PR review або перевірку колегою для нетехнічних задач)
- **Done** — задача затверджена/змержена (якщо код) або підтверджена як завершена (якщо не код) і не потребує подальших дій

Кожен issue має дві мітки: одну за **зоною відповідальності** (`repo`, `ci`, `tracker`, `brief`) і одну за **типом** (`bug`, `enhancement`, `documentation`, `task`, `question`, `scope`). Issues, пов'язані з невирішеними питаннями обсягу проєкту, позначаються міткою `scope` і розглядаються разом перед початком реалізації.

Issues групуються за milestones (наприклад, `Lab01: Team & Tooling Setup`), щоб відстежувати прогрес по кожному етапу проєкту окремо.

----------
Використання ШІ: Структурування документа та базовий текст згенеровані за допомогою ШІ Claude та Gemini на основі ідей команди. Увесь текст вичитано, відредаговано та затверджено учасниками команди для відповідності реальним планам проєкту
