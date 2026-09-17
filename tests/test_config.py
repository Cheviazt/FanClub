from bot.config import Settings, WIB


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "tok")
    monkeypatch.setenv("GUILD_ID", "123")
    monkeypatch.setenv("NOTIFY_CHANNEL_ID", "456")
    s = Settings(_env_file=None)
    assert s.discord_token == "tok"
    assert s.guild_id == 123
    assert s.notify_channel_id == 456
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.tz == "Asia/Jakarta"


def test_wib_zone():
    assert str(WIB) == "Asia/Jakarta"
