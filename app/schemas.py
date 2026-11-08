from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FontMeta(BaseModel):
    """Метаданные загруженного шрифта."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "095de6a3-5119-45bd-85c5-0b1b8088cfa8",
                "original_name": "MyFont.ttf",
                "format": "ttf",
                "content_type": "font/ttf",
                "size": 123456,
                "created_at": "2026-11-07T07:26:17Z",
            }
        }
    )

    id: UUID = Field(description="Идентификатор шрифта, используется во всех остальных запросах")
    original_name: str = Field(description="Имя файла, как его загрузил пользователь (без пути)")
    format: str = Field(description="Формат, определённый по содержимому: ttf, otf, woff, woff2")
    content_type: str = Field(description="MIME-тип, с которым отдаётся файл")
    size: int = Field(description="Размер файла в байтах")
    created_at: datetime = Field(description="Время загрузки (UTC)")


class ErrorResponse(BaseModel):
    """Единый формат ошибки."""

    code: str = Field(description="Машиночитаемый код ошибки", examples=["corrupted_font"])
    message: str = Field(description="Сообщение для пользователя", examples=["Файл повреждён или не читается как шрифт"])
