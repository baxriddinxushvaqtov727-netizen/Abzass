from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Document,
    FSInputFile,
    Message,
    PollAnswer,
    PhotoSize,
    ReplyKeyboardRemove,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.keyboards import (
    admin_broadcast_keyboard,
    admin_channels_keyboard,
    admin_content_keyboard,
    admin_panel_keyboard,
    admin_quiz_poll_keyboard,
    admin_ticket_actions,
    admin_test_builder_keyboard,
    admin_tests_keyboard,
    main_menu_keyboard,
    normalize_channel_url,
    phone_keyboard,
    referral_share_keyboard,
    regions_keyboard,
    required_channels_keyboard,
    test_selection_keyboard,
)
from app.bot.states import AdminStates, RegistrationStates, SupportStates
from app.core.config import get_settings
from app.core.i18n import resolve_menu_key, t
from app.db.session import AsyncSessionLocal
from app.models import ContestBook, ContestRule, RequiredChannel, Test, TestAttempt
from app.services.broadcasts import create_scheduled_broadcast, get_all_broadcasts, run_broadcast_now
from app.services.content import get_active_books, get_active_rules, get_all_books, get_all_rules
from app.services.storage import save_bot_file
from app.services.subscriptions import get_missing_subscriptions
from app.services.settings import (
    get_referral_share_media_path,
    get_referral_share_text,
    set_referral_share_content,
)
from app.services.tickets import answer_ticket, create_ticket, reject_ticket
from app.services.tests import (
    close_test_and_notify,
    create_test,
    get_active_tests,
    get_all_tests,
    get_or_create_attempt,
    get_referral_rankings,
    get_rankings_for_single_test,
    get_test_by_id,
    get_test_rankings,
    get_total_test_score,
    handle_poll_answer,
    start_quiz_attempt,
    user_can_take_test,
)
from app.services.users import complete_profile, get_user_by_telegram_id, set_phone_number, upsert_telegram_user


router = Router()


async def start_profile_registration(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_for_first_name)
    await message.answer("Ro'yxatdan o'tishni boshlaymiz.\nIsmingizni yuboring.", reply_markup=ReplyKeyboardRemove())


async def ensure_user_ready(
    message: Message,
    bot: Bot,
    state: FSMContext | None = None,
    telegram_user_id: int | None = None,
) -> bool:
    actor_id = telegram_user_id or (message.from_user.id if message.from_user else None)
    if actor_id is None:
        await message.answer("Avval /start buyrug'ini bosing.")
        return False
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, actor_id)
        if user is None:
            await message.answer("Avval /start buyrug'ini bosing.")
            return False
        language = user.language
        missing = await get_missing_subscriptions(bot, session, user)
        if missing:
            await message.answer(
                t(language, "subscriptions_check_first"),
                reply_markup=required_channels_keyboard(
                    [{"title": item.title, "url": item.invite_link or "https://t.me/"} for item in missing],
                    language,
                ),
            )
            return False
        if not user.phone_number:
            await message.answer(t(language, "start_phone"), reply_markup=phone_keyboard())
            return False
        if not user.is_profile_completed:
            if state is not None:
                await start_profile_registration(message, state)
            else:
                await message.answer(t(language, "profile_prompt"))
            return False
    return True


async def get_test_by_reference(session, value: str) -> Test | None:
    raw_value = value.strip()
    if raw_value.isdigit():
        test = await get_test_by_id(session, int(raw_value))
        if test is not None:
            return test
    code_stmt = select(Test).options(selectinload(Test.questions)).where(Test.test_code == raw_value.upper())
    return await session.scalar(code_stmt)


async def get_channel_by_reference(session, value: str) -> RequiredChannel | None:
    raw_value = value.strip()
    if raw_value.isdigit():
        channel = await session.get(RequiredChannel, int(raw_value))
        if channel is not None:
            return channel
        return await session.scalar(select(RequiredChannel).where(RequiredChannel.chat_id == int(raw_value)))
    normalized_reference = normalize_channel_reference(raw_value)
    normalized_url = normalize_channel_url(raw_value)
    stmt = select(RequiredChannel).where(
        (RequiredChannel.invite_link == normalized_url)
        | (RequiredChannel.invite_link == normalized_reference)
        | (RequiredChannel.invite_link == raw_value)
    )
    return await session.scalar(stmt)


async def send_attachment(message: Message, path: str) -> None:
    file_path = Path(path)
    if not file_path.exists():
        return
    suffix = file_path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        await message.answer_photo(FSInputFile(file_path))
    else:
        await message.answer_document(FSInputFile(file_path))


def is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_list


def parse_admin_datetime(value: str) -> datetime | None:
    raw = value.strip()
    if raw.lower() in {"yoq", "yo'q", "none", "no", "-"}:
        return None
    settings = get_settings()
    local_zone = ZoneInfo(settings.app_timezone)
    normalized = raw.replace("T", " ")
    parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=local_zone).astimezone(timezone.utc)


def format_channels(channels: list[RequiredChannel]) -> str:
    if not channels:
        return "Majburiy kanallar yo'q."
    lines = ["Majburiy kanallar:"]
    for channel in channels:
        lines.append(f"{channel.id}. {channel.title} | chat_id={channel.chat_id} | {channel.invite_link or '-'}")
    return "\n".join(lines)


def format_tests(tests: list) -> str:
    if not tests:
        return "📝 Testlar yo'q."
    lines = ["📝 Mavjud testlar:"]
    for test in tests:
        end_at = test.scheduled_end_at.strftime("%Y-%m-%d %H:%M") if test.scheduled_end_at else "qo'lda"
        status = "faol" if test.is_active else "yopilgan"
        creator = test.created_by_telegram_id or "-"
        question_count = len(test.questions) if getattr(test, "questions", None) is not None else "-"
        lines.append(
            f"{test.id}. {test.title} | ID: {test.test_code} | {status} | savol: {question_count} | "
            f"limit: {test.question_time_limit}s | tugash: {end_at} | creator: {creator}"
        )
    return "\n".join(lines)


