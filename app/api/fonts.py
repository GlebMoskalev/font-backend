from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from app.api.deps import get_service, get_settings
from app.config import Settings
from app.schemas import ErrorResponse, FontMeta
from app.services.fonts import FontNotFound, FontService

router = APIRouter(prefix="/api/fonts", tags=["fonts"])

CHUNK_SIZE = 1024 * 1024
# Запас на заголовки multipart поверх размера самого файла
MULTIPART_OVERHEAD = 64 * 1024

NOT_FOUND = {"code": "not_found", "message": "Шрифт не найден"}


def _content_disposition(filename: str) -> str:
    quoted = quote(filename)
    if quoted == filename:
        return f'attachment; filename="{filename}"'
    # Не-ASCII имена (кириллица и т.п.) по RFC 6266
    return f"attachment; filename*=utf-8''{quoted}"


def _too_large(limit: int) -> HTTPException:
    return HTTPException(
        413,
        {"code": "file_too_large", "message": f"Файл больше {limit // (1024 * 1024)} МБ"},
    )


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while chunk := await file.read(CHUNK_SIZE):
        buf.extend(chunk)
        if len(buf) > limit:
            raise _too_large(limit)
    return bytes(buf)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=FontMeta,
    summary="Загрузить шрифт",
    description=(
        "Принимает файл шрифта (multipart/form-data, поле `file`), проверяет его и кладёт во "
        "хранилище. Возвращает метаданные с `id`.\n\n"
        "Проверки по порядку:\n"
        "1. Размер не больше лимита (по умолчанию 20 МБ).\n"
        "2. Расширение: `.ttf`, `.otf`, `.woff`, `.woff2`.\n"
        "3. Формат по первым 4 байтам, а не по расширению.\n"
        "4. Полный разбор через fontTools: таблицы `head, maxp, cmap, hhea, hmtx` и наличие глифов."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "`empty_file` или `corrupted_font`"},
        413: {"model": ErrorResponse, "description": "`file_too_large`"},
        415: {"model": ErrorResponse, "description": "`unsupported_extension` или `unsupported_format` (в т.ч. TTC)"},
    },
)
async def upload_font(
    request: Request,
    file: UploadFile = File(..., description="Файл шрифта: TTF, OTF, WOFF или WOFF2"),
    service: FontService = Depends(get_service),
    settings: Settings = Depends(get_settings),
) -> FontMeta:
    limit = settings.max_upload_bytes
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > limit + MULTIPART_OVERHEAD:
        raise _too_large(limit)

    data = await _read_limited(file, limit)
    return await service.upload(file.filename, data)


@router.get(
    "/{font_id}",
    response_model=FontMeta,
    summary="Метаданные шрифта",
    responses={404: {"model": ErrorResponse, "description": "`not_found`: нет шрифта с таким id"}},
)
async def get_font(font_id: UUID, service: FontService = Depends(get_service)) -> FontMeta:
    try:
        return await service.get(font_id)
    except FontNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)


@router.get(
    "/{font_id}/file",
    response_class=Response,
    summary="Скачать файл шрифта",
    description="Отдаёт исходный файл с правильным `Content-Type`. Нужен для превью, редактора и анализа.",
    responses={
        200: {"content": {"font/ttf": {}, "font/otf": {}, "font/woff": {}, "font/woff2": {}}},
        404: {"model": ErrorResponse, "description": "`not_found`"},
    },
)
async def download_font(font_id: UUID, service: FontService = Depends(get_service)) -> Response:
    try:
        meta, data = await service.get_file(font_id)
    except FontNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return Response(
        content=data,
        media_type=meta.content_type,
        headers={"Content-Disposition": _content_disposition(meta.original_name)},
    )


@router.delete(
    "/{font_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить шрифт",
    description="Удаляет шрифт вместе с файлом.",
    responses={404: {"model": ErrorResponse, "description": "`not_found`"}},
)
async def delete_font(font_id: UUID, service: FontService = Depends(get_service)) -> Response:
    try:
        await service.delete(font_id)
    except FontNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
