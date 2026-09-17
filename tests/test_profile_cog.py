from datetime import datetime, timedelta, timezone
from decimal import Decimal

from bot.cf.models import Problem, UserInfo
from bot.cogs.profile import build_profile_data
from bot.db.repo import cf_cache, problemset, solved, users

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


async def test_build_profile_data(session):
    user = await users.create_user(session, 1, "tourist")
    user.exp = 450
    user.money = Decimal("12.50")
    user.streak = 3
    await cf_cache.upsert_cf_cache(session, 1, UserInfo("tourist", 3800, 4000, "legendary grandmaster", "lgm", int(NOW.timestamp()) - 7200, "https://x/y.png"), NOW)
    await problemset.replace_problemset(session, [Problem(1, "A", "Theatre Square", 1000, ())], NOW)
    await solved.add_solved(session, 1, 1, "A", NOW - timedelta(hours=2))
    await solved.add_solved(session, 1, 99, "Z", datetime(2020, 1, 1, tzinfo=timezone.utc))
    await session.commit()
    result = await build_profile_data(session, user, b"avatar", NOW)
    assert result.level == 3 and result.exp_in_level == 150 and result.exp_need == 300
    assert result.rank_name == "Rookie"
    assert result.rating == 3800 and result.cf_rank == "legendary grandmaster"
    assert result.last_seen == "2h ago"
    assert result.last_solved == ["1A · Theatre Square", "99Z"]
    assert result.solved_count == 2 and result.streak == 3


async def test_build_profile_data_without_cache(session):
    user = await users.create_user(session, 1, "nb")
    await session.commit()
    result = await build_profile_data(session, user, None, NOW)
    assert result.rating is None and result.last_seen == "never" and result.last_solved == []
