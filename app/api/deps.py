from fastapi import Request

from app.config import Settings
from app.services.fonts import FontService


def get_service(request: Request) -> FontService:
    return request.app.state.font_service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
