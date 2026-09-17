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
