from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import GuildRole


async def get_role_ids(session: AsyncSession, guild_id: int) -> dict[str, int]:
    rows = (await session.execute(select(GuildRole).where(GuildRole.guild_id == guild_id))).scalars().all()
    return {r.rank_name: r.role_id for r in rows}


async def set_role_id(session: AsyncSession, guild_id: int, rank_name: str, role_id: int) -> None:
    row = await session.get(GuildRole, (guild_id, rank_name))
    if row is None:
        session.add(GuildRole(guild_id=guild_id, rank_name=rank_name, role_id=role_id))
    else:
        row.role_id = role_id
    await session.flush()
