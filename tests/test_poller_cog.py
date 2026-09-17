from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from bot.cf.models import Problem
from bot.cogs.poller import PollerCog, format_solve_notification
from bot.db.repo import users
from bot.services.solve_processor import SolveResult


def test_format_solve_notification():
    r = SolveResult(1, "tourist", Problem(1842, "B", "Tenzing", 900, ()), 90, Decimal("4.50"), 1, 1, "Rookie", "Rookie", 3)
    text = format_solve_notification(r)
    assert "**tourist**" in text and "[1842B - Tenzing](https://codeforces.com/problemset/problem/1842/B)" in text
    assert "rating 900" in text and "+90 EXP" in text and "+$4.50" in text


def test_format_unrated_notification():
    r = SolveResult(1, "h", Problem(1, "A", "x", None, ()), 0, Decimal("0.00"), 1, 1, "Rookie", "Rookie", 1)
    text = format_solve_notification(r)
    assert "(unrated)" in text and "+0 EXP" in text and "+$0.00" in text


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
