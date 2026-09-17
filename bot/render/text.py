from PIL import ImageDraw, ImageFont

from bot.render.fonts import get_font

Box = tuple[int, int, int, int]
ELLIPSIS = "…"


def truncate(font: ImageFont.FreeTypeFont, text: str, max_width: float) -> str:
    if font.getlength(text) <= max_width:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.getlength(text[:mid] + ELLIPSIS) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ELLIPSIS


def fit_font(text: str, max_width: float, weight: str, max_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > min_size and get_font(weight, size).getlength(text) > max_width:
        size -= 1
    return get_font(weight, size)


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: Box,
    weight: str,
    max_size: int,
    min_size: int,
    fill: str,
    align: str = "center",
) -> None:
    x0, y0, x1, y1 = box
    width = x1 - x0
    font = fit_font(text, width, weight, max_size, min_size)
    shown = truncate(font, text, width)
    cy = (y0 + y1) / 2
    if align == "left":
        draw.text((x0, cy), shown, font=font, fill=fill, anchor="lm")
    elif align == "right":
        draw.text((x1, cy), shown, font=font, fill=fill, anchor="rm")
    else:
        draw.text(((x0 + x1) / 2, cy), shown, font=font, fill=fill, anchor="mm")
