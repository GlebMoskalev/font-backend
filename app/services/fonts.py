import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.models import Font
from app.repositories.fonts import FontRepository
from app.schemas import FontMeta
from app.services.validation import CONTENT_TYPES, validate_font

logger = logging.getLogger(__name__)


class FontNotFound(Exception):
    pass


def _clean_filename(name: str | None) -> str:
    # Оставляем только имя без пути; хранится лишь для отдачи при скачивании
    name = Path(name or "font").name.strip() or "font"
    return name[:255]


def _utc(dt: datetime) -> datetime:
    # SQLite (в тестах) возвращает naive datetime
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _to_meta(font: Font) -> FontMeta:
    return FontMeta(
        id=font.id,
        original_name=font.original_name,
        format=font.format,
        content_type=font.content_type,
        size=font.size,
        created_at=_utc(font.created_at),
    )


class FontService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], settings: Settings):
        self.sessions = sessions
        self.settings = settings

    async def upload(self, filename: str | None, data: bytes) -> FontMeta:
        name = _clean_filename(filename)
        # Разбор шрифта нагружает CPU — не блокируем event loop
        fmt = await asyncio.to_thread(validate_font, data, name)

        now = datetime.now(timezone.utc)
        font = Font(
            id=uuid.uuid4(),
            original_name=name,
            format=fmt,
            content_type=CONTENT_TYPES[fmt],
            size=len(data),
            created_at=now,
            data=data,
        )
        # Метаданные и файл пишутся в одной транзакции
        async with self.sessions.begin() as session:
            await FontRepository(session).add(font)

        logger.info("font uploaded id=%s format=%s size=%d", font.id, fmt, font.size)
        return _to_meta(font)

    async def _get_existing(self, repo: FontRepository, font_id: UUID) -> Font:
        font = await repo.get(font_id)
        if font is None:
            raise FontNotFound
        return font

    async def get(self, font_id: UUID) -> FontMeta:
        async with self.sessions() as session:
            return _to_meta(await self._get_existing(FontRepository(session), font_id))

    async def get_file(self, font_id: UUID) -> tuple[FontMeta, bytes]:
        async with self.sessions() as session:
            repo = FontRepository(session)
            font = await self._get_existing(repo, font_id)
            data = await repo.get_data(font_id)
        if data is None:
            raise FontNotFound
        return _to_meta(font), data

    async def delete(self, font_id: UUID) -> None:
        async with self.sessions.begin() as session:
            if not await FontRepository(session).delete(font_id):
                raise FontNotFound
