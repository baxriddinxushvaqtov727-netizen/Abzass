from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/")
async def home() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "telegram-bot"})


@router.get("/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"ok": True})


def register_routes(app: FastAPI) -> None:
    app.include_router(router)
