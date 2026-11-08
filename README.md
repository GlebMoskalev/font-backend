# Backend: Сервис создания шрифтов на базе ИИ

Загрузка шрифтов, проверка и хранение. FastAPI + fontTools.

## Запуск

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d db      # PostgreSQL
alembic upgrade head         # миграции
uvicorn app.main:app --reload
```

Или всё в Docker: `docker compose up --build`.

Всё хранится в PostgreSQL, в таблице `fonts` (метаданные и содержимое файла).
Новая миграция после изменения `app/models.py`: `alembic revision --autogenerate -m "..."`.

## Документация API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Схема: http://localhost:8000/openapi.json, копия в репозитории: [`docs/openapi.json`](docs/openapi.json)

Описание эндпоинтов живёт в коде (`app/api/`, `app/schemas.py`). После изменения API обнови копию схемы:

```bash
python -m scripts.export_openapi
```

## Тесты

```bash
pytest -q                                   # на SQLite
TEST_DATABASE_URL=postgresql+asyncpg://font:font@localhost:5432/font pytest -q   # на Postgres
```
