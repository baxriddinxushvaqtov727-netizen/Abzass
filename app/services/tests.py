from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.enums import PollType
from aiogram.types import PollAnswer
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.constants import MIN_REFERRALS_FOR_TEST
from app.core.i18n import t
from app.models import (
    ActiveQuizPoll,
    AttemptStatus,
    Question,
    QuestionOption,
    Test,
    TestAnswer,
    TestAttempt,
    User,
    UserProfile,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_test_open(test: Test) -> bool:
    if not test.is_active:
        return False
    if test.closed_at is not None:
        return False
    if test.scheduled_end_at and test.scheduled_end_at <= now_utc():
        return False
    return True


def user_can_take_test(user: User, test: Test | None = None) -> bool:
    required = test.min_referrals if test else MIN_REFERRALS_FOR_TEST
    return user.invited_users_count >= required


def _dump_question_order(question_ids: list[int]) -> str:
    return json.dumps(question_ids)


def _dump_option_order(option_map: dict[int, list[int]]) -> str:
    return json.dumps({str(key): value for key, value in option_map.items()})


def _load_question_order(attempt: TestAttempt) -> list[int]:
    raw_value = attempt.question_order_json or "[]"
    return [int(item) for item in json.loads(raw_value)]


def _load_option_order(attempt: TestAttempt) -> dict[int, list[int]]:
    raw_value = attempt.option_order_json or "{}"
    parsed = json.loads(raw_value)
    return {int(key): [int(item) for item in value] for key, value in parsed.items()}


def _question_map(test: Test) -> dict[int, Question]:
    return {question.id: question for question in test.questions}


def _build_attempt_rankings_title(language: str) -> tuple[str, str]:
    if language == "uz_cyrillic":
        return "📊 Натижа тайёр!", "🏁 Тест якунланди."
    if language == "ru":
        return "📊 Результат готов!", "🏁 Тест завершён."
    return "📊 Natija tayyor!", "🏁 Test yakunlandi."


async def get_active_tests(session: AsyncSession) -> list[Test]:
    stmt = (
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.options))
        .order_by(Test.id.desc())
    )
    result = await session.scalars(stmt)
    return [test for test in result.all() if is_test_open(test)]


async def get_all_tests(session: AsyncSession) -> list[Test]:
    result = await session.scalars(
        select(Test)
        .options(selectinload(Test.questions))
        .order_by(Test.id.desc())
    )
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
            selectinload(Test.attempts).selectinload(TestAttempt.answers).selectinload(TestAnswer.option),
            selectinload(Test.attempts).selectinload(TestAttempt.answers).selectinload(TestAnswer.question),
        )
        .where(Test.id == test_id)
    )
    return await session.scalar(stmt)


async def get_attempt(session: AsyncSession, attempt_id: int, user_id: int | None = None) -> TestAttempt | None:
    stmt = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.answers).selectinload(TestAnswer.question),
            selectinload(TestAttempt.answers).selectinload(TestAnswer.option),
            selectinload(TestAttempt.active_polls),
            joinedload(TestAttempt.user).selectinload(User.profile),
            joinedload(TestAttempt.test).selectinload(Test.questions).selectinload(Question.options),
        )
        .where(TestAttempt.id == attempt_id)
    )
    if user_id is not None:
        stmt = stmt.where(TestAttempt.user_id == user_id)
    return await session.scalar(stmt)


