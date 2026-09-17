from datetime import date, datetime, timedelta, timezone

from bot.config import WIB


def today_wib(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(WIB).date()


def next_streak(current: int, last_solve_date: date | None, today: date) -> int:
    if last_solve_date == today:
        return current
    if last_solve_date == today - timedelta(days=1):
        return current + 1
    return 1


def is_broken(last_solve_date: date | None, today: date) -> bool:
    if last_solve_date is None:
        return False
    return last_solve_date < today - timedelta(days=1)
