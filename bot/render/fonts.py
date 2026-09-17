from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
FONT_DIR = ASSETS_DIR / "fonts"


@lru_cache(maxsize=256)
def get_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Poppins-{weight}.ttf"), size)
