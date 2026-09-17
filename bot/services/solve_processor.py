from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem, Submission
from bot.db.repo import solved, users
from bot.services.leveling import level_for, rank_for
from bot.services.rewards import exp_for, money_for
from bot.services.solve_detector import detect_new_solves
from bot.services.streak import next_streak


@dataclass(frozen=True)
class SolveResult:
    discord_id: int
    handle: str
    problem: Problem
    exp_gained: int
    money_gained: Decimal
    old_level: int
    new_level: int
    old_rank: str
    new_rank: str
    streak: int


async def process_user(session: AsyncSession, discord_id: int, submissions: list[Submission], today: date) -> list[SolveResult]:
    user = await users.get_by_discord(session, discord_id)
    if user is None:
        return []
    known = await solved.solved_keys(session, discord_id)
    results: list[SolveResult] = []
    for sub in detect_new_solves(submissions, known):
        solved_at = datetime.fromtimestamp(sub.created_at, tz=timezone.utc)
        if not await solved.add_solved(session, discord_id, sub.problem.contest_id, sub.problem.index, solved_at):
            continue
        old_level = level_for(user.exp)
        exp_gain = exp_for(sub.problem.rating)
        money_gain = money_for(sub.problem.rating)
        user.exp += exp_gain
        user.money = Decimal(user.money) + money_gain
        user.streak = next_streak(user.streak, user.last_solve_date, today)
        user.last_solve_date = today
        new_level = level_for(user.exp)
        results.append(
            SolveResult(
                discord_id=discord_id,
                handle=user.handle,
                problem=sub.problem,
                exp_gained=exp_gain,
                money_gained=money_gain,
                old_level=old_level,
                new_level=new_level,
                old_rank=rank_for(old_level).name,
                new_rank=rank_for(new_level).name,
                streak=user.streak,
            )
        )
    await session.commit()
    return results
