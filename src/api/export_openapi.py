"""Скрипт для експорту OpenAPI-специфікації без запуску сервера (D-07)."""

import json
from pathlib import Path
import yaml

def export_openapi(app_instance):
    """Генерує та зберігає OpenAPI схему у файли."""
    # Шлях до папки docs/api/ в корені репозиторію
    docs_dir = Path(__file__).parent.parent.parent / "docs" / "api"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    openapi_schema = app_instance.openapi()
    
    # Збереження у JSON
    json_path = docs_dir / "openapi-generated.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
    # Збереження у YAML
    yaml_path = docs_dir / "openapi-generated.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, allow_unicode=True, sort_keys=False)
        
    print(f"OpenAPI schema успішно експортовано у {docs_dir}")

if __name__ == "__main__":
    # Якщо запускаємо скрипт вручну з терміналу
    from main import app
    export_openapi(app)