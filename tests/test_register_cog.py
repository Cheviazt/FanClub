from datetime import datetime, timezone

from bot.cf.models import Problem, Submission, UserInfo
from bot.cogs.register import build_instruction_embed, finalize_registration
from bot.db.repo import cf_cache, solved, users
from bot.services.register import PendingRegistration

PROBLEM = Problem(1, "A", "Theatre Square", 1000, ("math",))


def test_instruction_embed_contains_link_and_deadline():
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    embed = build_instruction_embed(pending)
    assert PROBLEM.url in embed.description
    assert "<t:400:R>" in embed.description
    assert "Compilation Error" in embed.description


async def test_finalize_registration(session):
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    info = UserInfo("tourist", 3800, 4000, "legendary grandmaster", "legendary grandmaster", 1, "https://x/y.png")
    accepted = [
        Submission(1, Problem(2, "B", "x", 800, ()), "OK", 10),
        Submission(2, Problem(2, "B", "x", 800, ()), "OK", 20),
        Submission(3, Problem(3, "C", "y", None, ()), "OK", 30),
    ]
    user = await finalize_registration(session, pending, info, accepted, datetime(2026, 9, 16, tzinfo=timezone.utc))
    assert user.handle == "tourist" and user.exp == 0
    assert await solved.solved_count(session, 1) == 2
    assert (await cf_cache.get_cf_cache(session, 1)).rating == 3800
    assert (await users.get_by_discord(session, 1)) is not None
