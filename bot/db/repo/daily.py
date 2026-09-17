from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.models import DailyProblem


async def get_daily(session: AsyncSession, user_id: int, day: date) -> list[DailyProblem]:
    stmt = select(DailyProblem).where(DailyProblem.user_id == user_id, DailyProblem.date == day).order_by(DailyProblem.rating)
    return list((await session.execute(stmt)).scalars().all())


async def save_daily(session: AsyncSession, user_id: int, day: date, problems: list[Problem]) -> None:
    for p in problems:
        session.add(DailyProblem(user_id=user_id, date=day, rating=p.rating, contest_id=p.contest_id, index=p.index, name=p.name, tags=list(p.tags)))
    await session.flush()


async def daily_keys(session: AsyncSession, user_id: int) -> set[tuple[int, str]]:
    stmt = select(DailyProblem.contest_id, DailyProblem.index).where(DailyProblem.user_id == user_id)
    return {(cid, idx) for cid, idx in (await session.execute(stmt)).all()}
