from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI

from app.bot.launcher import create_bot, create_dispatcher
from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import engine
from app.services.runtime_tasks import scheduler_loop
from app.web.routes import register_routes

logger = logging.getLogger(__name__)


settings = get_settings()
polling_task: asyncio.Task | None = None
scheduler_task: asyncio.Task | None = None
polling_bot = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global polling_task, polling_bot, scheduler_task

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    await init_db(engine)
    scheduler_task = asyncio.create_task(scheduler_loop())

    if settings.run_bot:
        try:
            print("🤖 [BOT] Starting bot with polling...")
            bot = create_bot()
            polling_bot = bot
            dispatcher = create_dispatcher()
            polling_task = asyncio.create_task(dispatcher.start_polling(bot))
            print("✅ [BOT] Bot polling started successfully")
            logger.info("✅ Bot polling started successfully")
        except Exception as e:
            print(f"❌ [BOT ERROR] Bot polling failed: {e}")
            logger.error(f"❌ Bot polling failed: {e}", exc_info=True)
    
    try:
        yield
    finally:
        if polling_task:
            polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await polling_task
        if scheduler_task:
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task
        if polling_bot is not None:
            await polling_bot.session.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_routes(app)
