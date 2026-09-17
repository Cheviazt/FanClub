from datetime import date, datetime, timezone

from bot.services.streak import is_broken, next_streak, today_wib


def test_today_wib_crosses_midnight():
    now = datetime(2026, 9, 16, 17, 30, tzinfo=timezone.utc)
    assert today_wib(now) == date(2026, 9, 17)


def test_next_streak():
    today = date(2026, 9, 16)
    assert next_streak(5, date(2026, 9, 16), today) == 5
    assert next_streak(5, date(2026, 9, 15), today) == 6
    assert next_streak(5, date(2026, 9, 10), today) == 1
    assert next_streak(0, None, today) == 1


def test_is_broken():
    today = date(2026, 9, 16)
    assert is_broken(date(2026, 9, 14), today) is True
    assert is_broken(date(2026, 9, 15), today) is False
    assert is_broken(date(2026, 9, 16), today) is False
    assert is_broken(None, today) is False
