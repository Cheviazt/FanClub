from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

WIB = ZoneInfo("Asia/Jakarta")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_token: str
    guild_id: int
    notify_channel_id: int
    database_url: str = "postgresql+asyncpg://bot:bot@db:5432/bot"
    tz: str = "Asia/Jakarta"
    log_level: str = "INFO"
    data_dir: str = "data"
    reminder_channel_id: int | None = None
    contest_channel_id: int | None = None
    reset_keep_role_ids: str = "1492609991717163230,1492610204611907644,1492609581740851353,1492608389413474324,1492607678948708548"

    @property
    def keep_role_ids(self) -> set[int]:
        return {int(part) for part in self.reset_keep_role_ids.split(",") if part.strip()}
