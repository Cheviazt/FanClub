from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from bot.db.models import SolvedProblem, User


async def test_create_user_and_solved(session):
    user = User(discord_id=1, handle="tourist", registered_at=datetime.now(timezone.utc))
    session.add(user)
    await session.commit()
    session.add(SolvedProblem(user_id=1, contest_id=1, index="A", solved_at=datetime.now(timezone.utc)))
    await session.commit()
    loaded = (await session.execute(select(User).where(User.discord_id == 1))).scalar_one()
    assert loaded.exp == 0 and loaded.money == Decimal("0.00") and loaded.streak == 0
    count = (await session.execute(select(SolvedProblem).where(SolvedProblem.user_id == 1))).scalars().all()
    assert len(count) == 1