async def get_or_create_attempt(session: AsyncSession, user: User, test: Test) -> TestAttempt:
    stmt: Select[tuple[TestAttempt]] = (
        select(TestAttempt)
        .options(
            selectinload(TestAttempt.answers),
            selectinload(TestAttempt.active_polls),
            joinedload(TestAttempt.user).selectinload(User.profile),
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
            score=0,
            current_question_index=0,
        )
        session.add(attempt)
        await session.commit()
    return await get_attempt(session, attempt.id)  # type: ignore[return-value]


async def create_test(
    session: AsyncSession,
    *,
    title: str,
    test_code: str,
    min_referrals: int,
    question_time_limit: int,
    created_by_telegram_id: int | None = None,
    description: str | None = None,
    scheduled_end_at: datetime | None = None,
    questions_payload: list[dict],
) -> Test:
    if not questions_payload:
        raise ValueError("Kamida bitta savol kerak.")
    if question_time_limit < 5 or question_time_limit > 600:
        raise ValueError("Har bir savol uchun vaqt 5-600 soniya oralig'ida bo'lishi kerak.")

    test = Test(
        title=title.strip(),
        test_code=test_code.strip().upper(),
        description=(description or "").strip() or None,
        min_referrals=min_referrals,
        created_by_telegram_id=created_by_telegram_id,
        question_time_limit=question_time_limit,
        scheduled_end_at=scheduled_end_at,
        is_active=True,
    )
    session.add(test)
    await session.flush()

    for index, item in enumerate(questions_payload, start=1):
        options = [str(option).strip() for option in item["options"] if str(option).strip()]
        if len(options) != 4:
            raise ValueError(f"{index}-savolda aynan 4 ta variant bo'lishi kerak.")
        correct_index = int(item["correct_index"])
        if correct_index not in range(4):
            raise ValueError(f"{index}-savolda to'g'ri variant 1-4 oralig'ida bo'lishi kerak.")
        question = Question(
            test_id=test.id,
            text=str(item["text"]).strip(),
            order_index=index - 1,
        )
        session.add(question)
        await session.flush()
        for option_index, option_text in enumerate(options):
            session.add(
                QuestionOption(
                    question_id=question.id,
                    text=option_text,
                    is_correct=option_index == correct_index,
                )
            )

    await session.commit()
    return await get_test_by_id(session, test.id)  # type: ignore[return-value]


async def prepare_attempt(session: AsyncSession, attempt: TestAttempt) -> TestAttempt:
    if attempt.question_order_json and attempt.option_order_json:
        return attempt

    question_ids = [question.id for question in attempt.test.questions]
    random.shuffle(question_ids)
    option_map: dict[int, list[int]] = {}
    for question in attempt.test.questions:
        option_ids = [option.id for option in question.options]
        random.shuffle(option_ids)
        option_map[question.id] = option_ids

    attempt.question_order_json = _dump_question_order(question_ids)
    attempt.option_order_json = _dump_option_order(option_map)
    attempt.total_questions = len(question_ids)
    attempt.current_question_index = 0
    attempt.started_at = now_utc()
    await session.commit()
    return await get_attempt(session, attempt.id)  # type: ignore[return-value]


def _get_current_question(attempt: TestAttempt) -> Question | None:
    question_order = _load_question_order(attempt)
    if attempt.current_question_index >= len(question_order):
        return None
    question_id = question_order[attempt.current_question_index]
    return _question_map(attempt.test).get(question_id)


async def _register_poll(
    session: AsyncSession,
    *,
    attempt: TestAttempt,
    question: Question,
    poll_id: str,
    expires_at: datetime,
) -> None:
    session.add(
        ActiveQuizPoll(
            poll_id=poll_id,
            attempt_id=attempt.id,
            question_id=question.id,
            expires_at=expires_at,
            is_processed=False,
        )
    )
    await session.commit()


async def _finalize_attempt(session: AsyncSession, attempt: TestAttempt) -> TestAttempt:
    attempt.status = AttemptStatus.COMPLETED.value
    attempt.completed_at = now_utc()
    await session.execute(delete(ActiveQuizPoll).where(ActiveQuizPoll.attempt_id == attempt.id))
    await session.commit()
    return await get_attempt(session, attempt.id)  # type: ignore[return-value]


async def _send_current_question(session: AsyncSession, bot: Bot, attempt: TestAttempt) -> TestAttempt:
    question = _get_current_question(attempt)
    if question is None:
        return await _finalize_attempt(session, attempt)

    option_order = _load_option_order(attempt)
    ordered_option_ids = option_order.get(question.id, [])
    option_map = {option.id: option for option in question.options}
    ordered_options = [option_map[option_id] for option_id in ordered_option_ids if option_id in option_map]
    if len(ordered_options) != len(question.options):
        ordered_options = list(question.options)
        random.shuffle(ordered_options)
        option_order[question.id] = [option.id for option in ordered_options]
        attempt.option_order_json = _dump_option_order(option_order)
        await session.commit()

    correct_option_id = next((option.id for option in ordered_options if option.is_correct), None)
    if correct_option_id is None:
        raise ValueError("Savol uchun to'g'ri javob topilmadi.")
    correct_option_index = next(
        index for index, option in enumerate(ordered_options) if option.id == correct_option_id
    )

    header = f"❓ Savol {attempt.current_question_index + 1}/{attempt.total_questions}"
    poll_message = await bot.send_poll(
        chat_id=attempt.user.telegram_id,
        question=f"{header}\n{question.text}",
        options=[option.text for option in ordered_options],
        type=PollType.QUIZ,
        is_anonymous=False,
        correct_option_id=correct_option_index,
        open_period=attempt.test.question_time_limit,
        explanation=f"⏳ {attempt.test.question_time_limit} soniya ichida javob bering.",
    )
    await _register_poll(
        session,
        attempt=attempt,
        question=question,
        poll_id=poll_message.poll.id,
        expires_at=now_utc() + timedelta(seconds=attempt.test.question_time_limit),
    )
    return attempt


async def start_quiz_attempt(session: AsyncSession, bot: Bot, attempt: TestAttempt) -> TestAttempt:
    if attempt.status == AttemptStatus.COMPLETED.value:
        return attempt
    attempt = await prepare_attempt(session, attempt)
    return await _send_current_question(session, bot, attempt)


async def _apply_answer_to_attempt(
    session: AsyncSession,
    *,
    attempt: TestAttempt,
    question: Question,
    selected_option_id: int | None,
) -> TestAttempt:
    await session.execute(
        delete(TestAnswer).where(TestAnswer.attempt_id == attempt.id, TestAnswer.question_id == question.id)
    )
    is_correct = False
    if selected_option_id is not None:
        selected = next((option for option in question.options if option.id == selected_option_id), None)
        if selected is not None:
            is_correct = selected.is_correct
            session.add(
                TestAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    option_id=selected_option_id,
                    is_correct=is_correct,
                )
            )
    if is_correct:
        attempt.score += 1
    attempt.current_question_index += 1
    await session.commit()
    return await get_attempt(session, attempt.id)  # type: ignore[return-value]


