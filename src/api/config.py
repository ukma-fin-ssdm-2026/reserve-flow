"""Спільні налаштування API (рішення D-01)."""

import os

API_TITLE = "Reserve Flow API"
API_DESCRIPTION = (
    "REST API системи онлайн-бронювання приміщень НаУКМА.\n\n"
    "Лабораторна 4: усі кінцеві точки повертають дані-заглушки. "
    "Специфікація OpenAPI генерується автоматично з коду."
)

# Версія документа OpenAPI: змінюється з кожним релізом.
API_VERSION = "1.0.0"

# Версія у шляху: змінюється лише при несумісних змінах (див. api-design.md).
API_PREFIX = "/api/v1"

# CORS (L5-17, #210): лише перелічені origin можуть звертатися до API з браузера.
# Список задається змінною середовища через кому; за замовчуванням — локальний
# фронтенд (Vite) і Swagger UI. Символ "*" разом із credentials заборонено.
_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:3000"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip() and origin.strip() != "*"
]
if _render_url := os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/"):
    if _render_url not in CORS_ORIGINS:
        CORS_ORIGINS.append(_render_url)


# Використання ШІ: При написанні коду було використано допомогу ШІ Claude та Gemini.
# Код вичитано, відредаговано та затверджено учасниками команди
