from __future__ import annotations

import re
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.constants import MIN_REFERRALS_FOR_TEST
from app.models import AttemptStatus, Question, QuestionOption, Test, TestAnswer, TestAttempt, User, UserProfile


ANSWER_PATTERN = re.compile(r"[A-Da-d]")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_answer_key(raw_value: str) -> list[str]:
    answers = [item.upper() for item in ANSWER_PATTERN.findall(raw_value or "")]
    if not answers:
        raise ValueError("Javob kaliti bo'sh. Faqat A, B, C, D harflaridan foydalaning.")
    return answers


def parse_submission_text(raw_value: str) -> tuple[str, list[str]]:
    if "*" not in raw_value:
        raise ValueError("Format: 1234*ABCDA yoki 1234*1a2b3c")
    test_code, answer_part = raw_value.split("*", 1)
    normalized_code = test_code.strip().upper()
    if not normalized_code:
        raise ValueError("Test ID kiritilmagan.")
    return normalized_code, normalize_answer_key(answer_part)


def is_test_open(test: Test) -> bool:
    if not test.is_active:
        return False
    if test.closed_at is not None:
        return False
    if test.scheduled_end_at and test.scheduled_end_at <= now_utc():
        return False
    return True


async def get_active_tests(session: AsyncSession) -> list[Test]:
    stmt = (
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.options))
        .order_by(Test.id.desc())
    )
    result = await session.scalars(stmt)
    return [test for test in result.all() if is_test_open(test)]


async def get_all_tests(session: AsyncSession) -> list[Test]:
    result = await session.scalars(select(Test).order_by(Test.id.desc()))
    return list(result.all())


async def get_test_by_code(session: AsyncSession, code: str) -> Test | None:
    stmt = (
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.options))
        .where(Test.test_code == code.strip().upper())
    )
    test = await session.scalar(stmt)
    if test is None or not is_test_open(test):
        return None
    return test


async def get_test_by_id(session: AsyncSession, test_id: int) -> Test | None:
    stmt = (
        select(Test)
        .options(
            selectinload(Test.questions).selectinload(Question.options),
            selectinload(Test.attempts).selectinload(TestAttempt.user).selectinload(User.profile),
        )
        .where(Test.id == test_id)
    )
    return await session.scalar(stmt)


def user_can_take_test(user: User, test: Test | None = None) -> bool:
    required = test.min_referrals if test else MIN_REFERRALS_FOR_TEST
    return user.invited_users_count >= required


async def get_or_create_attempt(session: AsyncSession, user: User, test: Test) -> TestAttempt:
    stmt: Select[tuple[TestAttempt]] = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.answers),
            joinedload(TestAttempt.test).selectinload(Test.questions).selectinload(Question.options),
        )
        .where(TestAttempt.user_id == user.id, TestAttempt.test_id == test.id)
    )
    attempt = await session.scalar(stmt)
    if attempt is None:
        attempt = TestAttempt(
            user_id=user.id,
            test_id=test.id,
            total_questions=len(test.questions),
            status=AttemptStatus.STARTED.value,
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
    return attempt


async def get_attempt(session: AsyncSession, attempt_id: int, user_id: int | None = None) -> TestAttempt | None:
    stmt = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.answers).selectinload(TestAnswer.question),
            selectinload(TestAttempt.answers).selectinload(TestAnswer.option),
            joinedload(TestAttempt.user).selectinload(User.profile),
            joinedload(TestAttempt.test).selectinload(Test.questions).selectinload(Question.options),
        )
        .where(TestAttempt.id == attempt_id)
    )
    if user_id is not None:
        stmt = stmt.where(TestAttempt.user_id == user_id)
    return await session.scalar(stmt)


async def submit_attempt(session: AsyncSession, attempt: TestAttempt, answers: dict[int, int]) -> TestAttempt:
    await session.execute(delete(TestAnswer).where(TestAnswer.attempt_id == attempt.id))
    score = 0
    question_map = {question.id: question for question in attempt.test.questions}

    for question_id, option_id in answers.items():
        question = question_map.get(question_id)
        if question is None:
            continue
        selected = next((item for item in question.options if item.id == option_id), None)
        if selected is None:
            continue
        is_correct = selected.is_correct
        if is_correct:
            score += 1
        session.add(
            TestAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                option_id=option_id,
                is_correct=is_correct,
            )
        )

    attempt.score = score
    attempt.total_questions = len(attempt.test.questions)
    attempt.status = AttemptStatus.COMPLETED.value
    attempt.completed_at = now_utc()
    await session.commit()
    return await get_attempt(session, attempt.id)  # type: ignore[return-value]


async def submit_attempt_by_letters(session: AsyncSession, attempt: TestAttempt, answers: list[str]) -> TestAttempt:
    if len(answers) != len(attempt.test.questions):
        raise ValueError(f"Javoblar soni {len(attempt.test.questions)} ta bo'lishi kerak.")

    option_map: dict[int, int] = {}
    for question, letter in zip(attempt.test.questions, answers, strict=False):
        selected = next((option for option in question.options if option.text.upper() == letter), None)
        if selected is None:
            raise ValueError(f"{question.order_index + 1}-savol uchun javob topilmadi.")
        option_map[question.id] = selected.id
    return await submit_attempt(session, attempt, option_map)