async def _resolve_poll_answer(
    session: AsyncSession,
    *,
    active_poll: ActiveQuizPoll,
    chosen_option_index: int | None,
) -> TestAttempt:
    attempt = await get_attempt(session, active_poll.attempt_id)
    if attempt is None:
        await session.execute(delete(ActiveQuizPoll).where(ActiveQuizPoll.id == active_poll.id))
        await session.commit()
        raise ValueError("Attempt topilmadi.")
    question = next((item for item in attempt.test.questions if item.id == active_poll.question_id), None)
    if question is None:
        await session.execute(delete(ActiveQuizPoll).where(ActiveQuizPoll.id == active_poll.id))
        await session.commit()
        raise ValueError("Savol topilmadi.")

    option_order = _load_option_order(attempt).get(question.id, [])
    selected_option_id = None
    if chosen_option_index is not None and chosen_option_index in range(len(option_order)):
        selected_option_id = option_order[chosen_option_index]

    await session.execute(delete(ActiveQuizPoll).where(ActiveQuizPoll.id == active_poll.id))
    await session.commit()
    return await _apply_answer_to_attempt(
        session,
        attempt=attempt,
        question=question,
        selected_option_id=selected_option_id,
    )


async def handle_poll_answer(session: AsyncSession, bot: Bot, answer: PollAnswer) -> TestAttempt | None:
    stmt = (
        select(ActiveQuizPoll)
        .options(joinedload(ActiveQuizPoll.attempt).joinedload(TestAttempt.user))
        .where(ActiveQuizPoll.poll_id == answer.poll_id, ActiveQuizPoll.is_processed.is_(False))
    )
    active_poll = await session.scalar(stmt)
    if active_poll is None:
        return None
    if active_poll.attempt.user.telegram_id != answer.user.id:
        return None

    chosen_index = answer.option_ids[0] if answer.option_ids else None
    attempt = await _resolve_poll_answer(session, active_poll=active_poll, chosen_option_index=chosen_index)
    if attempt.status == AttemptStatus.COMPLETED.value:
        return await finish_attempt_and_notify(session, bot, attempt.id)
    return await _send_current_question(session, bot, attempt)


async def process_expired_quiz_polls(session: AsyncSession, bot: Bot) -> int:
    stmt = (
        select(ActiveQuizPoll)
        .options(joinedload(ActiveQuizPoll.attempt).joinedload(TestAttempt.user))
        .where(ActiveQuizPoll.expires_at <= now_utc(), ActiveQuizPoll.is_processed.is_(False))
        .order_by(ActiveQuizPoll.expires_at.asc())
    )
    expired_polls = list((await session.scalars(stmt)).all())
    processed = 0
    for active_poll in expired_polls:
        attempt = await _resolve_poll_answer(session, active_poll=active_poll, chosen_option_index=None)
        if attempt.status == AttemptStatus.COMPLETED.value:
            await finish_attempt_and_notify(session, bot, attempt.id)
        else:
            await _send_current_question(session, bot, attempt)
        processed += 1
    return processed


async def get_total_test_score(session: AsyncSession, user_id: int) -> int:
    score = await session.scalar(
        select(func.coalesce(func.sum(TestAttempt.score), 0)).where(
            TestAttempt.user_id == user_id,
            TestAttempt.status == AttemptStatus.COMPLETED.value,
        )
    )
    return int(score or 0)


