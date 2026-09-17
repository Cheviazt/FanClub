from PIL import Image, ImageDraw

from bot.render.fonts import get_font
from bot.render.text import fit_text, truncate


def test_get_font_loads_all_weights():
    for w in ("Regular", "Medium", "SemiBold", "Bold"):
        assert get_font(w, 20).size == 20


def test_truncate_adds_ellipsis():
    font = get_font("Regular", 20)
    long = "A" * 200
    out = truncate(font, long, 100)
    assert out.endswith("…")
    assert font.getlength(out) <= 100


def test_truncate_keeps_short():
    font = get_font("Regular", 20)
    assert truncate(font, "abc", 500) == "abc"


def test_fit_text_draws_without_error():
    im = Image.new("RGB", (300, 60))
    draw = ImageDraw.Draw(im)
    fit_text(draw, "x" * 80, (0, 0, 300, 60), "Bold", 30, 12, "#FFFFFF")
    fit_text(draw, "short", (0, 0, 300, 60), "Bold", 30, 12, "#FFFFFF", align="left")
    assert im.getbbox() is not None
