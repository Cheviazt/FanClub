from datetime import date, datetime, timezone

from bot.cf.models import Problem, UserInfo
from bot.db.repo import cf_cache, daily, problemset, roles, solved, users

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def P(cid, idx, rating=None, name="n", tags=()):
    return Problem(cid, idx, name, rating, tuple(tags))


async def test_users_crud(session):
    u = await users.create_user(session, 1, "Tourist")
    await session.commit()
    assert u.exp == 0
    assert (await users.get_by_discord(session, 1)).handle == "Tourist"
    assert (await users.get_by_handle(session, "tourist")).discord_id == 1
    assert await users.get_by_discord(session, 2) is None
    assert len(await users.list_users(session)) == 1


async def test_solved(session):
    await users.create_user(session, 1, "a")
    assert await solved.add_solved(session, 1, 1, "A", NOW) is True
    assert await solved.add_solved(session, 1, 1, "A", NOW) is False
    n = await solved.bulk_add_solved(session, 1, [(2, "B", NOW), (1, "A", NOW), (3, "C", NOW)])
    await session.commit()
    assert n == 2
    assert await solved.solved_keys(session, 1) == {(1, "A"), (2, "B"), (3, "C")}
    assert await solved.solved_count(session, 1) == 3
    assert len(await solved.last_solved(session, 1, limit=2)) == 2


async def test_cf_cache_upsert(session):
    await users.create_user(session, 1, "a")
    info = UserInfo("a", 1500, 1600, "specialist", "expert", 1700000000, "https://x/y.png")
    await cf_cache.upsert_cf_cache(session, 1, info, NOW)
    await session.commit()
    info2 = UserInfo("a", 1550, 1600, "specialist", "expert", 1700000001, "https://x/y.png")
    await cf_cache.upsert_cf_cache(session, 1, info2, NOW)
    await session.commit()
    row = await cf_cache.get_cf_cache(session, 1)
    assert row.rating == 1550


async def test_problemset(session):
    n = await problemset.replace_problemset(session, [P(1, "A", 900), P(1, "B", 1200), P(2, "A", None)], NOW)
    await session.commit()
    assert n == 3
    assert await problemset.count_problems(session) == 3
    assert [p.key for p in await problemset.list_problems(session, rating=900)] == [(1, "A")]
    assert len(await problemset.list_problems(session)) == 3
    assert (await problemset.get_problem(session, 1, "B")).rating == 1200
    await problemset.replace_problemset(session, [P(9, "Z", 800)], NOW)
    await session.commit()
    assert await problemset.count_problems(session) == 1


async def test_daily(session):
    await users.create_user(session, 1, "a")
    day = date(2026, 9, 16)
    assert await daily.get_daily(session, 1, day) == []
    await daily.save_daily(session, 1, day, [P(1, "A", 900, "x", ["math"]), P(2, "B", 1200), P(3, "C", 1600)])
    await session.commit()
    rows = await daily.get_daily(session, 1, day)
    assert [r.rating for r in rows] == [900, 1200, 1600]
    assert rows[0].tags == ["math"]
    assert await daily.daily_keys(session, 1) == {(1, "A"), (2, "B"), (3, "C")}


async def test_roles(session):
    assert await roles.get_role_ids(session, 10) == {}
    await roles.set_role_id(session, 10, "Rookie", 100)
    await roles.set_role_id(session, 10, "Rookie", 101)
    await session.commit()
    assert await roles.get_role_ids(session, 10) == {"Rookie": 101}


async def test_delete_user_removes_children(session):
    await users.create_user(session, 1, "a")
    await solved.add_solved(session, 1, 1, "A", NOW)
    await daily.save_daily(session, 1, date(2026, 9, 16), [P(1, "A", 900)])
    await cf_cache.upsert_cf_cache(session, 1, UserInfo("a", None, None, None, None, 1, ""), NOW)
    await session.commit()
    assert await users.delete_user(session, 1) is True
    await session.commit()
    assert await users.get_by_discord(session, 1) is None
    assert await solved.solved_count(session, 1) == 0
    assert await daily.get_daily(session, 1, date(2026, 9, 16)) == []
    assert await cf_cache.get_cf_cache(session, 1) is None
    assert await users.delete_user(session, 1) is False
