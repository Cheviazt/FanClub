import io

from PIL import Image, ImageDraw

from bot.render.colors import DISCORD_RANK_COLORS, GRAY, WHITE
from bot.render.fonts import ASSETS_DIR
from bot.render.text import Box, fit_text
from bot.services.leaderboard import LeaderboardRow

ROWS: tuple[tuple[int, int], ...] = ((204, 244), (249, 288), (293, 332), (337, 377), (381, 421), (426, 465), (470, 509))
COL_NO: tuple[int, int] = (190, 240)
COL_USERNAME: tuple[int, int] = (324, 624)
COL_VALUE: tuple[int, int] = (650, 750)
PAGE_PILL: Box = (448, 581, 526, 621)


def render_leaderboard(kind: str, rows: list[LeaderboardRow], page: int, total_pages: int) -> bytes:
    base = Image.open(ASSETS_DIR / f"lb_{kind}.png").convert("RGB")
    draw = ImageDraw.Draw(base)
    for row, (y0, y1) in zip(rows, ROWS):
        color = DISCORD_RANK_COLORS.get(row.rank_name, GRAY)
        fit_text(draw, str(row.no), (COL_NO[0], y0, COL_NO[1], y1), "Medium", 20, 14, WHITE)
        fit_text(draw, row.handle, (COL_USERNAME[0], y0, COL_USERNAME[1], y1), "Medium", 20, 14, color, align="left")
        fit_text(draw, row.value, (COL_VALUE[0], y0, COL_VALUE[1], y1), "Medium", 20, 14, WHITE)
    fit_text(draw, f"{page}/{total_pages}", PAGE_PILL, "Medium", 16, 11, WHITE)
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
