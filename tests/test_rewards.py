from decimal import Decimal

from bot.services.rewards import exp_for, money_for


def test_exp_for():
    assert exp_for(900) == 90
    assert exp_for(1600) == 160
    assert exp_for(None) == 0


def test_money_for():
    assert money_for(900) == Decimal("4.50")
    assert money_for(800) == Decimal("4.00")
    assert money_for(None) == Decimal("0.00")
