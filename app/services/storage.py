from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aiogram import Bot
from fastapi import UploadFile

from app.core.config import get_settings


async def save_upload(upload: UploadFile | None, subdir: str) -> str | None:
    if not upload or not upload.filename:
        return None

    settings = get_settings()
    upload_root = Path(settings.upload_dir) / subdir
    upload_root.mkdir(parents=True, exist_ok=True)

    extension = Path(upload.filename).suffix
    file_path = upload_root / f"{uuid4().hex}{extension}"
    content = await upload.read()
    file_path.write_bytes(content)
    return str(file_path)


async def save_bot_file(bot: Bot, file_id: str, subdir: str, preferred_extension: str | None = None) -> str:
    settings = get_settings()
    upload_root = Path(settings.upload_dir) / subdir
    upload_root.mkdir(parents=True, exist_ok=True)

    telegram_file = await bot.get_file(file_id)
    extension = preferred_extension or Path(telegram_file.file_path or "").suffix or ""
    file_path = upload_root / f"{uuid4().hex}{extension}"
    await bot.download(file_id, destination=file_path)
    return str(file_path)
