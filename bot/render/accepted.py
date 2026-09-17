import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import DISCORD_RANK_COLORS, GRAY, MUTED, WHITE, cf_rating_color
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "acc.png"
SLOT_HANDLE: Box = (100, 228, 875, 280)
SLOT_PROBLEM: Box = (100, 292, 875, 334)
SLOT_RATING: Box = (215, 352, 385, 392)
SLOT_EXP: Box = (402, 352, 572, 392)
SLOT_MONEY: Box = (589, 352, 759, 392)
SLOT_TAGS: Box = (110, 408, 865, 438)
SLOT_FOOTER: Box = (100, 462, 875, 500)
GOLD = "#FFD54F"
GREEN = "#66BB6A"


@dataclass(frozen=True)
class AcceptedData:
    handle: str
    rank_name: str
    problem: Problem
    exp_gained: int
    money_gained: Decimal
    level: int
    streak: int


def render_accepted(data: AcceptedData) -> bytes:
    base = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(base)
    problem = data.problem
    fit_text(draw, data.handle, SLOT_HANDLE, "Bold", 40, 22, DISCORD_RANK_COLORS.get(data.rank_name, GRAY))
    fit_text(draw, f"{problem.code} · {problem.name}", SLOT_PROBLEM, "SemiBold", 28, 16, WHITE)
    rating_text = "unrated" if problem.rating is None else f"rating {problem.rating}"
    fit_text(draw, rating_text, SLOT_RATING, "Bold", 24, 14, cf_rating_color(problem.rating))
    fit_text(draw, f"+{data.exp_gained} EXP", SLOT_EXP, "Bold", 24, 14, GOLD)
    fit_text(draw, f"+${data.money_gained:.2f}", SLOT_MONEY, "Bold", 24, 14, GREEN)
    tags_font = get_font("Regular", 17)
    tags = " · ".join(problem.tags) if problem.tags else "no tags"
    x0, y0, x1, y1 = SLOT_TAGS
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), truncate(tags_font, tags, x1 - x0), font=tags_font, fill=MUTED, anchor="mm")
    footer = f"Level {data.level} · {data.rank_name} · streak {data.streak}"
    fit_text(draw, footer, SLOT_FOOTER, "Medium", 20, 14, MUTED)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
