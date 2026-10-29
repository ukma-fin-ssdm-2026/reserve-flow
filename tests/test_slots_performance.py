import concurrent.futures
import time
import pytest
from conftest import auth
import os

pytestmark = pytest.mark.req("PERF-001")

CLIENT = auth("client")


@pytest.mark.perf
@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="PT-001 - лише на PostgreSQL(SQLite in-memory не підтримує стабільну багатопотоковість)",
)
def test_search_slots_performance_pt_001(client):
    """
    PERF-001: 10 одночасних GET /api/v1/slots, кожна відповідь 200 і <= 5 с.
    Використовує ThreadPoolExecutor для симуляції одночасних запитів.

    Примітка: Вимірюється виключно час обробки застосунком (in-process через TestClient).
    Це свідоме спрощення, яке ігнорує мережеві затримки та оверхед ASGI-сервера (uvicorn),
    щоб ізолювати продуктивність бази даних.
    """
    num_requests = 10

    def fetch_slots():
        start_time = time.perf_counter()
        r = client.get("/api/v1/slots", headers=CLIENT)
        end_time = time.perf_counter()
        return r.status_code, end_time - start_time

    # Запускає 10 потоків одночасно
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(fetch_slots) for _ in range(num_requests)]
        results = [f.result() for f in futures]

    for status_code, _ in results:
        assert status_code == 200, f"Очікувався статус 200, отримано {status_code}"
    max_duration = max(duration for _, duration in results)

    # Виводимо час для звіту  в CI логах
    print(f"\nМаксимальний час відповіді серед {num_requests} запитів: {max_duration:.3f} с")
    assert max_duration <= 5.0, f"Час відповіді ({max_duration:.3f} с) перевищив ліміт у 5.0 с"


# Використання ШІ: для допрацювання тесту на основі ідей учасника команд було використано
# ШІ Gemini. Код був перевірений та затверджений командою.
