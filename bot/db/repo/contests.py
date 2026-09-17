from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ContestNotice


async def list_notices(session: AsyncSession) -> dict[tuple[str, str], ContestNotice]:
    rows = (await session.execute(select(ContestNotice))).scalars().all()
    return {(row.platform, row.contest_key): row for row in rows}


async def mark(session: AsyncSession, platform: str, contest_key: str, now: datetime, announced: bool = False, reminded: bool = False) -> ContestNotice:
    row = await session.get(ContestNotice, (platform, contest_key))
    if row is None:
        row = ContestNotice(platform=platform, contest_key=contest_key)
        session.add(row)
    if announced:
        row.announced_at = now
    if reminded:
        row.reminded_at = now
    await session.flush()
    return row
