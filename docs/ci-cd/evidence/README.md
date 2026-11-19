# Докази для `metrics-raw.md` (Лаб 10, L10-03)

Сирі дані, з яких складено таблицю [`../metrics-raw.md`](../metrics-raw.md): 104 запуски workflow `CI` на `main`, подія `push`.
За цими файлами можна перевірити кожен рядок таблиці.

**Дані отримано:** 19.11.2026 о 11:52 UTC (13:52 за Києвом), GitHub CLI `gh` 2.89.0, репозиторій `ukma-fin-ssdm-2026/reserve-flow`.

## Файли

| Файл | Що містить | Команда |
|---|---|---|
| `runs-main.json` | 200 останніх запусків `CI` на `main` (з 24.09 до 18.11), без змін; лише відформатовано `jq '.'` | `gh run list --workflow ci.yml --branch main --event push --limit 200 --json databaseId,headSha,workflowName,conclusion,attempt,createdAt,updatedAt` |
| `jobs-main.json` | 104 запуски з таблиці: `n` (номер рядка в таблиці), `databaseId`, `headSha`, `conclusion`, `createdAt` і для кожного завдання — `name`, `conclusion`, `startedAt`, `completedAt` | `gh run view <databaseId> --json jobs` для кожного запуску; з відповіді лишено ці чотири поля завдань (кроки `steps` не потрібні для таблиці) |
| `failed-logs/run-NNN-<databaseId>.txt` | 6 червоних запусків (№8, №9, №19, №20, №64, №65): уривки логів з рядками помилок і 4 рядками контексту перед кожною | `gh run view <databaseId> --log-failed` |

## Які запуски увійшли в таблицю

104 послідовні запуски з `runs-main.json`, у яких `createdAt` від `2026-10-22T13:15:51Z` (№1, коміт `7cb6a39`) до `2026-11-13T00:44:35Z` (№104, коміт `bbb25b4`) включно:

```bash
jq '[.[] | select(.createdAt >= "2026-10-22T13:15:51Z" and .createdAt <= "2026-11-13T00:44:35Z")] | length' runs-main.json   # 104
```

Запуски поза цими межами (раніше 22.10 16:15 за Києвом і пізніше 13.11 02:44) у `runs-main.json` є, але в таблицю не входять.

## Звірка з таблицею

Для всіх 104 рядків `metrics-raw.md` з цих файлів збігаються:
- коміт;
- номер рядка;
- статус (98 ✅, 6 ❌);
- **черга** — від `createdAt` до найранішого `startedAt`;
- **виконання** — від найранішого `startedAt` до найпізнішого `completedAt`.

Різниця для черги й виконання — не більше 0,5 хв, тобто в межах округлення до хвилини. Повторних спроб немає: в усіх 104 запусків `attempt = 1`.

## Червоні запуски

| № | Запуск | Коміт | Завдання, що впали | Причина з логу |
|---|---|---|---|---|
| 8 | [39814633477](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/39814633477) | `0e7fff9` | Code Quality and Security Linting, Tests with coverage | `would reformat tests/test_slots_unit.py`; 3 тести — `async def functions are not natively supported` |
| 9 | [39814904089](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/39814904089) | `977530b` | ті самі | ті самі збої, що в №8 |
| 19 | [39832856569](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/39832856569) | `ae49a45` | uml | завантаження JDK Temurin 17.0.21+9 → `Unexpected HTTP response: 404` |
| 20 | [39833369542](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/39833369542) | `be002e4` | uml | той самий `404` |
| 64 | [41336898520](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/41336898520) | `d0e600c` | Tests with coverage | `test_booking_e2e.py::test_row0_end_to_end` — `AssertionError: assert '…0001' in []` |
| 65 | [41337095116](https://github.com/ukma-fin-ssdm-2026/reserve-flow/actions/runs/41337095116) | `a4776e4` | Tests with coverage | той самий тест, що в №64 |

## Як повторити

```bash
gh run list --workflow ci.yml --branch main --event push --limit 200 \
  --json databaseId,headSha,workflowName,conclusion,attempt,createdAt,updatedAt > runs-main.json
gh run view 39814633477 --json jobs          # час завдань одного запуску
gh run view 39814633477 --log-failed         # повний лог завдань, що впали
```

Логи GitHub Actions зберігаються обмежений час, тож уривки логів збережено тут. Без них через кілька місяців причину ❌ вже не можна буде перевірити.

---

Використання ШІ: дані вивантажено й звірено з таблицею за допомогою ШІ-агента Claude Code (Anthropic); перевірено учасниками команди.
