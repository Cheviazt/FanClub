from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.models import ProblemsetCache


def _to_problem(row: ProblemsetCache) -> Problem:
    return Problem(row.contest_id, row.index, row.name, row.rating, tuple(row.tags or []))


async def replace_problemset(session: AsyncSession, problems: list[Problem], now: datetime) -> int:
    await session.execute(delete(ProblemsetCache))
    seen: set[tuple[int, str]] = set()
    rows = []
    for p in problems:
        if p.key in seen:
            continue
        seen.add(p.key)
        rows.append(ProblemsetCache(contest_id=p.contest_id, index=p.index, name=p.name, rating=p.rating, tags=list(p.tags), fetched_at=now))
    session.add_all(rows)
    await session.flush()
    return len(rows)


async def list_problems(session: AsyncSession, rating: int | None = None) -> list[Problem]:
    stmt = select(ProblemsetCache)
    if rating is not None:
        stmt = stmt.where(ProblemsetCache.rating == rating)
    return [_to_problem(r) for r in (await session.execute(stmt)).scalars().all()]


async def get_problem(session: AsyncSession, contest_id: int, index: str) -> Problem | None:
    row = await session.get(ProblemsetCache, (contest_id, index))
    return None if row is None else _to_problem(row)


async def count_problems(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(ProblemsetCache))).scalar_one())
