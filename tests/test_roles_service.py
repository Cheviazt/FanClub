from unittest.mock import AsyncMock, MagicMock

import discord

from bot.services.roles import apply_rank, ensure_rank_roles, nickname_for, set_level_nickname


def test_nickname_for():
    assert nickname_for(12, "tourist") == "【12】tourist"


async def test_ensure_rank_roles_creates_missing(session):
    guild = MagicMock()
    guild.id = 10
    guild.roles = []
    created = []

    async def create_role(name, colour, reason):
        role = MagicMock()
        role.id = 1000 + len(created)
        role.name = name
        created.append(role)
        return role

    guild.create_role = AsyncMock(side_effect=create_role)
    ids = await ensure_rank_roles(guild, session)
    assert len(ids) == 8 and ids["Rookie"] == 1000
    guild.roles = created
    ids2 = await ensure_rank_roles(guild, session)
    assert ids2 == ids and guild.create_role.await_count == 8


async def test_apply_rank_swaps_roles():
    member = MagicMock()
    rookie = MagicMock(); rookie.id = 1
    elite = MagicMock(); elite.id = 2
    member.roles = [rookie]
    member.guild.get_role = lambda rid: {1: rookie, 2: elite}[rid]
    member.remove_roles = AsyncMock()
    member.add_roles = AsyncMock()
    await apply_rank(member, "Elite", {"Rookie": 1, "Elite": 2})
    member.remove_roles.assert_awaited_once_with(rookie, reason="rank change")
    member.add_roles.assert_awaited_once_with(elite, reason="rank change")


async def test_set_level_nickname_ignores_forbidden():
    member = MagicMock()
    member.edit = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "no"))
    await set_level_nickname(member, 3, "h")
    member.edit.assert_awaited_once()
