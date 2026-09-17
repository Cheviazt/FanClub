from bot.services.leveling import RANKS

WHITE = "#FFFFFF"
MUTED = "#B0BEC5"
GRAY = "#808080"

DISCORD_RANK_COLORS: dict[str, str] = {r.name: r.color for r in RANKS}

CF_RANK_COLORS: dict[str, str] = {
    "newbie": GRAY,
    "pupil": "#008000",
    "specialist": "#03A89E",
    "expert": "#0000FF",
    "candidate master": "#AA00AA",
    "master": "#FF8C00",
    "international master": "#FF8C00",
    "grandmaster": "#FF0000",
    "international grandmaster": "#FF0000",
    "legendary grandmaster": "#FF0000",
}

CF_RATING_BANDS: tuple[tuple[int, str], ...] = (
    (1200, GRAY),
    (1400, "#008000"),
    (1600, "#03A89E"),
    (1900, "#0000FF"),
    (2100, "#AA00AA"),
    (2400, "#FF8C00"),
)


def cf_rank_color(rank: str | None) -> str:
    if not rank:
        return GRAY
    return CF_RANK_COLORS.get(rank.lower(), GRAY)


def cf_rating_color(rating: int | None) -> str:
    if rating is None:
        return GRAY
    for limit, color in CF_RATING_BANDS:
        if rating < limit:
            return color
    return "#FF0000"