def format_content(items: list, label: str) -> str:
    if not items:
        return f"{label} yo'q."
    lines = [f"{label} ro'yxati:"]
    for item in items:
        lines.append(f"{item.id}. {item.title}")
    return "\n".join(lines)


def format_broadcasts(items: list) -> str:
    if not items:
        return "Scheduled broadcastlar yo'q."
    lines = ["Scheduled broadcastlar:"]
    for item in items[:20]:
        status = "yuborildi" if item.is_sent else "kutilmoqda"
        lines.append(f"{item.id}. {item.scheduled_at.strftime('%Y-%m-%d %H:%M')} | {status}")
    return "\n".join(lines)


def parse_test_options(value: str) -> list[str]:
    options = [item.strip() for item in value.split("|") if item.strip()]
    if len(options) != 4:
        raise ValueError("Aynan 4 ta variant yuboring. Format: A | B | C | D")
    return options


def format_test_builder_summary(data: dict) -> str:
    questions = data.get("questions", [])
    lines = [
        "🧪 Test draft",
        f"📌 Nomi: {data.get('title', '-')}",
        f"🆔 ID: {data.get('test_code', '-')}",
        f"🤝 Min referral: {data.get('min_referrals', '-')}",
        f"⏱ Har savol vaqti: {data.get('question_time_limit', '-')} soniya",
        f"❓ Savollar soni: {len(questions)}",
    ]
    if questions:
        last_question = questions[-1]
        lines.append("")
        lines.append(f"So'nggi savol: {last_question['text']}")
    return "\n".join(lines)


def build_referral_share_url(link: str, share_text: str) -> str:
    return f"https://t.me/share/url?url={quote_plus(link)}&text={quote_plus(share_text)}"


def normalize_channel_reference(raw_value: str) -> str:
    value = raw_value.strip()
    if value.startswith("https://t.me/"):
        return f"@{value.removeprefix('https://t.me/').strip('/')}"
    if value.startswith("http://t.me/"):
        return f"@{value.removeprefix('http://t.me/').strip('/')}"
    if value.startswith("t.me/"):
        return f"@{value.removeprefix('t.me/').strip('/')}"
    if value.startswith("telegram.me/"):
        return f"@{value.removeprefix('telegram.me/').strip('/')}"
    if value.startswith("@"):
        return value
    return f"@{value.lstrip('/')}"


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        raise


def get_user_display_name(user) -> str:
    if getattr(user, "profile", None):
        full_name = f"{user.profile.first_name} {user.profile.last_name}".strip()
        if full_name:
            return full_name
    full_name = f"{getattr(user, 'telegram_first_name', '') or ''} {getattr(user, 'telegram_last_name', '') or ''}".strip()
    if full_name:
        return full_name
    return str(user.telegram_id)


def format_results_message(
    language: str,
    *,
    my_test_rank: dict | None,
    test_leader: dict | None,
    my_referral_rank: dict | None,
    referral_leader: dict | None,
    test_score: int,
    referral_score: int,
) -> str:
    lines = [
        f"<b>📊 {escape(t(language, 'results_title'))}</b>",
        f"📝 {t(language, 'results_test_score', score=test_score)}",
        f"🏅 {t(language, 'results_test_rank', rank=my_test_rank['rank'] if my_test_rank else '-')}",
        f"🤝 {t(language, 'results_referral_score', score=referral_score)}",
        f"🌟 {t(language, 'results_referral_rank', rank=my_referral_rank['rank'] if my_referral_rank else '-')}",
    ]
    if test_leader:
        lines.append(f"🥇 {t(language, 'results_test_leader', name=escape(test_leader['display_name']), score=test_leader['test_score'])}")
    if referral_leader:
        lines.append(f"🏆 {t(language, 'results_referral_leader', name=escape(referral_leader['display_name']), score=referral_leader['referral_score'])}")
    if not my_test_rank and not my_referral_rank:
        lines.append(t(language, "results_unranked"))
    return "\n".join(lines)


def format_cabinet_message(
    language: str,
    *,
    user,
    test_score: int,
    my_test_rank: dict | None,
    my_referral_rank: dict | None,
    attempts: list[TestAttempt],
) -> str:
    profile = user.profile
    lines = [
        f"<b>👤 {escape(t(language, 'cabinet_title'))}</b>",
        f"🧑 {t(language, 'cabinet_name', value=escape(profile.first_name))}",
        f"🪪 {t(language, 'cabinet_last_name', value=escape(profile.last_name))}",
        f"👨‍👦 {t(language, 'cabinet_patronymic', value=escape(profile.patronymic))}",
        f"📍 {t(language, 'cabinet_region', value=escape(profile.region))}",
        f"🏘 {t(language, 'cabinet_district', value=escape(profile.district))}",
        f"📱 {t(language, 'cabinet_phone', value=escape(user.phone_number or '-'))}",
        f"🤝 {t(language, 'cabinet_invited', count=user.invited_users_count)}",
        f"📝 {t(language, 'results_test_score', score=test_score)}",
        f"🏅 {t(language, 'results_test_rank', rank=my_test_rank['rank'] if my_test_rank else '-')}",
        f"🌟 {t(language, 'results_referral_score', score=user.referral_score)}",
        f"🏆 {t(language, 'results_referral_rank', rank=my_referral_rank['rank'] if my_referral_rank else '-')}",
        "",
        f"<b>📚 {escape(t(language, 'cabinet_history_title'))}</b>",
    ]
    if attempts:
        for attempt in attempts:
            test_name = escape(attempt.test.title if attempt.test else str(attempt.test_id))
            lines.append(f"{escape(attempt.test.test_code if attempt.test else '-')} | {test_name} | {attempt.score}/{attempt.total_questions}")
    else:
        lines.append(t(language, "cabinet_history_empty"))
    return "\n".join(lines)


