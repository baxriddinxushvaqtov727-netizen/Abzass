from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.core.constants import REGIONS
from app.core.i18n import menu_texts, t


def required_channels_keyboard(channels: list[dict], language: str) -> InlineKeyboardMarkup:
    rows = []
    for channel in channels:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Obuna bo'lish: {channel['title']}",
                    url=channel["url"],
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(language, "obuna_check"), callback_data="check_subscriptions")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=button)] for button in menu_texts(language).values()]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def admin_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Javob yozish", callback_data=f"ticket_answer:{ticket_id}"),
                InlineKeyboardButton(text="Rad etish", callback_data=f"ticket_reject:{ticket_id}"),
            ]
        ]
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Kanallar", callback_data="admin:channels"),
                InlineKeyboardButton(text="Testlar", callback_data="admin:tests"),
            ],
            [
                InlineKeyboardButton(text="Nizom/Kitob", callback_data="admin:content"),
                InlineKeyboardButton(text="Broadcast", callback_data="admin:broadcast"),
            ],
            [InlineKeyboardButton(text="Referral izohi", callback_data="admin:referral_text")],
            [InlineKeyboardButton(text="Yangilash", callback_data="admin:home")],
        ]
    )


def admin_channels_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Kanal qo'shish", callback_data="admin:add_channel"),
                InlineKeyboardButton(text="Kanal o'chirish", callback_data="admin:delete_channel"),
            ],
            [
                InlineKeyboardButton(text="Ro'yxat", callback_data="admin:list_channels"),
                InlineKeyboardButton(text="Orqaga", callback_data="admin:home"),
            ],
        ]
    )


def admin_tests_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Test yaratish", callback_data="admin:add_test"),
                InlineKeyboardButton(text="Testlar ro'yxati", callback_data="admin:list_tests"),
            ],
            [
                InlineKeyboardButton(text="Testni yopish", callback_data="admin:close_test"),
                InlineKeyboardButton(text="Testni o'chirish", callback_data="admin:delete_test"),
            ],
            [InlineKeyboardButton(text="Orqaga", callback_data="admin:home")],
        ]
    )


def admin_content_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Nizom qo'shish", callback_data="admin:add_rule"),
                InlineKeyboardButton(text="Kitob qo'shish", callback_data="admin:add_book"),
            ],
            [
                InlineKeyboardButton(text="Nizomlar", callback_data="admin:list_rules"),
                InlineKeyboardButton(text="Kitoblar", callback_data="admin:list_books"),
            ],
            [
                InlineKeyboardButton(text="Nizom o'chirish", callback_data="admin:delete_rule"),
                InlineKeyboardButton(text="Kitob o'chirish", callback_data="admin:delete_book"),
            ],
            [InlineKeyboardButton(text="Orqaga", callback_data="admin:home")],
        ]
    )


def admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Hozir yuborish", callback_data="admin:broadcast_now"),
                InlineKeyboardButton(text="Rejalashtirish", callback_data="admin:broadcast_schedule"),
            ],
            [
                InlineKeyboardButton(text="Rejalar ro'yxati", callback_data="admin:list_broadcasts"),
                InlineKeyboardButton(text="Orqaga", callback_data="admin:home"),
            ],
        ]
    )


def regions_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for region in REGIONS.keys():
        current_row.append(InlineKeyboardButton(text=region, callback_data=f"reg_region:{region}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def classes_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for class_no in range(1, 12):
        current_row.append(InlineKeyboardButton(text=str(class_no), callback_data=f"reg_class:{class_no}"))
        if len(current_row) == 4:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_share_keyboard(share_url: str, button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=button_text, url=share_url)]]
    )
