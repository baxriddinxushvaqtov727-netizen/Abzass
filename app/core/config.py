from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Contest Bot Platform"
    bot_token: str = Field(alias="BOT_TOKEN")
    bot_username: str = Field(alias="BOT_USERNAME")
    database_url: str = Field(default="sqlite+aiosqlite:///./app.db", alias="DATABASE_URL")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    run_bot: bool = Field(default=True, alias="RUN_BOT")
    app_timezone: str = Field(default="Asia/Samarkand", alias="APP_TIMEZONE")
    upload_dir: str = "uploads"

    @property
    def admin_id_list(self) -> list[int]:
        return [int(item.strip()) for item in self.admin_ids.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
