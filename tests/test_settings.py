from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.cf.models import Problem
from bot.cogs.poller import PollerCog
from bot.cogs.settings import SettingsView, settings_embed
from bot.db.repo import settings as settings_repo
from bot.db.repo import users
from bot.services.settings import MENTION_ON_SOLVE, NICKNAME_SYNC, SETTINGS, SOLVE_ANNOUNCEMENTS
from bot.services.solve_processor import SolveResult

RESULT = SolveResult(1, "tourist", Problem(1842, "B", "Tenzing", 900, ()), 90, Decimal("4.50"), 1, 1, "Rookie", "Rookie", 3)


async def test_flags_default_to_on(session):
    await users.create_user(session, 1, "tourist")
    await session.commit()
    flags = await settings_repo.get_flags(session, 1)
    assert flags == {setting.key: True for setting in SETTINGS}


async def test_toggle_and_set_flag(session):
    await users.create_user(session, 1, "tourist")
    await session.commit()
    flags = await settings_repo.toggle_flag(session, 1, MENTION_ON_SOLVE)
    await session.commit()
    assert flags[MENTION_ON_SOLVE] is False and flags[SOLVE_ANNOUNCEMENTS] is True
    assert (await settings_repo.get_flags(session, 1))[MENTION_ON_SOLVE] is False
    flags = await settings_repo.set_flag(session, 1, MENTION_ON_SOLVE, True)
    await session.commit()
    assert flags[MENTION_ON_SOLVE] is True
    with pytest.raises(KeyError):
        await settings_repo.set_flag(session, 1, "nonsense", True)


async def test_unregister_removes_settings(session):
    await users.create_user(session, 1, "tourist")
    await settings_repo.set_flag(session, 1, MENTION_ON_SOLVE, False)
    await session.commit()
    assert await users.delete_user(session, 1) is True
    await session.commit()
    assert (await settings_repo.get_flags(session, 1))[MENTION_ON_SOLVE] is True


def make_poller(flags):
    bot = MagicMock()
    bot.settings.guild_id = 10
    bot.settings.notify_channel_id = 555
    bot.get_guild = MagicMock(return_value=None)
    channel = MagicMock()
    channel.send = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel)
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    cog.role_ids = {}
    cog.user_flags = AsyncMock(return_value=flags)
    return cog, channel


async def test_announcement_mentions_by_default():
    cog, channel = make_poller({SOLVE_ANNOUNCEMENTS: True, MENTION_ON_SOLVE: True, NICKNAME_SYNC: True})
    await cog.apply_side_effects(RESULT)
    kwargs = channel.send.await_args.kwargs
    assert kwargs["content"] == "<@1>" and kwargs["allowed_mentions"].users is True


async def test_announcement_without_mention():
    cog, channel = make_poller({SOLVE_ANNOUNCEMENTS: True, MENTION_ON_SOLVE: False, NICKNAME_SYNC: True})
    await cog.apply_side_effects(RESULT)
    kwargs = channel.send.await_args.kwargs
    assert kwargs["content"] == "**tourist**" and kwargs["allowed_mentions"].users is False


async def test_announcement_disabled():
    cog, channel = make_poller({SOLVE_ANNOUNCEMENTS: False, MENTION_ON_SOLVE: True, NICKNAME_SYNC: True})
    await cog.apply_side_effects(RESULT)
    channel.send.assert_not_awaited()


async def test_batch_respects_flags():
    cog, channel = make_poller({SOLVE_ANNOUNCEMENTS: True, MENTION_ON_SOLVE: False, NICKNAME_SYNC: True})
    await cog.apply_batch_side_effects([RESULT, RESULT])
    text = channel.send.await_args.args[0]
    assert text.startswith("**tourist** solved 2 problems")


async def test_sync_member_skips_nickname_when_disabled():
    cog, _ = make_poller({SOLVE_ANNOUNCEMENTS: True, MENTION_ON_SOLVE: True, NICKNAME_SYNC: False})
    member = MagicMock()
    member.edit = AsyncMock()
    guild = MagicMock()
    guild.get_member = MagicMock(return_value=member)
    cog.bot.get_guild = MagicMock(return_value=guild)
    levelled = SolveResult(1, "tourist", RESULT.problem, 90, Decimal("4.50"), 1, 2, "Rookie", "Rookie", 3)
    await cog.sync_member(levelled, {SOLVE_ANNOUNCEMENTS: True, MENTION_ON_SOLVE: True, NICKNAME_SYNC: False})
    member.edit.assert_not_awaited()


async def test_settings_embed_and_view_shape(session_factory):
    flags = {setting.key: True for setting in SETTINGS}
    flags[MENTION_ON_SOLVE] = False
    embed = settings_embed("tourist", flags)
    assert "tourist" in embed.description and len(embed.fields) == len(SETTINGS)
    mention_field = next(f for f in embed.fields if f.name.startswith("Mention on solve"))
    assert mention_field.name.endswith("Off")
    bot = MagicMock()
    bot.session_factory = session_factory
    view = SettingsView(bot, 1, "tourist", flags)
    assert len(view.children) == len(SETTINGS)
    interaction = MagicMock()
    interaction.user.id = 2
    assert await view.interaction_check(interaction) is False
