from datetime import date, datetime, timezone
from decimal import Decimal

from bot.cf.models import Problem, Submission
from bot.db.repo import solved, users
from bot.services.solve_processor import process_user


def S(id, cid, idx, rating, t):
    return Submission(id, Problem(cid, idx, "n", rating, ()), "OK", t)


async def test_process_user_rewards_and_streak(session):
    await users.create_user(session, 1, "a")
    await solved.add_solved(session, 1, 9, "Z", datetime(2026, 1, 1, tzinfo=timezone.utc))
    await session.commit()
    today = date(2026, 9, 16)
    results = await process_user(session, 1, [S(1, 1, "A", 900, 100), S(2, 9, "Z", 3000, 200), S(3, 2, "B", None, 300)], today)
    assert [r.problem.key for r in results] == [(1, "A"), (2, "B")]
    assert results[0].exp_gained == 90 and results[0].money_gained == Decimal("4.50")
    assert results[1].exp_gained == 0 and results[1].money_gained == Decimal("0.00")
    assert results[0].streak == 1
    user = await users.get_by_discord(session, 1)
    assert user.exp == 90 and user.money == Decimal("4.50") and user.streak == 1 and user.last_solve_date == today
    assert await solved.solved_count(session, 1) == 3


async def test_process_user_level_up(session):
    u = await users.create_user(session, 1, "a")
    u.exp = 95
    await session.commit()
    results = await process_user(session, 1, [S(1, 1, "A", 100, 1)], date(2026, 9, 16))
    assert results[0].old_level == 1 and results[0].new_level == 2
    assert results[0].old_rank == "Rookie" and results[0].new_rank == "Rookie"


async def test_process_user_second_call_is_noop(session):
    await users.create_user(session, 1, "a")
    await session.commit()
    subs = [S(1, 1, "A", 900, 1)]
    await process_user(session, 1, subs, date(2026, 9, 16))
    assert await process_user(session, 1, subs, date(2026, 9, 16)) == []
