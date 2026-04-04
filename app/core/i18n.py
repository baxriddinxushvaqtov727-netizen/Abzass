from __future__ import annotations

from app.core.constants import LANGUAGES, MENU_KEYS


TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz_latin": {
        "menu.cabinet": "Shaxsiy kabinet",
        "menu.invite": "Do'stlarni taklif qilish",
        "menu.test": "Testda qatnashish",
        "menu.results": "Natijalar",
        "menu.rules": "Tanlov nizomi",
        "menu.books": "Tanlov kitoblari",
        "menu.question": "Savol yuborish",
        "profile_prompt": "Ro'yxatdan o'tishni davom ettirish uchun Web App oynasini oching va ism, familiya, otasining ismi, viloyat hamda sinfni kiriting.",
        "start_ready": "Asosiy menyu ochildi.",
        "start_phone": "Telefon raqamingizni yuboring.",
        "subscriptions_needed": "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        "subscriptions_incomplete": "Hali barcha kanallarga obuna bo'linmagan.",
        "subscriptions_check_first": "Avval barcha majburiy kanallarga obuna bo'ling.",
        "subscription_verified": "Obuna tasdiqlandi. Endi telefon raqamingizni yuboring.",
        "contact_saved": "Telefon raqamingiz saqlandi.",
        "self_contact_only": "Faqat o'zingizning telefon raqamingizni yuboring.",
        "invite_text": "Taklif havolangiz:\n{link}\n\nTaklif qilgan foydalanuvchilar: {count}\nReferral ball: {score}\nUmumiy ball: {total}",
        "test_locked": "Test ishlash uchun kamida {minimum} ta do'st taklif qilishingiz kerak. Hozirgi son: {count}.",
        "test_open_prompt": "Web Appni oching, test ID ni kiriting va testni ishlang.",
        "results_prompt": "Natijalarni Web App orqali ko'rishingiz mumkin.",
        "cabinet_prompt": "Shaxsiy kabinetni Web App orqali ochishingiz mumkin.",
        "rules_empty": "Hozircha tanlov nizomi joylanmagan.",
        "books_empty": "Hozircha tanlov kitoblari joylanmagan.",
        "support_prompt": "Savolingizni matn yoki media bilan yuboring.",
        "support_sent": "Savolingiz adminga yuborildi.",
        "support_rejected": "Savolingiz ko'rib chiqildi, lekin rad etildi.",
        "admin_reply": "Admin javobi:\n\n{reply}",
        "open_profile": "Ma'lumotlarni kiritish",
        "open_webapp": "Web Appni ochish",
        "open_tests": "Test oynasini ochish",
        "open_results": "Natijalarni ochish",
        "open_cabinet": "Kabinetni ochish",
        "obuna_check": "Obunani tekshirish",
    },
    "uz_cyrillic": {
        "menu.cabinet": "Шахсий кабинет",
        "menu.invite": "Дўстларни таклиф қилиш",
        "menu.test": "Тестда қатнашиш",
        "menu.results": "Натижалар",
        "menu.rules": "Танлов низоми",
        "menu.books": "Танлов китоблари",
        "menu.question": "Савол юбориш",
        "profile_prompt": "Рўйхатдан ўтишни давом эттириш учун Web App ойнасини очинг ва исм, фамилия, отасининг исми, вилоят ҳамда синфни киритинг.",
        "start_ready": "Асосий меню очилди.",
        "start_phone": "Телефон рақамингизни юборинг.",
        "subscriptions_needed": "Ботдан фойдаланиш учун қуйидаги каналларга обуна бўлинг:",
        "subscriptions_incomplete": "Ҳали барча каналларга обуна бўлинмаган.",
        "subscriptions_check_first": "Аввал барча мажбурий каналларга обуна бўлинг.",
        "subscription_verified": "Обуна тасдиқланди. Энди телефон рақамингизни юборинг.",
        "contact_saved": "Телефон рақамингиз сақланди.",
        "self_contact_only": "Фақат ўзингизнинг телефон рақамингизни юборинг.",
        "invite_text": "Таклиф ҳаволангиз:\n{link}\n\nТаклиф қилган фойдаланувчилар: {count}\nReferral балл: {score}\nУмумий балл: {total}",
        "test_locked": "Тест ишлаш учун камида {minimum} та дўст таклиф қилишингиз керак. Ҳозирги сон: {count}.",
        "test_open_prompt": "Web Appни очинг, тест ID ни киритинг ва тестни ишланг.",
        "results_prompt": "Натижаларни Web App орқали кўришингиз мумкин.",
        "cabinet_prompt": "Шахсий кабинетни Web App орқали очишингиз мумкин.",
        "rules_empty": "Ҳозирча танлов низоми жойланмаган.",
        "books_empty": "Ҳозирча танлов китоблари жойланмаган.",
        "support_prompt": "Саволингизни матн ёки медиа билан юборинг.",
        "support_sent": "Саволингиз админга юборилди.",
        "support_rejected": "Саволингиз кўриб чиқилди, лекин рад этилди.",
        "admin_reply": "Админ жавоби:\n\n{reply}",
        "open_profile": "Маълумотларни киритиш",
        "open_webapp": "Web Appни очиш",
        "open_tests": "Тест ойнасини очиш",
        "open_results": "Натижаларни очиш",
        "open_cabinet": "Кабинетни очиш",
        "obuna_check": "Обуна текшириш",
    },
    "ru": {
        "menu.cabinet": "Личный кабинет",
        "menu.invite": "Пригласить друзей",
        "menu.test": "Участвовать в тесте",
        "menu.results": "Результаты",
        "menu.rules": "Положение конкурса",
        "menu.books": "Книги конкурса",
        "menu.question": "Отправить вопрос",
        "profile_prompt": "Чтобы продолжить регистрацию, откройте Web App и заполните имя, фамилию, отчество, область и класс.",
        "start_ready": "Главное меню открыто.",
        "start_phone": "Отправьте свой номер телефона.",
        "subscriptions_needed": "Чтобы пользоваться ботом, подпишитесь на следующие каналы:",
        "subscriptions_incomplete": "Подписка на все каналы еще не подтверждена.",
        "subscriptions_check_first": "Сначала подпишитесь на все обязательные каналы.",
        "subscription_verified": "Подписка подтверждена. Теперь отправьте номер телефона.",
        "contact_saved": "Номер телефона сохранен.",
        "self_contact_only": "Отправьте только свой номер телефона.",
        "invite_text": "Ваша ссылка:\n{link}\n\nПриглашено пользователей: {count}\nReferral баллы: {score}\nОбщий балл: {total}",
        "test_locked": "Для доступа к тесту нужно пригласить минимум {minimum} друзей. Сейчас: {count}.",
        "test_open_prompt": "Откройте Web App, введите ID теста и пройдите тест.",
        "results_prompt": "Результаты доступны в Web App.",
        "cabinet_prompt": "Личный кабинет доступен в Web App.",
        "rules_empty": "Положение конкурса пока не опубликовано.",
        "books_empty": "Книги конкурса пока не опубликованы.",
        "support_prompt": "Отправьте вопрос текстом или медиа.",
        "support_sent": "Ваш вопрос отправлен администратору.",
        "support_rejected": "Ваш вопрос рассмотрен, но отклонен.",
        "admin_reply": "Ответ администратора:\n\n{reply}",
        "open_profile": "Заполнить данные",
        "open_webapp": "Открыть Web App",
        "open_tests": "Открыть тест",
        "open_results": "Открыть результаты",
        "open_cabinet": "Открыть кабинет",
        "obuna_check": "Проверить подписку",
    },
}


def normalize_language(language: str | None) -> str:
    if language in LANGUAGES:
        return language
    return "uz_latin"


def t(language: str | None, key: str, **kwargs: object) -> str:
    lang = normalize_language(language)
    value = TRANSLATIONS.get(lang, TRANSLATIONS["uz_latin"]).get(key, key)
    if kwargs:
        return value.format(**kwargs)
    return value


def menu_texts(language: str | None) -> dict[str, str]:
    lang = normalize_language(language)
    return {key: t(lang, f"menu.{key}") for key in MENU_KEYS}


def resolve_menu_key(language: str | None, text: str | None) -> str | None:
    if not text:
        return None
    normalized = text.strip()
    for lang in LANGUAGES:
        for key, label in menu_texts(lang).items():
            if normalized == label:
                return key
    for key, label in menu_texts(language).items():
        if normalized == label:
            return key
    return None
