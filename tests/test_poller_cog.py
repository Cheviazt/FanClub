import asyncio
import logging
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.cf.client import CodeforcesError
from bot.cf.models import Problem, UserInfo
from bot.cogs.poller import PollerCog, accepted_data, accepted_view
from bot.db.repo import cf_cache, users
from bot.services.solve_processor import SolveResult


def test_accepted_data_maps_result():
    r = SolveResult(1, "tourist", Problem(1842, "B", "Tenzing", 900, ()), 90, Decimal("4.50"), 1, 2, "Rookie", "Elite", 3)
    data = accepted_data(r)
    assert data.handle == "tourist" and data.rank_name == "Elite"
    assert data.exp_gained == 90 and data.money_gained == Decimal("4.50") and data.problem.code == "1842B"


async def test_accepted_view_links_to_problem():
    r = SolveResult(1, "h", Problem(1, "A", "x", None, ()), 0, Decimal("0.00"), 1, 1, "Rookie", "Rookie", 1)
    view = accepted_view(r)
    button = view.children[0]
    assert button.label == "Open 1A" and button.url == "https://codeforces.com/problemset/problem/1/A"


async def test_reset_broken_streaks(session_factory):
    async with session_factory() as s:
        a = await users.create_user(s, 1, "a")
        a.streak = 5
        a.last_solve_date = date(2026, 9, 10)
        b = await users.create_user(s, 2, "b")
        b.streak = 2
        b.last_solve_date = date(2026, 9, 15)
        await s.commit()
    bot = MagicMock()
    bot.session_factory = session_factory
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    assert await cog.reset_broken_streaks(date(2026, 9, 16)) == 1
    async with session_factory() as s:
        assert (await users.get_by_discord(s, 1)).streak == 0
        assert (await users.get_by_discord(s, 2)).streak == 2


async def test_wait_ready_serializes_role_creation(session_factory):
    bot = MagicMock()
    bot.session_factory = session_factory
    bot.settings.guild_id = 10
    bot.wait_until_ready = AsyncMock()

    guild = MagicMock()
    guild.id = 10
    guild.roles = []

    async def _create_role(name, colour, reason):
        await asyncio.sleep(0)
        role = MagicMock()
        role.id = len(guild.roles) + 1
        role.name = name
        guild.roles.append(role)
        return role

    guild.create_role = AsyncMock(side_effect=_create_role)
    bot.get_guild = MagicMock(return_value=guild)

    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    cog.role_ids = {}
    cog._roles_lock = asyncio.Lock()

    await asyncio.gather(cog.wait_ready(), cog.wait_ready(), cog.wait_ready(), cog.wait_ready())

    assert guild.create_role.await_count == 8
    assert len(cog.role_ids) == 8


async def test_wait_ready_survives_role_setup_failure(session_factory):
    bot = MagicMock()
    bot.session_factory = session_factory
    bot.settings.guild_id = 10
    bot.wait_until_ready = AsyncMock()
    guild = MagicMock()
    guild.id = 10
    guild.roles = []
    guild.create_role = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "missing permissions"))
    bot.get_guild = MagicMock(return_value=guild)

    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    cog.role_ids = {}
    cog._roles_lock = asyncio.Lock()

    await cog.wait_ready()

    assert cog.role_ids == {}


async def test_refresh_cf_cache_falls_back_per_handle(session_factory):
    async with session_factory() as s:
        await users.create_user(s, 1, "good")
        await users.create_user(s, 2, "gone")
        await s.commit()
    good = UserInfo("good", 1500, 1600, "specialist", "expert", 1, "https://a/b.png")

    async def fake_user_info(handles):
        if len(handles) > 1:
            raise CodeforcesError("handles: User with handle gone not found")
        if handles == ["good"]:
            return [good]
        raise CodeforcesError("handles: User with handle gone not found")

    bot = MagicMock()
    bot.session_factory = session_factory
    bot.cf.user_info = AsyncMock(side_effect=fake_user_info)
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot

    await PollerCog.refresh_cf_cache.coro(cog)

    assert bot.cf.user_info.await_count == 3
    async with session_factory() as s:
        assert (await cf_cache.get_cf_cache(s, 1)).rating == 1500
        assert await cf_cache.get_cf_cache(s, 2) is None


async def test_apply_side_effects_warns_when_channel_missing(caplog):
    bot = MagicMock()
    bot.settings.guild_id = 10
    bot.settings.notify_channel_id = 555
    bot.get_guild = MagicMock(return_value=None)
    bot.get_channel = MagicMock(return_value=None)
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    cog.role_ids = {}
    r = SolveResult(1, "h", Problem(1, "A", "x", None, ()), 0, Decimal("0.00"), 1, 1, "Rookie", "Rookie", 1)

    with caplog.at_level(logging.WARNING, logger="bot.cogs.poller"):
        await cog.apply_side_effects(r)

    assert "notify channel 555 not found" in caplog.text


async def test_apply_batch_side_effects_sends_one_summary():
    bot = MagicMock()
    bot.settings.guild_id = 10
    bot.settings.notify_channel_id = 555
    bot.get_guild = MagicMock(return_value=None)
    channel = MagicMock()
    channel.send = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel)
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    cog.role_ids = {}
    results = [
        SolveResult(1, "h", Problem(i, "A", "x", 900, ()), 90, Decimal("4.50"), 1, 1, "Rookie", "Rookie", 1)
        for i in range(1, 8)
    ]
    await cog.apply_batch_side_effects(results)
    channel.send.assert_awaited_once()
    text = channel.send.await_args.args[0]
    assert "solved 7 problems" in text and "+630 EXP" in text and "+$31.50" in text
