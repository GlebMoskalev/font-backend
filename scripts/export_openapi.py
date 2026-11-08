"""Выгружает OpenAPI-схему в docs/openapi.json (для фронта и генерации клиентов).

Запуск: python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.main import create_app

out = Path("docs/openapi.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"written {out}")
