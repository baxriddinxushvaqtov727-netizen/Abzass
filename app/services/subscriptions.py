from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RequiredChannel, User


async def get_active_channels(session: AsyncSession) -> list[RequiredChannel]:
    result = await session.scalars(
        select(RequiredChannel).where(RequiredChannel.is_active.is_(True)).order_by(RequiredChannel.id.desc())
    )
    return list(result.all())


async def get_missing_subscriptions(
    bot: Bot,
    session: AsyncSession,
    user: User,
) -> list[RequiredChannel]:
    channels = await get_active_channels(session)
    missing: list[RequiredChannel] = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.chat_id, user.telegram_id)
            if member.status in {"left", "kicked"}:
                missing.append(channel)
        except TelegramBadRequest:
            missing.append(channel)
    return missing
