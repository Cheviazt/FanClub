from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import UserInfo
from bot.db.models import CfCache


async def upsert_cf_cache(session: AsyncSession, user_id: int, info: UserInfo, now: datetime) -> CfCache:
    row = await session.get(CfCache, user_id)
    if row is None:
        row = CfCache(user_id=user_id)
        session.add(row)
    row.rating = info.rating
    row.max_rating = info.max_rating
    row.rank = info.rank
    row.max_rank = info.max_rank
    row.last_online = datetime.fromtimestamp(info.last_online, tz=timezone.utc)
    row.avatar_url = info.avatar_url
    row.updated_at = now
    await session.flush()
    return row


async def get_cf_cache(session: AsyncSession, user_id: int) -> CfCache | None:
    return await session.get(CfCache, user_id)
