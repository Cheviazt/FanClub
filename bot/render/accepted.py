import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import DISCORD_RANK_COLORS, GRAY, MUTED, WHITE
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "acc.png"
REFERENCE_WIDTH = 450
SLOT_HANDLE: Box = (62, 70, 387, 104)
SLOT_PROBLEM: Box = (62, 106, 387, 129)
SLOT_EXP: Box = (85, 132, 222, 161)
SLOT_MONEY: Box = (228, 132, 365, 161)
SLOT_TAGS: Box = (66, 164, 383, 178)
SLOT_FOOTER: Box = (62, 180, 387, 199)
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
    fit_text(draw, data.handle, scaled(SLOT_HANDLE, scale), "Bold", size(32, scale), size(14, scale), DISCORD_RANK_COLORS.get(data.rank_name, GRAY))
    fit_text(draw, f"{problem.code} · {problem.name}", scaled(SLOT_PROBLEM, scale), "SemiBold", size(19, scale), size(10, scale), WHITE)
    fit_text(draw, f"+{data.exp_gained} EXP", scaled(SLOT_EXP, scale), "Bold", size(25, scale), size(12, scale), GOLD)
    fit_text(draw, f"+${data.money_gained:.2f}", scaled(SLOT_MONEY, scale), "Bold", size(25, scale), size(12, scale), GREEN)
    tags_font = get_font("Regular", size(12, scale))
    tags = " · ".join(problem.tags) if problem.tags else "no tags"
    x0, y0, x1, y1 = scaled(SLOT_TAGS, scale)
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), truncate(tags_font, tags, x1 - x0), font=tags_font, fill=MUTED, anchor="mm")
    footer = f"Level {data.level} · {data.rank_name} · streak {data.streak}"
    fit_text(draw, footer, scaled(SLOT_FOOTER, scale), "Medium", size(15, scale), size(9, scale), MUTED)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
