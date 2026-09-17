import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import CfCache, SolvedProblem, User
from bot.services.leveling import level_for, rank_for

LEADERBOARD_TYPES: tuple[str, ...] = ("level", "rating", "solved", "streaks")
PER_PAGE = 7


@dataclass(frozen=True)
class LeaderboardRow:
    no: int
    handle: str
    rank_name: str
    value: str


async def fetch_page(session: AsyncSession, kind: str, page: int) -> tuple[list[LeaderboardRow], int]:
    solved_count = (
        select(SolvedProblem.user_id, func.count().label("cnt"))
        .group_by(SolvedProblem.user_id)
        .subquery()
    )
    rating = func.coalesce(CfCache.rating, 0)
    max_rating = func.coalesce(CfCache.max_rating, 0)
    cnt = func.coalesce(solved_count.c.cnt, 0)
    stmt = (
        select(User.handle, User.exp, User.streak, rating, cnt)
        .outerjoin(CfCache, CfCache.user_id == User.discord_id)
        .outerjoin(solved_count, solved_count.c.user_id == User.discord_id)
    )
    if kind == "level":
        stmt = stmt.order_by(User.exp.desc(), User.discord_id)
    elif kind == "rating":
        stmt = stmt.order_by(rating.desc(), max_rating.desc(), User.discord_id)
    elif kind == "solved":
        stmt = stmt.order_by(cnt.desc(), User.exp.desc(), User.discord_id)
    elif kind == "streaks":
        stmt = stmt.order_by(User.streak.desc(), User.exp.desc(), User.discord_id)
    else:
        raise ValueError(kind)
    total = int((await session.execute(select(func.count()).select_from(User))).scalar_one())
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * PER_PAGE
    rows = (await session.execute(stmt.offset(offset).limit(PER_PAGE))).all()
    out: list[LeaderboardRow] = []
    for i, (handle, exp, streak, rating_value, solved_value) in enumerate(rows, start=offset + 1):
        level = level_for(exp)
        if kind == "level":
            value = str(level)
        elif kind == "rating":
            value = str(int(rating_value))
        elif kind == "solved":
            value = str(int(solved_value))
        else:
            value = str(streak)
        out.append(LeaderboardRow(i, handle, rank_for(level).name, value))
    return out, total_pages
