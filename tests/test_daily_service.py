import random
from datetime import date, datetime, timezone

import pytest

from bot.cf.models import Problem
from bot.db.repo import problemset, solved, users
from bot.services.daily import NotEnoughProblems, get_or_create_daily

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def P(cid, rating):
    return Problem(cid, "A", f"p{cid}", rating, ("math",))


async def test_daily_excludes_solved_and_is_stable(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(2, 900), P(3, 1200), P(4, 1600)], NOW)
    await solved.add_solved(session, 1, 1, "A", NOW)
    await session.commit()
    day = date(2026, 9, 16)
    first = await get_or_create_daily(session, 1, day, random.Random(0))
    assert [p.rating for p in first] == [900, 1200, 1600]
    assert first[0].key == (2, "A")
    again = await get_or_create_daily(session, 1, day)
    assert [p.key for p in again] == [p.key for p in first]


async def test_daily_excludes_previous_daily(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(2, 900), P(3, 1200), P(4, 1600), P(5, 1200), P(6, 1600)], NOW)
    await session.commit()
    d1 = await get_or_create_daily(session, 1, date(2026, 9, 16), random.Random(0))
    d2 = await get_or_create_daily(session, 1, date(2026, 9, 17), random.Random(0))
    assert d1[0].key != d2[0].key


async def test_daily_raises_when_empty(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(3, 1200)], NOW)
    await session.commit()
    with pytest.raises(NotEnoughProblems):
        await get_or_create_daily(session, 1, date(2026, 9, 16))
