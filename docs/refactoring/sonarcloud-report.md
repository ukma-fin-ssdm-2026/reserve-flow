# Звіт SonarQube Cloud — reserve-flow

**Проєкт:** `ukma-fin-ssdm-2026_reserve-flow`  
**Платформа:** SonarQube Cloud (автоматичний аналіз; `htmlcov/` виключено — `.sonarcloud.properties`)  
**Стан «до»:** гілка [`pre-refactor`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/pre-refactor) — коміт [`3cbd8ae`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3cbd8ae1e37729809d75e143467b1634c1c8a453) (05.11.2026)  
**Аналіз «до»:** 05.11.2026 13:47 UTC, `main` @ `3cbd8ae` (останній аналіз перед рефакторингами Лаб 8)  
**Quality Gate («до»):** Passed  
**Аналіз «після»:** 07.11.2026 18:31 UTC, `main` @ [`34067a8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/34067a80dabeeda5a277bafbc9fc7c11f1030d39) — після злиття всіх рефакторингів (#430, #432, #423, #438)  
**Quality Gate («після»):** Passed  

## 1. Показники «до» і «після»

Дані — з історії аналізів SonarQube Cloud (API `measures/search_history`, `issues/search`) для аналізів `3cbd8ae` («до») і `34067a8` («після»). Між ними в `main` злито також Лаб 9 (див. розділ 2) — розбір змін у розділі 5.

| Метрика | «до» (`3cbd8ae`) | «після» |
|---|---:|---:|
| Code Smells (Maintainability issues) | 0 | 0 |
| Maintainability Rating | A | A |
| Technical Debt | 0 хв | 0 хв |
| Duplicated Lines | 0,0 % | 0,0 % |
| Reliability Rating | A (0 bugs) | A (0 bugs) |
| **Security Rating** | **C** (14 vulnerabilities) | **C** (14 vulnerabilities) |
| Security Hotspots | 0 | 0 |
| Cognitive Complexity (проєкт) | 217 | **204** |
| Cyclomatic Complexity (проєкт) | 433 | 486 |
| Рядків коду (ncloc) | 6 806 | 7 239 |

Скриншоти «до»: [історія метрик (Activity)](img/before-activity.png) · [Issues](img/before-issues.png) · [Security](img/before-security.png). Історія (Activity) показує саме аналіз `3cbd8ae`; Issues і Security знято 07.11 на `8aab34e` — до злиття рефакторингів, кількість зауважень (0 і 14) та сама, що на `3cbd8ae`.

### 1.1. Чому показники відрізняються від попередньої версії звіту

Попередня версія (аналіз 30.10, `4f0d996`) показувала 12 Code Smells, Reliability C, 24 хв боргу і 11,8 % дублювання. За історією SonarQube Cloud **усе це було в згенерованому звіті покриття `htmlcov/`**, а не в нашому коді. Після виключення `htmlcov/` з аналізу (`.sonarcloud.properties`: `sonar.exclusions=**/htmlcov/**,**/coverage/**`) обсяг аналізованого коду зменшився з 14 570 до 6 806 рядків, а Maintainability, Reliability, борг і дублювання — найкращі значення (0 / A).

## 2. Обрані метрики для покращення

П'ять стандартних метрик супроводжуваності й надійності на `3cbd8ae` уже мають найкращі значення (див. 1.1), тож покращити їх рефакторингом неможливо. Тому обрано метрики, що описують **наш код**:

| № | Метрика | «до» | Чому обрано | Що очікуємо |
|---|---|---:|---|---|
| 1 | **Cognitive Complexity** `scripts/check_traceability.py` | 57 | найскладніший файл проєкту (наступні — `routes/slots.py` 28, `routes/bookings.py` 25); у функціях `main` 23 і `scan_tests` 20 — вище порогу правила python:S3776 (15)¹ | зменшення: Extract Method / Decompose Conditional (#430) |
| 2 | **Cognitive Complexity** проєкту | 217 | сумарна складність нашого коду; показує ефект усіх рефакторингів разом | зменшення |
| 3 | **Code Smells** | 0 | контрольна: рефакторинги (#423, #430, #432) не мають додати нових вад | лишається 0 |

¹ Складність окремих функцій виміряно `flake8-cognitive-complexity`, бо SonarQube Cloud показує складність на рівні файлу.

**Чому не Cyclomatic Complexity.** Extract Method розбиває функцію на кілька менших, і кожна нова функція додає щонайменше 1 до цикломатичної складності файлу. Для `check_traceability.py` очікуємо зростання (47 → ≈ 67 за `radon`), хоча кожна функція стає простішою. Тому цю метрику наводимо для повноти, але не обираємо як ціль.

**Що ще змінилось між «до» і «після».** Після `3cbd8ae` у `main` злито також Лаб 9 (#435, #437: виправлення надійності в `routes/bookings.py`, `routes/slots.py`, `services/bookings.py`, `db.py`, `errors.py`). Ці зміни теж впливають на загальні метрики проєкту (на `8aab34e`: Cognitive Complexity 217 → 220, ncloc 6 806 → 7 033). Тому ефект рефакторингів Лаб 8 у розділі «після» показано і для проєкту, і окремо для змінених файлів, які Лаб 9 не зачіпала.

## 3. Security Rating — обов'язковий показник

**«До» (`3cbd8ae`): Security Rating C, 14 vulnerabilities, 0 Security Hotspots.** Усі 14 зауважень — у файлах GitHub Actions (`.github/workflows/`), у коді застосунку їх немає.

| Правило | Що означає | Де | Кількість | Серйозність |
|---|---|---|---:|---|
| githubactions:S8544 | залежності встановлюються без фіксації версій (немає lock-файлу з хешами) | `ci.yml:44, 147, 179, 180`, `security.yml:32`, `deploy-api-docs.yml:42` | 6 | Medium |
| githubactions:S8541 | `pip install` без `--only-binary :all:` — можуть виконатися скрипти встановлення пакета | `ci.yml:147, 179, 180`, `security.yml:32`, `deploy-api-docs.yml:42` | 5 | Medium |
| githubactions:S6506 | `curl -L` без примусу HTTPS — перенаправлення може привести на HTTP | `ci.yml:116` (завантаження PlantUML) | 1 | Medium |
| githubactions:S8233 | право на запис задано для всього workflow, а не для job | `deploy-api-docs.yml:19, 20` | 2 | Low |
| **Разом** | | | **14** | |

**Прийняте зауваження (Accepted, 1).** Окрім 14 відкритих, одне зауваження позначено як прийняте (01.11.2026): **docker:S8544**, `Dockerfile:9`, рядок `RUN pip install --only-binary :all: --no-cache-dir -r requirements.txt` — «Using dependencies without locking resolved versions». Це те саме, що S8544 у workflows: залежності встановлюються без lock-файлу з хешами. `--only-binary :all:` у Dockerfile вже є (#394), а фіксація версій потребує окремої зміни (крок 4 нижче), тож зауваження свідомо прийнято до неї. Прийняті зауваження не входять у 14 і не впливають на Security Rating; після кроку 4 його слід повторно відкрити й закрити виправленням.

**Узгодження чисел.** У попередній версії звіту були 19, 15 і 17 — ці числа неточні. За історією SonarQube Cloud Security issues було 17, потім 14 — після виправлень #374 (`--only-binary :all:` у двох кроках `ci.yml`) і #375 (Subresource Integrity для Swagger UI в `docs/api/index.html`, Web:S5725). На `3cbd8ae` — **14**.

**Зв'язок з Лаб 3 і Лаб 5.** Усі зауваження — про ланцюг постачання збірки: підміна пакета або скрипта під час CI — загроза **Tampering** за STRIDE. У `docs/architecture/threat-model.md` межі довіри описують лише застосунок, рядка для CI немає — його варто додати. У `docs/code-quality/static-analysis.md` (Лаб 5) залежності вже перевіряються `pip-audit` і Dependabot, але вони шукають відомі вразливості, а не фіксують версії — тому S8544 лишається.

**Що робимо далі (#407):**
1. S8541 — додати `--only-binary :all:` у решті п'яти кроків (як у #374);
2. S6506 — `curl --proto '=https' --tlsv1.2 -sSL …` для PlantUML;
3. S8233 — перенести `permissions: contents: write / pages: write` з рівня workflow на рівень job у `deploy-api-docs.yml`;
4. S8544 (і прийняте зауваження в `Dockerfile`) — потребує lock-файлу з хешами (`pip-compile --generate-hashes`) для всіх `requirements*.txt`; це окрема зміна поза рефакторингом Лаб 8, план — у #407.

Рефакторинги Лаб 8 (#423, #430, #432) файли workflow не змінюють, тому Security Rating після них очікувано не зміниться; його змінять лише кроки 1–4.

## 4. Виключення згенерованих файлів

`htmlcov/` (звіт покриття з Лаб 6) виключено з аналізу файлом `.sonarcloud.properties` (`sonar.exclusions=**/htmlcov/**,**/coverage/**`). На вкладці Code файлів з `htmlcov/` немає. Сам каталог ще в репозиторії — прибирається з git окремим PR; звіт покриття лишається артефактом `htmlcov` у кожному прогоні CI.

## 5. Рефакторинги, регресія і «після»

### 5.1. Обрані метрики: до і після

| № | Метрика | «до» (`3cbd8ae`) | «після» (`34067a8`) | Зміна |
|---|---|---:|---:|---|
| 1 | Cognitive Complexity `scripts/check_traceability.py` | 57 | **40** | −17 (−30 %) ✅ |
| 2 | Cognitive Complexity проєкту | 217 | **204** | −13 ✅ (без урахування Лаб 9: 220 → 204, −16) |
| 3 | Code Smells (контроль) | 0 | **0** | без змін ✅ — рефакторинги не додали вад |
| — | **Security Rating** | **C** (14) | **C** (14) | без змін — див. нижче |

Скриншоти «після»: [Overview, Overall Code](img/after-overview.png) · [історія метрик (Activity)](img/after-activity.png).

**Вплив Лаб 9.** Між «до» і «після» злито також Лаб 9 (#435, #437). Проміжний аналіз `8aab34e` (06.11, після Лаб 9, до рефакторингів): Cognitive Complexity 220, Cyclomatic 457, ncloc 7 033. Отже, Лаб 9 додала +3 до когнітивної складності, а рефакторинги Лаб 8 її зменшили на 16 (220 → 204).

**Що не покращилось і чому.**
- **Cyclomatic Complexity** 433 → 486. Лаб 9 дала +24 (→ 457), рефакторинги — ще +29. Це очікуваний наслідок Extract Method: кожна винесена функція додає щонайменше 1, хоча кожна окрема функція стала простішою (розділ 2). Тому цю метрику не обирали як ціль.
- **Security Rating** лишився C (14). Усі 14 зауважень — у `.github/workflows/`, а рефакторинги ці файли не змінювали (розділ 3). Виправлення — окремою зміною (#407).
- **`routes/bookings.py::update_booking`** після Лаб 9 має когнітивну складність 16 за `flake8-cognitive-complexity` (поріг 15). SonarQube Cloud зауваження не показує (Code Smells 0), але функція — кандидат на наступний рефакторинг (#404, не виконано в Лаб 8).

### 5.2. Складність змінених файлів

Складність файлів — SonarQube Cloud; складність окремих функцій — `flake8-cognitive-complexity`.

| Файл | PR | Cognitive (файл) | Cyclomatic (файл) | ncloc | Найскладніша функція |
|---|---|---:|---:|---:|---|
| `scripts/check_traceability.py` | #430 | 57 → **40** | 47 → 54 | 125 → 160 | `main` 23 → 1, `scan_tests` 20 → 1 |
| `src/api/routes/slots.py` | #438 | 28 → **26**¹ | 27 → 31 | 162 → 182 | `search_slots` 19 → 3 |
| `src/api/mcp_server.py` | #432 | 5 → 5 | 5 → 5 | 46 → 45 | — (Remove Dead Code) |
| `src/api/services/bookings.py` | #423 | 8 → 8¹ | 6 → 6 | 77 → 76 | — (одна константа) |

¹ «До» для файлів, які змінювала Лаб 9, — з аналізу `8aab34e` (після Лаб 9, до рефакторингів).

### 5.3. Рефакторинги

**R1. `scripts/check_traceability.py` — з ШІ-агентом** ([#430](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/430), #402, Лавришин)
- **Запах:** Cognitive Complexity > 15 (python:S3776) — `main` 23, `scan_tests` 20.
- **Техніка:** Extract Method + Decompose Conditional; вкладену функцію `visit` винесено на рівень модуля.
- **Що незмінне:** вивід скрипта, `GITHUB_STEP_SUMMARY`, анотації `::error::`, код виходу, публічні функції.
- **Який тест доводить:** коміт [`394a907`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/394a907) додав 4 тести на ще не покриті гілки — зелені на старому коді; ті самі 10 тестів `tests/test_traceability.py` зелені після рефакторингу [`07c1b3e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/07c1b3e). Вивід скрипта до/після ідентичний (`diff` порожній), у сценарії з помилками — теж. Крок CI «Traceability» зелений.

**R2. `src/api/mcp_server.py` — після характеризаційних тестів** ([#432](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/432), #413, Лавришин; бонус)
- **Запах:** мертвий код — ключ `get_health_api_v1_health_get` у `TOOL_NAMES` не відповідає жодній операції API (роутер `routes/health.py` не підключено).
- **Техніка:** Remove Dead Code.
- **Що незмінне:** набір інструментів агента і їх назви, JWT-хук, вибір ролі.
- **Який тест доводить:** 9 характеризаційних тестів `tests/test_mcp_server.py` (коміт [`233e0ea`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/233e0ea)) зелені до і після рефакторингу [`4ea8035`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/4ea8035); з реальним `fastmcp` список інструментів до/після ідентичний (10).

**R3. Одна константа `REMINDER_LEAD`** ([#423](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/423), #405, Покормяк)
- **Запах:** дубльована константа — `REMINDER_LEAD` у `services/bookings.py` і `_REMINDER_LEAD_TIME` у `services/notifications.py` (обидві 24 год).
- **Техніка:** Replace Magic Number with Constant (одне джерело в `services/notifications.py`).
- **Що незмінне:** час нагадування під час створення бронювання (`start_time − REMINDER_LEAD`); заміну на `compute_reminder_time` свідомо не робили — це зміна поведінки, винесена в #421.
- **Який тест доводить:** `tests/test_notifications.py`, `tests/api/test_booking_service.py`, `tests/test_booking_create_db.py` — зелені до і після (21 passed в описі PR).

**R4. `routes/slots.py::search_slots`** ([#438](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/438), #403, Ромах)
- **Запах:** Cognitive Complexity > 15 — `search_slots` 19.
- **Техніка:** Extract Method — `_validate_time_range` (перевірка часу), `_build_slots_query` (SQL-запит з фільтрів), `_matches_slot_filter` (фільтр слота за датою і часом); Decompose Conditional.
- **Що незмінне:** відповідь `GET /api/v1/slots` (фільтри, пагінація, `422` для `end <= start`), OpenAPI — крок CI перевірки специфікації зелений.
- **Який тест доводить:** `tests/api/test_slots_rooms.py`, `tests/test_slots_unit.py`, PT-001 (`tests/test_slots_performance.py`) — зелені до і після; CI PR зелений.

### 5.4. Регресійне тестування

**Команда:** `pytest -q` (локально); у CI — `pytest tests -q -m "not perf" --cov` (job «Tests with coverage») і окрема job «Performance Tests (NFR)».

| | Коміт | Результат |
|---|---|---|
| «До» | `pre-refactor` = `3cbd8ae` | 235 passed, 2 skipped |
| «Після» | `main` = `34067a8` | **258 passed, 2 skipped**, 0 failed |

258 = 235 + 4 (тести R1, #430) + 9 (характеризаційні тести R2, #432) + 10 (тести Лаб 9, #437). Рефакторинги Лаб 8 наявних тестів не змінювали (лише додавали нові); з наявних тестів змінювала лише Лаб 9 (`tests/test_slots_unit.py`, #437). Збоїв немає. `scripts/check_traceability.py` — код 0.

**CI на `main` після всіх рефакторингів:** [CI, `34067a8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/42401676904) — зелений (лінтери, тести з покриттям, перевірка OpenAPI, UML, Performance); [Security, `34067a8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/42401676916) — зелений.

### 5.5. Використання ШІ

**Рефакторинг з ШІ-агентом — R1** (`scripts/check_traceability.py`, #430) · агент: Claude Code (Anthropic) · виконавиця: Анастасія Лавришин.
- **Завдання агенту:** запах — Cognitive Complexity > 15 (python:S3776) у `main` (23) і `scan_tests` (20); техніка — Extract Method, Decompose Conditional; незмінні — вивід скрипта, `GITHUB_STEP_SUMMARY`, `::error::`, код виходу, публічні функції; спершу тести на непокриті гілки.
- **Що згенеровано:** 4 тести (окремий коміт до рефакторингу) і 12 допоміжних функцій замість двох великих.
- **Що виправлено вручну:** нічого — після перегляду diff рядок за рядком прийнято без змін.
- **Як верифіковано:** перегляд diff рядок за рядком; 4 нові тести зелені на старому і новому коді; вивід скрипта до/після ідентичний (на репозиторії — перевірено вручну, у сценарії з помилками — агентом); Cognitive Complexity: функції 23/20 → 1/1, файл у SonarQube 57 → 40; повний прогін і CI зелені (5.4).

**Інші рефакторинги.** R2 і характеризаційні тести (#432) підготовлено тим самим агентом і перевірено так само: тести на старому коді → рефакторинг → ті самі тести + порівняння списку інструментів з реальним `fastmcp`. R3 (#423) — підготовлено за допомогою Claude, перевірено тестами. Для R4 (#438) використання ШІ в PR не зазначено.

## 6. Бонуси

Бонуси Лаб 8, обрані командою (#398). Докази (PR, прогони CI, коміти) додаються сюди в міру виконання; кожен бонус пояснює у своєму відео відповідальний.

| Бонус | Відповідальний (пояснює у відео) | Що зроблено | Докази | Стан |
|---|---|---|---|---|
| Quality Gate як обов'язкова перевірка PR (#412) | Ромах | правило захисту гілки `main`: required status check `SonarCloud Code Analysis` — PR з червоним Quality Gate не можна злити | PR #388: зупинено Quality Gate ([`2e82519`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/388/changes/2e82519da80964ac5d9ae7ff1a374af4d8e803ae#diff-dd2c0eb6ea5cfc6c4bd4eac30934e2d5746747af48fef6da689e85b752f39557)); зелений прогін після виправлення ([`9a2f31c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/388/changes/9a2f31c14a8045d82c5616839454246a83163632)) | ✅ виконано |
| Характеризаційні тести `mcp_server.py` (#413) | Лавришин | тести фіксують поточну поведінку `mcp_server.py` (`TOOL_NAMES` ↔ `operationId` з `app.openapi()`, вибір ролі `RESERVE_FLOW_ROLE`, JWT у `_add_token`), потім рефакторинг Remove Dead Code (ключ `get_health_api_v1_health_get`); ті самі тести зелені до і після | коміт з тестами: [`233e0ea`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/233e0ea) (05.11 20:38); коміт з рефакторингом: [`4ea8035`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/4ea8035) (05.11 20:40) — PR [#432](https://github.com/ukma-fin-ssdm-2026/reserve-flow/pull/432); тести виконано, а не пропущено (`fastmcp` замінено заглушкою): [CI на `main` після злиття](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/42401643799) | ✅ виконано |
| Автоматизований реліз, release-please (#414) | — | — | — | **не виконано**: команда обрала ручний реліз (#409, #410) — CI працює на повільних self-hosted раннерах, і ризик для обов'язкової частини «CHANGELOG + версіонування» не вартий бонусу; issue закрито як «не плануємо» |


---

Використання ШІ: перша версія звіту — допомога у формулюванні та структуруванні ШІ ChatGPT. Розділи 1–5 оновлено (Лаб 8, #400, #408) за допомогою Claude (Anthropic): дані взято з API SonarQube Cloud для аналізів `3cbd8ae` і `34067a8`, складність функцій виміряно `flake8-cognitive-complexity` і `radon`. Увесь текст вичитано, перевірено та затверджено учасниками команди.
