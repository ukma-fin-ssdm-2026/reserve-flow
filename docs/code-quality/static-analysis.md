# Статичний аналіз коду

**Проєкт:** Reserve Flow (Team 3) · **Лабораторна 5** · issues #199, #200, #208, #209, #210

Документ фіксує, якими інструментами перевіряли код, що вони знайшли і що ми зробили з кожною знахідкою: виправили, свідомо прийняли ризик чи визнали хибним спрацюванням.

---

## 1. Інструменти, конфігурація і покриття

| Шар | Інструмент | Версія | Конфігурація | Де запускається |
|---|---|---|---|---|
| Форматування | black | 26.10 | `pyproject.toml` → `[tool.black] line-length = 100` | локально, pre-commit, CI (`lint`) |
| Стиль PEP 8 | flake8 | 7.4 | `.flake8` → `max-line-length = 100`, `extend-ignore = E203` | локально, pre-commit, CI (`lint`) |
| **Безпека коду** | **bandit** | 1.9.4 | `pyproject.toml` → `[tool.bandit] exclude_dirs = ["tests", ".venv", ".pytest_cache"]` | локально, pre-commit, CI (`lint`, `-ll`) |
| Секрети | detect-secrets | 1.5.0 | `.pre-commit-config.yaml` + `.secrets.baseline` | pre-commit |
| Залежності | pip-audit | 2.10 | `requirements*.txt` | CI (`security.yml`), щотижня |
| Залежності | Dependabot | — | `.github/dependabot.yml` | GitHub, щотижня |

**Покриття bandit:** увесь код застосунку в `src/` — 17 файлів, 1 498 рядків (`config.py`, `deps.py`, `errors.py`, `export_openapi.py`, `main.py`, `mcp_server.py`, `mocks.py`, `routes/*.py` (4), `schemas/*.py` (5)). Тести (`tests/`) виключено свідомо: у них навмисні тестові паролі й токени, і вони не потрапляють у робочий застосунок.

**Як запустити локально:**
```bash
pip install -r requirements-dev.txt
black --check src tests
flake8 src tests
bandit -c pyproject.toml -r src
pip-audit -r requirements.txt
pre-commit run --all-files
```

---

## 2. Стильовий шар: black + flake8

