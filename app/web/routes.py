from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import LANGUAGES, REGIONS
from app.core.i18n import normalize_language
from app.core.security import parse_user_token
from app.db.session import get_db
from app.models import TestAnswer, TestAttempt, User
from app.services.content import get_active_books, get_active_rules
from app.services.tests import (
    get_active_tests,
    get_attempt,
    get_or_create_attempt,
    get_test_by_code,
    get_total_test_score,
    get_user_rankings,
    submit_attempt,
    user_can_take_test,
)
from app.services.users import complete_profile, get_user_by_telegram_id, set_user_language


templates = Jinja2Templates(directory="templates")
templates.env.globals["REGIONS"] = REGIONS
templates.env.globals["LANGUAGES"] = LANGUAGES
templates.env.globals["range"] = range

user_router = APIRouter()


async def current_user(token: str, session: AsyncSession) -> User:
    try:
        telegram_id = parse_user_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token yaroqsiz.") from exc
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
    return user


@user_router.get("/")
async def home() -> HTMLResponse:
    return HTMLResponse(
        "<h2>Contest Bot Platform</h2><p>Bu web qism faqat Telegram Web App uchun ishlaydi. Bot ichidan oching.</p>"
    )


@user_router.get("/app/profile")
async def profile_page(request: Request, token: str, session: AsyncSession = Depends(get_db)):
    user = await current_user(token, session)
    return templates.TemplateResponse(
        "user/profile.html",
        {
            "request": request,
            "user": user,
            "profile": user.profile,
            "token": token,
            "languages": LANGUAGES,
        },
    )


@user_router.post("/app/profile")
async def profile_submit(
    request: Request,
    token: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    patronymic: str = Form(...),
    region: str = Form(...),
    school_class: int = Form(...),
    language: str = Form("uz_latin"),
    session: AsyncSession = Depends(get_db),
):
    user = await current_user(token, session)
    if region not in REGIONS:
        raise HTTPException(status_code=400, detail="Viloyat noto'g'ri tanlangan.")
    if school_class not in range(1, 12):
        raise HTTPException(status_code=400, detail="Sinf 1 dan 11 gacha bo'lishi kerak.")
    language = normalize_language(language)
    await complete_profile(
        session,
        user,
        first_name=first_name,
        last_name=last_name,
        patronymic=patronymic,
        region=region,
        school_class=school_class,
    )
    await set_user_language(session, user, language)
    return templates.TemplateResponse(
        "user/profile_success.html",
        {
            "request": request,
            "token": token,
        },
    )


@user_router.get("/app/cabinet")
async def cabinet_page(request: Request, token: str, session: AsyncSession = Depends(get_db)):
    user = await current_user(token, session)
    stmt = (
        select(TestAttempt)
        .options(selectinload(TestAttempt.test))
        .where(TestAttempt.user_id == user.id)
        .order_by(TestAttempt.id.desc())
    )
    attempts = list((await session.scalars(stmt)).all())
    rankings = await get_user_rankings(session)
    my_rank = next((item for item in rankings if item["user_id"] == user.id), None)
    test_score = await get_total_test_score(session, user.id)
    return templates.TemplateResponse(
        "user/cabinet.html",
        {
            "request": request,
            "token": token,
            "user": user,
            "profile": user.profile,
            "attempts": attempts,
            "test_score": test_score,
            "total_score": test_score + user.referral_score,
            "my_rank": my_rank,
            "languages": LANGUAGES,
        },
    )


@user_router.post("/app/cabinet/language")
async def cabinet_language_update(
    token: str = Form(...),
    language: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    user = await current_user(token, session)
    await set_user_language(session, user, normalize_language(language))
    return RedirectResponse(url=f"/app/cabinet?token={token}", status_code=303)


@user_router.get("/app/tests")
async def tests_page(request: Request, token: str, error: str | None = None, session: AsyncSession = Depends(get_db)):
    user = await current_user(token, session)
    tests = await get_active_tests(session)
    allowed = 3
    return templates.TemplateResponse(
        "user/tests.html",
        {
            "request": request,
            "token": token,
            "tests": tests,
            "user": user,
            "can_take": user.invited_users_count >= allowed,
            "required_referrals": allowed,
            "error": error,
        },
    )


@user_router.post("/app/tests/start")
async def start_test(
    token: str = Form(...),
    test_code: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    user = await current_user(token, session)
    test = await get_test_by_code(session, test_code)
    if test is None:
        return RedirectResponse(url=f"/app/tests?token={token}&error=notfound", status_code=303)
    if not user_can_take_test(user, test):
        return RedirectResponse(url=f"/app/tests?token={token}&error=referrals", status_code=303)
    attempt = await get_or_create_attempt(session, user, test)
    if attempt.status == "completed":
        return RedirectResponse(url=f"/app/results?token={token}", status_code=303)
    return RedirectResponse(url=f"/app/tests/{attempt.id}?token={token}", status_code=303)


@user_router.get("/app/tests/{attempt_id}")
async def take_test_page(
    request: Request,
    attempt_id: int,
    token: str,
    session: AsyncSession = Depends(get_db),
):
    user = await current_user(token, session)
    attempt = await get_attempt(session, attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Test urinish topilmadi.")
    if attempt.status == "completed":
        return RedirectResponse(url=f"/app/results?token={token}", status_code=303)
    return templates.TemplateResponse(
        "user/take_test.html",
        {
            "request": request,
            "attempt": attempt,
            "token": token,
        },
    )


@user_router.post("/app/tests/{attempt_id}/submit")
async def submit_test(
    request: Request,
    attempt_id: int,
    token: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    user = await current_user(token, session)
    attempt = await get_attempt(session, attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Test topilmadi.")
    if attempt.status == "completed":
        return RedirectResponse(url=f"/app/results?token={token}", status_code=303)

    form = await request.form()
    answers: dict[int, int] = {}
    for question in attempt.test.questions:
        selected = form.get(f"question_{question.id}")
        if selected:
            answers[question.id] = int(selected)

    await submit_attempt(session, attempt, answers)
    return RedirectResponse(url=f"/app/results?token={token}", status_code=303)


@user_router.get("/app/results")
async def results_page(request: Request, token: str, session: AsyncSession = Depends(get_db)):
    user = await current_user(token, session)
    stmt = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.test),
            selectinload(TestAttempt.answers).selectinload(TestAnswer.question),
            selectinload(TestAttempt.answers).selectinload(TestAnswer.option),
        )
        .where(TestAttempt.user_id == user.id)
        .order_by(TestAttempt.id.desc())
    )
    result = await session.scalars(stmt)
    attempts = list(result.all())
    rankings = await get_user_rankings(session)
    top_50 = rankings[:50]
    my_rank = next((item for item in rankings if item["user_id"] == user.id), None)
    test_score = await get_total_test_score(session, user.id)
    return templates.TemplateResponse(
        "user/results.html",
        {
            "request": request,
            "attempts": attempts,
            "token": token,
            "top_50": top_50,
            "my_rank": my_rank,
            "test_score": test_score,
            "referral_score": user.referral_score,
            "total_score": test_score + user.referral_score,
        },
    )


@user_router.get("/app/library")
async def library_page(request: Request, token: str, session: AsyncSession = Depends(get_db)):
    await current_user(token, session)
    books = await get_active_books(session)
    rules = await get_active_rules(session)
    return templates.TemplateResponse(
        "user/library.html",
        {
            "request": request,
            "books": books,
            "rules": rules,
            "token": token,
        },
    )


def register_routes(app: FastAPI) -> None:
    app.include_router(user_router)
