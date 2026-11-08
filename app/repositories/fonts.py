from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Font


class FontRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, font: Font) -> None:
        self.session.add(font)
        await self.session.flush()

    async def get(self, font_id: UUID) -> Font | None:
        return await self.session.get(Font, font_id)

    async def get_data(self, font_id: UUID) -> bytes | None:
        return await self.session.scalar(select(Font.data).where(Font.id == font_id))

    async def delete(self, font_id: UUID) -> bool:
        result = await self.session.execute(delete(Font).where(Font.id == font_id))
        return result.rowcount > 0
