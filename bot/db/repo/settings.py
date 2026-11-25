from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import UserSettings
from bot.services.settings import SETTINGS, SETTINGS_BY_KEY, defaults


async def get_flags(session: AsyncSession, user_id: int) -> dict[str, bool]:
    row = await session.get(UserSettings, user_id)
    if row is None:
        return defaults()
    return {setting.key: bool(getattr(row, setting.key)) for setting in SETTINGS}


async def set_flag(session: AsyncSession, user_id: int, key: str, value: bool) -> dict[str, bool]:
    if key not in SETTINGS_BY_KEY:
        raise KeyError(key)
    row = await session.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(user_id=user_id, **defaults())
        session.add(row)
    setattr(row, key, value)
    await session.flush()
    return {setting.key: bool(getattr(row, setting.key)) for setting in SETTINGS}


async def toggle_flag(session: AsyncSession, user_id: int, key: str) -> dict[str, bool]:
    flags = await get_flags(session, user_id)
    return await set_flag(session, user_id, key, not flags[key])
