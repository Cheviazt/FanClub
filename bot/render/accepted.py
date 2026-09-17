import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import DISCORD_RANK_COLORS, GRAY, MUTED, WHITE
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "acc.png"
SLOT_HANDLE: Box = (85, 94, 515, 132)
SLOT_PROBLEM: Box = (85, 136, 515, 162)
SLOT_EXP: Box = (130, 168, 296, 198)
SLOT_MONEY: Box = (304, 168, 470, 198)
SLOT_TAGS: Box = (90, 204, 510, 222)
SLOT_FOOTER: Box = (85, 228, 515, 254)
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
    fit_text(draw, data.handle, SLOT_HANDLE, "Bold", 32, 16, DISCORD_RANK_COLORS.get(data.rank_name, GRAY))
    fit_text(draw, f"{problem.code} · {problem.name}", SLOT_PROBLEM, "SemiBold", 21, 12, WHITE)
    fit_text(draw, f"+{data.exp_gained} EXP", SLOT_EXP, "Bold", 24, 12, GOLD)
    fit_text(draw, f"+${data.money_gained:.2f}", SLOT_MONEY, "Bold", 24, 12, GREEN)
    tags_font = get_font("Regular", 13)
    tags = " · ".join(problem.tags) if problem.tags else "no tags"
    x0, y0, x1, y1 = SLOT_TAGS
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), truncate(tags_font, tags, x1 - x0), font=tags_font, fill=MUTED, anchor="mm")
    footer = f"Level {data.level} · {data.rank_name} · streak {data.streak}"
    fit_text(draw, footer, SLOT_FOOTER, "Medium", 16, 10, MUTED)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
