import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.repo import problemset, solved
from bot.services.daily import NotEnoughProblems

MIN_COUNT = 1
MAX_COUNT = 4
MIN_RATING = 800
MAX_RATING = 3500


class UnknownTags(Exception):
    def __init__(self, tags: list[str]) -> None:
        super().__init__(", ".join(tags))
        self.tags = tags


def parse_tags(text: str | None) -> list[str]:
    if not text:
        return []
    seen: list[str] = []
    for raw in text.split(","):
        tag = " ".join(raw.strip().lower().split())
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def is_valid_rating(rating: int) -> bool:
    return MIN_RATING <= rating <= MAX_RATING and rating % 100 == 0


async def pick_problems(
    session: AsyncSession,
    user_id: int,
    count: int,
    rating: int,
    tags: list[str],
    rng: random.Random | None = None,
) -> list[Problem]:
    all_problems = await problemset.list_problems(session)
    known_tags = {tag for problem in all_problems for tag in problem.tags}
    unknown = [tag for tag in tags if tag not in known_tags]
    if unknown:
        raise UnknownTags(unknown)
    done = await solved.solved_keys(session, user_id)
    wanted = set(tags)
    candidates = [p for p in all_problems if p.rating == rating and wanted <= set(p.tags) and p.key not in done]
    if len(candidates) < count:
        raise NotEnoughProblems(f"only {len(candidates)} problems match")
    chooser = rng or random.Random()
    return chooser.sample(candidates, count)
