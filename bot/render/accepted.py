import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import DISCORD_RANK_COLORS, GRAY, MUTED, WHITE
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "acc.png"
SLOT_HANDLE: Box = (100, 222, 875, 292)
SLOT_PROBLEM: Box = (100, 300, 875, 352)
SLOT_EXP: Box = (240, 366, 480, 420)
SLOT_MONEY: Box = (494, 366, 734, 420)
SLOT_TAGS: Box = (110, 436, 865, 466)
SLOT_FOOTER: Box = (100, 480, 875, 520)
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
    fit_text(draw, data.handle, SLOT_HANDLE, "Bold", 56, 26, DISCORD_RANK_COLORS.get(data.rank_name, GRAY))
    fit_text(draw, f"{problem.code} · {problem.name}", SLOT_PROBLEM, "SemiBold", 36, 18, WHITE)
    fit_text(draw, f"+{data.exp_gained} EXP", SLOT_EXP, "Bold", 38, 18, GOLD)
    fit_text(draw, f"+${data.money_gained:.2f}", SLOT_MONEY, "Bold", 38, 18, GREEN)
    tags_font = get_font("Regular", 21)
    tags = " · ".join(problem.tags) if problem.tags else "no tags"
    x0, y0, x1, y1 = SLOT_TAGS
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), truncate(tags_font, tags, x1 - x0), font=tags_font, fill=MUTED, anchor="mm")
    footer = f"Level {data.level} · {data.rank_name} · streak {data.streak}"
    fit_text(draw, footer, SLOT_FOOTER, "Medium", 26, 14, MUTED)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
