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
* `docs/` — проєктна документація (вимоги, архітектура, API)
* `src/` — вихідний код проєкту
* `tests/` — модульні та інтеграційні тести
* `labs/` — посилання на Loom-відео до лабораторних у txt-файлах

## Запуск API (Локальна розробка)

Щоб запустити бекенд локально, спочатку встановіть залежності, а потім запустіть сервер з кореня репозиторію:
```bash
pip install -r requirements.txt
uvicorn main:app --app-dir src/api --reload --port 3000
```

Адреса Swagger UI після запуску: [http://localhost:3000/api-docs](http://localhost:3000/api-docs)

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

**Інструменти:** `search_slots`, `get_room`, `create_booking`, `list_bookings`, `get_booking`, `change_booking_status`, `update_slot_availability`, `who_am_i`, `issue_test_token`, `check_health`.

**Роль агента.** Агент викликає API від імені тестового користувача (заглушка автентифікації D-06). За замовчуванням це клієнт; іншу роль задає змінна середовища:
```bash
RESERVE_FLOW_TOKEN=mock-provider-token python src/api/mcp_server.py
```

**Підключення до агента** (Claude Desktop, Cursor та інші). Додайте сервер у конфігурацію MCP агента, вказавши абсолютні шляхи:
```json
{
  "mcpServers": {
    "reserve-flow": {
      "command": "/абсолютний/шлях/до/.venv/bin/python",
      "args": ["/абсолютний/шлях/до/reserve-flow/src/api/mcp_server.py"],
      "env": { "RESERVE_FLOW_TOKEN": "mock-client-token" }
    }
  }
}
```
Приклад завдання для агента: «Які аудиторії вільні 15 жовтня о 14:00?» — агент має обрати `search_slots`.

## Артефакти вимог (Requirements Artifacts)

Уся документація з інженерії вимог зберігається в каталозі `docs/requirements/`. Ключові документи проєкту:

* [Користувацькі історії (User Stories)](docs/requirements/user-stories.md)
* [Функціональні та нефункціональні вимоги (FR & NFR)](docs/requirements/requirements.md)
* [Матриця простежуваності (Requirements Traceability Matrix)](docs/requirements/rtm.md)
* [Варіанти використання (Use Cases)](docs/requirements/use-cases.md)

## Архітектурні артефакти (Architecture Artifacts)

Усі архітектурні рішення, діаграми та моделі зберігаються в каталозі `docs/architecture/`. Ключові документи проєкту:

* [Високорівневий дизайн (High-Level Design)](docs/architecture/high-level-design.md) — опис архітектурного стилю (модульний моноліт + SPA), компонентна архітектура та зведені UML-діаграми.
* [Матриця простежуваності (Traceability Matrix)](docs/architecture/traceability-matrix.md) — відображення функціональних та нефункціональних вимог на конкретні архітектурні компоненти.
* [Модель даних (Data Model)](docs/architecture/data-model.md) — ER-модель бази даних із позначеними чутливими даними.
* [Модель загроз (Threat Model)](docs/architecture/threat-model.md) — аналіз безпекових ризиків за методологією STRIDE на основі діаграми розгортання.
* [Журнал архітектурних рішень (ADR)](docs/architecture/decisions/) — реєстр ключових технічних рішень (вибір стилю, перехід на FastAPI тощо).
* [UML-діаграми (UML Diagrams)](docs/architecture/uml/) — вихідні файли діаграм компонентів, розгортання, послідовності та діяльності у форматі PlantUML.

## Робочий процес

Команда відстежує всю роботу через GitHub Issues і дошку Project з чотирма колонками:

- **Todo** — задача відкрита і ще не розпочата
- **In Progress** — задача призначена і над нею активно працюють
- **In Review** — робота завершена й очікує на перевірку чи затвердження (через PR review або перевірку колегою для нетехнічних задач)
- **Done** — задача затверджена/змержена (якщо код) або підтверджена як завершена (якщо не код) і не потребує подальших дій

Кожен issue має дві мітки: одну за **зоною відповідальності** (`repo`, `ci`, `tracker`, `brief`) і одну за **типом** (`bug`, `enhancement`, `documentation`, `task`, `question`, `scope`). Issues, пов'язані з невирішеними питаннями обсягу проєкту, позначаються міткою `scope` і розглядаються разом перед початком реалізації.

Issues групуються за milestones (наприклад, `Lab01: Team & Tooling Setup`), щоб відстежувати прогрес по кожному етапу проєкту окремо.

----------
Використання ШІ: Структурування документа та базовий текст згенеровані за допомогою ШІ Claude на основі ідей команди. Увесь текст вичитано, відредаговано та затверджено учасниками команди для відповідності реальним планам проєкту
