import concurrent.futures
import time
import pytest
from conftest import auth

CLIENT = auth("client")


@pytest.mark.perf
def test_search_slots_performance_pt_001(client):
    """
    PERF-001: 10 одночасних GET /api/v1/slots, кожна відповідь 200 і <= 5 с.
    Використовує ThreadPoolExecutor для симуляції одночасних запитів.
    """
    num_requests = 10

    def fetch_slots():
        start_time = time.time()
        r = client.get("/api/v1/slots", headers=CLIENT)
        end_time = time.time()
        return r.status_code, end_time - start_time

    # Запускає 10 потоків одночасно
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(fetch_slots) for _ in range(num_requests)]
        results = [f.result() for f in futures]

    max_duration = 0.0
    for status_code, duration in results:
        assert status_code == 200, f"Очікувався статус 200, отримано {status_code}"
        if duration > max_duration:
            max_duration = duration

    # Виводимо час для звіту  в CI логах
    print(f"\nМаксимальний час відповіді серед {num_requests} запитів: {max_duration:.3f} с")
    assert max_duration <= 5.0, f"Час відповіді ({max_duration:.3f} с) перевищив ліміт у 5.0 с"


# Використання ШІ: для допрацювання тесту на основі ідей учасника команд було використано
# ШІ Gemini. Код був перевірений та затверджений командою.
