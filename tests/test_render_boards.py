import io

import pytest
from PIL import Image

from bot.cf.models import Problem
from bot.render.daily import render_daily
from bot.render.leaderboard import render_leaderboard
from bot.services.leaderboard import LeaderboardRow


@pytest.mark.parametrize("kind", ["level", "rating", "solved", "streaks"])
def test_render_leaderboard(kind):
    rows = [LeaderboardRow(i, f"handle_number_{i}_that_is_quite_long", "Elite", str(i * 10)) for i in range(1, 8)]
    im = Image.open(io.BytesIO(render_leaderboard(kind, rows, 2, 5)))
    assert im.size == (974, 650)


def test_render_leaderboard_partial_rows():
    assert Image.open(io.BytesIO(render_leaderboard("level", [], 1, 1))).size == (974, 650)


def test_render_daily():
    problems = [
        Problem(1842, "B", "Tenzing and Books With A Really Long Problem Name Here", 900, ("bitmasks", "greedy", "math", "constructive algorithms", "implementation")),
        Problem(4, "A", "Watermelon", 1200, ("math",)),
        Problem(1, "A", "Theatre Square", 1600, ()),
    ]
    assert Image.open(io.BytesIO(render_daily(problems))).size == (974, 650)


def test_render_accepted():
    from decimal import Decimal

    from bot.render.accepted import AcceptedData, render_accepted
    from bot.render.fonts import ASSETS_DIR

    data = AcceptedData("cheviazt", "Rookie", Problem(1842, "B", "Tenzing and Books", 900, ("math", "greedy")), 90, Decimal("4.50"))
    template = Image.open(ASSETS_DIR / "acc.png").size
    assert Image.open(io.BytesIO(render_accepted(data))).size == template
    unrated = AcceptedData("h", "Elite", Problem(1, "A", "x", None, ()), 0, Decimal("0.00"))
    assert Image.open(io.BytesIO(render_accepted(unrated))).size == template
