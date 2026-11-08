from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Font(Base):
    """Загруженный шрифт: метаданные и содержимое файла."""

    __tablename__ = "fonts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(8))
    content_type: Mapped[str] = mapped_column(String(32))
    size: Mapped[int] = mapped_column(BigInteger)
    # Результат анализа шрифта (автор, символы, начертание...) — заполнит модуль анализа
    analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # deferred: байты не грузятся при обычных запросах, только при явном обращении
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
