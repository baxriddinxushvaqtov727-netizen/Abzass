from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_for_user_ticket = State()
    waiting_for_admin_reply = State()


class AdminStates(StatesGroup):
    waiting_for_channel_create = State()
    waiting_for_channel_delete = State()

    waiting_for_test_title = State()
    waiting_for_test_code = State()
    waiting_for_test_description = State()
    waiting_for_test_min_referrals = State()
    waiting_for_test_end_at = State()
    waiting_for_test_questions = State()
    waiting_for_test_close = State()
    waiting_for_test_delete = State()

    waiting_for_content_title = State()
    waiting_for_content_body = State()
    waiting_for_content_delete = State()

    waiting_for_broadcast_message = State()
    waiting_for_broadcast_schedule = State()
