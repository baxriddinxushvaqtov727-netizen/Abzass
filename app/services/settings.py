from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BotConfig


async def get_or_create_bot_config(session: AsyncSession) -> BotConfig:
    config = await session.get(BotConfig, 1)
    if config is None:
        config = BotConfig(id=1)
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


async def get_referral_share_text(session: AsyncSession) -> str | None:
    config = await get_or_create_bot_config(session)
    if config.referral_share_text:
        return config.referral_share_text.strip() or None
    return None


async def set_referral_share_text(session: AsyncSession, text: str | None) -> BotConfig:
    config = await get_or_create_bot_config(session)
    config.referral_share_text = text.strip() if text else None
    await session.commit()
    await session.refresh(config)
    return config