def _chunk_text_blocks(header: str, lines: list[str], limit: int = 3500) -> list[str]:
    if not lines:
        return [header]
    chunks: list[str] = []
    current = header
    for line in lines:
        candidate = f"{current}\n{line}"
        if len(candidate) > limit and current != header:
            chunks.append(current)
            current = f"{header}\n{line}"
        elif len(candidate) > limit:
            chunks.append(candidate[:limit])
            current = header
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return chunks


def build_referral_leaderboard_messages(language: str, rankings: list[dict]) -> list[str]:
    header = f"<b>🏆 {escape(t(language, 'leaderboard_title'))}</b>\n<b>🤝 {escape(t(language, 'leaderboard_referral_title'))}</b>"
    if not rankings:
        return [f"{header}\n{t(language, 'leaderboard_empty')}"]
    lines = [
        t(
            language,
            "leaderboard_referral_line",
            rank=item["rank"],
            name=escape(item["display_name"]),
            score=item["referral_score"],
            count=item["invited_users_count"],
        )
        for item in rankings
    ]
    return _chunk_text_blocks(header, lines)


def build_test_leaderboard_messages(language: str, *, test, rankings: list[dict]) -> list[str]:
    header = (
        f"<b>🧪 {escape(test.title)}</b>\n"
        f"🆔 {escape(test.test_code)}\n"
        f"<b>📋 {escape(t(language, 'leaderboard_tests_title'))}</b>"
    )
    if not rankings:
        return [f"{header}\n{t(language, 'leaderboard_no_test_results')}"]
    lines = [
        t(
            language,
            "leaderboard_test_line",
            rank=item["rank"],
            name=escape(item["display_name"]),
            score=item["test_score"],
            total=len(test.questions),
        )
        for item in rankings
    ]
    return _chunk_text_blocks(header, lines)


@router.message(Command("start"))
async def start_handler(message: Message, command: CommandObject, bot: Bot, state: FSMContext) -> None:
    if not message.from_user:
        return

    async with AsyncSessionLocal() as session:
        user = await upsert_telegram_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referral_code=command.args,
        )
        missing = await get_missing_subscriptions(bot, session, user)
        if missing:
            await message.answer(
                t(user.language, "subscriptions_needed"),
                reply_markup=required_channels_keyboard(
                    [{"title": item.title, "url": item.invite_link or "https://t.me/"} for item in missing],
                    user.language,
                ),
            )
            return

        if not user.phone_number:
            await message.answer(
                t(user.language, "start_phone"),
                reply_markup=phone_keyboard(),
            )
            return

        if not user.is_profile_completed:
            await start_profile_registration(message, state)
            return

    await message.answer(
        t(user.language, "start_ready"),
        reply_markup=main_menu_keyboard(user.language),
    )


@router.callback_query(F.data == "check_subscriptions")
async def check_subscriptions_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.message.answer("Avval /start buyrug'ini yuboring.")
            await callback.answer()
            return

        missing = await get_missing_subscriptions(bot, session, user)
        if missing:
            await callback.message.answer(
                t(user.language, "subscriptions_incomplete"),
                reply_markup=required_channels_keyboard(
                    [{"title": item.title, "url": item.invite_link or "https://t.me/"} for item in missing],
                    user.language,
                ),
            )
            await callback.answer("Obuna hali to'liq emas.", show_alert=True)
            return

        if not user.phone_number:
            await callback.message.answer(t(user.language, "subscription_verified"), reply_markup=phone_keyboard())
        elif not user.is_profile_completed:
            await start_profile_registration(callback.message, state)
        else:
            await callback.message.answer(t(user.language, "start_ready"), reply_markup=main_menu_keyboard(user.language))
    await callback.answer()


@router.message(F.contact)
async def contact_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.contact:
        return
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_telegram_id(session, message.from_user.id)
            language = user.language if user else "uz_latin"
        await message.answer(t(language, "self_contact_only"))
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Avval /start buyrug'ini yuboring.")
            return
        await set_phone_number(session, user, message.contact.phone_number)
        language = user.language

    await message.answer(
        t(language, "contact_saved"),
        reply_markup=ReplyKeyboardRemove(),
    )
    await start_profile_registration(message, state)


@router.message(RegistrationStates.waiting_for_first_name)
async def registration_first_name_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    await state.update_data(first_name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_last_name)
    await message.answer("Familiyangizni yuboring.")


@router.message(RegistrationStates.waiting_for_last_name)
async def registration_last_name_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    await state.update_data(last_name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_patronymic)
    await message.answer("Otasining ismini yuboring.")


@router.message(RegistrationStates.waiting_for_patronymic)
async def registration_patronymic_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    await state.update_data(patronymic=message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_region)
    await message.answer("Viloyatni tanlang.", reply_markup=regions_keyboard())


@router.callback_query(RegistrationStates.waiting_for_region, F.data.startswith("reg_region:"))
async def registration_region_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)
    await state.set_state(RegistrationStates.waiting_for_district)
    await callback.message.answer(f"Tanlangan viloyat: {region}\nEndi tuman nomini matn ko'rinishida yuboring.")
    await callback.answer()


@router.message(RegistrationStates.waiting_for_district)
async def registration_district_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    await state.update_data(district=message.text.strip())
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Avval /start yuboring.")
            return
        await complete_profile(
            session,
            user,
            first_name=data["first_name"],
            last_name=data["last_name"],
            patronymic=data["patronymic"],
            region=data["region"],
            district=data["district"],
        )
    await state.clear()
    await message.answer("Ro'yxatdan o'tish yakunlandi.", reply_markup=main_menu_keyboard(user.language))


