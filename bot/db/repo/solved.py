from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import SolvedProblem


async def solved_keys(session: AsyncSession, user_id: int) -> set[tuple[int, str]]:
    stmt = select(SolvedProblem.contest_id, SolvedProblem.index).where(SolvedProblem.user_id == user_id)
    return {(cid, idx) for cid, idx in (await session.execute(stmt)).all()}


async def add_solved(session: AsyncSession, user_id: int, contest_id: int, index: str, solved_at: datetime) -> bool:
    existing = await session.get(SolvedProblem, (user_id, contest_id, index))
    if existing is not None:
        return False
    session.add(SolvedProblem(user_id=user_id, contest_id=contest_id, index=index, solved_at=solved_at))
    await session.flush()
    return True


async def bulk_add_solved(session: AsyncSession, user_id: int, items: list[tuple[int, str, datetime]]) -> int:
    existing = await solved_keys(session, user_id)
    added = 0
    for contest_id, index, solved_at in items:
        if (contest_id, index) in existing:
            continue
        existing.add((contest_id, index))
        session.add(SolvedProblem(user_id=user_id, contest_id=contest_id, index=index, solved_at=solved_at))
        added += 1
    await session.flush()
    return added


async def solved_count(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(SolvedProblem).where(SolvedProblem.user_id == user_id)
    return int((await session.execute(stmt)).scalar_one())


async def last_solved(session: AsyncSession, user_id: int, limit: int = 3) -> list[SolvedProblem]:
    stmt = (
        select(SolvedProblem)
        .where(SolvedProblem.user_id == user_id)
        .order_by(SolvedProblem.solved_at.desc(), SolvedProblem.contest_id.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
