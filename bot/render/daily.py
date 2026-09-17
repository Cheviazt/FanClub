import io

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import MUTED, WHITE, cf_rating_color
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import fit_text, truncate

BOXES: tuple[tuple[int, int, int, int], ...] = ((163, 130, 810, 266), (163, 283, 810, 419), (163, 436, 810, 572))
PADDING = 28
TITLE_Y = 54
TAGS_Y = 98
RATING_WIDTH = 100


def render_daily(problems: list[Problem]) -> bytes:
    base = Image.open(ASSETS_DIR / "daily.png").convert("RGB")
    draw = ImageDraw.Draw(base)
    for problem, (x0, y0, x1, y1) in zip(problems, BOXES):
        left = x0 + PADDING
        right = x1 - PADDING
        title_box = (left, y0 + TITLE_Y - 14, right - RATING_WIDTH, y0 + TITLE_Y + 14)
        fit_text(draw, f"{problem.code} · {problem.name}", title_box, "SemiBold", 26, 14, WHITE, align="left")
        rating_text = "?" if problem.rating is None else str(problem.rating)
        rating_box = (right - RATING_WIDTH, y0 + TITLE_Y - 14, right, y0 + TITLE_Y + 14)
        fit_text(draw, rating_text, rating_box, "Bold", 26, 14, cf_rating_color(problem.rating), align="right")
        tags_font = get_font("Regular", 17)
        tags = " · ".join(problem.tags) if problem.tags else "no tags"
        draw.text((left, y0 + TAGS_Y), truncate(tags_font, tags, right - left), font=tags_font, fill=MUTED, anchor="lm")
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
