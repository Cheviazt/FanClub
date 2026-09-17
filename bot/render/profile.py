import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from PIL import Image, ImageDraw, ImageOps

from bot.render.colors import DISCORD_RANK_COLORS, GRAY, WHITE, cf_rank_color, cf_rating_color
from bot.render.fonts import ASSETS_DIR
from bot.render.text import Box, fit_text

TEMPLATE = ASSETS_DIR / "profile.png"

SLOT_AVATAR: Box = (167, 158, 386, 377)
SLOT_LAST_SOLVED: Box = (167, 415, 386, 492)
SLOT_LEVEL: Box = (411, 158, 485, 207)
SLOT_HANDLE: Box = (509, 158, 807, 207)
SLOT_RANK: Box = (411, 226, 525, 267)
SLOT_EXP: Box = (551, 226, 666, 267)
SLOT_MONEY: Box = (692, 226, 807, 267)
SLOT_RATING: Box = (430, 366, 530, 392)
SLOT_CF_RANK: Box = (563, 366, 663, 392)
SLOT_MAX: Box = (696, 366, 796, 392)
SLOT_LAST_SEEN: Box = (430, 434, 530, 460)
SLOT_SOLVED: Box = (563, 434, 663, 460)
SLOT_STREAK: Box = (696, 434, 796, 460)
AVATAR_RADIUS = 12


@dataclass(frozen=True)
class ProfileData:
    handle: str
    avatar: bytes | None
    level: int
    rank_name: str
    exp_in_level: int
    exp_need: int
    money: Decimal
    rating: int | None
    max_rating: int | None
    cf_rank: str | None
    last_seen: str
    last_solved: list[str]
    solved_count: int
    streak: int


def format_last_seen(last_online: datetime, now: datetime) -> str:
    seconds = int((now - last_online).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _paste_avatar(base: Image.Image, avatar: bytes | None) -> None:
    x0, y0, x1, y1 = SLOT_AVATAR
    size = (x1 - x0, y1 - y0)
    if avatar is None:
        return
    try:
        img = Image.open(io.BytesIO(avatar)).convert("RGB")
    except OSError:
        return
    img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=AVATAR_RADIUS, fill=255)
    base.paste(img, (x0, y0), mask)


def _title(rank: str | None) -> str:
    return rank.title() if rank else "Unrated"


def render_profile(data: ProfileData) -> bytes:
    base = Image.open(TEMPLATE).convert("RGB")
    _paste_avatar(base, data.avatar)
    draw = ImageDraw.Draw(base)
    handle_color = cf_rank_color(data.cf_rank)
    rank_color = DISCORD_RANK_COLORS.get(data.rank_name, GRAY)

    fit_text(draw, f"Lv {data.level}", SLOT_LEVEL, "Bold", 22, 14, WHITE)
    fit_text(draw, data.handle, SLOT_HANDLE, "Bold", 30, 18, handle_color)
    fit_text(draw, data.rank_name, SLOT_RANK, "SemiBold", 18, 12, rank_color)
    fit_text(draw, f"{data.exp_in_level}/{data.exp_need}", SLOT_EXP, "SemiBold", 18, 12, WHITE)
    fit_text(draw, f"${data.money:.2f}", SLOT_MONEY, "SemiBold", 18, 12, WHITE)

    rating_text = "Unrated" if data.rating is None else str(data.rating)
    fit_text(draw, rating_text, SLOT_RATING, "SemiBold", 20, 12, cf_rating_color(data.rating))
    fit_text(draw, _title(data.cf_rank), SLOT_CF_RANK, "SemiBold", 16, 11, handle_color)
    max_text = "-" if data.max_rating is None else str(data.max_rating)
    fit_text(draw, max_text, SLOT_MAX, "SemiBold", 20, 12, cf_rating_color(data.max_rating))
    fit_text(draw, data.last_seen, SLOT_LAST_SEEN, "Medium", 16, 11, WHITE)
    fit_text(draw, str(data.solved_count), SLOT_SOLVED, "SemiBold", 20, 12, WHITE)
    fit_text(draw, str(data.streak), SLOT_STREAK, "SemiBold", 20, 12, WHITE)

    x0, y0, x1, y1 = SLOT_LAST_SOLVED
    row_h = (y1 - y0) // 3
    for i, line in enumerate(data.last_solved[:3]):
        box = (x0 + 8, y0 + i * row_h, x1 - 8, y0 + (i + 1) * row_h)
        fit_text(draw, line, box, "Regular", 16, 12, WHITE, align="left")

    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