async def get_test_rankings(session: AsyncSession) -> list[dict]:
    stmt = (
        select(
            User.id,
            User.telegram_id,
            UserProfile.first_name,
            UserProfile.last_name,
            func.coalesce(func.sum(TestAttempt.score), 0).label("test_score"),
        )
        .join(TestAttempt, (TestAttempt.user_id == User.id) & (TestAttempt.status == AttemptStatus.COMPLETED.value))
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .group_by(User.id, UserProfile.first_name, UserProfile.last_name)
        .order_by(func.coalesce(func.sum(TestAttempt.score), 0).desc(), User.id.asc())
    )
    result = await session.execute(stmt)
    rankings: list[dict] = []
    for row in result.all():
        rankings.append(
            {
                "user_id": row.id,
                "telegram_id": row.telegram_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "test_score": int(row.test_score or 0),
            }
        )
    for index, item in enumerate(rankings, start=1):
        item["rank"] = index
        item["display_name"] = (f"{item['first_name'] or ''} {item['last_name'] or ''}").strip() or str(item["telegram_id"])
    return rankings


async def get_referral_rankings(session: AsyncSession) -> list[dict]:
    stmt = (
        select(
            User.id,
            User.telegram_id,
            User.referral_score,
            User.invited_users_count,
            UserProfile.first_name,
            UserProfile.last_name,
        )
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .order_by(User.referral_score.desc(), User.invited_users_count.desc(), User.id.asc())
    )
    result = await session.execute(stmt)
    rankings: list[dict] = []
    for row in result.all():
        rankings.append(
            {
                "user_id": row.id,
                "telegram_id": row.telegram_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "referral_score": int(row.referral_score or 0),
                "invited_users_count": int(row.invited_users_count or 0),
            }
        )
    for index, item in enumerate(rankings, start=1):
        item["rank"] = index
        item["display_name"] = (f"{item['first_name'] or ''} {item['last_name'] or ''}").strip() or str(item["telegram_id"])
    return rankings


async def get_user_rankings(session: AsyncSession) -> list[dict]:
    test_rankings = await get_test_rankings(session)
    referral_rankings = await get_referral_rankings(session)
    referral_map = {item["user_id"]: item for item in referral_rankings}
    combined: list[dict] = []
    for item in test_rankings:
        referral_item = referral_map.get(item["user_id"], {})
        combined.append(
            {
                "user_id": item["user_id"],
                "telegram_id": item["telegram_id"],
                "first_name": item["first_name"],
                "last_name": item["last_name"],
                "display_name": item["display_name"],
                "test_score": item["test_score"],
                "test_rank": item["rank"],
                "referral_score": int(referral_item.get("referral_score", 0)),
                "referral_rank": referral_item.get("rank"),
            }
        )
    return combined


def build_attempt_review(attempt: TestAttempt) -> str:
    user_name = (
        f"{attempt.user.profile.first_name} {attempt.user.profile.last_name}"
        if attempt.user and attempt.user.profile
        else str(attempt.user.telegram_id)
    )
    lines = [
        f"🧑‍🎓 Ishtirokchi: {user_name}",
        f"📝 Test: {attempt.test.title}",
        f"🆔 Test ID: {attempt.test.test_code}",
        f"📊 Natija: {attempt.score}/{attempt.total_questions}",
        "",
    ]
    answer_map = {answer.question_id: answer for answer in attempt.answers}
    for index, question in enumerate(attempt.test.questions, start=1):
        answer = answer_map.get(question.id)
        chosen = answer.option.text if answer else "Javob belgilanmagan"
        correct = next((option.text for option in question.options if option.is_correct), "Noma'lum")
        status = "✅ To'g'ri" if answer and answer.is_correct else "❌ Noto'g'ri"
        lines.extend(
            [
                f"{index}. {question.text}",
                f"Siz belgilagan javob: {chosen}",
                f"To'g'ri javob: {correct}",
                f"Holat: {status}",
                "",
            ]
        )
    return "\n".join(lines).strip()


async def finish_attempt_and_notify(session: AsyncSession, bot: Bot, attempt_id: int) -> TestAttempt | None:
    attempt = await get_attempt(session, attempt_id)
    if attempt is None:
        return None
    if attempt.status != AttemptStatus.COMPLETED.value:
        attempt = await _finalize_attempt(session, attempt)
    test_rankings = await get_test_rankings(session)
    user_test_rank = next((item for item in test_rankings if item["user_id"] == attempt.user_id), None)
    title, subtitle = _build_attempt_rankings_title(attempt.user.language)
    leader = test_rankings[0] if test_rankings else None
    text = "\n".join(
        [
            title,
            subtitle,
            f"📝 Test: {attempt.test.title}",
            f"📊 Bal: {attempt.score}/{attempt.total_questions}",
            f"🏅 O'rin: {user_test_rank['rank'] if user_test_rank else '-'}",
            f"🥇 Lider: {leader['display_name']} - {leader['test_score']} ball" if leader else "🥇 Lider yo'q",
        ]
    )
    try:
        await bot.send_message(attempt.user.telegram_id, text)
    except Exception:
        pass
    return attempt


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
