from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


async def create_user(session: AsyncSession, discord_id: int, handle: str) -> User:
    user = User(discord_id=discord_id, handle=handle, registered_at=datetime.now(timezone.utc))
    session.add(user)
    await session.flush()
    return user


async def get_by_discord(session: AsyncSession, discord_id: int) -> User | None:
    return await session.get(User, discord_id)


async def get_by_handle(session: AsyncSession, handle: str) -> User | None:
    stmt = select(User).where(func.lower(User.handle) == handle.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_users(session: AsyncSession) -> list[User]:
    return list((await session.execute(select(User).order_by(User.discord_id))).scalars().all())
