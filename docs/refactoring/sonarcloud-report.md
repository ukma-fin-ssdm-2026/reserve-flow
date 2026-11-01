# Звіт SonarQube Cloud — reserve-flow

**Проєкт:** `ukma-fin-ssdm-2026_reserve-flow`  
**Платформа:** SonarQube Cloud  
**Дата фіксації результатів:** 30.10.2026, аналіз `main` @ `4f0d996`  
**Quality Gate:** Passed

## 1. Початкові показники

| Метрика | Результат |
|---|---:|
| Code Smells / Maintainability issues | 12 |
| Maintainability Rating | A |
| Technical Debt | 24 min |
| Duplicated Lines | 11,8% (дають згенеровані `htmlcov/`; після їх виключення — 0%) |
| Reliability Rating | C |
| Reliability issues | 21 |
| Security Rating | C |
| Security issues | 17 |
| Security Hotspots | 0 |
| Quality Gate | Passed |


## 2. Вибрані метрики для покращення

Для подальшого рефакторингу обрано три показники. Security Rating фіксується окремо, оскільки він є обов'язковим, але не входить до цих трьох метрик.

### 2.1. Reliability Rating — C

У SonarQube Cloud відображено 21 Reliability issue.

**План покращення:**
- переглянути перелік зауважень категорії Reliability;
- визначити причини проблем;
- виправити підтверджені дефекти;
- запустити автоматизовані тести після внесення змін;
- повторити аналіз у SonarQube Cloud та порівняти рейтинг.

### 2.2. Cognitive Complexity (замість Duplicated Lines)

**Чому не Duplicated Lines.** 11,8 % давали згенеровані сторінки звіту покриття `htmlcov/`. Після їх виключення з аналізу показник — **0 %**. Власний код перевірено додатково: pylint (`duplicate-code`, блоки від 4 рядків) у `src/` і `scripts/` дублювання не знаходить; у `tests/` є лише 2 повтори по 6–9 рядків (`test_bookings.py:203–209` ↔ `test_bookings_regression.py:72–78`, `test_booking_transitions.py:61–70` ↔ `test_bookings_regression.py:49–58`) — нижче порогу SonarQube. Тож рефакторингом цей показник не покращити.

**Обрано когнітивну складність** (правило python:S3776, поріг SonarQube — 15):

| Функція | Складність |
|---|---:|
| `scripts/check_traceability.py::main` | 23 |
| `scripts/check_traceability.py::scan_tests` | 20 |
| `src/api/routes/slots.py::search_slots` | 19 |

**План покращення:**
- Extract Method / Decompose Conditional для кожної функції — складність кожної нижче 15;
- поведінка не змінюється: `tests/test_traceability.py` (6 тестів), `tests/api/test_slots_rooms.py`, `tests/test_slots_unit.py`, PT-001;
- повторний аналіз SonarQube Cloud.

### 2.3. Code Smells — 12

У проєкті зафіксовано 12 Code Smells. Maintainability Rating при цьому становить A.

**План покращення:**
- переглянути всі 12 зауважень;
- визначити, які з них реально ускладнюють читання та підтримку коду;
- виправити доцільні зауваження;
- перевірити зміни тестами та повторним аналізом.

## 3. Security Rating — обов'язковий показник

**Поточний Security Rating: C.**  
**Security issues: 19.**  
**Security Hotspots: 0.**

Нуль Security Hotspots не означає відсутності проблем безпеки: у проєкті окремо зафіксовано 19 Security issues.

Серед проблем:

- використання залежностей без фіксації resolved versions;
- відсутність параметра `--only-binary :all:` у командах встановлення пакетів;
- зауваження щодо перенаправлень на вебсайти без належного примусу HTTPS.

**Уже виправлено (після цього аналізу):**
- `pip install --only-binary :all:` у CI (`.github/workflows/ci.yml`, обидві job) — PR #374;
- Swagger UI в `docs/api/index.html`: версію зафіксовано на `5.34.0`, додано `integrity="sha384-…"` і `crossorigin="anonymous"` (Subresource Integrity) — PR #375, закриває 2 issues Web:S5725 (CWE-353, загроза Tampering зі STRIDE, Лаб 3).

Після повторного аналізу: Security Rating — C, Security issues — 15.

**План покращення безпеки (решта):**
1. Перевірити залежності та забезпечити фіксацію їхніх версій у lock-файлах.
2. Для встановлення залежностей використовувати hash-locked requirements там, де це застосовно.
3. Перевірити конфігурацію HTTPS та перенаправлень у відповідному workflow або конфігурації розгортання.
4. Повторити аналіз SonarQube Cloud і перевірити, чи покращився Security Rating та зменшилася кількість Security issues.

Наведені приклади не обов'язково охоплюють усі 17 проблем. Для повного переліку потрібно переглянути вкладку Issues із фільтром Security.

## 4. Виключення автогенерованих файлів

Під час перегляду Issues було пропущено зауваження з каталогу `htmlcov/`, зокрема з автогенерованого файлу:

`htmlcov/coverage_html_cb_54cfdca1.js`

Ці файли є результатом генерації звіту покриття тестами, а не основним вихідним кодом проєкту.

Автоматично згенеровані файли виключено з аналізу (`htmlcov/**`, налаштування проєкту SonarQube Cloud ). Після цього Duplicated Lines — 11,8 % → 0 %.

## 5. Підсумок та наступні кроки

Поточний Quality Gate має статус **Passed**, Maintainability Rating — **A**. Водночас Reliability Rating — **C**, Security Rating — **C**, а частка дубльованого коду — **0 %** після виключення `htmlcov/` (було 11,8 %).

Основні напрями подальшої роботи:

1. Покращити Reliability Rating шляхом усунення підтверджених проблем надійності.
2. Знизити когнітивну складність `check_traceability.main`, `scan_tests`, `search_slots` нижче 15.
3. Переглянути та виправити Code Smells.
4. Окремо усунути проблеми, що впливають на Security Rating.
5. Повторити аналіз і порівняти результати з початковими показниками.

---

Використання ШІ: Допомога в формулюванні, структуруванні ідей та форматуванні тексту: ШІ ChatGPT. Увесь текст вичитано, відредаговано та затверджено учасниками команди.
