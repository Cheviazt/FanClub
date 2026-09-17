from datetime import datetime, timezone

from bot.cf.models import UserInfo
from bot.db.repo import cf_cache, solved, users
from bot.services.leaderboard import PER_PAGE, fetch_page

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


async def seed(session, n):
    for i in range(1, n + 1):
        u = await users.create_user(session, i, f"h{i}")
        u.exp = i * 100
        u.streak = n - i
        await cf_cache.upsert_cf_cache(session, i, UserInfo(f"h{i}", 1000 + i if i % 2 else None, 1500, "pupil", "pupil", 1, ""), NOW)
        for j in range(i):
            await solved.add_solved(session, i, j, "A", NOW)
    await session.commit()


async def test_level_pages(session):
    await seed(session, 9)
    rows, total = await fetch_page(session, "level", 1)
    assert total == 2 and len(rows) == PER_PAGE
    assert rows[0].handle == "h9" and rows[0].no == 1
    rows2, _ = await fetch_page(session, "level", 2)
    assert [r.handle for r in rows2] == ["h2", "h1"] and rows2[0].no == 8


async def test_rating_null_as_zero(session):
    await seed(session, 4)
    rows, _ = await fetch_page(session, "rating", 1)
    assert [r.handle for r in rows] == ["h3", "h1", "h2", "h4"]
    assert rows[0].value == "1003" and rows[-1].value == "0"


async def test_solved_and_streaks(session):
    await seed(session, 3)
    rows, _ = await fetch_page(session, "solved", 1)
    assert [r.value for r in rows] == ["3", "2", "1"]
    rows, _ = await fetch_page(session, "streaks", 1)
    assert [r.handle for r in rows] == ["h1", "h2", "h3"]


async def test_empty(session):
    rows, total = await fetch_page(session, "level", 1)
    assert rows == [] and total == 1
