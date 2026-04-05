from __future__ import annotations

import secrets

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import REFERRAL_REWARD
from app.models import User, UserProfile


def build_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10]


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    stmt: Select[tuple[User]] = (
        select(User)
        .options(selectinload(User.profile), selectinload(User.referrer))
        .where(User.telegram_id == telegram_id)
    )
    return await session.scalar(stmt)


async def get_user_by_referral_code(session: AsyncSession, referral_code: str) -> User | None:
    stmt = select(User).where(User.referral_code == referral_code)
    return await session.scalar(stmt)


async def get_all_users(session: AsyncSession) -> list[User]:
    stmt = select(User).order_by(User.id)
    result = await session.scalars(stmt)
    return list(result.all())


async def upsert_telegram_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    referral_code: str | None = None,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            telegram_first_name=first_name,
            telegram_last_name=last_name,
            referral_code=build_referral_code(),
            language="uz_latin",
        )
        if referral_code:
            referrer = await get_user_by_referral_code(session, referral_code)
            if referrer and referrer.telegram_id != telegram_id:
                user.referrer = referrer
        session.add(user)
    else:
        user.username = username
        user.telegram_first_name = first_name
        user.telegram_last_name = last_name
        if referral_code and not user.referrer_id:
            referrer = await get_user_by_referral_code(session, referral_code)
            if referrer and referrer.telegram_id != telegram_id:
                user.referrer = referrer

    await session.commit()
    await session.refresh(user)
    return user


async def set_phone_number(session: AsyncSession, user: User, phone_number: str) -> User:
    user.phone_number = phone_number
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_language(session: AsyncSession, user: User, language: str) -> User:
    user.language = language
    await session.commit()
    await session.refresh(user)
    return user


async def complete_profile(
    session: AsyncSession,
    user: User,
    *,
    first_name: str,
    last_name: str,
    patronymic: str,
    region: str,
    district: str,
) -> User:
    if user.profile is None:
        profile = UserProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            region=region,
            district=district,
        )
        session.add(profile)
        user.profile = profile
    else:
        user.profile.first_name = first_name
        user.profile.last_name = last_name
        user.profile.patronymic = patronymic
        user.profile.region = region
        user.profile.district = district

    previously_completed = user.is_profile_completed
    user.is_profile_completed = True

    if user.referrer and user.referrer_id and not user.referral_reward_granted:
        if not previously_completed:
            user.referrer.referral_score += REFERRAL_REWARD
            user.referrer.invited_users_count += 1
            user.referral_reward_granted = True

    await session.commit()
    await session.refresh(user)
    return user
