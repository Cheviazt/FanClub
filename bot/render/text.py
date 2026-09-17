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
    strike: bool = False,
) -> None:
    x0, y0, x1, y1 = box
    width = x1 - x0
    font = fit_font(text, width, weight, max_size, min_size)
    shown = truncate(font, text, width)
    cy = (y0 + y1) / 2
    shown_width = font.getlength(shown)
    if align == "left":
        draw.text((x0, cy), shown, font=font, fill=fill, anchor="lm")
        start = x0
    elif align == "right":
        draw.text((x1, cy), shown, font=font, fill=fill, anchor="rm")
        start = x1 - shown_width
    else:
        draw.text(((x0 + x1) / 2, cy), shown, font=font, fill=fill, anchor="mm")
        start = (x0 + x1) / 2 - shown_width / 2
    if strike and shown:
        thickness = max(2, font.size // 12)
        draw.line((start, cy, start + shown_width, cy), fill=fill, width=thickness)


def wrap_lines(font: ImageFont.FreeTypeFont, text: str, max_width: float, max_lines: int, separator: str = " ") -> list[str]:
    words = text.split(separator)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + separator + word
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        rest = separator.join(lines[max_lines - 1:])
        lines = lines[: max_lines - 1] + [rest]
    return [truncate(font, line, max_width) for line in lines]
