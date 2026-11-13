# Сирі дані конвеєра CI на `main` (Клініка продуктивності CI/CD, етап 1)

**Джерело:** історія запусків workflow `CI` (`.github/workflows/ci.yml`) на гілці `main`, подія `push`.
**Період:** 22.10.2026 – 13.11.2026 (3,15 тижня), **104 запуски**: 98 ✅ і 6 ❌. Повторних спроб (`attempt > 1`) не було.
Час у таблиці київський: до 25.10 EEST (UTC+3), після — EET (UTC+2).

## Як отримано дані

Дані зібрано через GitHub API — це ті самі поля, що повертають `gh run list` і `gh run view --json jobs`:

```bash
gh run list --workflow ci.yml --branch main --event push --limit 200 \
  --json databaseId,headSha,workflowName,conclusion,attempt,createdAt,updatedAt
gh run view <databaseId> --json jobs   # startedAt / completedAt кожного завдання
gh pr view <номер> --json commits      # authoredDate першого коміту PR
```

**Стовпці таблиці:**

| Стовпець | Як обчислено |
|---|---|
| **Черга, хв** | від `createdAt` запуску до `startedAt` **першого** завдання |
| **Виконання, хв** | від `startedAt` першого завдання до `completedAt` **останнього**. Завдань 4–5 (`Tests with coverage`, `api`, `uml`, `Code Quality and Security Linting`, `Performance Tests (NFR)`), і коли вільних раннерів бракує, вони чекають одне на одного. Тому у великих значеннях сидить ще й очікування раннера всередині запуску (див. `dora-summary.md`) |
| **Запуск завершено** | `completedAt` останнього завдання. Поле `updatedAt` для цього не годиться: GitHub інколи оновлює його на кілька хвилин пізніше |
| **PR / Перший коміт PR** | номер PR, з якого злито коміт, і `authoredDate` найранішого коміту PR, тобто першого коміту в `git rev-list <merge>^1..<merge>^2`. 18 PR злито через інтерфейс GitHub зі зміненим заголовком, їхні номери знайдено пошуком за SHA злиття |
| **Час виконання зміни** | від першого коміту PR до завершення **першого зеленого** запуску на `main`, що містить цей коміт. Для червоного запуску це наступний зелений |
| **Причина ❌** | з логів завдань, що впали (`gh run view <id> --log-failed`) |

## Таблиця

