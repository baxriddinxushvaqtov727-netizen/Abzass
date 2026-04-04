from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.base import Base
from app.models import entities  # noqa: F401


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