@router.message(Command("admin"))
async def admin_panel_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    await state.clear()
    await message.answer(
        "Telegram admin panel.\nBo'limni tanlang:",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not is_admin(callback.from_user.id):
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]
    await state.clear()

    async with AsyncSessionLocal() as session:
        if action == "home":
            await safe_edit_text(callback.message, "Telegram admin panel.\nBo'limni tanlang:", reply_markup=admin_panel_keyboard())
        elif action == "channels":
            await safe_edit_text(callback.message, "Kanallar boshqaruvi:", reply_markup=admin_channels_keyboard())
        elif action == "list_channels":
            channels = list((await session.scalars(select(RequiredChannel).order_by(RequiredChannel.id.desc()))).all())
            await safe_edit_text(callback.message, format_channels(channels), reply_markup=admin_channels_keyboard())
        elif action == "add_channel":
            await state.set_state(AdminStates.waiting_for_channel_create)
            await callback.message.answer(
                "Yangi kanal uchun faqat username yoki havolani yuboring.\n"
                "Masalan: `@FizikaMathUz` yoki `https://t.me/FizikaMathUz`\n"
                "Bot kanal nomi va chat ID ni o'zi topadi."
            )
        elif action == "delete_channel":
            channels = list((await session.scalars(select(RequiredChannel).order_by(RequiredChannel.id.desc()))).all())
            await state.set_state(AdminStates.waiting_for_channel_delete)
            await callback.message.answer(
                f"{format_channels(channels)}\n\nO'chirish uchun kanal ID, chat_id yoki @username yuboring."
            )
        elif action == "tests":
            await safe_edit_text(callback.message, "Testlar boshqaruvi:", reply_markup=admin_tests_keyboard())
        elif action == "list_tests":
            await safe_edit_text(callback.message, format_tests(await get_all_tests(session)), reply_markup=admin_tests_keyboard())
        elif action == "add_test":
            await state.set_state(AdminStates.waiting_for_test_title)
            await callback.message.answer("🧪 Test nomini yuboring.")
        elif action == "close_test":
            await state.set_state(AdminStates.waiting_for_test_close)
            await callback.message.answer(f"{format_tests(await get_all_tests(session))}\n\nYopish uchun test ID yoki test code yuboring.")
        elif action == "delete_test":
            await state.set_state(AdminStates.waiting_for_test_delete)
            await callback.message.answer(f"{format_tests(await get_all_tests(session))}\n\nO'chirish uchun test ID yoki test code yuboring.")
        elif action == "content":
            await safe_edit_text(callback.message, "Nizom va kitoblar boshqaruvi:", reply_markup=admin_content_keyboard())
        elif action == "add_rule":
            await state.update_data(content_kind="rule")
            await state.set_state(AdminStates.waiting_for_content_title)
            await callback.message.answer("Nizom sarlavhasini yuboring.")
        elif action == "add_book":
            await state.update_data(content_kind="book")
            await state.set_state(AdminStates.waiting_for_content_title)
            await callback.message.answer("Kitob sarlavhasini yuboring.")
        elif action == "list_rules":
            await safe_edit_text(callback.message, format_content(await get_all_rules(session), "Nizomlar"), reply_markup=admin_content_keyboard())
        elif action == "list_books":
            await safe_edit_text(callback.message, format_content(await get_all_books(session), "Kitoblar"), reply_markup=admin_content_keyboard())
        elif action == "delete_rule":
            await state.update_data(content_kind="rule")
            await state.set_state(AdminStates.waiting_for_content_delete)
            await callback.message.answer(f"{format_content(await get_all_rules(session), 'Nizomlar')}\n\nO'chirish uchun ID yuboring.")
        elif action == "delete_book":
            await state.update_data(content_kind="book")
            await state.set_state(AdminStates.waiting_for_content_delete)
            await callback.message.answer(f"{format_content(await get_all_books(session), 'Kitoblar')}\n\nO'chirish uchun ID yuboring.")
        elif action == "broadcast":
            await safe_edit_text(callback.message, "Broadcast boshqaruvi:", reply_markup=admin_broadcast_keyboard())
        elif action == "referral_text":
            current_text = await get_referral_share_text(session)
            await state.set_state(AdminStates.waiting_for_referral_content)
            preview = current_text or "Hozircha alohida izoh yo'q."
            await callback.message.answer(
                "🖼 Referral izohi uchun matn yoki rasm+caption yuboring.\n`yo'q` yuborsangiz izoh va rasm o'chiriladi.\n\n"
                f"Joriy izoh:\n{preview}"
            )
        elif action == "broadcast_now":
            await state.update_data(broadcast_mode="now")
            await state.set_state(AdminStates.waiting_for_broadcast_message)
            await callback.message.answer("Darhol yuboriladigan broadcast matnini yuboring.")
        elif action == "broadcast_schedule":
            await state.update_data(broadcast_mode="schedule")
            await state.set_state(AdminStates.waiting_for_broadcast_message)
            await callback.message.answer("Rejalashtiriladigan broadcast matnini yuboring.")
        elif action == "list_broadcasts":
            await safe_edit_text(callback.message, format_broadcasts(await get_all_broadcasts(session)), reply_markup=admin_broadcast_keyboard())

    await callback.answer()


@router.callback_query(F.data == "test_more")
async def admin_test_more_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message or not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_test_question_text)
    data = await state.get_data()
    next_index = len(data.get("questions", [])) + 1
    await callback.message.answer(
        f"🧪 {next_index}-savol uchun quiz poll yuboring.",
        reply_markup=admin_quiz_poll_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "test_finish")
