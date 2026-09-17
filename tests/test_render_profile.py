import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from PIL import Image

from bot.render.profile import ProfileData, format_last_seen, render_profile


def make_avatar() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "red").save(buf, "PNG")
    return buf.getvalue()


def test_render_profile_size():
    data = ProfileData(
        handle="tourist_with_a_very_long_handle_name", avatar=make_avatar(), level=42, rank_name="Specialist",
        exp_in_level=150, exp_need=4200, money=Decimal("123.45"), rating=3800, max_rating=4000,
        cf_rank="legendary grandmaster", last_seen="2h ago",
        last_solved=["1842B · Tenzing and Books With Extremely Long Title", "1A · Theatre Square", "4A · Watermelon"],
        solved_count=1234, streak=7,
    )
    png = render_profile(data)
    im = Image.open(io.BytesIO(png))
    assert im.size == (974, 650)


def test_render_profile_unrated_without_avatar():
    data = ProfileData("nb", None, 1, "Rookie", 0, 100, Decimal("0.00"), None, None, None, "just now", [], 0, 0)
    assert Image.open(io.BytesIO(render_profile(data))).size == (974, 650)


def test_format_last_seen():
    now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    assert format_last_seen(now - timedelta(seconds=30), now) == "just now"
    assert format_last_seen(now - timedelta(minutes=5), now) == "5m ago"
    assert format_last_seen(now - timedelta(hours=3), now) == "3h ago"
    assert format_last_seen(now - timedelta(days=2), now) == "2d ago"
