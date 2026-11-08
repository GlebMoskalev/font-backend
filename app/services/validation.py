"""Проверка, что загруженный файл действительно шрифт."""

import io
from pathlib import Path

from fontTools.ttLib import TTFont

# Первые 4 байта файла -> формат
MAGIC_BYTES: dict[bytes, str] = {
    b"\x00\x01\x00\x00": "ttf",
    b"true": "ttf",  # Apple TrueType
    b"OTTO": "otf",
    b"wOFF": "woff",
    b"wOF2": "woff2",
}

CONTENT_TYPES: dict[str, str] = {
    "ttf": "font/ttf",
    "otf": "font/otf",
    "woff": "font/woff",
    "woff2": "font/woff2",
}

ALLOWED_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}

# Таблицы, без которых шрифт нельзя нормально использовать
REQUIRED_TABLES = ("head", "maxp", "cmap", "hhea", "hmtx")


class FontValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def detect_format(data: bytes) -> str:
    head = data[:4]
    if head == b"ttcf":
        raise FontValidationError(
            "unsupported_format", "Коллекции шрифтов (TTC) пока не поддерживаются", 415
        )
    fmt = MAGIC_BYTES.get(head)
    if fmt is None:
        raise FontValidationError(
            "unsupported_format", "Файл не является шрифтом TTF, OTF, WOFF или WOFF2", 415
        )
    return fmt


def validate_font(data: bytes, filename: str) -> str:
    """Проверяет файл и возвращает его формат. Бросает FontValidationError."""
    if not data:
        raise FontValidationError("empty_file", "Файл пустой")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FontValidationError(
            "unsupported_extension",
            f"Недопустимое расширение '{ext or '(нет)'}'. Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            415,
        )

    # Формат определяем по содержимому, расширению не доверяем
    fmt = detect_format(data)

    try:
        font = TTFont(io.BytesIO(data))
        try:
            missing = [tag for tag in REQUIRED_TABLES if tag not in font]
            if missing:
                raise FontValidationError(
                    "corrupted_font", f"В шрифте нет обязательных таблиц: {', '.join(missing)}"
                )
            # Обращение к таблицам заставляет fontTools их реально разобрать
            for tag in REQUIRED_TABLES:
                font[tag]
            if font["maxp"].numGlyphs == 0:
                raise FontValidationError("corrupted_font", "В шрифте нет глифов")
        finally:
            font.close()
    except FontValidationError:
        raise
    except Exception:
        raise FontValidationError("corrupted_font", "Файл повреждён или не читается как шрифт")

    return fmt
