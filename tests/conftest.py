import io
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from app.config import Settings
from app.main import create_app


def _square():
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 500))
    pen.lineTo((500, 500))
    pen.lineTo((500, 0))
    pen.closePath()
    return pen.glyph()


def build_ttf() -> bytes:
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A"])
    fb.setupCharacterMap({0x41: "A"})
    fb.setupGlyf({".notdef": _square(), "A": _square()})
    fb.setupHorizontalMetrics({".notdef": (500, 0), "A": (500, 0)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()


def to_flavor(data: bytes, flavor: str) -> bytes:
    font = TTFont(io.BytesIO(data))
    font.flavor = flavor
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@pytest.fixture
def ttf_bytes() -> bytes:
    return build_ttf()


def migrate(url: str) -> None:
    """Накатывает настоящие миграции Alembic — заодно проверяем, что они рабочие."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


@pytest.fixture
def database_url(tmp_path) -> str:
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    migrate(url)
    yield url
    if url.startswith("postgresql"):
        import asyncio

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        async def _clean():
            engine = create_async_engine(url)
            async with engine.begin() as conn:
                await conn.execute(text("TRUNCATE fonts"))
            await engine.dispose()

        asyncio.run(_clean())


@pytest.fixture
def make_client(tmp_path, database_url):
    clients = []

    def _make(**overrides) -> TestClient:
        settings = Settings(
            database_url=database_url, _env_file=None, **overrides
        )
        client = TestClient(create_app(settings))
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
