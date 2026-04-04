from __future__ import annotations

import asyncio
from contextlib import suppress

from app.bot.launcher import create_bot
from app.db.session import AsyncSessionLocal
from app.services.broadcasts import run_due_broadcasts
from app.services.tests import close_due_tests


async def scheduler_loop(poll_interval: int = 20) -> None:
    bot = create_bot()
    try:
        while True:
            async with AsyncSessionLocal() as session:
                await run_due_broadcasts(session, bot)
                await close_due_tests(session, bot)
            await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        raise
    finally:
        with suppress(Exception):
            await bot.session.close()