| № | Коміт | PR | Перший коміт PR | Запуск завершено | Черга, хв | Виконання, хв | Статус | Час виконання зміни | Примітка |
|---|---|---|---|---|---:|---:|---|---:|---|
| 1 | [`7cb6a39`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/7cb6a3958023d1b6616ecc55bf71e67093b6c1d2) | #277 | 22.10 03:12 | 22.10 16:17 | 0 | 1 | ✅ | 13 год 5 хв |  |
| 2 | [`2dce2cb`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/2dce2cb300870b8390eedbc4352b9c4c7a243e9b) | #278 | 22.10 16:35 | 22.10 17:13 | 0 | 5 | ✅ | 38 хв |  |
| 3 | [`f99f284`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/f99f284f279096f903c79a50642105b79e3e0205) | #279 | 22.10 16:59 | 22.10 17:23 | 0 | 1 | ✅ | 25 хв |  |
| 4 | [`32b8649`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/32b864920afd04d319bf2ff6f8990fb882da97dd) | #280 | 22.10 17:30 | 22.10 17:35 | 0 | 1 | ✅ | 5 хв |  |
| 5 | [`f9ba7f8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/f9ba7f82ed07fd4754c6159ccb651cf035e9bac5) | #281 | 22.10 17:32 | 22.10 17:56 | 0 | 1 | ✅ | 24 хв |  |
| 6 | [`624047b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/624047bd614e9307c5fb26a4788fb3530d301d94) | #282 | 22.10 17:35 | 22.10 18:25 | 0 | 6 | ✅ | 50 хв |  |
| 7 | [`3b987f4`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3b987f45bb610c1b616589d73ee9885f8b585114) | #284 | 22.10 18:44 | 22.10 19:25 | 0 | 1 | ✅ | 41 хв |  |
| 8 | [`0e7fff9`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0e7fff99d9fb6fc9d74e6004ef83758539cf533c) | #286 | 22.10 18:55 | 22.10 19:31 | 0 | 1 | ❌ | 1 год 3 хв | lint: Black — `tests/test_slots_unit.py` не відформатовано; tests: 3 async-тести в `test_slots_unit.py` впали — «async def functions are not natively supported» (немає pytest-asyncio). Зламав PR #286, злитий з червоними перевірками; зміна дійшла до зеленого `main` у №10 |
| 9 | [`977530b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/977530b7b96900251842dc3b4fb12363f9909211) | #287 | 22.10 17:52 | 22.10 19:34 | 0 | 2 | ❌ | 2 год 6 хв | ті самі збої, що в №8: `main` уже червоний після #286 (зміни #287 тут ні до чого); зміна дійшла до зеленого `main` у №10 |
| 10 | [`9b07b71`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/9b07b717ad2cf0889410e708e4c7aa8f3c4f8c36) | #288 | 22.10 19:46 | 22.10 19:58 | 0 | 1 | ✅ | 11 хв | відновлення після №8 (27 хв), №9 (24 хв) |
| 11 | [`bfcc34c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/bfcc34c3c3f7287096dc51ab3f740f4849f74be3) | #289 | 22.10 19:58 | 22.10 20:04 | 0 | 1 | ✅ | 7 хв |  |
| 12 | [`0b4e4bc`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0b4e4bc64cac77f91800870bb531eb3ce7df8d97) | #290 | 22.10 20:18 | 22.10 20:28 | 0 | 2 | ✅ | 10 хв |  |
| 13 | [`a382162`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/a382162d30c425686f854834c0eae69665d00a10) | #292 | 22.10 20:27 | 22.10 20:42 | 0 | 1 | ✅ | 15 хв |  |
| 14 | [`3fdbe4a`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3fdbe4aeeea7c828f667ff9f131035bc4d9d0774) | #291 | 22.10 20:31 | 22.10 20:51 | 0 | 2 | ✅ | 20 хв |  |
| 15 | [`f077a7f`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/f077a7fbeb3d9ef9f04c0953779b875649af3f87) | #293 | 22.10 20:32 | 22.10 20:53 | 0 | 1 | ✅ | 21 хв |  |
| 16 | [`729647c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/729647c9ffe018679d93910595ad11dfbb0ae35d) | #295 | 22.10 20:56 | 22.10 21:00 | 0 | 2 | ✅ | 3 хв |  |
| 17 | [`0174e96`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0174e96a1d35ab46f90b6ff5a0e590d976a78d8f) | #296 | 22.10 20:57 | 22.10 21:05 | 0 | 1 | ✅ | 8 хв |  |
| 18 | [`20859ae`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/20859ae3efd94feb059b089e569c212ddd6d10a2) | #298 | 22.10 21:22 | 22.10 21:35 | 0 | 1 | ✅ | 13 хв |  |
| 19 | [`ae49a45`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/ae49a45fab313de98861374de5492dc5233b01ab) | #297 | 22.10 21:12 | 22.10 21:38 | 0 | 2 | ❌ | 43 хв | uml: `setup-java` (Temurin 17) — завантаження JDK 17.0.21+9 → HTTP 404 (зовнішній збій, не код); зміна дійшла до зеленого `main` у №21 |
| 20 | [`be002e4`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/be002e474f571d5314d496ea20489f01cee8e76b) | #300 | 22.10 21:37 | 22.10 21:41 | 0 | 1 | ❌ | 19 хв | uml: той самий HTTP 404 Temurin, що в №19 (PR #300 — лише посилання на відео); зміна дійшла до зеленого `main` у №21 |
| 21 | [`06f5ed4`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/06f5ed46a304a9fb8cd94eb93743c3a0a52d839d) | #301 | 22.10 21:45 | 22.10 21:56 | 0 | 1 | ✅ | 10 хв | відновлення після №19 (18 хв), №20 (14 хв) |
| 22 | [`0e729ed`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0e729ed422b09c59adc9653716cccbe615bbf18d) | #299 | 22.10 21:30 | 22.10 21:58 | 0 | 1 | ✅ | 28 хв |  |
| 23 | [`1992c0f`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/1992c0fb9408ea8cbbdcfa44ec9207cde3feabb3) | #304 | 22.10 22:15 | 22.10 22:19 | 0 | 1 | ✅ | 5 хв |  |
| 24 | [`0bc10ad`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0bc10ad5a9c27a7f28f334b12f16e9b7e4192859) | #302 | 22.10 22:07 | 22.10 22:30 | 0 | 2 | ✅ | 23 хв |  |
| 25 | [`c1c3436`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c1c3436e9dca9f414be2ee196593cee8b73cafd9) | #305 | 22.10 22:36 | 22.10 22:40 | 0 | 1 | ✅ | 4 хв |  |
| 26 | [`ba88041`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/ba88041a7bcadfa1cdd3ec97708351009c4052ab) | #307 | 22.10 23:26 | 22.10 23:28 | 0 | 2 | ✅ | 3 хв |  |
| 27 | [`fac08c0`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/fac08c0fa58afcd5de0f373f59feb74c78134423) | #306 | 22.10 22:42 | 22.10 23:31 | 1 | 2 | ✅ | 48 хв |  |
| 28 | [`0bb180e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0bb180e4f82fdb195ffab52af0337f5ad05f58f0) | #308 | 22.10 23:34 | 22.10 23:39 | 0 | 1 | ✅ | 5 хв |  |
| 29 | [`3c82102`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3c8210256a898a564176f2c1e571b9b87af1860e) | #309 | 22.10 23:42 | 22.10 23:48 | 0 | 1 | ✅ | 6 хв |  |
| 30 | [`c90fd6d`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c90fd6d3b8459d740dcac32ca057ee56536aec92) | #310 | 22.10 23:59 | 23.10 00:03 | 0 | 1 | ✅ | 4 хв |  |
| 31 | [`1074d92`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/1074d92a7d64ab55db9c51b11fe53a3e430333d2) | #311 | 23.10 13:49 | 23.10 14:22 | 0 | 1 | ✅ | 33 хв |  |
| 32 | [`9fdbee1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/9fdbee195b596b0cdeddc48c41d78a4f3778f38c) | #338 | 28.10 15:59 | 28.10 17:43 | 0 | 3 | ✅ | 1 год 43 хв |  |
| 33 | [`dbec802`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/dbec8026bae1f9ffedf0f9a0875e300b9e975884) | #339 | 28.10 23:52 | 29.10 14:02 | 0 | 1 | ✅ | 14 год 10 хв |  |
| 34 | [`cc693be`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/cc693be71c03429c5c30a1b3030fa538bea23c66) | #350 | 29.10 11:48 | 29.10 14:06 | 0 | 2 | ✅ | 2 год 18 хв |  |
| 35 | [`46d3ce2`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/46d3ce22b7bf29487484fcd58bfb48ab91674621) | #351 | 29.10 13:54 | 29.10 14:51 | 8 | 5 | ✅ | 57 хв |  |
| 36 | [`79e4e98`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/79e4e98cb7d36e81fcf229b77b8273f7bc25f45b) | #352 | 29.10 14:01 | 29.10 14:52 | 7 | 2 | ✅ | 51 хв |  |
| 37 | [`2ae4230`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/2ae4230d405727629fe6ffb367f56bcfa005f765) | #354 | 29.10 14:45 | 29.10 14:56 | 0 | 2 | ✅ | 10 хв |  |
| 38 | [`253318e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/253318e101392e3a6e6dd243de7aedf84b01c264) | #353 | 29.10 14:41 | 29.10 14:57 | 1 | 1 | ✅ | 16 хв |  |
| 39 | [`a70284d`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/a70284d554b3d835c7942a97a28c73e0b299b95b) | #356 | 29.10 15:00 | 29.10 17:03 | 0 | 2 | ✅ | 2 год 3 хв |  |
| 40 | [`2a9a341`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/2a9a3414883485906cf58dce6a7068833b4a4bb6) | #357 | 29.10 16:43 | 29.10 17:05 | 0 | 2 | ✅ | 21 хв |  |
| 41 | [`1e0df38`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/1e0df38ae3904a7c9c4b42d1e73532d261cd422a) | #341 | 29.10 09:08 | 29.10 17:30 | 0 | 2 | ✅ | 8 год 22 хв |  |
| 42 | [`20e5fb1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/20e5fb1772302b64d75753f15967c4d79687ddb6) | #360 | 29.10 17:13 | 29.10 17:32 | 0 | 2 | ✅ | 18 хв |  |
| 43 | [`689dec6`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/689dec659a5b3d2be61bfddc66ad50892fca32be) | #359 | 29.10 17:07 | 29.10 18:02 | 0 | 1 | ✅ | 55 хв |  |
| 44 | [`518fa4c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/518fa4c5df53061102ef05f4dc3b9ed5aa77da84) | #362 | 29.10 17:39 | 29.10 18:13 | 0 | 3 | ✅ | 34 хв |  |
| 45 | [`7971e3d`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/7971e3d231d50b8a9def67b84f502dad4ba58796) | #363 | 29.10 18:16 | 29.10 19:05 | 0 | 1 | ✅ | 49 хв |  |
| 46 | [`e2b2330`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/e2b2330c69c870f281a8cab44c476ab2c23b6d14) | #365 | 29.10 19:05 | 29.10 19:10 | 0 | 2 | ✅ | 5 хв |  |
| 47 | [`029513a`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/029513a92e1d1ab25c1563d28f40345ab41420b3) | #364 | 29.10 17:35 | 29.10 19:11 | 1 | 1 | ✅ | 1 год 36 хв |  |
| 48 | [`0be2c22`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0be2c22e37d10dae4262838c4d9550c396f62b7e) | #366 | 29.10 19:11 | 29.10 19:17 | 0 | 1 | ✅ | 6 хв |  |
| 49 | [`ed03147`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/ed03147827ce45d4426fa481058603a69870ab89) | #367 | 29.10 19:39 | 29.10 20:02 | 1 | 2 | ✅ | 22 хв |  |
| 50 | [`135d27b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/135d27b8565ba08a3f73f8fdbed2c05f30b1a183) | #368 | 29.10 19:57 | 29.10 20:03 | 1 | 2 | ✅ | 6 хв |  |
| 51 | [`eced203`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/eced203aff569214249b5f8b1b340cdf589f55c7) | #369 | 29.10 20:07 | 29.10 20:32 | 0 | 2 | ✅ | 25 хв |  |
| 52 | [`5f476a2`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/5f476a2f3f330c77ad90feccac6f0c6057211326) | #371 | 29.10 23:51 | 30.10 01:38 | 1 | 4 | ✅ | 1 год 46 хв |  |
| 53 | [`4f0d996`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/4f0d996f7442f260939c3b619ec65f505492109f) | #372 | 30.10 14:01 | 30.10 14:36 | 29 | 5 | ✅ | 35 хв | довга черга на раннер |
| 54 | [`f344ee5`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/f344ee5e3f12136e0d101a14b6c5c9bafd11be65) | #374 | 30.10 14:38 | 30.10 16:12 | 5 | 81 | ✅ | 1 год 34 хв | завдання всередині запуску чекали на вільний раннер |
| 55 | [`5c917e8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/5c917e8f4c7522cc2d02cb42849c774802f59255) | #373 | 30.10 14:15 | 30.10 17:09 | 118 | 16 | ✅ | 2 год 54 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 56 | [`cc0b323`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/cc0b323c48473e5d79fbe34a0b1888a18de1d614) | #370 | 29.10 23:01 | 30.10 18:28 | 5 | 8 | ✅ | 19 год 27 хв |  |
| 57 | [`e6084bc`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/e6084bc8020c283c10898ec0b3459060ab8e6c2f) | #375 | 30.10 14:44 | 30.10 18:33 | 13 | 2 | ✅ | 3 год 48 хв | довга черга на раннер |
| 58 | [`30e9a5b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/30e9a5b24678238acad03ccddacefdbdc23bab27) | #386 | 31.10 21:28 | 31.10 22:32 | 2 | 2 | ✅ | 1 год 5 хв |  |
| 59 | [`a242cc5`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/a242cc553a615df9def7e2f509c4a83356494f37) | #387 | 01.11 12:43 | 01.11 13:55 | 12 | 10 | ✅ | 1 год 12 хв | довга черга на раннер |
| 60 | [`c370adb`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c370adbfa48321d4b1e4cbe845b260bcc73ef8bc) | #388 | 01.11 13:38 | 01.11 14:12 | 0 | 2 | ✅ | 33 хв |  |
| 61 | [`36d0c03`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/36d0c0340ce162e1c68f1e1ef529252f83e78325) | #390 | 01.11 17:21 | 01.11 20:17 | 20 | 20 | ✅ | 2 год 56 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 62 | [`c1e5d7a`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c1e5d7abe1ee934601ae34b1fef5af518a5b6f82) | #378 | 30.10 18:06 | 01.11 20:29 | 29 | 11 | ✅ | 2 д 2 год 23 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 63 | [`315ea8b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/315ea8b8f7ea281c066e9e6c6e9c1b3c99ea6778) | #389 | 01.11 14:47 | 01.11 21:08 | 20 | 20 | ✅ | 6 год 22 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 64 | [`d0e600c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/d0e600c5506504afcb74dadd5223fa05059a70ad) | #391 | 01.11 19:36 | 01.11 23:10 | 97 | 63 | ❌ | 6 год 56 хв | tests: `test_booking_e2e.py::test_row0_end_to_end` — `assert '…0001' in []`: #391 змінив дати в seed, а e2e-тест із #390 шукав слот на 15.10. Перевірки PR #391 пройшли на `main` без #390; довга черга на раннер; завдання всередині запуску чекали на вільний раннер; зміна дійшла до зеленого `main` у №66 |
| 65 | [`a4776e4`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/a4776e4280ec8d1ffa228fd210939a9822dae893) | #392 | 01.11 19:45 | 02.11 01:10 | 165 | 113 | ❌ | 6 год 47 хв | той самий e2e-тест, що в №64: `main` уже червоний після #391 (PR #392 — лише README); довга черга на раннер; завдання всередині запуску чекали на вільний раннер; зміна дійшла до зеленого `main` у №66 |
| 66 | [`5741878`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/57418782915bc23818df2ac30a40e2365d1c024d) | #393 | 01.11 20:25 | 02.11 02:32 | 309 | 48 | ✅ | 6 год 7 хв | відновлення після №64 (3 год 22 хв), №65 (1 год 22 хв); довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 67 | [`9383ba1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/9383ba18312062d3bc8a81a6c5125679bc3f51e3) | #394 | 01.11 20:40 | 02.11 03:32 | 354 | 37 | ✅ | 6 год 52 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 68 | [`50b5acd`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/50b5acddf89761e850ca6a5665f85dabfaf3d2d2) | #395 | 01.11 21:15 | 02.11 04:13 | 379 | 38 | ✅ | 6 год 58 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 69 | [`4e0145b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/4e0145b813d35226d5e144170eafbff3e9e62c14) | #396 | 01.11 21:46 | 02.11 04:30 | 379 | 17 | ✅ | 6 год 44 хв | довга черга на раннер; завдання всередині запуску чекали на вільний раннер |
| 70 | [`3cbd8ae`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3cbd8ae1e37729809d75e143467b1634c1c8a453) | #422 | 05.11 03:06 | 05.11 15:49 | 0 | 2 | ✅ | 12 год 43 хв |  |
| 71 | [`c2761c0`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c2761c0b6ad71b2a6466ccb68c402bcd943ed324) | #431 | 05.11 20:28 | 05.11 20:33 | 0 | 1 | ✅ | 5 хв |  |
| 72 | [`3d4fa8e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/3d4fa8e685e42e935feb8402a64cecffac9d7a2a) | #433 | 05.11 21:15 | 05.11 22:10 | 1 | 3 | ✅ | 55 хв |  |
| 73 | [`84a192f`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/84a192f492e310c02987529363a2ea61b9534f68) | #435 | 06.11 13:35 | 06.11 13:55 | 0 | 2 | ✅ | 20 хв |  |
| 74 | [`8aab34e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/8aab34e9ca8790e1331f2f028da845b6a1482410) | #437 | 06.11 13:58 | 06.11 14:12 | 0 | 2 | ✅ | 14 хв |  |
| 75 | [`2dbc796`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/2dbc79622bbbc1f06458dbcbd23647d7f8c369ac) | #440 | 07.11 19:54 | 07.11 20:01 | 0 | 2 | ✅ | 7 хв |  |
| 76 | [`36db6b6`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/36db6b69f045f3e5821e283bfd0ea54db517bb0d) | #439 | 07.11 19:39 | 07.11 20:19 | 0 | 1 | ✅ | 40 хв |  |
| 77 | [`32f037f`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/32f037fcf65378573534488e1f535511e14c9d85) | #430 | 05.11 20:07 | 07.11 20:35 | 3 | 6 | ✅ | 2 д 0 год 29 хв |  |
| 78 | [`5aa2aa1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/5aa2aa162734b403330d62ae334a3a81932efaed) | #423 | 05.11 03:12 | 07.11 20:37 | 8 | 2 | ✅ | 2 д 17 год 25 хв |  |
| 79 | [`0e70441`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0e704411247c1a4cd67d97ad7120c82db02c38e9) | #432 | 05.11 20:38 | 07.11 20:39 | 6 | 2 | ✅ | 2 д 0 год 1 хв |  |
| 80 | [`34067a8`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/34067a80dabeeda5a277bafbc9fc7c11f1030d39) | #438 | 07.11 18:56 | 07.11 20:40 | 7 | 2 | ✅ | 1 год 43 хв |  |
| 81 | [`0972fd5`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/0972fd539b7021f5a5d8aeccfb94727927dc2383) | #441 | 09.11 13:48 | 09.11 14:01 | 0 | 2 | ✅ | 12 хв |  |
| 82 | [`7070169`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/7070169ce39ccbc3fff561cd168416d0b91b7d9a) | #442 | 09.11 14:06 | 09.11 14:16 | 0 | 2 | ✅ | 9 хв |  |
| 83 | [`302fc1d`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/302fc1dcc9788add06251b543ab39187c800aae7) | #443 | 09.11 14:20 | 09.11 15:13 | 1 | 3 | ✅ | 53 хв |  |
| 84 | [`c320dc1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/c320dc18934ee53fc729904c1bf2f887502a97ee) | #444 | 09.11 14:24 | 09.11 15:23 | 1 | 2 | ✅ | 59 хв |  |
| 85 | [`263b658`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/263b658f2392e34aa16246520ede337ed45cd7f9) | #445 | 09.11 15:02 | 09.11 15:27 | 3 | 3 | ✅ | 25 хв |  |
| 86 | [`aad09e1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/aad09e1ab6bc3f8ee9e80c65b0b3beba65dd34aa) | #446 | 09.11 15:10 | 09.11 15:28 | 5 | 2 | ✅ | 18 хв |  |
| 87 | [`07446dc`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/07446dcf5971acf736ea627954dd950d2c63c3fb) | #447 | 09.11 15:19 | 10.11 16:31 | 0 | 2 | ✅ | 1 д 1 год 12 хв |  |
| 88 | [`6c5c8b1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/6c5c8b1c2ce516952a11513b49de087299e9549f) | #466 | 10.11 16:00 | 10.11 16:32 | 1 | 2 | ✅ | 32 хв |  |
| 89 | [`9b9eaed`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/9b9eaedfb884a240226cc28fd93f5000946a9ee8) | #470 | 11.11 23:50 | 12.11 00:09 | 0 | 2 | ✅ | 19 хв |  |
| 90 | [`ab52357`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/ab52357c85bfa73f09a5ff6c58d649b6dbfaf86f) | #471 | 11.11 23:56 | 12.11 00:11 | 1 | 2 | ✅ | 16 хв |  |
| 91 | [`7f4602d`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/7f4602d861dc5d4325b502db945ce55b1a2a9dcf) | #473 | 12.11 00:11 | 12.11 01:02 | 0 | 2 | ✅ | 50 хв |  |
| 92 | [`2552934`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/2552934d2b45fb9fa305e28ed21855219efe976a) | #474 | 12.11 18:23 | 12.11 18:35 | 2 | 2 | ✅ | 12 хв |  |
| 93 | [`5667c6e`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/5667c6eac19fe55fafa97371af0c107669f928aa) | #475 | 12.11 18:49 | 12.11 19:08 | 0 | 2 | ✅ | 19 хв |  |
| 94 | [`474b1e5`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/474b1e5174454b8520cbadc7b02089f367aac633) | #476 | 12.11 19:15 | 12.11 19:28 | 0 | 4 | ✅ | 12 хв |  |
| 95 | [`9b99cf2`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/9b99cf231caa5773921ec8b53405d964270895ba) | #477 | 12.11 19:39 | 12.11 22:17 | 0 | 3 | ✅ | 2 год 38 хв |  |
| 96 | [`7feb274`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/7feb27405a374d57e2fc4b3eddad9e843313a9ea) | #478 | 12.11 22:06 | 12.11 22:22 | 0 | 4 | ✅ | 16 хв |  |
| 97 | [`aa1f42b`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/aa1f42be70c2f835b28b234ebeeba0084aa624f1) | #479 | 12.11 22:35 | 12.11 23:07 | 7 | 5 | ✅ | 32 хв |  |
| 98 | [`bd33dc9`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/bd33dc9a7ac1a6e541f23ecc80aaa3b61d7e4adf) | #480 | 12.11 22:53 | 12.11 23:17 | 0 | 5 | ✅ | 24 хв |  |
| 99 | [`59d979a`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/59d979aca6c437e76df6a55f2e919f89a64745cd) | #481 | 12.11 23:06 | 12.11 23:30 | 0 | 4 | ✅ | 25 хв |  |
| 100 | [`54a1fb1`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/54a1fb18ce57b34364af7624580e648fec191b18) | #482 | 12.11 23:34 | 12.11 23:56 | 1 | 7 | ✅ | 23 хв |  |
| 101 | [`dc06c6a`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/dc06c6ab234ccfac0c9a111a39e37ddeaf9ca549) | #483 | 12.11 23:45 | 13.11 00:03 | 3 | 7 | ✅ | 18 хв |  |
| 102 | [`dfd0442`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/dfd0442dd0f15dcc8e25fb4c74fd4e8213d437c5) | #472 | 12.11 00:00 | 13.11 00:10 | 0 | 3 | ✅ | 1 д 0 год 10 хв |  |
| 103 | [`1fa668c`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/1fa668c718271db2944bfd85bf810290aa8e080c) | #485 | 13.11 00:19 | 13.11 01:04 | 0 | 4 | ✅ | 46 хв |  |
| 104 | [`bbb25b4`](https://github.com/ukma-fin-ssdm-2026/reserve-flow/commit/bbb25b473981d866f984139bc40c84fabf558441) | #486 | 13.11 01:27 | 13.11 02:46 | 0 | 2 | ✅ | 1 год 19 хв |  |

## Підсумок за таблицею

- **Червоні запуски:** 6 з 104. Це 3 інциденти, у кожному по два червоні запуски поспіль: №8–9, №19–20, №64–65.
- **Довга черга (понад 10 хв):** 13 запусків. Усі вони припадають на 30.10 вдень (№53–57) і 01.11 (№59 — вдень, №61–69 — увечері).
- **Найдовший запуск:** №68 (PR #395, 01.11) — ≈ 7 год від створення до завершення, з них 6 год 19 хв у черзі на runner. Ще 38 хв завдання по черзі отримували runner'и, а самі вони працювали лише ≈ 6,5 хв.
- **Найповільніше завдання:** у середньому (за медіаною) завдання триває 0,5–1,4 хв, найповільніше за весь період — 5,8 хв (`uml`, встановлення Graphviz). Вся решта часу — очікування раннера.

---
*Використання ШІ: дані зібрано та таблицю згенеровано за допомогою Claude Code, перевірено командою.*
