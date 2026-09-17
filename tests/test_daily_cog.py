import discord

from bot.cf.models import Problem
from bot.cogs.daily import build_daily_view


async def test_daily_view_has_three_link_buttons():
    problems = [Problem(1, "A", "a", 900, ()), Problem(2, "B", "b", 1200, ()), Problem(3, "C", "c", 1600, ())]
    view = build_daily_view(problems)
    buttons = [c for c in view.children if isinstance(c, discord.ui.Button)]
    assert [b.label for b in buttons] == ["900", "1200", "1600"]
    assert buttons[0].url == "https://codeforces.com/problemset/problem/1/A"
    assert all(b.style is discord.ButtonStyle.link for b in buttons)
