"""Регресійні тести CORS (L5-17, #210).

До виправлення API мав allow_origins=["*"] разом з allow_credentials=True:
будь-який сайт міг робити запити до API з браузера користувача. Ці тести
падають на тій конфігурації і проходять після виправлення.
"""

FRONTEND = "http://localhost:5173"
EVIL = "https://evil.example"
HEALTH = "/api/v1/health"


def test_cors_rejects_unknown_origin(client):
    r = client.get(HEALTH, headers={"Origin": EVIL})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers


def test_cors_preflight_rejects_unknown_origin(client):
    r = client.options(
        "/api/v1/bookings",
        headers={"Origin": EVIL, "Access-Control-Request-Method": "POST"},
    )
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_cors_allows_frontend_origin(client):
    r = client.get(HEALTH, headers={"Origin": FRONTEND})
    assert r.headers["access-control-allow-origin"] == FRONTEND
    assert r.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_frontend_origin(client):
    r = client.options(
        "/api/v1/bookings",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == FRONTEND
