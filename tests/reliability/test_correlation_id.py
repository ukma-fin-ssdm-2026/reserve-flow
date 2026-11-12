"""Лаб 9, №11 (#468): заголовок X-Correlation-ID від клієнта перевіряється.

Безпечна відмова (fail safe): невалідний ID не зупиняє запит — його замінює новий UUID,
а в лог іде попередження без «сирого» значення.
"""

import logging
import uuid

import pytest

import main

pytestmark = pytest.mark.no_req("інфраструктура: трасування запитів (Лаб 9, №11)")

HEADER = "X-Correlation-ID"
HEALTH = "/api/v1/health"


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def test_missing_header_gets_generated_uuid(client):
    response = client.get(HEALTH)

    assert _is_uuid(response.headers[HEADER])


def test_valid_uuid_passes_through(client):
    sent = str(uuid.uuid4())

    response = client.get(HEALTH, headers={HEADER: sent})

    assert response.headers[HEADER] == sent


@pytest.mark.parametrize(
    ("value", "kept"),
    [("a" * 64, True), ("a" * 65, False), ("req-42", True), ("", False)],
    ids=["64-chars", "65-chars", "short-custom", "empty"],
)
def test_length_boundaries(client, value, kept):
    response = client.get(HEALTH, headers={HEADER: value})

    returned = response.headers[HEADER]
    if kept:
        assert returned == value
    else:
        assert returned != value and _is_uuid(returned)


@pytest.mark.parametrize(
    "value",
    ["has space", "id;drop", "<script>", "a/b", "ід-кирилиця"],
    ids=["space", "semicolon", "html", "slash", "non-ascii"],
)
def test_unsafe_characters_are_replaced(value):
    returned = main.safe_correlation_id(value)

    assert returned != value and _is_uuid(returned)


@pytest.mark.parametrize("value", ["abc\r\nFAKE LOG LINE", "abc\nx", "abc\x00"])
def test_log_injection_is_replaced(value):
    returned = main.safe_correlation_id(value)

    assert "\n" not in returned and "\r" not in returned and _is_uuid(returned)


def test_replacement_is_logged_without_raw_value(client, caplog):
    sent = "x" * 200

    with caplog.at_level(logging.WARNING):
        client.get(HEALTH, headers={HEADER: sent})

    assert any("X-Correlation-ID" in record.getMessage() for record in caplog.records)
    assert all(sent not in record.getMessage() for record in caplog.records)


def test_error_body_uses_safe_id(client):
    response = client.get("/api/v1/no-such-route", headers={HEADER: "bad id with spaces"})

    body_id = response.json()["error"]["correlation_id"]
    assert response.status_code == 404
    assert _is_uuid(body_id)
    assert body_id == response.headers[HEADER]
