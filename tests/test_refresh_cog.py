from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from bot.cf.models import Problem, Submission, UserInfo
from bot.cogs.refresh import can_refresh, is_allowed, refresh_user
from bot.db.repo import cf_cache, solved, users
from bot.services.avatars import AvatarCache


def test_is_allowed():
    assert is_allowed(1, 1, manage_guild=False) is True
    assert is_allowed(1, 2, manage_guild=False) is False
    assert is_allowed(1, 2, manage_guild=True) is True


def test_can_refresh_cooldown():
    last: dict[int, float] = {}
    assert can_refresh(last, 1, 100.0) is True
    last[1] = 100.0
    assert can_refresh(last, 1, 130.0) is False
    assert can_refresh(last, 1, 160.0) is True
    assert can_refresh(last, 2, 130.0) is True


def make_bot(session_factory, tmp_path, accepted):
    bot = MagicMock()
    bot.session_factory = session_factory
    bot.avatars = AvatarCache(tmp_path / "avatars")
    bot.cf.user_info = AsyncMock(return_value=[UserInfo("tourist", 3800, 4000, "legendary grandmaster", "lgm", 1700000000, "https://x/y.png")])
    bot.cf.fetch_bytes = AsyncMock(return_value=b"jpg")
    bot.register_service.fetch_all_accepted = AsyncMock(return_value=accepted)
    poller = MagicMock()
    poller.apply_side_effects = AsyncMock()
    poller.role_ids = {}
    bot.get_cog = MagicMock(return_value=poller)
    bot.get_guild = MagicMock(return_value=None)
    return bot, poller


async def test_refresh_user_updates_cache_and_awards_missed_solves(session_factory, tmp_path):
    async with session_factory() as s:
        await users.create_user(s, 1, "tourist")
        await s.commit()
    accepted = [Submission(1, Problem(1, "A", "x", 900, ()), "OK", 10), Submission(2, Problem(2, "B", "y", 1200, ()), "OK", 20)]
    bot, poller = make_bot(session_factory, tmp_path, accepted)
    report = await refresh_user(bot, 1, date(2026, 9, 16))
    assert report.handle == "tourist" and report.rating == 3800 and report.new_solves == 2 and report.level == 2
    assert poller.apply_side_effects.await_count == 2
    assert bot.avatars.load(1) == b"jpg"
    async with session_factory() as s:
        assert (await cf_cache.get_cf_cache(s, 1)).rating == 3800
        assert await solved.solved_count(s, 1) == 2
        assert (await users.get_by_discord(s, 1)).money == Decimal("10.50")


async def test_refresh_user_unregistered_returns_none(session_factory, tmp_path):
    bot, _ = make_bot(session_factory, tmp_path, [])
    assert await refresh_user(bot, 99, date(2026, 9, 16)) is None
    bot.cf.user_info.assert_not_awaited()