async def admin_test_finish_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message or not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    questions = list(data.get("questions", []))
    if not questions:
        await callback.answer("Kamida bitta savol qo'shing.", show_alert=True)
        return
    scheduled_end_at = datetime.fromisoformat(data["scheduled_end_at"]) if data.get("scheduled_end_at") else None
    async with AsyncSessionLocal() as session:
        try:
            test = await create_test(
                session,
                title=data["title"],
                test_code=data["test_code"],
                min_referrals=int(data["min_referrals"]),
                question_time_limit=int(data["question_time_limit"]),
                created_by_telegram_id=callback.from_user.id,
                scheduled_end_at=scheduled_end_at,
                questions_payload=questions,
            )
        except Exception as exc:
            await callback.message.answer(f"❌ Test yaratilmadi: {exc}")
            await callback.answer()
            return
    await state.clear()
    await callback.message.answer(
        "🎉 Test yaratildi!\n"
        f"📝 Nomi: {test.title}\n"
        f"🆔 Test ID: {test.test_code}\n"
        f"❓ Savollar: {len(test.questions)}\n"
        f"🤝 Min referral: {test.min_referrals}\n"
        f"⏱ Har savol: {test.question_time_limit} soniya",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer("Test saqlandi ✅")


@router.message(AdminStates.waiting_for_channel_create)
async def admin_channel_create_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        reference = normalize_channel_reference(message.text)
        chat = await bot.get_chat(reference)
    except TelegramBadRequest:
        await message.answer(
            "Kanal topilmadi yoki bot kanalni ko'ra olmayapti.\n"
            "Username ni `@kanal` ko'rinishida yuboring va bot kanalga qo'shilganini tekshiring."
        )
        return
    title = getattr(chat, "title", None) or getattr(chat, "full_name", None) or reference
    invite_link = normalize_channel_url(message.text)
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(RequiredChannel).where(RequiredChannel.chat_id == int(chat.id)))
        if existing is not None:
            existing.title = title
            existing.invite_link = invite_link
            existing.is_active = True
        else:
            session.add(RequiredChannel(title=title, chat_id=int(chat.id), invite_link=invite_link, is_active=True))
        await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Kanal qo'shildi.\n📝 Nomi: {title}\n🆔 Chat ID: {int(chat.id)}\n🔗 Havola: {invite_link}",
        reply_markup=admin_panel_keyboard(),
    )


@router.message(AdminStates.waiting_for_channel_delete)
async def admin_channel_delete_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    async with AsyncSessionLocal() as session:
        channel = await get_channel_by_reference(session, message.text)
        if channel is None:
            await message.answer("Kanal topilmadi. ID, chat_id yoki @username yuboring.")
            return
        removed_title = channel.title
        await session.delete(channel)
        await session.commit()
    await state.clear()
    await message.answer(f"🗑 Kanal o'chirildi: {removed_title}", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_referral_content)
async def admin_referral_content_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    raw_text = (message.text or message.caption or "").strip()
    if raw_text.lower() in {"yo'q", "yoq", "none", "no", "-"}:
        text = None
        media_path = None
        replace_media = True
    else:
        text = raw_text or None
        media_path = None
        replace_media = False
        if message.photo:
            media_path = await save_bot_file(bot, message.photo[-1].file_id, "referral", ".jpg")
            replace_media = True
    async with AsyncSessionLocal() as session:
        await set_referral_share_content(session, text=text, media_path=media_path, replace_media=replace_media)
    await state.clear()
    if text or media_path:
        await message.answer("✅ Referral izohi saqlandi.", reply_markup=admin_panel_keyboard())
    else:
        await message.answer("🗑 Referral izohi o'chirildi.", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_test_title)
async def admin_test_title_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.waiting_for_test_code)
    await message.answer("🆔 Test ID ni yuboring. Masalan: 1234")


@router.message(AdminStates.waiting_for_test_code)
async def admin_test_code_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    await state.update_data(test_code=message.text.strip().upper())
    await state.set_state(AdminStates.waiting_for_test_min_referrals)
    await message.answer("🤝 Test uchun minimal referral sonini yuboring.")


@router.message(AdminStates.waiting_for_test_min_referrals)
async def admin_test_min_referrals_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        min_referrals = int(message.text.strip())
    except ValueError:
        await message.answer("Referral soni butun son bo'lishi kerak.")
        return
    await state.update_data(min_referrals=min_referrals)
    await state.set_state(AdminStates.waiting_for_test_time_limit)
    await message.answer("⏱ Har bir savol uchun vaqtni soniyada yuboring. Masalan: 30")


@router.message(AdminStates.waiting_for_test_time_limit)
async def admin_test_time_limit_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        question_time_limit = int(message.text.strip())
    except ValueError:
        await message.answer("Vaqt butun son bo'lishi kerak.")
        return
    if question_time_limit < 5 or question_time_limit > 600:
        await message.answer("Vaqt 5 dan 600 soniyagacha bo'lishi kerak.")
        return
    await state.update_data(question_time_limit=question_time_limit)
    await state.set_state(AdminStates.waiting_for_test_end_at)
    await message.answer("📅 Tugash vaqtini `YYYY-MM-DD HH:MM` formatida yuboring. Kerak bo'lmasa `yo'q` yuboring.")


@router.message(AdminStates.waiting_for_test_end_at)
async def admin_test_end_at_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        scheduled_end_at = parse_admin_datetime(message.text)
    except ValueError:
        await message.answer("Vaqt formati xato. `YYYY-MM-DD HH:MM` ko'rinishida yuboring yoki `yo'q` deb yozing.")
        return
    await state.update_data(scheduled_end_at=scheduled_end_at.isoformat() if scheduled_end_at else "")
    await state.update_data(questions=[])
    await state.set_state(AdminStates.waiting_for_test_question_text)
    await message.answer(
        "🧪 1-savol uchun native quiz poll yuboring.\n"
        "Pastdagi tugmani bossangiz Telegram quiz oynasi ochiladi.",
        reply_markup=admin_quiz_poll_keyboard(),
    )


