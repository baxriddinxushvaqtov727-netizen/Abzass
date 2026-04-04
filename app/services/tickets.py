from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import SupportTicket, TicketStatus, User


async def create_ticket(
    session: AsyncSession,
    user_id: int,
    text: str | None,
    media_file_id: str | None,
    media_type: str | None,
) -> SupportTicket:
    ticket = SupportTicket(
        user_id=user_id,
        text=text,
        media_file_id=media_file_id,
        media_type=media_type,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def get_ticket(session: AsyncSession, ticket_id: int) -> SupportTicket | None:
    stmt = (
        select(SupportTicket)
        .options(selectinload(SupportTicket.user).selectinload(User.profile))
        .where(SupportTicket.id == ticket_id)
    )
    return await session.scalar(stmt)


async def answer_ticket(session: AsyncSession, ticket_id: int, reply_text: str) -> SupportTicket | None:
    ticket = await get_ticket(session, ticket_id)
    if ticket is None:
        return None
    ticket.status = TicketStatus.ANSWERED.value
    ticket.admin_reply = reply_text
    ticket.answered_at = datetime.now(timezone.utc)
    await session.commit()
    return ticket


async def reject_ticket(session: AsyncSession, ticket_id: int, reason: str) -> SupportTicket | None:
    ticket = await get_ticket(session, ticket_id)
    if ticket is None:
        return None
    ticket.status = TicketStatus.REJECTED.value
    ticket.admin_reply = reason
    ticket.answered_at = datetime.now(timezone.utc)
    await session.commit()
    return ticket
