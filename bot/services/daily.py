import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.repo import daily, problemset, solved

DAILY_RATINGS: tuple[int, ...] = (900, 1200, 1600)


class NotEnoughProblems(Exception):
    pass


async def get_or_create_daily(session: AsyncSession, user_id: int, day: date, rng: random.Random | None = None) -> list[Problem]:
    existing = await daily.get_daily(session, user_id, day)
    if existing:
        return [Problem(r.contest_id, r.index, r.name, r.rating, tuple(r.tags or [])) for r in existing]
    chooser = rng or random.Random()
    excluded = await solved.solved_keys(session, user_id) | await daily.daily_keys(session, user_id)
    picked: list[Problem] = []
    for rating in DAILY_RATINGS:
        candidates = [p for p in await problemset.list_problems(session, rating=rating) if p.key not in excluded]
        if not candidates:
            raise NotEnoughProblems(f"no unsolved problem with rating {rating}")
        choice = chooser.choice(candidates)
        excluded.add(choice.key)
        picked.append(choice)
    await daily.save_daily(session, user_id, day, picked)
    await session.commit()
    return picked