@router.message(AdminStates.waiting_for_test_question_text)
async def admin_test_question_text_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if not message.poll:
        await message.answer(
            "❌ Bu bosqichda quiz poll yuborilishi kerak.\n"
            "Pastdagi tugmani bosib Telegram quiz oynasini oching.",
            reply_markup=admin_quiz_poll_keyboard(),
        )
        return
    if message.poll.type != "quiz":
        await message.answer("❌ Oddiy poll emas, aynan quiz poll yuboring.", reply_markup=admin_quiz_poll_keyboard())
        return
    if len(message.poll.options) != 4:
        await message.answer("❌ Quiz poll aynan 4 ta variantdan iborat bo'lishi kerak.", reply_markup=admin_quiz_poll_keyboard())
        return
    correct_index = message.poll.correct_option_id
    if correct_index is None or correct_index not in range(4):
        await message.answer("❌ To'g'ri javob belgilangan quiz poll yuboring.", reply_markup=admin_quiz_poll_keyboard())
        return
    data = await state.get_data()
    questions = list(data.get("questions", []))
    options = [option.text.strip() for option in message.poll.options]
    questions.append(
        {
            "text": message.poll.question.strip(),
            "options": options,
            "correct_index": correct_index,
        }
    )
    await state.update_data(questions=questions)
    preview = "\n".join(
        [
            f"❓ {questions[-1]['text']}",
            f"1. {options[0]}",
            f"2. {options[1]}",
            f"3. {options[2]}",
            f"4. {options[3]}",
            f"✅ To'g'ri javob: {correct_index + 1}",
        ]
    )
    await message.answer(
        f"✅ {len(questions)}-savol saqlandi.\n\n{preview}\n\n{format_test_builder_summary({**data, 'questions': questions})}",
        reply_markup=admin_test_builder_keyboard(),
    )


@router.message(AdminStates.waiting_for_test_close)
async def admin_test_close_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    async with AsyncSessionLocal() as session:
        target = await get_test_by_reference(session, message.text)
        if target is None:
            await message.answer("Test topilmadi.")
            return
        test = await close_test_and_notify(session, bot, target.id)
    if test is None:
        await message.answer("Test topilmadi.")
        return
    await state.clear()
    await message.answer("Test yopildi va ishtirokchilarga natija yuborildi.", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_test_delete)
async def admin_test_delete_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    async with AsyncSessionLocal() as session:
        test = await get_test_by_reference(session, message.text)
        if test is None:
            await message.answer("Test topilmadi.")
            return
        await session.delete(test)
        await session.commit()
    await state.clear()
    await message.answer("Test o'chirildi.", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_content_title)
async def admin_content_title_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    await state.update_data(content_title=message.text.strip())
    await state.set_state(AdminStates.waiting_for_content_body)
    await message.answer("Endi matn yoki matn+media yuboring.")


@router.message(AdminStates.waiting_for_content_body)
async def admin_content_body_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    kind = data.get("content_kind")
    title = data.get("content_title")
    if not kind or not title:
        await state.clear()
        await message.answer("Admin jarayoni bekor qilindi.")
        return

    content_text = (message.text or message.caption or "").strip() or "Matn kiritilmagan."
    media_path = None
    file_path = None

    if message.photo:
        media_path = await save_bot_file(bot, message.photo[-1].file_id, "media", ".jpg")
    elif message.video:
        media_path = await save_bot_file(bot, message.video.file_id, "media", ".mp4")
    elif message.document:
        extension = Path(message.document.file_name or "").suffix or None
        file_path = await save_bot_file(bot, message.document.file_id, "files", extension)

    async with AsyncSessionLocal() as session:
        if kind == "rule":
            session.add(ContestRule(title=title, content=content_text, file_path=file_path, media_path=media_path))
        else:
            session.add(ContestBook(title=title, content=content_text, file_path=file_path, media_path=media_path))
        await session.commit()
    await state.clear()
    await message.answer("Ma'lumot saqlandi.", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_content_delete)
async def admin_content_delete_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        item_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID son bo'lishi kerak.")
        return
    data = await state.get_data()
    kind = data.get("content_kind")
    model = ContestRule if kind == "rule" else ContestBook
    async with AsyncSessionLocal() as session:
        item = await session.get(model, item_id)
        if item is None:
            await message.answer("Element topilmadi.")
            return
        await session.delete(item)
        await session.commit()
    await state.clear()
    await message.answer("Element o'chirildi.", reply_markup=admin_panel_keyboard())


@router.message(AdminStates.waiting_for_broadcast_message)
async def admin_broadcast_message_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    mode = data.get("broadcast_mode")
    if mode == "now":
        async with AsyncSessionLocal() as session:
            delivered = await run_broadcast_now(session, bot, message.text)
        await state.clear()
        await message.answer(f"Broadcast yuborildi. Yetkazildi: {delivered}", reply_markup=admin_panel_keyboard())
        return
    await state.update_data(broadcast_message=message.text)
    await state.set_state(AdminStates.waiting_for_broadcast_schedule)
    await message.answer("Yuborish vaqtini `YYYY-MM-DD HH:MM` formatida yuboring.")


@router.message(AdminStates.waiting_for_broadcast_schedule)
async def admin_broadcast_schedule_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text or not is_admin(message.from_user.id):
        return
    try:
        scheduled_at = parse_admin_datetime(message.text)
    except ValueError:
        await message.answer("Vaqt formati xato. `YYYY-MM-DD HH:MM` ko'rinishida yuboring.")
        return
    if scheduled_at is None:
        await message.answer("Scheduled broadcast uchun vaqt majburiy.")
        return
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        await create_scheduled_broadcast(session, message_text=data["broadcast_message"], scheduled_at=scheduled_at)
    await state.clear()
    await message.answer("Scheduled broadcast saqlandi.", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data.startswith("quiz_start:"))
