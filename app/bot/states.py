from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_for_user_ticket = State()
    waiting_for_admin_reply = State()


class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_patronymic = State()
    waiting_for_region = State()
    waiting_for_district = State()
    waiting_for_school_class = State()


class AdminStates(StatesGroup):
    waiting_for_channel_create = State()
    waiting_for_channel_delete = State()
    waiting_for_referral_content = State()

    waiting_for_test_title = State()
    waiting_for_test_code = State()
    waiting_for_test_min_referrals = State()
    waiting_for_test_time_limit = State()
    waiting_for_test_end_at = State()
    waiting_for_test_question_text = State()
    waiting_for_test_options = State()
    waiting_for_test_correct_option = State()
    waiting_for_test_close = State()
    waiting_for_test_delete = State()

    waiting_for_content_title = State()
    waiting_for_content_body = State()
    waiting_for_content_delete = State()

    waiting_for_broadcast_message = State()
    waiting_for_broadcast_schedule = State()
