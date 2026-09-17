from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def exp_for(rating: int | None) -> int:
    if rating is None:
        return 0
    return rating // 10


def money_for(rating: int | None) -> Decimal:
    if rating is None:
        return Decimal("0.00")
    return (Decimal(rating) / Decimal(200)).quantize(CENT, rounding=ROUND_HALF_UP)