async def quiz_start_callback(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    ready = await ensure_user_ready(callback.message, bot, state, telegram_user_id=callback.from_user.id)
    if not ready:
        await callback.answer()
        return

    test_id = int(callback.data.split(":", 1)[1])
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        test = await get_test_by_id(session, test_id)
        if test is None or not test.is_active or test.closed_at is not None or (test.scheduled_end_at and test.scheduled_end_at <= datetime.now(timezone.utc)):
            await callback.message.answer("❌ Test topilmadi yoki yopilgan.")
            await callback.answer()
            return
        if not user_can_take_test(user, test):
            await callback.message.answer(
                f"🚫 {t(user.language, 'test_locked', minimum=test.min_referrals, count=user.invited_users_count)}",
                reply_markup=main_menu_keyboard(user.language),
            )
            await callback.answer()
            return
        attempt = await get_or_create_attempt(session, user, test)
        if attempt.status == "completed":
            await callback.message.answer("♻️ Siz bu testni allaqachon ishlab bo'lgansiz.")
            await callback.answer()
            return
        if attempt.active_polls:
            await callback.message.answer("⏳ Sizga savol yuborilgan. Avval o'sha savolga javob bering.")
            await callback.answer()
            return
        await callback.message.answer(
            f"🚀 <b>{test.title}</b> testi boshlandi.\n"
            f"⏱ Har savol uchun {test.question_time_limit} soniya.\n"
            "🔀 Savollar va variantlar aralash tartibda keladi.",
            reply_markup=main_menu_keyboard(user.language),
        )
        await start_quiz_attempt(session, bot, attempt)
    await callback.answer("Test boshlandi ✅")


@router.poll_answer()
async def poll_answer_handler(answer: PollAnswer, bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        await handle_poll_answer(session, bot, answer)


@router.message(StateFilter(None), F.text)
async def menu_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user:
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            return
        menu_key = resolve_menu_key(user.language, message.text)
        if menu_key is None:
            return

    if menu_key == "invite":
        async with AsyncSessionLocal() as session:
            user = await get_user_by_telegram_id(session, message.from_user.id)
            settings = get_settings()
            link = f"https://t.me/{settings.bot_username}?start={user.referral_code}"
            custom_caption = await get_referral_share_text(session)
            custom_media = await get_referral_share_media_path(session)
            invite_text = t(
                user.language,
                "invite_text",
                link=link,
                count=user.invited_users_count,
                score=user.referral_score,
            )
            if custom_caption:
                invite_text = f"{invite_text}\n\n{t(user.language, 'invite_share_caption', caption=custom_caption)}"
            share_text = custom_caption or t(user.language, "invite_share_default")
            share_url = build_referral_share_url(link, share_text)
            if custom_media and Path(custom_media).exists():
                await message.answer_photo(FSInputFile(custom_media), caption=invite_text, reply_markup=main_menu_keyboard(user.language))
            else:
                await message.answer(invite_text, reply_markup=main_menu_keyboard(user.language))
            await message.answer(
                f"📨 {t(user.language, 'invite_share_prompt')}",
                reply_markup=referral_share_keyboard(share_url, t(user.language, "invite_share_button")),
            )
        return

    ready = await ensure_user_ready(message, bot, state)
    if not ready:
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if menu_key == "test":
            tests = await get_active_tests(session)
            if not tests:
                await message.answer("🛑 Hozircha faol test yo'q.", reply_markup=main_menu_keyboard(user.language))
                return
            available = []
            blocked_messages = []
            for test in tests:
                if user_can_take_test(user, test):
                    available.append(
                        {
                            "id": test.id,
                            "text": f"📝 {test.title} | ID: {test.test_code} | ⏱ {test.question_time_limit}s",
                        }
                    )
                else:
                    blocked_messages.append(
                        f"🔒 {test.title}: kamida {test.min_referrals} ta referral kerak. Sizda {user.invited_users_count} ta."
                    )
            if available:
                await message.answer(
                    "🧪 Testni tanlang. Savollar ketma-ket quiz ko'rinishida keladi:",
                    reply_markup=test_selection_keyboard(available),
                )
            if blocked_messages:
                await message.answer("\n".join(blocked_messages), reply_markup=main_menu_keyboard(user.language))
            return
        if menu_key == "results":
            test_rankings = await get_test_rankings(session)
            referral_rankings = await get_referral_rankings(session)
            my_test_rank = next((item for item in test_rankings if item["user_id"] == user.id), None)
            my_referral_rank = next((item for item in referral_rankings if item["user_id"] == user.id), None)
            test_leader = test_rankings[0] if test_rankings else None
            referral_leader = referral_rankings[0] if referral_rankings else None
            test_score = await get_total_test_score(session, user.id)
            await message.answer(
                format_results_message(
                    user.language,
                    my_test_rank=my_test_rank,
                    test_leader=test_leader,
                    my_referral_rank=my_referral_rank,
                    referral_leader=referral_leader,
                    test_score=test_score,
                    referral_score=user.referral_score,
                ),
                reply_markup=main_menu_keyboard(user.language),
            )
            return
        if menu_key == "leaderboard":
            referral_rankings = await get_referral_rankings(session)
            tests = await get_all_tests(session)
            first_message = True
            for chunk in build_referral_leaderboard_messages(user.language, referral_rankings):
                await message.answer(
                    chunk,
                    reply_markup=main_menu_keyboard(user.language) if first_message else None,
                )
                first_message = False
            for test in tests:
                test_rankings = await get_rankings_for_single_test(session, test.id)
                for chunk in build_test_leaderboard_messages(user.language, test=test, rankings=test_rankings):
                    await message.answer(chunk)
            return
        if menu_key == "cabinet":
            test_rankings = await get_test_rankings(session)
            referral_rankings = await get_referral_rankings(session)
            my_test_rank = next((item for item in test_rankings if item["user_id"] == user.id), None)
            my_referral_rank = next((item for item in referral_rankings if item["user_id"] == user.id), None)
            test_score = await get_total_test_score(session, user.id)
            stmt = (
                select(TestAttempt)
                .options(selectinload(TestAttempt.test))
                .where(TestAttempt.user_id == user.id)
                .order_by(TestAttempt.id.desc())
                .limit(5)
            )
            attempts = list((await session.scalars(stmt)).all())
            await message.answer(
                format_cabinet_message(
                    user.language,
                    user=user,
                    test_score=test_score,
                    my_test_rank=my_test_rank,
                    my_referral_rank=my_referral_rank,
                    attempts=attempts,
                ),
                reply_markup=main_menu_keyboard(user.language),
            )
            return
        if menu_key == "rules":
            rules = await get_active_rules(session)
            if not rules:
                await message.answer(f"📘 {t(user.language, 'rules_empty')}")
                return
            for rule in rules:
                text = f"📘 <b>{escape(rule.title)}</b>\n\n{escape(rule.content)}"
                if rule.media_path and Path(rule.media_path).exists() and Path(rule.media_path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    await message.answer_photo(FSInputFile(rule.media_path), caption=text)
                else:
                    await message.answer(text)
                    if rule.media_path:
                        await send_attachment(message, rule.media_path)
                if rule.file_path:
                    await send_attachment(message, rule.file_path)
            return
        if menu_key == "books":
            books = await get_active_books(session)
            if not books:
                await message.answer(f"📚 {t(user.language, 'books_empty')}")
                return
            for book in books:
                text = f"📚 <b>{escape(book.title)}</b>\n\n{escape(book.content)}"
                if book.media_path and Path(book.media_path).exists() and Path(book.media_path).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                    await message.answer_photo(FSInputFile(book.media_path), caption=text)
                else:
                    await message.answer(text)
                    if book.media_path:
                        await send_attachment(message, book.media_path)
                if book.file_path:
                    await send_attachment(message, book.file_path)
            return
        if menu_key == "question":
            await state.set_state(SupportStates.waiting_for_user_ticket)
            await message.answer(t(user.language, "support_prompt"))
            return


@router.message(SupportStates.waiting_for_user_ticket)
async def support_ticket_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user:
        return

    text = message.text or message.caption
    media_file_id = None
    media_type = None

    if message.photo:
        photo: PhotoSize = message.photo[-1]
        media_file_id = photo.file_id
        media_type = "photo"
    elif message.document:
        document: Document = message.document
        media_file_id = document.file_id
        media_type = "document"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Avval /start yuboring.")
            return
        ticket = await create_ticket(session, user.id, text, media_file_id, media_type)
        await state.clear()

        full_name = (
            f"{user.profile.first_name} {user.profile.last_name}" if user.profile else user.telegram_first_name or "Foydalanuvchi"
        )
        admin_text = (
            f"Yangi savol #{ticket.id}\n"
            f"Ism: {full_name}\n"
            f"Telegram: <a href='tg://user?id={user.telegram_id}'>Profilni ochish</a>\n"
            f"Telegram ID: {user.telegram_id}\n"
            f"Telefon: {user.phone_number or 'yoq'}\n\n"
            f"Matn: {text or 'Matn yoq'}"
        )

        settings = get_settings()
        for admin_id in settings.admin_id_list:
            try:
                if media_type == "photo" and media_file_id:
                    await bot.send_photo(admin_id, media_file_id, caption=admin_text, reply_markup=admin_ticket_actions(ticket.id))
                elif media_type == "video" and media_file_id:
                    await bot.send_video(admin_id, media_file_id, caption=admin_text, reply_markup=admin_ticket_actions(ticket.id))
                elif media_type == "document" and media_file_id:
                    await bot.send_document(admin_id, media_file_id, caption=admin_text, reply_markup=admin_ticket_actions(ticket.id))
                else:
                    await bot.send_message(admin_id, admin_text, reply_markup=admin_ticket_actions(ticket.id))
            except Exception:
                continue

    await message.answer(t(user.language, "support_sent"), reply_markup=main_menu_keyboard(user.language))


@router.callback_query(F.data.startswith("ticket_answer:"))
async def ticket_answer_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user:
        return
    settings = get_settings()
    if callback.from_user.id not in settings.admin_id_list:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    ticket_id = int(callback.data.split(":")[1])
    await state.set_state(SupportStates.waiting_for_admin_reply)
    await state.update_data(ticket_id=ticket_id)
    await callback.message.answer(f"#{ticket_id} savol uchun javob matnini yuboring.")
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_reject:"))
async def ticket_reject_callback(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user:
        return
    settings = get_settings()
    if callback.from_user.id not in settings.admin_id_list:
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return
    ticket_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        ticket = await reject_ticket(session, ticket_id, "Savolingiz admin tomonidan rad etildi.")
        if ticket:
            await bot.send_message(ticket.user.telegram_id, t(ticket.user.language, "support_rejected"))
    await callback.answer("Savol rad etildi.")


@router.message(SupportStates.waiting_for_admin_reply)
async def ticket_admin_reply_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user or not message.text:
        return
    settings = get_settings()
    if message.from_user.id not in settings.admin_id_list:
        return
    data = await state.get_data()
    ticket_id = int(data["ticket_id"])
    async with AsyncSessionLocal() as session:
        ticket = await answer_ticket(session, ticket_id, message.text)
        if ticket:
            await bot.send_message(ticket.user.telegram_id, t(ticket.user.language, "admin_reply", reply=message.text))
    await state.clear()
    await message.answer("Javob foydalanuvchiga yuborildi.")
