import pytest
from unittest.mock import patch

from conftest import auth

pytestmark = pytest.mark.req("FR-010", "FR-007", "FR-002")

# Матриця переходів станів
# Збігається з таблицею переходів станів у test-plan.md (Бонус 2)
TRANSITIONS = [
    ("TR-01", "Pending", "Confirmed", "provider", 200),
    ("TR-02", "Pending", "Confirmed", "client", 403),
    ("TR-03", "Pending", "Rejected", "provider", 200),
    ("TR-04", "Pending", "Rejected", "client", 403),
    ("TR-05", "Pending", "Cancelled", "client", 200),
    ("TR-06", "Pending", "Cancelled", "provider", 403),
    ("TR-07", "Confirmed", "Cancelled", "client", 200),
    ("TR-08", "Confirmed", "Cancelled", "provider", 403),
    ("TR-09", "Confirmed", "Confirmed", "provider", 409),
    ("TR-10", "Confirmed", "Rejected", "provider", 409),
    ("TR-11", "Rejected", "Cancelled", "client", 409),
    ("TR-12", "Cancelled", "Confirmed", "provider", 409),
    ("TR-13", "Pending", "Pending", "client", 409),
]


@pytest.mark.parametrize("test_id, initial_status, target_status, role, expected_code", TRANSITIONS)
@patch("routes.bookings._can_view", return_value=True)
@patch("routes.bookings._get_booking_or_404")
def test_booking_status_transition_matrix(
    mock_get_booking,
    mock_can_view,
    client,
    test_id,
    initial_status,
    target_status,
    role,
    expected_code,
):
    """
    Перевіряє техніку тест-дизайну 'Таблиця переходів станів' (State Transition Testing).
    Кожен ID відповідає рядку з таблиці в test-plan.md.
    """
    mock_get_booking.return_value = {
        "id": "c3000000-0000-4000-8000-111111111111",
        "client_id": "c1000000-0000-4000-8000-000000000001",
        "slot_id": "00000000-0000-0000-0000-000000000000",  # Валідний UUID, якого немає в БД
        "status": initial_status,
        "purpose": "State Transition Test",
        "rejection_reason": None,
        "created_at": "2026-01-01T00:00:00Z",
    }

    payload = {"status": target_status}
    if target_status == "Rejected":
        payload["reason"] = "Причина відмови"

    headers = auth(role)

    r = client.patch(
        "/api/v1/bookings/c3000000-0000-4000-8000-111111111111", headers=headers, json=payload
    )

    assert r.status_code == expected_code, (
        f"[{test_id}] Очікувався {expected_code} для переходу "
        f"{initial_status} -> {target_status} ({role}), отримано {r.status_code}"
    )
