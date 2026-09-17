from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    handle: Mapped[str] = mapped_column(String(64), unique=True)
    exp: Mapped[int] = mapped_column(Integer, default=0)
    money: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_solve_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SolvedProblem(Base):
    __tablename__ = "solved_problems"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    contest_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index: Mapped[str] = mapped_column(String(8), primary_key=True)
    solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailyProblem(Base):
    __tablename__ = "daily_problems"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    rating: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(Integer)
    index: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(255))
    tags: Mapped[list] = mapped_column(JSON, default=list)


class GuildRole(Base):
    __tablename__ = "guild_roles"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    rank_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger)


class CfCache(Base):
    __tablename__ = "cf_cache"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True, autoincrement=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_online: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemsetCache(Base):
    __tablename__ = "problemset_cache"

    contest_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    index: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ContestNotice(Base):
    __tablename__ = "contest_notices"

    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    contest_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    announced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
