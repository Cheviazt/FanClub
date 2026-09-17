import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import DISCORD_RANK_COLORS, GRAY, MUTED, WHITE
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "acc.png"
REFERENCE_WIDTH = 600
SLOT_HANDLE: Box = (85, 94, 515, 132)
SLOT_PROBLEM: Box = (85, 136, 515, 162)
SLOT_EXP: Box = (130, 168, 296, 198)
SLOT_MONEY: Box = (304, 168, 470, 198)
SLOT_TAGS: Box = (90, 204, 510, 222)
SLOT_FOOTER: Box = (85, 228, 515, 254)
GOLD = "#FFD54F"
GREEN = "#66BB6A"


def scaled(box: Box, scale: float) -> Box:
    x0, y0, x1, y1 = box
    return round(x0 * scale), round(y0 * scale), round(x1 * scale), round(y1 * scale)


def size(value: int, scale: float) -> int:
    return max(8, round(value * scale))


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
    scale = base.width / REFERENCE_WIDTH
    problem = data.problem
    fit_text(draw, data.handle, scaled(SLOT_HANDLE, scale), "Bold", size(32, scale), size(16, scale), DISCORD_RANK_COLORS.get(data.rank_name, GRAY))
    fit_text(draw, f"{problem.code} · {problem.name}", scaled(SLOT_PROBLEM, scale), "SemiBold", size(21, scale), size(12, scale), WHITE)
    fit_text(draw, f"+{data.exp_gained} EXP", scaled(SLOT_EXP, scale), "Bold", size(24, scale), size(12, scale), GOLD)
    fit_text(draw, f"+${data.money_gained:.2f}", scaled(SLOT_MONEY, scale), "Bold", size(24, scale), size(12, scale), GREEN)
    tags_font = get_font("Regular", size(13, scale))
    tags = " · ".join(problem.tags) if problem.tags else "no tags"
    x0, y0, x1, y1 = scaled(SLOT_TAGS, scale)
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), truncate(tags_font, tags, x1 - x0), font=tags_font, fill=MUTED, anchor="mm")
    footer = f"Level {data.level} · {data.rank_name} · streak {data.streak}"
    fit_text(draw, footer, scaled(SLOT_FOOTER, scale), "Medium", size(16, scale), size(10, scale), MUTED)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
