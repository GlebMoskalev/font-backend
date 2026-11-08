import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import fonts, health
from app.config import Settings
from app.db import make_engine, make_sessionmaker
from app.services.fonts import FontService
from app.services.validation import FontValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("font-backend")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    service = FontService(make_sessionmaker(engine), settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="Font backend",
        version="0.1.0",
        description=(
            "Бэкенд сервиса создания шрифтов: загрузка, проверка и хранение файлов шрифтов.\n\n"
            "Все ошибки возвращаются в формате `{\"code\": \"...\", \"message\": \"...\"}`."
        ),
        openapi_tags=[
            {"name": "fonts", "description": "Загрузка и хранение шрифтов"},
            {"name": "health", "description": "Служебное"},
        ],
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.font_service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(FontValidationError)
    async def _validation_error(_: Request, exc: FontValidationError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        # Единый формат ошибок: {"code": ..., "message": ...}
        content = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    app.include_router(health.router)
    app.include_router(fonts.router)
    return app


app = create_app()