async def create_test(
    session: AsyncSession,
    *,
    title: str,
    test_code: str,
    answer_key: str,
    min_referrals: int,
    created_by_telegram_id: int | None = None,
    description: str | None = None,
    scheduled_end_at: datetime | None = None,
) -> Test:
    normalized_answers = normalize_answer_key(answer_key)
    normalized_key = "".join(normalized_answers)

    test = Test(
        title=title.strip(),
        test_code=test_code.strip().upper(),
        answer_key=normalized_key,
        description=(description or "").strip() or None,
        min_referrals=min_referrals,
        created_by_telegram_id=created_by_telegram_id,
        scheduled_end_at=scheduled_end_at,
        is_active=True,
    )
    session.add(test)
    await session.flush()

    for idx, correct_answer in enumerate(normalized_answers):
        question = Question(
            test_id=test.id,
            text=f"Savol {idx + 1}",
            order_index=idx,
        )
        session.add(question)
        await session.flush()
        for letter in ["A", "B", "C", "D"]:
            session.add(
                QuestionOption(
                    question_id=question.id,
                    text=letter,
                    is_correct=letter == correct_answer,
                )
            )

    await session.commit()
    return test


def build_attempt_review(attempt: TestAttempt) -> str:
    user_name = (
        f"{attempt.user.profile.first_name} {attempt.user.profile.last_name}"
        if attempt.user and attempt.user.profile
        else str(attempt.user.telegram_id)
    )
    lines = [
        f"Ishtirokchi: {user_name}",
        f"Test: {attempt.test.title}",
        f"Test ID: {attempt.test.test_code}",
        f"Natija: {attempt.score}/{attempt.total_questions}",
        "",
    ]
    answer_map = {answer.question_id: answer for answer in attempt.answers}
    for index, question in enumerate(attempt.test.questions, start=1):
        answer = answer_map.get(question.id)
        chosen = answer.option.text if answer else "Javob belgilanmagan"
        correct = next((option.text for option in question.options if option.is_correct), "Noma'lum")
        status = "To'g'ri" if answer and answer.is_correct else "Noto'g'ri"
        lines.extend(
            [
                f"{index}-savol",
                f"Siz belgilagan javob: {chosen}",
                f"To'g'ri javob: {correct}",
                f"Holat: {status}",
                "",
            ]
        )
    return "\n".join(lines).strip()


async def close_test_and_notify(session: AsyncSession, bot: Bot, test_id: int) -> Test | None:
    test = await get_test_by_id(session, test_id)
    if test is None:
        return None
    if test.closed_at is None:
        test.is_active = False
        test.closed_at = now_utc()
        await session.commit()

    refreshed = await get_test_by_id(session, test_id)
    if refreshed is None:
        return None

    for attempt in refreshed.attempts:
        detailed_attempt = await get_attempt(session, attempt.id)
        if detailed_attempt and detailed_attempt.status == AttemptStatus.COMPLETED.value:
            review = build_attempt_review(detailed_attempt)
            try:
                await bot.send_message(detailed_attempt.user.telegram_id, review)
            except Exception:
                continue
    return refreshed


async def close_due_tests(session: AsyncSession, bot: Bot) -> int:
    stmt = select(Test).where(Test.is_active.is_(True), Test.scheduled_end_at.is_not(None))
    result = await session.scalars(stmt)
    closed = 0
    for test in result.all():
        if test.scheduled_end_at and test.scheduled_end_at <= now_utc():
            await close_test_and_notify(session, bot, test.id)
            closed += 1
    return closed


async def get_total_test_score(session: AsyncSession, user_id: int) -> int:
    score = await session.scalar(
        select(func.coalesce(func.sum(TestAttempt.score), 0)).where(
            TestAttempt.user_id == user_id, TestAttempt.status == AttemptStatus.COMPLETED.value
        )
    )
    return int(score or 0)


async def get_user_rankings(session: AsyncSession) -> list[dict]:
    stmt = (
        select(
            User.id,
            User.telegram_id,
            User.referral_score,
            User.invited_users_count,
            UserProfile.first_name,
            UserProfile.last_name,
            func.coalesce(func.sum(TestAttempt.score), 0).label("test_score"),
        )
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(
            TestAttempt,
            (TestAttempt.user_id == User.id) & (TestAttempt.status == AttemptStatus.COMPLETED.value),
        )
        .group_by(User.id, UserProfile.first_name, UserProfile.last_name)
        .order_by((func.coalesce(func.sum(TestAttempt.score), 0) + User.referral_score).desc(), User.id.asc())
    )
    result = await session.execute(stmt)
    rankings: list[dict] = []
    for row in result.all():
        total_score = int(row.test_score or 0) + int(row.referral_score or 0)
        rankings.append(
            {
                "user_id": row.id,
                "telegram_id": row.telegram_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "test_score": int(row.test_score or 0),
                "referral_score": int(row.referral_score or 0),
                "invited_users_count": int(row.invited_users_count or 0),
                "total_score": total_score,
            }
        )
    for index, item in enumerate(rankings, start=1):
        item["rank"] = index
        item["display_name"] = (f"{item['first_name'] or ''} {item['last_name'] or ''}").strip() or str(item["telegram_id"])
    return rankings
