import logging

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import roles as roles_repo
from bot.services.leveling import RANKS

log = logging.getLogger(__name__)


def nickname_for(level: int, handle: str) -> str:
    return f"【{level}】{handle}"


async def ensure_rank_roles(guild: discord.Guild, session: AsyncSession) -> dict[str, int]:
    stored = await roles_repo.get_role_ids(session, guild.id)
    by_name = {r.name: r for r in guild.roles}
    result: dict[str, int] = {}
    for rank in RANKS:
        role = by_name.get(rank.name)
        if role is None and rank.name in stored:
            role = discord.utils.get(guild.roles, id=stored[rank.name])
        if role is None:
            role = await guild.create_role(name=rank.name, colour=discord.Colour.from_str(rank.color), reason="rank role")
        result[rank.name] = role.id
        if stored.get(rank.name) != role.id:
            await roles_repo.set_role_id(session, guild.id, rank.name, role.id)
    await session.commit()
    return result


async def apply_rank(member: discord.Member, rank_name: str, role_ids: dict[str, int]) -> None:
    target_id = role_ids.get(rank_name)
    rank_ids = set(role_ids.values())
    try:
        for role in list(member.roles):
            if role.id in rank_ids and role.id != target_id:
                await member.remove_roles(role, reason="rank change")
        if target_id is not None and all(r.id != target_id for r in member.roles):
            target = member.guild.get_role(target_id)
            if target is not None:
                await member.add_roles(target, reason="rank change")
    except (discord.Forbidden, discord.HTTPException) as exc:
        log.warning("cannot update roles for %s: %s", member.id, exc)


async def set_level_nickname(member: discord.Member, level: int, handle: str) -> None:
    try:
        await member.edit(nick=nickname_for(level, handle), reason="level update")
    except (discord.Forbidden, discord.HTTPException) as exc:
        log.warning("cannot set nickname for %s: %s", member.id, exc)


async def clear_nickname(member: discord.Member) -> None:
    try:
        await member.edit(nick=None, reason="unregister")
    except (discord.Forbidden, discord.HTTPException) as exc:
        log.warning("cannot clear nickname for %s: %s", member.id, exc)
