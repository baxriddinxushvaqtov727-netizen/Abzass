from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScheduledBroadcast
from app.services.users import get_all_users


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def create_scheduled_broadcast(
    session: AsyncSession,
    *,
    message_text: str,
    scheduled_at: datetime,
) -> ScheduledBroadcast:
    item = ScheduledBroadcast(message_text=message_text, scheduled_at=scheduled_at)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_all_broadcasts(session: AsyncSession) -> list[ScheduledBroadcast]:
    result = await session.scalars(select(ScheduledBroadcast).order_by(ScheduledBroadcast.id.desc()))
    return list(result.all())


async def run_broadcast_now(session: AsyncSession, bot: Bot, message_text: str) -> int:
    users = await get_all_users(session)
    delivered = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, message_text)
            delivered += 1
        except Exception:
            continue
    return delivered


async def run_due_broadcasts(session: AsyncSession, bot: Bot) -> int:
    result = await session.scalars(
        select(ScheduledBroadcast).where(
            ScheduledBroadcast.is_sent.is_(False),
            ScheduledBroadcast.scheduled_at <= now_utc(),
        )
    )
    total_sent = 0
    for broadcast in result.all():
        await run_broadcast_now(session, bot, broadcast.message_text)
        broadcast.is_sent = True
        broadcast.sent_at = now_utc()
        total_sent += 1
    if total_sent:
        await session.commit()
    return total_sent
