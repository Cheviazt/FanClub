import io

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import MUTED, WHITE, cf_rating_color
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import Box, fit_text, truncate

TEMPLATE = ASSETS_DIR / "grinding.png"
BOX: Box = (143, 134, 830, 567)
PADDING_X = 30
PADDING_Y = 18
RATING_WIDTH = 100
DIVIDER = "#2E4A78"


def row_boxes(count: int) -> list[Box]:
    x0, y0, x1, y1 = BOX
    height = (y1 - y0 - 2 * PADDING_Y) / max(count, 1)
    top = y0 + PADDING_Y
    return [(x0, round(top + i * height), x1, round(top + (i + 1) * height)) for i in range(count)]


def render_grinding(problems: list[Problem], solved: set[tuple[int, str]] | None = None) -> bytes:
    base = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(base)
    done = solved or set()
    rows = row_boxes(len(problems))
    for index, (problem, (x0, y0, x1, y1)) in enumerate(zip(problems, rows)):
        left = x0 + PADDING_X
        right = x1 - PADDING_X
        height = y1 - y0
        title_size = max(18, min(30, round(height * 0.26)))
        tags_size = max(13, min(19, round(height * 0.16)))
        center_y = (y0 + y1) / 2
        title_cy = center_y - min(height * 0.16, 20)
        tags_cy = center_y + min(height * 0.18, 26)
        is_done = problem.key in done
        title_box = (left, round(title_cy - title_size), right - RATING_WIDTH, round(title_cy + title_size))
        fit_text(draw, f"{problem.code} · {problem.name}", title_box, "SemiBold", title_size, 20, MUTED if is_done else WHITE, align="left", strike=is_done)
        rating_text = "?" if problem.rating is None else str(problem.rating)
        rating_box = (right - RATING_WIDTH, round(title_cy - title_size), right, round(title_cy + title_size))
        fit_text(draw, rating_text, rating_box, "Bold", title_size, 14, cf_rating_color(problem.rating), align="right")
        tags_font = get_font("Regular", tags_size)
        tags = " · ".join(problem.tags) if problem.tags else "no tags"
        draw.text((left, tags_cy), truncate(tags_font, tags, right - left), font=tags_font, fill=MUTED, anchor="lm")
        if index < len(rows) - 1:
            draw.line((left, y1, right, y1), fill=DIVIDER, width=2)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
