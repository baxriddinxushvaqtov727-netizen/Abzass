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
        "profile_prompt": "Ro'yxatdan o'tishni davom ettirish uchun ism, familiya, otasining ismi, viloyat, tuman va sinfni kiriting.",
        "start_ready": "Asosiy menyu ochildi.",
        "start_phone": "Telefon raqamingizni yuboring.",
        "subscriptions_needed": "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        "subscriptions_incomplete": "Hali barcha kanallarga obuna bo'linmagan.",
        "subscriptions_check_first": "Avval barcha majburiy kanallarga obuna bo'ling.",
        "subscription_verified": "Obuna tasdiqlandi. Endi telefon raqamingizni yuboring.",
        "contact_saved": "Telefon raqamingiz saqlandi.",
        "self_contact_only": "Faqat o'zingizning telefon raqamingizni yuboring.",
        "invite_text": "Taklif havolangiz:\n{link}\n\nTaklif qilgan foydalanuvchilar: {count}\nReferral ball: {score}\nUmumiy ball: {total}",
        "invite_share_default": "Tanlovda qatnashing. Quyidagi havola orqali ro'yxatdan o'ting:",
        "invite_share_caption": "Izoh:\n{caption}",
        "invite_share_prompt": "Tugmani bosib tanishlaringizga yuboring.",
        "invite_share_button": "Tanishlarga yuborish",
        "test_locked": "Test ishlash uchun kamida {minimum} ta do'st taklif qilishingiz kerak. Hozirgi son: {count}.",
        "test_open_prompt": "Testni `1234*ABCDA` yoki `1234*1a2b3c` formatida yuboring.",
        "results_title": "Natijalar",
        "results_place": "Sizning o'rningiz: {rank}",
        "results_score": "Sizning jami ochkoingiz: {score}",
        "results_test_score": "Test bali: {score}",
        "results_referral_score": "Referral bali: {score}",
        "results_leader": "1-o'rin: {name} - {score} ball",
        "results_unranked": "Siz hali reytingga kirmagansiz.",
        "cabinet_title": "Shaxsiy kabinet",
        "cabinet_name": "Ism: {value}",
        "cabinet_last_name": "Familiya: {value}",
        "cabinet_patronymic": "Otasining ismi: {value}",
        "cabinet_region": "Viloyat: {value}",
        "cabinet_district": "Tuman: {value}",
        "cabinet_class": "Sinf: {value}",
        "cabinet_phone": "Telefon: {value}",
        "cabinet_invited": "Taklif qilganlar soni: {count}",
        "cabinet_rank": "O'rningiz: {rank}",
        "cabinet_history_title": "Oxirgi testlar:",
        "cabinet_history_empty": "Hali test ishlamagansiz.",
        "rules_empty": "Hozircha tanlov nizomi joylanmagan.",
        "books_empty": "Hozircha tanlov kitoblari joylanmagan.",
        "support_prompt": "Savolingizni matn yoki media bilan yuboring.",
        "support_sent": "Savolingiz adminga yuborildi.",
        "support_rejected": "Savolingiz ko'rib chiqildi, lekin rad etildi.",
        "admin_reply": "Admin javobi:\n\n{reply}",
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
        "profile_prompt": "Рўйхатдан ўтишни давом эттириш учун исм, фамилия, отасининг исми, вилоят, туман ва синфни киритинг.",
        "start_ready": "Асосий меню очилди.",
        "start_phone": "Телефон рақамингизни юборинг.",
        "subscriptions_needed": "Ботдан фойдаланиш учун қуйидаги каналларга обуна бўлинг:",
        "subscriptions_incomplete": "Ҳали барча каналларга обуна бўлинмаган.",
        "subscriptions_check_first": "Аввал барча мажбурий каналларга обуна бўлинг.",
        "subscription_verified": "Обуна тасдиқланди. Энди телефон рақамингизни юборинг.",
        "contact_saved": "Телефон рақамингиз сақланди.",
        "self_contact_only": "Фақат ўзингизнинг телефон рақамингизни юборинг.",
        "invite_text": "Таклиф ҳаволангиз:\n{link}\n\nТаклиф қилган фойдаланувчилар: {count}\nReferral балл: {score}\nУмумий балл: {total}",
        "invite_share_default": "Танловда қатнашинг. Қуйидаги ҳавола орқали рўйхатдан ўтинг:",
        "invite_share_caption": "Изоҳ:\n{caption}",
        "invite_share_prompt": "Тугмани босиб танишларингизга юборинг.",
        "invite_share_button": "Танишларга юбориш",
        "test_locked": "Тест ишлаш учун камида {minimum} та дўст таклиф қилишингиз керак. Ҳозирги сон: {count}.",
        "test_open_prompt": "Тестни `1234*ABCDA` ёки `1234*1a2b3c` форматида юборинг.",
        "results_title": "Натижалар",
        "results_place": "Сизнинг ўрнингиз: {rank}",
        "results_score": "Сизнинг жами очконгиз: {score}",
        "results_test_score": "Тест бали: {score}",
        "results_referral_score": "Referral бали: {score}",
        "results_leader": "1-ўрин: {name} - {score} балл",
        "results_unranked": "Сиз ҳали рейтингга кирмагансиз.",
        "cabinet_title": "Шахсий кабинет",
        "cabinet_name": "Исм: {value}",
        "cabinet_last_name": "Фамилия: {value}",
        "cabinet_patronymic": "Отасининг исми: {value}",
        "cabinet_region": "Вилоят: {value}",
        "cabinet_district": "Туман: {value}",
        "cabinet_class": "Синф: {value}",
        "cabinet_phone": "Телефон: {value}",
        "cabinet_invited": "Таклиф қилганлар сони: {count}",
        "cabinet_rank": "Ўрнингиз: {rank}",
        "cabinet_history_title": "Охирги тестлар:",
        "cabinet_history_empty": "Ҳали тест ишламагансиз.",
        "rules_empty": "Ҳозирча танлов низоми жойланмаган.",
        "books_empty": "Ҳозирча танлов китоблари жойланмаган.",
        "support_prompt": "Саволингизни матн ёки медиа билан юборинг.",
        "support_sent": "Саволингиз админга юборилди.",
        "support_rejected": "Саволингиз кўриб чиқилди, лекин рад этилди.",
        "admin_reply": "Админ жавоби:\n\n{reply}",
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
        "profile_prompt": "Чтобы продолжить регистрацию, заполните имя, фамилию, отчество, область, район и класс.",
        "start_ready": "Главное меню открыто.",
        "start_phone": "Отправьте свой номер телефона.",
        "subscriptions_needed": "Чтобы пользоваться ботом, подпишитесь на следующие каналы:",
        "subscriptions_incomplete": "Подписка на все каналы еще не подтверждена.",
        "subscriptions_check_first": "Сначала подпишитесь на все обязательные каналы.",
        "subscription_verified": "Подписка подтверждена. Теперь отправьте номер телефона.",
        "contact_saved": "Номер телефона сохранен.",
        "self_contact_only": "Отправьте только свой номер телефона.",
        "invite_text": "Ваша ссылка:\n{link}\n\nПриглашено пользователей: {count}\nReferral баллы: {score}\nОбщий балл: {total}",
        "invite_share_default": "Участвуйте в конкурсе. Зарегистрируйтесь по ссылке ниже:",
        "invite_share_caption": "Комментарий:\n{caption}",
        "invite_share_prompt": "Нажмите кнопку и отправьте выбранным контактам.",
        "invite_share_button": "Отправить друзьям",
        "test_locked": "Для доступа к тесту нужно пригласить минимум {minimum} друзей. Сейчас: {count}.",
        "test_open_prompt": "Отправьте тест в формате `1234*ABCDA` или `1234*1a2b3c`.",
        "results_title": "Результаты",
        "results_place": "Ваше место: {rank}",
        "results_score": "Ваш общий балл: {score}",
        "results_test_score": "Баллы за тест: {score}",
        "results_referral_score": "Referral баллы: {score}",
        "results_leader": "1-е место: {name} - {score} баллов",
        "results_unranked": "Вы пока не вошли в рейтинг.",
        "cabinet_title": "Личный кабинет",
        "cabinet_name": "Имя: {value}",
        "cabinet_last_name": "Фамилия: {value}",
        "cabinet_patronymic": "Отчество: {value}",
        "cabinet_region": "Область: {value}",
        "cabinet_district": "Район: {value}",
        "cabinet_class": "Класс: {value}",
        "cabinet_phone": "Телефон: {value}",
        "cabinet_invited": "Количество приглашённых: {count}",
        "cabinet_rank": "Ваше место: {rank}",
        "cabinet_history_title": "Последние тесты:",
        "cabinet_history_empty": "Вы ещё не проходили тесты.",
        "rules_empty": "Положение конкурса пока не опубликовано.",
        "books_empty": "Книги конкурса пока не опубликованы.",
        "support_prompt": "Отправьте вопрос текстом или медиа.",
        "support_sent": "Ваш вопрос отправлен администратору.",
        "support_rejected": "Ваш вопрос рассмотрен, но отклонен.",
        "admin_reply": "Ответ администратора:\n\n{reply}",
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
