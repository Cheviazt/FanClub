from unittest.mock import AsyncMock, MagicMock

import discord

from bot.cogs.admin import ResetReport, reset_member, roles_to_strip
from bot.config import Settings


def role(role_id: int, position: int, managed: bool = False, default: bool = False):
    r = MagicMock(spec=discord.Role)
    r.id = role_id
    r.managed = managed
    r.is_default = MagicMock(return_value=default)
    r.__lt__ = lambda self, other: position < other.position
    r.position = position
    return r


def member_with(roles, nick="x", bot=False):
    m = MagicMock()
    m.bot = bot
    m.nick = nick
    m.roles = roles
    m.guild.me.top_role = role(999, 100)
    m.remove_roles = AsyncMock()
    m.edit = AsyncMock()
    return m


def test_keep_role_ids_parsed():
    s = Settings(discord_token="t", guild_id=1, notify_channel_id=1, _env_file=None)
    assert 1492609991717163230 in s.keep_role_ids and len(s.keep_role_ids) == 5


def test_roles_to_strip_skips_kept_managed_default_and_higher():
    everyone = role(1, 0, default=True)
    kept = role(2, 5)
    managed = role(3, 6, managed=True)
    higher = role(4, 200)
    normal = role(5, 7)
    m = member_with([everyone, kept, managed, higher, normal])
    assert roles_to_strip(m, {2}) == [normal]


async def test_reset_member_removes_and_clears():
    normal = role(5, 7)
    m = member_with([normal], nick="old")
    report = ResetReport()
    await reset_member(m, set(), report)
    m.remove_roles.assert_awaited_once_with(normal, reason="resetall")
    m.edit.assert_awaited_once_with(nick=None, reason="resetall")
    assert report.members == 1 and report.roles_removed == 1 and report.nicknames_cleared == 1


async def test_reset_member_skips_bots_and_counts_failures():
    report = ResetReport()
    await reset_member(member_with([role(5, 7)], bot=True), set(), report)
    assert report.members == 0
    m = member_with([role(5, 7)])
    m.remove_roles = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "no"))
    await reset_member(m, set(), report)
    assert report.failed == 1
