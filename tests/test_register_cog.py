from datetime import datetime, timezone

import pytest

from bot.cf.models import Problem, Submission, UserInfo
from bot.cogs.register import AlreadyRegistered, build_instruction_embed, finalize_registration, is_valid_handle
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


async def test_finalize_registration_raises_when_handle_exists(session):
    await users.create_user(session, 99, "Tourist")
    await session.commit()
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    info = UserInfo("tourist", 3800, 4000, "lgm", "lgm", 1, "https://x/y.png")
    with pytest.raises(AlreadyRegistered):
        await finalize_registration(session, pending, info, [], datetime(2026, 9, 16, tzinfo=timezone.utc))
    assert await users.get_by_discord(session, 1) is None


async def test_finalize_registration_raises_when_discord_exists(session):
    await users.create_user(session, 1, "other")
    await session.commit()
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    info = UserInfo("tourist", 3800, 4000, "lgm", "lgm", 1, "https://x/y.png")
    with pytest.raises(AlreadyRegistered):
        await finalize_registration(session, pending, info, [], datetime(2026, 9, 16, tzinfo=timezone.utc))


@pytest.mark.parametrize("handle", ["abc", "tourist", "Um_nik", "a.b-c_1", "x" * 24])
def test_is_valid_handle_accepts(handle):
    assert is_valid_handle(handle)


@pytest.mark.parametrize("handle", ["", "ab", "x" * 25, "a b", "a;b", "a/b", "name?x=1", "tourist\n"])
def test_is_valid_handle_rejects(handle):
    assert not is_valid_handle(handle)
