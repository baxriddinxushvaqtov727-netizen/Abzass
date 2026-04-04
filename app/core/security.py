from itsdangerous import URLSafeSerializer

from app.core.config import get_settings


TOKEN_SALT = "telegram-webapp-auth"


def build_serializer() -> URLSafeSerializer:
    settings = get_settings()
    return URLSafeSerializer(settings.secret_key, salt=TOKEN_SALT)


def create_user_token(telegram_id: int) -> str:
    serializer = build_serializer()
    return serializer.dumps({"telegram_id": telegram_id})


def parse_user_token(token: str) -> int:
    serializer = build_serializer()
    data = serializer.loads(token)
    return int(data["telegram_id"])
