from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContestBook, ContestRule


async def get_active_rules(session: AsyncSession) -> list[ContestRule]:
    result = await session.scalars(
        select(ContestRule).where(ContestRule.is_active.is_(True)).order_by(ContestRule.id.desc())
    )
    return list(result.all())


async def get_active_books(session: AsyncSession) -> list[ContestBook]:
    result = await session.scalars(
        select(ContestBook).where(ContestBook.is_active.is_(True)).order_by(ContestBook.id.desc())
    )
    return list(result.all())


async def get_all_rules(session: AsyncSession) -> list[ContestRule]:
    result = await session.scalars(select(ContestRule).order_by(ContestRule.id.desc()))
    return list(result.all())


async def get_all_books(session: AsyncSession) -> list[ContestBook]:
    result = await session.scalars(select(ContestBook).order_by(ContestBook.id.desc()))
    return list(result.all())
