# Звіт SonarQube Cloud — reserve-flow

**Проєкт:** `ukma-fin-ssdm-2026_reserve-flow`  
**Платформа:** SonarQube Cloud (автоматичний аналіз; `htmlcov/` виключено — `.sonarcloud.properties`)  
**Стан «до»:** гілка [`pre-refactor`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/tree/pre-refactor) — коміт [`3cbd8ae`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3cbd8ae1e37729809d75e143467b1634c1c8a453) (05.11.2026)  
**Аналіз «до»:** 05.11.2026 13:47 UTC, `main` @ `3cbd8ae` (останній аналіз перед рефакторингами Лаб 8)  
**Quality Gate («до»):** Passed  
**Аналіз «після»:** заповнюється після злиття рефакторингів #423, #430, #432 (#408)

## 1. Показники «до»

Дані — з історії аналізів SonarQube Cloud (API `measures/search_history`, `issues/search`) для аналізу `3cbd8ae`.

| Метрика | «до» (`3cbd8ae`) | «після» |
|---|---:|---:|
| Code Smells (Maintainability issues) | 0 | — |
| Maintainability Rating | A | — |
| Technical Debt | 0 хв | — |
| Duplicated Lines | 0,0 % | — |
| Reliability Rating | A (0 bugs) | — |
| **Security Rating** | **C** (14 vulnerabilities) | — |
| Security Hotspots | 0 | — |
| Cognitive Complexity (проєкт) | 217 | — |
| Cyclomatic Complexity (проєкт) | 433 | — |
| Рядків коду (ncloc) | 6 806 | — |

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

**Узгодження чисел.** У попередній версії звіту були 19, 15 і 17 — ці числа неточні. За історією SonarQube Cloud Security issues було 17, потім 14 — після виправлень #374 (`--only-binary :all:` у двох кроках `ci.yml`) і #375 (Subresource Integrity для Swagger UI в `docs/api/index.html`, Web:S5725). На `3cbd8ae` — **14**.

**Зв'язок з Лаб 3 і Лаб 5.** Усі зауваження — про ланцюг постачання збірки: підміна пакета або скрипта під час CI — загроза **Tampering** за STRIDE. У `docs/architecture/threat-model.md` межі довіри описують лише застосунок, рядка для CI немає — його варто додати. У `docs/code-quality/static-analysis.md` (Лаб 5) залежності вже перевіряються `pip-audit` і Dependabot, але вони шукають відомі вразливості, а не фіксують версії — тому S8544 лишається.

**Що робимо далі (#407):**
1. S8541 — додати `--only-binary :all:` у решті п'яти кроків (як у #374);
2. S6506 — `curl --proto '=https' --tlsv1.2 -sSL …` для PlantUML;
3. S8233 — перенести `permissions: contents: write / pages: write` з рівня workflow на рівень job у `deploy-api-docs.yml`;
4. S8544 — потребує lock-файлу з хешами (`pip-compile --generate-hashes`) для всіх `requirements*.txt`; це окрема зміна поза рефакторингом Лаб 8, план — у #407.

Рефакторинги Лаб 8 (#423, #430, #432) файли workflow не змінюють, тому Security Rating після них очікувано не зміниться; його змінять лише кроки 1–4.

## 4. Виключення згенерованих файлів

`htmlcov/` (звіт покриття з Лаб 6) виключено з аналізу файлом `.sonarcloud.properties` (`sonar.exclusions=**/htmlcov/**,**/coverage/**`). На вкладці Code файлів з `htmlcov/` немає. Сам каталог ще в репозиторії — прибирається з git окремим PR; звіт покриття лишається артефактом `htmlcov` у кожному прогоні CI.

## 5. Рефакторинги, регресія і «після»

Заповнюється після злиття #423, #430, #432 і нового аналізу `main` (#406, #408, #411).

## 6. Бонуси

Бонуси Лаб 8, обрані командою (#398). Докази (PR, прогони CI, коміти) додаються сюди в міру виконання; кожен бонус пояснює у своєму відео відповідальний.

| Бонус | Відповідальний (пояснює у відео) | Що зроблено | Докази | Стан |
|---|---|---|---|---|
| Quality Gate як обов'язкова перевірка PR (#412) | Ромах | правило захисту гілки `main`: required status check `SonarCloud Code Analysis` — PR з червоним Quality Gate не можна злити | PR, зупинений Quality Gate: <посилання>; зелений прогін після виправлення: <посилання> | у роботі (правило налаштовано, доказів ще немає) |
| Характеризаційні тести `mcp_server.py` (#413) | Лавришин | тести фіксують поточну поведінку `mcp_server.py` (`TOOL_NAMES` ↔ `operationId` з `app.openapi()`, вибір ролі `RESERVE_FLOW_ROLE`, JWT у `_add_token`), потім рефакторинг Remove Dead Code (ключ `get_health_api_v1_health_get`); ті самі тести зелені до і після | коміт з тестами: <sha>; коміт з рефакторингом: <sha>; прогін CI, де тести виконано (не пропущено): <посилання> | у роботі |
| Автоматизований реліз, release-please (#414) | — | — | — | **не виконано**: команда обрала ручний реліз (#409, #410) — CI працює на повільних self-hosted раннерах, і ризик для обов'язкової частини «CHANGELOG + версіонування» не вартий бонусу; issue закрито як «не плануємо» |


---

Використання ШІ: перша версія звіту — допомога у формулюванні та структуруванні ШІ ChatGPT. Розділи 1–4 оновлено (Лаб 8, #400) за допомогою Claude (Anthropic): дані взято з API SonarQube Cloud для аналізу `3cbd8ae`, складність функцій виміряно `flake8-cognitive-complexity` і `radon`. Увесь текст вичитано, перевірено та затверджено учасниками команди.