> Розділ доповнює керівник якості (Ромах, #197).

| Момент | flake8 (`src/api`, межа 100) | black |
|---|---|---|
| До (13.10, `main` @ `96372b7`) | **80 зауважень**: E501 довгі рядки (19), E402 імпорт не на початку файлу (12), W291/W293 пробіли (18), E302/E303 порожні рядки (14), W292 немає переносу в кінці (7) … | 12 файлів не відформатовано |
| Після PR #214–#216 | **0** | без змін |

---

## 3. Аналізатор безпеки: bandit

### 3.1. Результат першого прогону

`bandit -c pyproject.toml -r src` на `main` @ `b600cc1`:

```text
>> Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'lab4-demo'
   Severity: Low   Confidence: Medium
   CWE: CWE-259
   Location: src/api/deps.py:30:16
30	MOCK_PASSWORD = "lab4-demo"
--------------------------------------------------
>> Issue: [B104:hardcoded_bind_all_interfaces] Possible binding to all interfaces.
   Severity: Medium   Confidence: Medium
   CWE: CWE-605
   Location: src/api/main.py:98:26
98	    uvicorn.run(app, host="0.0.0.0", port=3000)
--------------------------------------------------
>> Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'issue_test_token'
   Severity: Low   Confidence: Medium
   CWE: CWE-259
   Location: src/api/mcp_server.py:36:4
36	    "issue_token_api_v1_auth_token_post": "issue_test_token",

Total issues (by severity): Low: 2, Medium: 1, High: 0
```

### 3.2. Рішення щодо кожної знахідки

| ID | Де | Рішення | Чому |
|---|---|---|---|
| **B104** | `main.py:98` | ✅ **Виправлено** (PR #218) | див. розділ 4 |
| **B105** | `deps.py:30` | ⚠️ **Ризик свідомо прийнято** | див. 5.1 |
| **B105** | `mcp_server.py:36` | ❎ **Хибне спрацювання** | див. 5.2 |

### 3.3. Після виправлень

```text
$ bandit -c pyproject.toml -r src -ll ; echo $?
0
Total potential issues skipped due to specifically being disabled (#nosec BXXX): 2
```

Обидва `# nosec` прописані з конкретним правилом (`B105`), а не загальним `# nosec`, і з коментарем-поясненням поруч. Так bandit і далі ловитиме інші проблеми в тих самих рядках.

---

## 4. Задокументована вразливість: B104, API доступний в обхід Nginx

| | |
|---|---|
| **Що знайдено** | `uvicorn.run(app, host="0.0.0.0", port=3000)` у `src/api/main.py`: сервер приймає з'єднання з усіх мережевих інтерфейсів машини |
| **Чим знайдено** | bandit, правило **B104** `hardcoded_bind_all_interfaces`, Severity: Medium, CWE-605 |
| **Чому це ризик** | За архітектурою (HLD, розділи 5–6) API працює лише за Nginx: Nginx завершує HTTPS і обмежує частоту запитів (`limit_req`, `limit_conn`). Якщо uvicorn слухає `0.0.0.0` на машині з публічною або університетською мережею, до API можна звернутися напряму на порт 3000, **в обхід обох контрзаходів**: <br>• трафік іде по HTTP, і токен можна перехопити — загроза **Spoofing (TB1–TB2)** з `threat-model.md`; <br>• немає обмеження частоти — загроза **Denial of Service (TB1–TB2)** |
| **Що зроблено** | Адресу й порт беремо зі змінних середовища, за замовчуванням лише `127.0.0.1`. У Docker і на сервері `API_HOST=0.0.0.0` задається явно, і там контейнер API доступний тільки у внутрішній мережі `app_net` за Nginx |
| **PR** | #218 (L5-06, #199), злито в `main` @ `aa8ac48`. Розблокував job `lint` з PR #217 |
| **Перевірка** | `bandit -ll` → 0 знахідок; 63 тести зелені; `python src/api/main.py` слухає `127.0.0.1:3000` |

```python
# було
uvicorn.run(app, host="0.0.0.0", port=3000)

# стало
uvicorn.run(
    app,
    host=os.getenv("API_HOST", "127.0.0.1"),
    port=int(os.getenv("API_PORT", "3000")),
)
```

---

## 5. Хибні спрацювання і прийняті ризики

### 5.1. B105 у `deps.py`: пароль заглушки (ризик прийнято)

- **Що:** `MOCK_PASSWORD = "lab4-demo"` — спільний пароль тестових користувачів заглушки автентифікації (рішення D-06, Лабораторна 4).
- **Чому не виправляємо зараз:** це не справжній секрет. Він задокументований у README і Swagger, щоб будь-хто міг перевірити API, а справжніх облікових записів у системі немає.
- **Обмеження ризику:** заглушка працює лише з даними-заглушками; у README і в описі `POST /auth/token` вказано, що це тестовий доступ.
- **Коли зникне:** разом із заглушкою, коли з'явиться справжня автентифікація за ADR-003 (PyJWT + pwdlib, #205). Тоді пароль зберігатиметься лише як bcrypt-хеш у БД.
- **У коді:** `# nosec B105` з коментарем-посиланням на цей документ.
- **Оновлення (L5-12, #205):** заглушку прибрано. Паролі зберігаються лише як bcrypt-хеші в БД, пароль тестових користувачів seed береться зі змінної `SEED_USER_PASSWORD` (`.env`), секрет JWT — з `JWT_SECRET`. У коді жодного пароля чи секрету; у тестах обидва значення генеруються випадково на кожен запуск. Знахідку B105 у `deps.py` закрито.

### 5.2. B105 у `mcp_server.py`: назва інструмента (хибне спрацювання)

- bandit вважає паролем будь-яке рядкове значення, ключ якого містить слово «token». Тут ключ — `issue_token_api_v1_auth_token_post` (operationId кінцевої точки), а значення `issue_test_token` — назва MCP-інструмента для агента.
- **У коді:** `# nosec B105` з поясненням. Позначено лише цей рядок, а не весь файл.
- **Оновлення (L5-12, #205):** інструмент перейменовано на `issue_token` (токен більше не тестовий). Спрацювання те саме, `# nosec B105` залишено.

### 5.3. detect-secrets: тестові паролі

Під час створення `.secrets.baseline` detect-secrets знайшов 3 «Secret Keyword»: `deps.py:30` (той самий пароль заглушки, див. 5.1) і `tests/api/test_auth.py:30–31` (тестові паролі `"wrong"` і `"lab4-demo"` у перевірці 401). Усі три позначено в baseline як `"is_secret": false`. Нові секрети хук і далі блокуватиме (див. розділ 8).

---

## 6. Вразливість, яку bandit не знайшов: CORS (бонус 3)

> Показує межі статичного аналізу: bandit перевіряє шаблони в Python-коді, але не логіку конфігурації безпеки. Цю проблему знайдено під час ручного огляду `main.py`.

| | |
|---|---|
| **Що знайдено** | `CORSMiddleware(allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])` |
| **Чим знайдено** | ручний огляд коду (аналітик безпеки); bandit і flake8 цього не ловлять |
| **Чому це ризик** | Будь-який сайт може робити запити до нашого API з браузера користувача і читати відповіді. Коли з'являться cookies або сесії, це відкриє атаки з чужого сайту від імені користувача. Загроза **Information Disclosure / Spoofing** на межі TB1–TB2 |
| **Що зроблено** | Дозволені origin задаються явно змінною `CORS_ORIGINS` (за замовчуванням `http://localhost:5173` для SPA і `http://localhost:3000` для Swagger); `"*"` відкидається навіть зі змінної; методи й заголовки обмежено тими, що реально використовуються |
| **PR** | #220 (L5-17, #210), окремий PR |
| **Регресійний тест** | `tests/api/test_cors.py` |

**Доказ, що тест ловить вразливість:**

```text
# на коді ДО виправлення (main @ aa8ac48, лише новий тест)
$ pytest tests/api/test_cors.py -q
FAILED tests/api/test_cors.py::test_cors_rejects_unknown_origin
  assert 'access-control-allow-origin' not in Headers({...,
    'access-control-allow-origin': 'https://evil.example',
    'access-control-allow-credentials': 'true', ...})
FAILED tests/api/test_cors.py::test_cors_preflight_rejects_unknown_origin
  assert 200 == 400
2 failed, 2 passed

# ПІСЛЯ виправлення
$ pytest tests/api/test_cors.py -q
4 passed
$ pytest tests -q
67 passed
```

| Тест | Що перевіряє |
|---|---|
| `test_cors_rejects_unknown_origin` | Запит з `Origin: https://evil.example` не отримує `Access-Control-Allow-Origin` |
| `test_cors_preflight_rejects_unknown_origin` | Preflight `OPTIONS` з чужого origin → `400` |
| `test_cors_allows_frontend_origin` | Наш фронтенд отримує дозвіл і `Allow-Credentials: true` |
| `test_cors_preflight_allows_frontend_origin` | Preflight з нашого фронтенду → `200` |

---

## 7. Аудит залежностей: pip-audit + Dependabot (бонус 2)

**Поточні версії чисті:** `pip-audit -r requirements.txt` → `No known vulnerabilities found`.

**Знахідка.** Наш `requirements.txt` задає діапазони (`fastapi>=0.115,<1.0`), а не точні версії. pip-audit перевіряє лише найновіші версії, тож ми окремо перевірили **найстаріші версії, які дозволяють наші діапазони**:

```text
$ pip-audit -r requirements-min.txt      # fastapi==0.115.0 та інші нижні межі
Name      Version  ID               Fix Versions
starlette 0.38.6   PYSEC-2026-1943  0.40.0     (CVE-2024-47874: DoS через multipart без filename)
starlette 0.38.6   PYSEC-2026-1941  0.47.2     (CVE-2025-54121: блокування event loop при великих файлах)
starlette 0.38.6   PYSEC-2026-161   1.0.1      (CVE-2026-48710: заголовок Host не валідується)
starlette 0.38.6   PYSEC-2026-2280  1.1.0      (CVE-2026-48817)
starlette 0.38.6   PYSEC-2026-2281  1.1.0      (CVE-2026-48818, StaticFiles на Windows)
starlette 0.38.6   PYSEC-2026-248   1.3.0      (CVE-2026-54282: шлях запиту не валідується)
starlette 0.38.6   PYSEC-2026-249   1.3.1      (CVE-2026-54283: обмеження request.form())
```

| | |
|---|---|
| **Чому це ризик** | Будь-хто з команди чи сервер з кешем pip міг встановити `fastapi 0.115.0`, а разом із ним `starlette 0.38.6` із 7 відомими вразливостями. Наш `requirements.txt` формально це дозволяв |
| **Що зроблено** | Додано явну нижню межу `starlette>=1.3.1` — версію, у якій виправлено всі знайдені вразливості. Сумісність перевірено: FastAPI ≥ 0.135 вимагає `starlette>=0.46` |
| **Перевірка** | `pip-audit` на нижніх межах після виправлення (`fastapi==0.135.0`, `starlette==1.3.1`) → `No known vulnerabilities found`; 63 тести зелені |
| **PR** | #221 (L5-15, L5-16; #208, #209) |

**Автоматизація:**
- `.github/workflows/security.yml`: `pip-audit` для `requirements.txt`, `requirements-mcp.txt`, `requirements-dev.txt` на кожен PR, push у `main` і щопонеділка;
- `.github/dependabot.yml`: щотижня перевіряє pip-пакети і GitHub Actions і відкриває PR з оновленнями. Перший кандидат — оновлення actions на Node.js 24: CI вже попереджає, що `actions/checkout@v4` і `actions/setup-python@v5` працюють на застарілому Node.js 20.

> **Стан CI на 15.10.2026.** З 14.10 запуски GitHub Actions в організації заблоковано лімітом витрат (billing): job-и завершуються без жодного кроку. Тому для #220 і #221 наведено результати локальних запусків тих самих команд. Після того як власник організації зніме обмеження (Settings → Billing → Actions), CI (`lint`, `security`) буде перезапущено, а посилання на прогони додано сюди.

---

## 8. pre-commit зі сканером секретів (бонус 1)

`.pre-commit-config.yaml` запускає перед кожним комітом:

| Хук | Що робить |
|---|---|
| trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict | базова гігієна файлів |
| **detect-secrets** (`--baseline .secrets.baseline`) | блокує коміт із новим секретом |
| black, flake8, bandit `-ll` | ті самі інструменти й конфігурація, що в CI (локальні хуки) |

Згенеровані `docs/api/openapi-generated.*` виключено: їх перевіряє CI, а хуки не повинні їх змінювати.

**Доказ спрацювання.** Спроба закомітити ключ JWT прямо в коді (запуск на комп'ютері автора, демонстраційний файл після перевірки видалено):

```text
$ cat src/api/jwt_demo.py
JWT_SECRET = "sk-live-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c"

$ git commit -m "add jwt secret"
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
check yaml...........................................(no files to check)Skipped
check for added large files..............................................Passed
check for merge conflicts................................................Passed
Detect secrets...........................................................Failed
- hook id: detect-secrets
- exit code: 1

ERROR: Potential secrets about to be committed to git repo!

Secret Type: Secret Keyword
Location:    src/api/jwt_demo.py:1

black (форматування).....................................................Passed
flake8 (стиль PEP 8).....................................................Passed
bandit (безпека).........................................................Passed

$ echo $?
1          ← коміт НЕ створено
```

Після виправлення (`JWT_SECRET = os.environ["JWT_SECRET"]`) усі хуки `Passed`, і коміт створюється.

---

## 9. Зв'язок із моделлю загроз (`threat-model.md`, STRIDE)

| Загроза (Лабораторна 3) | Знахідка / рішення Лабораторної 5 | Як код протистоїть |
|---|---|---|
| **Spoofing** TB1–TB2: перехоплення токена в незахищеній мережі | B104 | API не слухає зовнішні інтерфейси, тож трафік іде лише через Nginx з HTTPS |
| **Denial of Service** TB1–TB2: флуд `/auth`, `/bookings` | B104; CVE-2024-47874, CVE-2026-54283 у starlette | Немає обходу `limit_req` у Nginx; залежності без відомих DoS-вразливостей |
| **Information Disclosure / Spoofing** TB1–TB2 (браузер) | CORS `*` + credentials | Лише дозволені origin; регресійний тест |
| **Information Disclosure** TB2–TB3: витік облікових даних | detect-secrets, B105 | Секрети не потрапляють у git; паролі заглушки задокументовано як тестові |
| **Elevation of Privilege** TB1–TB2 | (покрито тестами Лабораторної 4: 401/403, `require_role`) | — |

---

## 10. Висновки

1. **Аналізатор безпеки знайшов реальну проблему (B104)**, яка зводила нанівець два контрзаходи з моделі загроз. Її виправлено.
2. **Не все, що знаходить bandit, — вразливість.** З трьох знахідок одна справжня, один ризик прийнято (тестовий пароль) і одне хибне спрацювання. Кожне рішення пояснено в коді й тут.
3. **Статичний аналіз не бачить усього.** CORS-помилку знайдено лише ручним оглядом. Тому огляд колегою лишається обов'язковим кроком політики якості.
4. **Діапазони версій теж треба перевіряти.** Поточні версії були чисті, але `requirements.txt` дозволяв встановити вразливий starlette.
5. Перевірки тепер автоматичні на трьох рівнях: **pre-commit** (до коміту), **CI** (`lint`, `security`) і **Dependabot** (щотижня).

---

*Використання ШІ: при підготовці документа, виправлень і тестів використано допомогу ШІ Claude. Усі результати інструментів отримано реальним запуском на коді репозиторію. Документ перевірено, відредаговано та затверджено учасниками команди.*
