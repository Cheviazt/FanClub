# Codeforces Discord Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot Discord yang menghubungkan akun Codeforces, memberi EXP/money/level/role dari solve baru, dan menyajikan profile, leaderboard, daily problem sebagai gambar.

**Architecture:** Monolit discord.py satu proses. Cogs tipis memanggil layer `services/` (logika murni, bisa di-unit-test), `db/repo/` (SQLAlchemy async), `cf/` (client Codeforces), `render/` (Pillow). Background `tasks.loop` di `cogs/poller.py` mendeteksi solve baru dan menyalurkan side effect Discord.

**Tech Stack:** Python 3.12, discord.py 2.x, httpx, Pillow, SQLAlchemy 2 async + asyncpg, Alembic, pydantic-settings, pytest + pytest-asyncio + respx + aiosqlite, Docker + docker-compose (PostgreSQL 16).

**Spec:** `docs/superpowers/specs/2026-09-16-cf-discord-bot-design.md`

## Global Constraints

- Commit tidak menyertakan `Co-Authored-By` atau atribusi AI apa pun.
- Kode tidak memakai komentar.
- Tidak ada emoji bergaya AI di kode, dokumen, pesan bot.
- Tidak ada em dash di teks apa pun.
- Python 3.12. Semua template gambar 974x650.
- Zona waktu hari: `Asia/Jakarta`.
- Jeda antar request Codeforces >= 2 detik.
- Rank Discord: Rookie 1-20, Elite 21-40, Specialist 41-80, Expert 81-120, Master 121-160, Grandmaster 161-200, Legendary 201-300, Legendary Master 301+.
- `threshold(n) = 100 * (n-1) * n / 2`. EXP per solve `rating // 10`. Money per solve `rating / 200` (2 desimal). Rating null: 0 dan 0.
- Perintah test: `python -m pytest -q` dari root repo.
- Setiap task diakhiri commit tanpa atribusi.

---

### Task 1: Scaffold proyek, config, Docker

**Files:**
- Create: `pyproject.toml`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `bot/__init__.py`, `bot/config.py`, `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `bot.config.Settings` dengan field `discord_token: str`, `guild_id: int`, `notify_channel_id: int`, `database_url: str`, `tz: str`, `log_level: str`; `bot.config.WIB: ZoneInfo`.

- [ ] **Step 1: Tulis `pyproject.toml`**

```toml
[project]
name = "fanclub-bot"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "discord.py>=2.4,<3",
    "httpx>=0.27",
    "Pillow>=10.4",
    "SQLAlchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic-settings>=2.4",
    "tzdata>=2024.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
    "aiosqlite>=0.20",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["bot*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
filterwarnings = [
    'ignore:Dialect sqlite\+pysqlite does \*not\* support Decimal objects natively:sqlalchemy.exc.SAWarning',
]
```

- [ ] **Step 2: Buat venv dan install**

Run:
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -U pip && .venv/Scripts/python -m pip install -e ".[dev]"
```
Expected: instalasi sukses tanpa error. Selanjutnya semua perintah `python` berarti `.venv/Scripts/python`.

- [ ] **Step 3: Tulis test config yang gagal**

`tests/test_config.py`:
```python
from bot.config import Settings, WIB


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "tok")
    monkeypatch.setenv("GUILD_ID", "123")
    monkeypatch.setenv("NOTIFY_CHANNEL_ID", "456")
    s = Settings(_env_file=None)
    assert s.discord_token == "tok"
    assert s.guild_id == 123
    assert s.notify_channel_id == 456
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.tz == "Asia/Jakarta"


def test_wib_zone():
    assert str(WIB) == "Asia/Jakarta"
```

- [ ] **Step 4: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'bot.config'`

- [ ] **Step 5: Tulis `bot/__init__.py` (kosong) dan `bot/config.py`**

```python
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

WIB = ZoneInfo("Asia/Jakarta")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_token: str
    guild_id: int
    notify_channel_id: int
    database_url: str = "postgresql+asyncpg://bot:bot@db:5432/bot"
    tz: str = "Asia/Jakarta"
    log_level: str = "INFO"
```

- [ ] **Step 6: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_config.py -q`
Expected: `2 passed`

- [ ] **Step 7: Tulis `.env.example`, `Dockerfile`, `docker-compose.yml`**

`.env.example`:
```
DISCORD_TOKEN=
GUILD_ID=
NOTIFY_CHANNEL_ID=
DATABASE_URL=postgresql+asyncpg://bot:bot@db:5432/bot
TZ=Asia/Jakarta
LOG_LEVEL=INFO
```

`Dockerfile`:
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml ./
COPY bot ./bot
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY bot ./bot
COPY assets ./assets
COPY alembic ./alembic
COPY alembic.ini ./
USER app
CMD ["sh", "-c", "alembic upgrade head && python -m bot"]
```

`docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: bot
      POSTGRES_PASSWORD: bot
      POSTGRES_DB: bot
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bot -d bot"]
      interval: 5s
      timeout: 3s
      retries: 10

  bot:
    build: .
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .env.example Dockerfile docker-compose.yml bot tests
git commit -m "chore: scaffold project, settings, docker"
```

---

### Task 2: Leveling service

**Files:**
- Create: `bot/services/__init__.py`, `bot/services/leveling.py`, `tests/test_leveling.py`

**Interfaces:**
- Produces:
  - `threshold(level: int) -> int`
  - `level_for(exp: int) -> int`
  - `exp_progress(exp: int) -> tuple[int, int]` (exp dalam level, kebutuhan level)
  - `@dataclass(frozen=True) Rank(name: str, color: str, min_level: int, max_level: int | None)`
  - `RANKS: tuple[Rank, ...]`
  - `rank_for(level: int) -> Rank`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_leveling.py`:
```python
import pytest

from bot.services.leveling import RANKS, exp_progress, level_for, rank_for, threshold


@pytest.mark.parametrize("level,expected", [(1, 0), (2, 100), (3, 300), (4, 600), (5, 1000)])
def test_threshold(level, expected):
    assert threshold(level) == expected


@pytest.mark.parametrize("exp,level", [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (450, 3), (600, 4), (1000, 5)])
def test_level_for(exp, level):
    assert level_for(exp) == level


def test_exp_progress():
    assert exp_progress(450) == (150, 300)
    assert exp_progress(0) == (0, 100)
    assert exp_progress(100) == (0, 200)


@pytest.mark.parametrize(
    "level,name",
    [
        (1, "Rookie"), (20, "Rookie"), (21, "Elite"), (40, "Elite"), (41, "Specialist"),
        (80, "Specialist"), (81, "Expert"), (120, "Expert"), (121, "Master"), (160, "Master"),
        (161, "Grandmaster"), (200, "Grandmaster"), (201, "Legendary"), (300, "Legendary"),
        (301, "Legendary Master"), (999, "Legendary Master"),
    ],
)
def test_rank_for(level, name):
    assert rank_for(level).name == name


def test_rank_colors():
    colors = {r.name: r.color for r in RANKS}
    assert colors["Rookie"] == "#9E9E9E"
    assert colors["Legendary Master"] == "#8B0000"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_leveling.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis `bot/services/__init__.py` (kosong) dan `bot/services/leveling.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Rank:
    name: str
    color: str
    min_level: int
    max_level: int | None


RANKS: tuple[Rank, ...] = (
    Rank("Rookie", "#9E9E9E", 1, 20),
    Rank("Elite", "#C0C0C0", 21, 40),
    Rank("Specialist", "#4CAF50", 41, 80),
    Rank("Expert", "#2196F3", 81, 120),
    Rank("Master", "#F44336", 121, 160),
    Rank("Grandmaster", "#FF9800", 161, 200),
    Rank("Legendary", "#FFEB3B", 201, 300),
    Rank("Legendary Master", "#8B0000", 301, None),
)

RANK_NAMES: tuple[str, ...] = tuple(r.name for r in RANKS)


def threshold(level: int) -> int:
    return 100 * (level - 1) * level // 2


def level_for(exp: int) -> int:
    level = 1
    while exp >= threshold(level + 1):
        level += 1
    return level


def exp_progress(exp: int) -> tuple[int, int]:
    level = level_for(exp)
    return exp - threshold(level), level * 100


def rank_for(level: int) -> Rank:
    for rank in RANKS:
        if rank.max_level is None or level <= rank.max_level:
            return rank
    return RANKS[-1]
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_leveling.py -q`
Expected: semua passed

- [ ] **Step 5: Commit**

```bash
git add bot/services tests/test_leveling.py
git commit -m "feat: add leveling service"
```

---

### Task 3: Rewards dan streak service

**Files:**
- Create: `bot/services/rewards.py`, `bot/services/streak.py`, `tests/test_rewards.py`, `tests/test_streak.py`

**Interfaces:**
- Produces:
  - `rewards.exp_for(rating: int | None) -> int`
  - `rewards.money_for(rating: int | None) -> Decimal` (quantize `0.01`)
  - `streak.today_wib(now: datetime | None = None) -> date`
  - `streak.next_streak(current: int, last_solve_date: date | None, today: date) -> int`
  - `streak.is_broken(last_solve_date: date | None, today: date) -> bool`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_rewards.py`:
```python
from decimal import Decimal

from bot.services.rewards import exp_for, money_for


def test_exp_for():
    assert exp_for(900) == 90
    assert exp_for(1600) == 160
    assert exp_for(None) == 0


def test_money_for():
    assert money_for(900) == Decimal("4.50")
    assert money_for(800) == Decimal("4.00")
    assert money_for(None) == Decimal("0.00")
```

`tests/test_streak.py`:
```python
from datetime import date, datetime, timezone

from bot.services.streak import is_broken, next_streak, today_wib


def test_today_wib_crosses_midnight():
    now = datetime(2026, 9, 16, 17, 30, tzinfo=timezone.utc)
    assert today_wib(now) == date(2026, 9, 17)


def test_next_streak():
    today = date(2026, 9, 16)
    assert next_streak(5, date(2026, 9, 16), today) == 5
    assert next_streak(5, date(2026, 9, 15), today) == 6
    assert next_streak(5, date(2026, 9, 10), today) == 1
    assert next_streak(0, None, today) == 1


def test_is_broken():
    today = date(2026, 9, 16)
    assert is_broken(date(2026, 9, 14), today) is True
    assert is_broken(date(2026, 9, 15), today) is False
    assert is_broken(date(2026, 9, 16), today) is False
    assert is_broken(None, today) is False
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_rewards.py tests/test_streak.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/services/rewards.py`:
```python
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def exp_for(rating: int | None) -> int:
    if rating is None:
        return 0
    return rating // 10


def money_for(rating: int | None) -> Decimal:
    if rating is None:
        return Decimal("0.00")
    return (Decimal(rating) / Decimal(200)).quantize(CENT, rounding=ROUND_HALF_UP)
```

`bot/services/streak.py`:
```python
from datetime import date, datetime, timedelta, timezone

from bot.config import WIB


def today_wib(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(WIB).date()


def next_streak(current: int, last_solve_date: date | None, today: date) -> int:
    if last_solve_date == today:
        return current
    if last_solve_date == today - timedelta(days=1):
        return current + 1
    return 1


def is_broken(last_solve_date: date | None, today: date) -> bool:
    if last_solve_date is None:
        return False
    return last_solve_date < today - timedelta(days=1)
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_rewards.py tests/test_streak.py -q`
Expected: semua passed

- [ ] **Step 5: Commit**

```bash
git add bot/services/rewards.py bot/services/streak.py tests/test_rewards.py tests/test_streak.py
git commit -m "feat: add rewards and streak services"
```

---

### Task 4: Font Poppins, warna, text fitting

**Files:**
- Create: `assets/fonts/Poppins-Regular.ttf`, `assets/fonts/Poppins-Medium.ttf`, `assets/fonts/Poppins-SemiBold.ttf`, `assets/fonts/Poppins-Bold.ttf`, `assets/fonts/OFL.txt`, `bot/render/__init__.py`, `bot/render/fonts.py`, `bot/render/colors.py`, `bot/render/text.py`, `tests/test_render_text.py`, `tests/test_colors.py`

**Interfaces:**
- Produces:
  - `fonts.ASSETS_DIR: Path` (root `assets/`), `fonts.get_font(weight: str, size: int) -> ImageFont.FreeTypeFont` (weight in `"Regular" | "Medium" | "SemiBold" | "Bold"`)
  - `colors.DISCORD_RANK_COLORS: dict[str, str]`, `colors.cf_rank_color(rank: str | None) -> str`, `colors.cf_rating_color(rating: int | None) -> str`, `colors.WHITE = "#FFFFFF"`, `colors.MUTED = "#B0BEC5"`
  - `text.Box = tuple[int, int, int, int]`
  - `text.fit_text(draw, text, box, weight, max_size, min_size, fill, align="center") -> None`
  - `text.truncate(font, text, max_width) -> str`

- [ ] **Step 1: Unduh font Poppins (OFL)**

Run:
```bash
mkdir -p assets/fonts && for w in Regular Medium SemiBold Bold; do curl -fsSL "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-$w.ttf" -o "assets/fonts/Poppins-$w.ttf"; done && curl -fsSL "https://github.com/google/fonts/raw/main/ofl/poppins/OFL.txt" -o assets/fonts/OFL.txt && ls -l assets/fonts
```
Expected: 4 file `.ttf` masing-masing > 100 KB, plus `OFL.txt`.

- [ ] **Step 2: Tulis test yang gagal**

`tests/test_colors.py`:
```python
from bot.render.colors import DISCORD_RANK_COLORS, cf_rank_color, cf_rating_color


def test_discord_rank_colors_match_leveling():
    from bot.services.leveling import RANKS
    for r in RANKS:
        assert DISCORD_RANK_COLORS[r.name] == r.color


def test_cf_rank_color():
    assert cf_rank_color("pupil") == "#008000"
    assert cf_rank_color("international grandmaster") == "#FF0000"
    assert cf_rank_color(None) == "#808080"


def test_cf_rating_color():
    assert cf_rating_color(900) == "#808080"
    assert cf_rating_color(1200) == "#008000"
    assert cf_rating_color(1600) == "#0000FF"
    assert cf_rating_color(None) == "#808080"
```

`tests/test_render_text.py`:
```python
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
```

- [ ] **Step 3: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_colors.py tests/test_render_text.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 4: Tulis implementasi**

`bot/render/__init__.py`: kosong.

`bot/render/fonts.py`:
```python
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
FONT_DIR = ASSETS_DIR / "fonts"


@lru_cache(maxsize=256)
def get_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Poppins-{weight}.ttf"), size)
```

`bot/render/colors.py`:
```python
from bot.services.leveling import RANKS

WHITE = "#FFFFFF"
MUTED = "#B0BEC5"
GRAY = "#808080"

DISCORD_RANK_COLORS: dict[str, str] = {r.name: r.color for r in RANKS}

CF_RANK_COLORS: dict[str, str] = {
    "newbie": GRAY,
    "pupil": "#008000",
    "specialist": "#03A89E",
    "expert": "#0000FF",
    "candidate master": "#AA00AA",
    "master": "#FF8C00",
    "international master": "#FF8C00",
    "grandmaster": "#FF0000",
    "international grandmaster": "#FF0000",
    "legendary grandmaster": "#FF0000",
}

CF_RATING_BANDS: tuple[tuple[int, str], ...] = (
    (1200, GRAY),
    (1400, "#008000"),
    (1600, "#03A89E"),
    (1900, "#0000FF"),
    (2100, "#AA00AA"),
    (2400, "#FF8C00"),
)


def cf_rank_color(rank: str | None) -> str:
    if not rank:
        return GRAY
    return CF_RANK_COLORS.get(rank.lower(), GRAY)


def cf_rating_color(rating: int | None) -> str:
    if rating is None:
        return GRAY
    for limit, color in CF_RATING_BANDS:
        if rating < limit:
            return color
    return "#FF0000"
```

`bot/render/text.py`:
```python
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
```

- [ ] **Step 5: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_colors.py tests/test_render_text.py -q`
Expected: semua passed

- [ ] **Step 6: Commit**

```bash
git add assets/fonts bot/render tests/test_colors.py tests/test_render_text.py
git commit -m "feat: add Poppins fonts, colors, text fitting"
```

---

### Task 5: Codeforces client

**Files:**
- Create: `bot/cf/__init__.py`, `bot/cf/models.py`, `bot/cf/client.py`, `tests/test_cf_client.py`

**Interfaces:**
- Produces:
  - `models.Problem(contest_id: int, index: str, name: str, rating: int | None, tags: tuple[str, ...])` dengan `key -> tuple[int, str]`, `code -> str` (`"1842B"`), `url -> str`
  - `models.Submission(id: int, problem: Problem, verdict: str | None, created_at: int)`
  - `models.UserInfo(handle: str, rating: int | None, max_rating: int | None, rank: str | None, max_rank: str | None, last_online: int, avatar_url: str)`
  - `models.problem_from_api(data: dict) -> Problem | None` (None jika tanpa `contestId`)
  - `client.CodeforcesError(Exception)`
  - `client.CodeforcesClient(http: httpx.AsyncClient | None = None, min_interval: float = 2.0, sleep=asyncio.sleep)` dengan `user_info(handles: list[str]) -> list[UserInfo]`, `user_status(handle: str, from_: int = 1, count: int = 30) -> list[Submission]`, `problemset_problems() -> list[Problem]`, `fetch_bytes(url: str) -> bytes`, `close()`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_cf_client.py`:
```python
import httpx
import pytest
import respx

from bot.cf.client import CodeforcesClient, CodeforcesError
from bot.cf.models import problem_from_api

BASE = "https://codeforces.com/api"


async def no_sleep(_: float) -> None:
    return None


def make_client() -> CodeforcesClient:
    return CodeforcesClient(http=httpx.AsyncClient(), min_interval=0, sleep=no_sleep)


def test_problem_from_api_without_contest_returns_none():
    assert problem_from_api({"index": "A", "name": "x"}) is None


@respx.mock
async def test_user_info_parses():
    respx.get(f"{BASE}/user.info").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "OK",
                "result": [
                    {
                        "handle": "tourist",
                        "rating": 3800,
                        "maxRating": 4000,
                        "rank": "legendary grandmaster",
                        "maxRank": "legendary grandmaster",
                        "lastOnlineTimeSeconds": 1700000000,
                        "titlePhoto": "//userpic.codeforces.org/x.jpg",
                    }
                ],
            },
        )
    )
    client = make_client()
    infos = await client.user_info(["tourist"])
    assert infos[0].rating == 3800
    assert infos[0].avatar_url == "https://userpic.codeforces.org/x.jpg"
    await client.close()


@respx.mock
async def test_user_info_unrated_has_none_rating():
    respx.get(f"{BASE}/user.info").mock(
        return_value=httpx.Response(
            200,
            json={"status": "OK", "result": [{"handle": "nb", "lastOnlineTimeSeconds": 1, "titlePhoto": "https://a/b.png"}]},
        )
    )
    client = make_client()
    info = (await client.user_info(["nb"]))[0]
    assert info.rating is None and info.rank is None
    await client.close()


@respx.mock
async def test_failed_status_raises():
    respx.get(f"{BASE}/user.info").mock(
        return_value=httpx.Response(400, json={"status": "FAILED", "comment": "handles: User with handle zz not found"})
    )
    client = make_client()
    with pytest.raises(CodeforcesError, match="not found"):
        await client.user_info(["zz"])
    await client.close()


@respx.mock
async def test_user_status_parses_and_skips_no_contest():
    respx.get(f"{BASE}/user.status").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "OK",
                "result": [
                    {"id": 1, "creationTimeSeconds": 10, "verdict": "OK",
                     "problem": {"contestId": 1842, "index": "B", "name": "Tenzing", "rating": 900, "tags": ["math"]}},
                    {"id": 2, "creationTimeSeconds": 11, "verdict": "OK",
                     "problem": {"index": "A", "name": "no contest"}},
                    {"id": 3, "creationTimeSeconds": 12,
                     "problem": {"contestId": 1, "index": "A", "name": "Theatre"}},
                ],
            },
        )
    )
    client = make_client()
    subs = await client.user_status("x", count=30)
    assert [s.id for s in subs] == [1, 3]
    assert subs[0].problem.code == "1842B"
    assert subs[0].problem.url == "https://codeforces.com/problemset/problem/1842/B"
    assert subs[1].verdict is None
    await client.close()


@respx.mock
async def test_retries_on_503():
    route = respx.get(f"{BASE}/problemset.problems")
    route.side_effect = [
        httpx.Response(503, text="busy"),
        httpx.Response(200, json={"status": "OK", "result": {"problems": [
            {"contestId": 1, "index": "A", "name": "T", "rating": 1000, "tags": []}], "problemStatistics": []}}),
    ]
    client = make_client()
    problems = await client.problemset_problems()
    assert len(problems) == 1 and route.call_count == 2
    await client.close()


@respx.mock
async def test_gives_up_after_three_attempts():
    respx.get(f"{BASE}/problemset.problems").mock(return_value=httpx.Response(503, text="busy"))
    client = make_client()
    with pytest.raises(CodeforcesError):
        await client.problemset_problems()
    await client.close()
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_cf_client.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/cf/__init__.py`: kosong.

`bot/cf/models.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    contest_id: int
    index: str
    name: str
    rating: int | None
    tags: tuple[str, ...]

    @property
    def key(self) -> tuple[int, str]:
        return self.contest_id, self.index

    @property
    def code(self) -> str:
        return f"{self.contest_id}{self.index}"

    @property
    def url(self) -> str:
        return f"https://codeforces.com/problemset/problem/{self.contest_id}/{self.index}"


@dataclass(frozen=True)
class Submission:
    id: int
    problem: Problem
    verdict: str | None
    created_at: int


@dataclass(frozen=True)
class UserInfo:
    handle: str
    rating: int | None
    max_rating: int | None
    rank: str | None
    max_rank: str | None
    last_online: int
    avatar_url: str

    @property
    def profile_url(self) -> str:
        return f"https://codeforces.com/profile/{self.handle}"


def problem_from_api(data: dict) -> Problem | None:
    if "contestId" not in data:
        return None
    return Problem(
        contest_id=int(data["contestId"]),
        index=str(data["index"]),
        name=str(data.get("name", "")),
        rating=data.get("rating"),
        tags=tuple(data.get("tags", [])),
    )


def submission_from_api(data: dict) -> Submission | None:
    problem = problem_from_api(data["problem"])
    if problem is None:
        return None
    return Submission(
        id=int(data["id"]),
        problem=problem,
        verdict=data.get("verdict"),
        created_at=int(data["creationTimeSeconds"]),
    )


def user_info_from_api(data: dict) -> UserInfo:
    photo = str(data.get("titlePhoto", ""))
    if photo.startswith("//"):
        photo = "https:" + photo
    return UserInfo(
        handle=str(data["handle"]),
        rating=data.get("rating"),
        max_rating=data.get("maxRating"),
        rank=data.get("rank"),
        max_rank=data.get("maxRank"),
        last_online=int(data.get("lastOnlineTimeSeconds", 0)),
        avatar_url=photo,
    )
```

`bot/cf/client.py`:
```python
import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from bot.cf.models import Problem, Submission, UserInfo, problem_from_api, submission_from_api, user_info_from_api

BASE_URL = "https://codeforces.com/api"
MAX_ATTEMPTS = 3


class CodeforcesError(Exception):
    pass


class CodeforcesClient:
    def __init__(
        self,
        http: httpx.AsyncClient | None = None,
        min_interval: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._http = http or httpx.AsyncClient(timeout=15.0)
        self._min_interval = min_interval
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def close(self) -> None:
        await self._http.aclose()

    async def _wait_turn(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            await self._sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    async def _get(self, method: str, **params: Any) -> Any:
        last_error: Exception | None = None
        async with self._lock:
            for attempt in range(MAX_ATTEMPTS):
                await self._wait_turn()
                try:
                    response = await self._http.get(f"{BASE_URL}/{method}", params=params)
                except httpx.HTTPError as exc:
                    last_error = exc
                    await self._sleep(2**attempt)
                    continue
                if response.status_code >= 500:
                    last_error = CodeforcesError(f"HTTP {response.status_code}")
                    await self._sleep(2**attempt)
                    continue
                payload = response.json()
                if payload.get("status") != "OK":
                    raise CodeforcesError(payload.get("comment", "unknown error"))
                return payload["result"]
        raise CodeforcesError(str(last_error))

    async def user_info(self, handles: list[str]) -> list[UserInfo]:
        result = await self._get("user.info", handles=";".join(handles))
        return [user_info_from_api(item) for item in result]

    async def user_status(self, handle: str, from_: int = 1, count: int = 30) -> list[Submission]:
        result = await self._get("user.status", handle=handle, **{"from": from_}, count=count)
        subs = (submission_from_api(item) for item in result)
        return [s for s in subs if s is not None]

    async def problemset_problems(self) -> list[Problem]:
        result = await self._get("problemset.problems")
        problems = (problem_from_api(item) for item in result["problems"])
        return [p for p in problems if p is not None]

    async def fetch_bytes(self, url: str) -> bytes:
        response = await self._http.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_cf_client.py -q`
Expected: semua passed

- [ ] **Step 5: Commit**

```bash
git add bot/cf tests/test_cf_client.py
git commit -m "feat: add Codeforces API client"
```

---

### Task 6: Model DB, session, Alembic

**Files:**
- Create: `bot/db/__init__.py`, `bot/db/models.py`, `bot/db/session.py`, `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_initial.py`, `tests/conftest.py`, `tests/test_models.py`

**Interfaces:**
- Produces:
  - `models.Base`, `models.User`, `models.SolvedProblem`, `models.DailyProblem`, `models.GuildRole`, `models.CfCache`, `models.ProblemsetCache`
  - `session.make_engine(url: str) -> AsyncEngine`, `session.make_session_factory(engine) -> async_sessionmaker[AsyncSession]`
  - fixture pytest `session` (AsyncSession di SQLite in-memory)

- [ ] **Step 1: Tulis `tests/conftest.py` dan test yang gagal**

`tests/conftest.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from bot.db.models import Base


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s
```

`tests/test_models.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from bot.db.models import SolvedProblem, User


async def test_create_user_and_solved(session):
    user = User(discord_id=1, handle="tourist", registered_at=datetime.now(timezone.utc))
    session.add(user)
    await session.commit()
    session.add(SolvedProblem(user_id=1, contest_id=1, index="A", solved_at=datetime.now(timezone.utc)))
    await session.commit()
    loaded = (await session.execute(select(User).where(User.discord_id == 1))).scalar_one()
    assert loaded.exp == 0 and loaded.money == Decimal("0.00") and loaded.streak == 0
    count = (await session.execute(select(SolvedProblem).where(SolvedProblem.user_id == 1))).scalars().all()
    assert len(count) == 1
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_models.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'bot.db'`

- [ ] **Step 3: Tulis `bot/db/__init__.py` (kosong), `bot/db/models.py`, `bot/db/session.py`**

`bot/db/models.py`:
```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    handle: Mapped[str] = mapped_column(String(64), unique=True)
    exp: Mapped[int] = mapped_column(Integer, default=0)
    money: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_solve_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SolvedProblem(Base):
    __tablename__ = "solved_problems"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    contest_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index: Mapped[str] = mapped_column(String(8), primary_key=True)
    solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailyProblem(Base):
    __tablename__ = "daily_problems"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    rating: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(Integer)
    index: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(255))
    tags: Mapped[list] = mapped_column(JSON, default=list)


class GuildRole(Base):
    __tablename__ = "guild_roles"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    rank_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger)


class CfCache(Base):
    __tablename__ = "cf_cache"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True, autoincrement=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_online: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProblemsetCache(Base):
    __tablename__ = "problemset_cache"

    contest_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    index: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

`bot/db/session.py`:
```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_models.py -q`
Expected: `1 passed`

- [ ] **Step 5: Setup Alembic (async)**

Run: `python -m alembic init -t async alembic`

Ganti isi `alembic/env.py` dengan:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from bot.config import Settings
from bot.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", Settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Di `alembic.ini`, pastikan `script_location = alembic` dan baris `sqlalchemy.url` dikosongkan (`sqlalchemy.url =`).

- [ ] **Step 6: Tulis migrasi awal secara manual**

`alembic/versions/0001_initial.py`:
```python
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("discord_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("handle", sa.String(64), nullable=False, unique=True),
        sa.Column("exp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("money", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_solve_date", sa.Date(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "solved_problems",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True),
        sa.Column("contest_id", sa.Integer(), primary_key=True),
        sa.Column("index", sa.String(8), primary_key=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "daily_problems",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("rating", sa.Integer(), primary_key=True),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.String(8), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
    )
    op.create_table(
        "guild_roles",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("rank_name", sa.String(32), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "cf_cache",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True, autoincrement=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("max_rating", sa.Integer(), nullable=True),
        sa.Column("rank", sa.String(64), nullable=True),
        sa.Column("max_rank", sa.String(64), nullable=True),
        sa.Column("last_online", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "problemset_cache",
        sa.Column("contest_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("index", sa.String(8), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problemset_cache_rating", "problemset_cache", ["rating"])


def downgrade() -> None:
    op.drop_index("ix_problemset_cache_rating", table_name="problemset_cache")
    op.drop_table("problemset_cache")
    op.drop_table("cf_cache")
    op.drop_table("guild_roles")
    op.drop_table("daily_problems")
    op.drop_table("solved_problems")
    op.drop_table("users")
```

- [ ] **Step 7: Verifikasi migrasi terhadap SQLite lokal**

Run:
```bash
DISCORD_TOKEN=x GUILD_ID=1 NOTIFY_CHANNEL_ID=1 DATABASE_URL=sqlite+aiosqlite:///./tmp_migrate.db python -m alembic upgrade head && rm -f tmp_migrate.db
```
Expected: log `Running upgrade  -> 0001_initial` tanpa error.

- [ ] **Step 8: Jalankan seluruh test lalu commit**

Run: `python -m pytest -q`
Expected: semua passed

```bash
git add bot/db alembic alembic.ini tests/conftest.py tests/test_models.py
git commit -m "feat: add database models and initial migration"
```

---

### Task 7: Repository layer

**Files:**
- Create: `bot/db/repo/__init__.py`, `bot/db/repo/users.py`, `bot/db/repo/solved.py`, `bot/db/repo/cf_cache.py`, `bot/db/repo/problemset.py`, `bot/db/repo/daily.py`, `bot/db/repo/roles.py`, `tests/test_repo.py`

**Interfaces:**
- Produces (semua `async`, argumen pertama `session: AsyncSession`):
  - `users.create_user(session, discord_id: int, handle: str) -> User`
  - `users.get_by_discord(session, discord_id: int) -> User | None`
  - `users.get_by_handle(session, handle: str) -> User | None` (case-insensitive)
  - `users.list_users(session) -> list[User]`
  - `solved.add_solved(session, user_id, contest_id, index, solved_at) -> bool` (False jika sudah ada)
  - `solved.bulk_add_solved(session, user_id, items: list[tuple[int, str, datetime]]) -> int`
  - `solved.solved_keys(session, user_id) -> set[tuple[int, str]]`
  - `solved.solved_count(session, user_id) -> int`
  - `solved.last_solved(session, user_id, limit: int = 3) -> list[SolvedProblem]`
  - `cf_cache.upsert_cf_cache(session, user_id, info: UserInfo, now: datetime) -> CfCache`
  - `cf_cache.get_cf_cache(session, user_id) -> CfCache | None`
  - `problemset.replace_problemset(session, problems: list[Problem], now: datetime) -> int`
  - `problemset.list_problems(session, rating: int | None = None) -> list[Problem]`
  - `problemset.get_problem(session, contest_id, index) -> Problem | None`
  - `problemset.count_problems(session) -> int`
  - `daily.get_daily(session, user_id, day: date) -> list[DailyProblem]`
  - `daily.save_daily(session, user_id, day: date, problems: list[Problem]) -> None`
  - `daily.daily_keys(session, user_id) -> set[tuple[int, str]]`
  - `roles.get_role_ids(session, guild_id) -> dict[str, int]`
  - `roles.set_role_id(session, guild_id, rank_name, role_id) -> None`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_repo.py`:
```python
from datetime import date, datetime, timezone

from bot.cf.models import Problem, UserInfo
from bot.db.repo import cf_cache, daily, problemset, roles, solved, users

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def P(cid, idx, rating=None, name="n", tags=()):
    return Problem(cid, idx, name, rating, tuple(tags))


async def test_users_crud(session):
    u = await users.create_user(session, 1, "Tourist")
    await session.commit()
    assert u.exp == 0
    assert (await users.get_by_discord(session, 1)).handle == "Tourist"
    assert (await users.get_by_handle(session, "tourist")).discord_id == 1
    assert await users.get_by_discord(session, 2) is None
    assert len(await users.list_users(session)) == 1


async def test_solved(session):
    await users.create_user(session, 1, "a")
    assert await solved.add_solved(session, 1, 1, "A", NOW) is True
    assert await solved.add_solved(session, 1, 1, "A", NOW) is False
    n = await solved.bulk_add_solved(session, 1, [(2, "B", NOW), (1, "A", NOW), (3, "C", NOW)])
    await session.commit()
    assert n == 2
    assert await solved.solved_keys(session, 1) == {(1, "A"), (2, "B"), (3, "C")}
    assert await solved.solved_count(session, 1) == 3
    assert len(await solved.last_solved(session, 1, limit=2)) == 2


async def test_cf_cache_upsert(session):
    await users.create_user(session, 1, "a")
    info = UserInfo("a", 1500, 1600, "specialist", "expert", 1700000000, "https://x/y.png")
    await cf_cache.upsert_cf_cache(session, 1, info, NOW)
    await session.commit()
    info2 = UserInfo("a", 1550, 1600, "specialist", "expert", 1700000001, "https://x/y.png")
    await cf_cache.upsert_cf_cache(session, 1, info2, NOW)
    await session.commit()
    row = await cf_cache.get_cf_cache(session, 1)
    assert row.rating == 1550


async def test_problemset(session):
    n = await problemset.replace_problemset(session, [P(1, "A", 900), P(1, "B", 1200), P(2, "A", None)], NOW)
    await session.commit()
    assert n == 3
    assert await problemset.count_problems(session) == 3
    assert [p.key for p in await problemset.list_problems(session, rating=900)] == [(1, "A")]
    assert len(await problemset.list_problems(session)) == 3
    assert (await problemset.get_problem(session, 1, "B")).rating == 1200
    await problemset.replace_problemset(session, [P(9, "Z", 800)], NOW)
    await session.commit()
    assert await problemset.count_problems(session) == 1


async def test_daily(session):
    await users.create_user(session, 1, "a")
    day = date(2026, 9, 16)
    assert await daily.get_daily(session, 1, day) == []
    await daily.save_daily(session, 1, day, [P(1, "A", 900, "x", ["math"]), P(2, "B", 1200), P(3, "C", 1600)])
    await session.commit()
    rows = await daily.get_daily(session, 1, day)
    assert [r.rating for r in rows] == [900, 1200, 1600]
    assert rows[0].tags == ["math"]
    assert await daily.daily_keys(session, 1) == {(1, "A"), (2, "B"), (3, "C")}


async def test_roles(session):
    assert await roles.get_role_ids(session, 10) == {}
    await roles.set_role_id(session, 10, "Rookie", 100)
    await roles.set_role_id(session, 10, "Rookie", 101)
    await session.commit()
    assert await roles.get_role_ids(session, 10) == {"Rookie": 101}
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_repo.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'bot.db.repo'`

- [ ] **Step 3: Tulis implementasi**

`bot/db/repo/__init__.py`: kosong.

`bot/db/repo/users.py`:
```python
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


async def create_user(session: AsyncSession, discord_id: int, handle: str) -> User:
    user = User(discord_id=discord_id, handle=handle, registered_at=datetime.now(timezone.utc))
    session.add(user)
    await session.flush()
    return user


async def get_by_discord(session: AsyncSession, discord_id: int) -> User | None:
    return await session.get(User, discord_id)


async def get_by_handle(session: AsyncSession, handle: str) -> User | None:
    stmt = select(User).where(func.lower(User.handle) == handle.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_users(session: AsyncSession) -> list[User]:
    return list((await session.execute(select(User).order_by(User.discord_id))).scalars().all())
```

`bot/db/repo/solved.py`:
```python
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import SolvedProblem


async def solved_keys(session: AsyncSession, user_id: int) -> set[tuple[int, str]]:
    stmt = select(SolvedProblem.contest_id, SolvedProblem.index).where(SolvedProblem.user_id == user_id)
    return {(cid, idx) for cid, idx in (await session.execute(stmt)).all()}


async def add_solved(session: AsyncSession, user_id: int, contest_id: int, index: str, solved_at: datetime) -> bool:
    existing = await session.get(SolvedProblem, (user_id, contest_id, index))
    if existing is not None:
        return False
    session.add(SolvedProblem(user_id=user_id, contest_id=contest_id, index=index, solved_at=solved_at))
    await session.flush()
    return True


async def bulk_add_solved(session: AsyncSession, user_id: int, items: list[tuple[int, str, datetime]]) -> int:
    existing = await solved_keys(session, user_id)
    added = 0
    for contest_id, index, solved_at in items:
        if (contest_id, index) in existing:
            continue
        existing.add((contest_id, index))
        session.add(SolvedProblem(user_id=user_id, contest_id=contest_id, index=index, solved_at=solved_at))
        added += 1
    await session.flush()
    return added


async def solved_count(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(SolvedProblem).where(SolvedProblem.user_id == user_id)
    return int((await session.execute(stmt)).scalar_one())


async def last_solved(session: AsyncSession, user_id: int, limit: int = 3) -> list[SolvedProblem]:
    stmt = (
        select(SolvedProblem)
        .where(SolvedProblem.user_id == user_id)
        .order_by(SolvedProblem.solved_at.desc(), SolvedProblem.contest_id.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
```

`bot/db/repo/cf_cache.py`:
```python
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import UserInfo
from bot.db.models import CfCache


async def upsert_cf_cache(session: AsyncSession, user_id: int, info: UserInfo, now: datetime) -> CfCache:
    row = await session.get(CfCache, user_id)
    if row is None:
        row = CfCache(user_id=user_id)
        session.add(row)
    row.rating = info.rating
    row.max_rating = info.max_rating
    row.rank = info.rank
    row.max_rank = info.max_rank
    row.last_online = datetime.fromtimestamp(info.last_online, tz=timezone.utc)
    row.avatar_url = info.avatar_url
    row.updated_at = now
    await session.flush()
    return row


async def get_cf_cache(session: AsyncSession, user_id: int) -> CfCache | None:
    return await session.get(CfCache, user_id)
```

`bot/db/repo/problemset.py`:
```python
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.models import ProblemsetCache


def _to_problem(row: ProblemsetCache) -> Problem:
    return Problem(row.contest_id, row.index, row.name, row.rating, tuple(row.tags or []))


async def replace_problemset(session: AsyncSession, problems: list[Problem], now: datetime) -> int:
    await session.execute(delete(ProblemsetCache))
    seen: set[tuple[int, str]] = set()
    rows = []
    for p in problems:
        if p.key in seen:
            continue
        seen.add(p.key)
        rows.append(ProblemsetCache(contest_id=p.contest_id, index=p.index, name=p.name, rating=p.rating, tags=list(p.tags), fetched_at=now))
    session.add_all(rows)
    await session.flush()
    return len(rows)


async def list_problems(session: AsyncSession, rating: int | None = None) -> list[Problem]:
    stmt = select(ProblemsetCache)
    if rating is not None:
        stmt = stmt.where(ProblemsetCache.rating == rating)
    return [_to_problem(r) for r in (await session.execute(stmt)).scalars().all()]


async def get_problem(session: AsyncSession, contest_id: int, index: str) -> Problem | None:
    row = await session.get(ProblemsetCache, (contest_id, index))
    return None if row is None else _to_problem(row)


async def count_problems(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(ProblemsetCache))).scalar_one())
```

`bot/db/repo/daily.py`:
```python
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.models import DailyProblem


async def get_daily(session: AsyncSession, user_id: int, day: date) -> list[DailyProblem]:
    stmt = select(DailyProblem).where(DailyProblem.user_id == user_id, DailyProblem.date == day).order_by(DailyProblem.rating)
    return list((await session.execute(stmt)).scalars().all())


async def save_daily(session: AsyncSession, user_id: int, day: date, problems: list[Problem]) -> None:
    for p in problems:
        session.add(DailyProblem(user_id=user_id, date=day, rating=p.rating, contest_id=p.contest_id, index=p.index, name=p.name, tags=list(p.tags)))
    await session.flush()


async def daily_keys(session: AsyncSession, user_id: int) -> set[tuple[int, str]]:
    stmt = select(DailyProblem.contest_id, DailyProblem.index).where(DailyProblem.user_id == user_id)
    return {(cid, idx) for cid, idx in (await session.execute(stmt)).all()}
```

`bot/db/repo/roles.py`:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import GuildRole


async def get_role_ids(session: AsyncSession, guild_id: int) -> dict[str, int]:
    rows = (await session.execute(select(GuildRole).where(GuildRole.guild_id == guild_id))).scalars().all()
    return {r.rank_name: r.role_id for r in rows}


async def set_role_id(session: AsyncSession, guild_id: int, rank_name: str, role_id: int) -> None:
    row = await session.get(GuildRole, (guild_id, rank_name))
    if row is None:
        session.add(GuildRole(guild_id=guild_id, rank_name=rank_name, role_id=role_id))
    else:
        row.role_id = role_id
    await session.flush()
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_repo.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/db/repo tests/test_repo.py
git commit -m "feat: add repository layer"
```

---

### Task 8: Solve detector dan solve processor

**Files:**
- Create: `bot/services/solve_detector.py`, `bot/services/solve_processor.py`, `tests/test_solve_detector.py`, `tests/test_solve_processor.py`

**Interfaces:**
- Produces:
  - `solve_detector.detect_new_solves(submissions: list[Submission], solved: set[tuple[int, str]]) -> list[Submission]` (hanya `verdict == "OK"`, belum solved, unik per problem, urut `created_at` naik)
  - `solve_processor.SolveResult(discord_id: int, handle: str, problem: Problem, exp_gained: int, money_gained: Decimal, old_level: int, new_level: int, old_rank: str, new_rank: str, streak: int)`
  - `solve_processor.process_user(session, discord_id: int, submissions: list[Submission], today: date) -> list[SolveResult]` (commit di dalam)

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_solve_detector.py`:
```python
from bot.cf.models import Problem, Submission
from bot.services.solve_detector import detect_new_solves


def S(id, cid, idx, verdict, t):
    return Submission(id, Problem(cid, idx, "n", 800, ()), verdict, t)


def test_detect_new_solves():
    subs = [
        S(5, 1, "A", "OK", 50),
        S(4, 2, "B", "OK", 40),
        S(3, 2, "B", "OK", 30),
        S(2, 3, "C", "WRONG_ANSWER", 20),
        S(1, 4, "D", "OK", 10),
    ]
    out = detect_new_solves(subs, {(4, "D")})
    assert [(s.problem.key, s.id) for s in out] == [((2, "B"), 3), ((1, "A"), 5)]


def test_detect_ignores_none_verdict():
    assert detect_new_solves([S(1, 1, "A", None, 1)], set()) == []
```

`tests/test_solve_processor.py`:
```python
from datetime import date, datetime, timezone
from decimal import Decimal

from bot.cf.models import Problem, Submission
from bot.db.repo import solved, users
from bot.services.solve_processor import process_user


def S(id, cid, idx, rating, t):
    return Submission(id, Problem(cid, idx, "n", rating, ()), "OK", t)


async def test_process_user_rewards_and_streak(session):
    await users.create_user(session, 1, "a")
    await solved.add_solved(session, 1, 9, "Z", datetime(2026, 1, 1, tzinfo=timezone.utc))
    await session.commit()
    today = date(2026, 9, 16)
    results = await process_user(session, 1, [S(1, 1, "A", 900, 100), S(2, 9, "Z", 3000, 200), S(3, 2, "B", None, 300)], today)
    assert [r.problem.key for r in results] == [(1, "A"), (2, "B")]
    assert results[0].exp_gained == 90 and results[0].money_gained == Decimal("4.50")
    assert results[1].exp_gained == 0 and results[1].money_gained == Decimal("0.00")
    assert results[0].streak == 1
    user = await users.get_by_discord(session, 1)
    assert user.exp == 90 and user.money == Decimal("4.50") and user.streak == 1 and user.last_solve_date == today
    assert await solved.solved_count(session, 1) == 3


async def test_process_user_level_up(session):
    u = await users.create_user(session, 1, "a")
    u.exp = 95
    await session.commit()
    results = await process_user(session, 1, [S(1, 1, "A", 100, 1)], date(2026, 9, 16))
    assert results[0].old_level == 1 and results[0].new_level == 2
    assert results[0].old_rank == "Rookie" and results[0].new_rank == "Rookie"


async def test_process_user_second_call_is_noop(session):
    await users.create_user(session, 1, "a")
    await session.commit()
    subs = [S(1, 1, "A", 900, 1)]
    await process_user(session, 1, subs, date(2026, 9, 16))
    assert await process_user(session, 1, subs, date(2026, 9, 16)) == []
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_solve_detector.py tests/test_solve_processor.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/services/solve_detector.py`:
```python
from bot.cf.models import Submission


def detect_new_solves(submissions: list[Submission], solved: set[tuple[int, str]]) -> list[Submission]:
    earliest: dict[tuple[int, str], Submission] = {}
    for sub in submissions:
        if sub.verdict != "OK":
            continue
        key = sub.problem.key
        if key in solved:
            continue
        current = earliest.get(key)
        if current is None or sub.created_at < current.created_at:
            earliest[key] = sub
    return sorted(earliest.values(), key=lambda s: (s.created_at, s.id))
```

`bot/services/solve_processor.py`:
```python
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem, Submission
from bot.db.repo import solved, users
from bot.services.leveling import level_for, rank_for
from bot.services.rewards import exp_for, money_for
from bot.services.solve_detector import detect_new_solves
from bot.services.streak import next_streak


@dataclass(frozen=True)
class SolveResult:
    discord_id: int
    handle: str
    problem: Problem
    exp_gained: int
    money_gained: Decimal
    old_level: int
    new_level: int
    old_rank: str
    new_rank: str
    streak: int


async def process_user(session: AsyncSession, discord_id: int, submissions: list[Submission], today: date) -> list[SolveResult]:
    user = await users.get_by_discord(session, discord_id)
    if user is None:
        return []
    known = await solved.solved_keys(session, discord_id)
    results: list[SolveResult] = []
    for sub in detect_new_solves(submissions, known):
        solved_at = datetime.fromtimestamp(sub.created_at, tz=timezone.utc)
        if not await solved.add_solved(session, discord_id, sub.problem.contest_id, sub.problem.index, solved_at):
            continue
        old_level = level_for(user.exp)
        exp_gain = exp_for(sub.problem.rating)
        money_gain = money_for(sub.problem.rating)
        user.exp += exp_gain
        user.money = Decimal(user.money) + money_gain
        user.streak = next_streak(user.streak, user.last_solve_date, today)
        user.last_solve_date = today
        new_level = level_for(user.exp)
        results.append(
            SolveResult(
                discord_id=discord_id,
                handle=user.handle,
                problem=sub.problem,
                exp_gained=exp_gain,
                money_gained=money_gain,
                old_level=old_level,
                new_level=new_level,
                old_rank=rank_for(old_level).name,
                new_rank=rank_for(new_level).name,
                streak=user.streak,
            )
        )
    await session.commit()
    return results
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_solve_detector.py tests/test_solve_processor.py -q`
Expected: semua passed

- [ ] **Step 5: Commit**

```bash
git add bot/services/solve_detector.py bot/services/solve_processor.py tests/test_solve_detector.py tests/test_solve_processor.py
git commit -m "feat: add solve detection and reward processing"
```

---

### Task 9: Register service

**Files:**
- Create: `bot/services/register.py`, `tests/test_register_service.py`

**Interfaces:**
- Consumes: `CodeforcesClient.user_status`, `Submission`, `Problem`
- Produces:
  - `PendingRegistration(discord_id: int, handle: str, problem: Problem, started_at: int, deadline: int)`
  - `is_verification(sub: Submission, pending: PendingRegistration) -> bool`
  - `RegisterService(client, timeout: int = 300, interval: int = 10, sleep=asyncio.sleep, clock=time.time)` dengan:
    - `pending: dict[int, PendingRegistration]`
    - `start(discord_id, handle, problem) -> PendingRegistration` (raise `RegistrationInProgress` jika sudah ada)
    - `wait_for_verification(pending) -> bool` (hapus dari `pending` saat selesai)
    - `fetch_all_accepted(handle) -> list[Submission]` (paginasi 1000, hanya `verdict == "OK"`)
  - `RegistrationInProgress(Exception)`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_register_service.py`:
```python
import pytest

from bot.cf.models import Problem, Submission
from bot.services.register import PendingRegistration, RegisterService, RegistrationInProgress, is_verification

PROBLEM = Problem(1, "A", "T", 800, ())


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = 0

    async def user_status(self, handle, from_=1, count=30):
        self.calls += 1
        if self.pages:
            return self.pages.pop(0)
        return []


async def no_sleep(_):
    return None


def test_is_verification():
    pending = PendingRegistration(1, "h", PROBLEM, 100, 400)
    assert is_verification(Submission(1, PROBLEM, "COMPILATION_ERROR", 150), pending)
    assert not is_verification(Submission(1, PROBLEM, "COMPILATION_ERROR", 50), pending)
    assert not is_verification(Submission(1, PROBLEM, "OK", 150), pending)
    assert not is_verification(Submission(1, Problem(2, "B", "x", None, ()), "COMPILATION_ERROR", 150), pending)


async def test_start_rejects_duplicate():
    svc = RegisterService(FakeClient([]), sleep=no_sleep, clock=lambda: 100)
    svc.start(1, "h", PROBLEM)
    with pytest.raises(RegistrationInProgress):
        svc.start(1, "h", PROBLEM)


async def test_wait_success():
    client = FakeClient([[], [Submission(1, PROBLEM, "COMPILATION_ERROR", 120)]])
    svc = RegisterService(client, timeout=300, interval=10, sleep=no_sleep, clock=lambda: 100)
    pending = svc.start(1, "h", PROBLEM)
    assert await svc.wait_for_verification(pending) is True
    assert 1 not in svc.pending
    assert client.calls == 2


async def test_wait_timeout():
    times = iter([100, 100, 200, 300, 401])
    svc = RegisterService(FakeClient([]), timeout=300, interval=10, sleep=no_sleep, clock=lambda: next(times))
    pending = svc.start(1, "h", PROBLEM)
    assert await svc.wait_for_verification(pending) is False
    assert 1 not in svc.pending


async def test_fetch_all_accepted_paginates():
    ok = lambda i: Submission(i, Problem(i, "A", "x", None, ()), "OK", i)
    page1 = [ok(i) for i in range(1000)]
    page2 = [ok(1000), Submission(2000, PROBLEM, "WRONG_ANSWER", 5)]
    client = FakeClient([page1, page2])
    svc = RegisterService(client, sleep=no_sleep)
    subs = await svc.fetch_all_accepted("h")
    assert len(subs) == 1001 and client.calls == 2
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_register_service.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/services/register.py`:
```python
import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from bot.cf.models import Problem, Submission

PAGE_SIZE = 1000


class RegistrationInProgress(Exception):
    pass


@dataclass(frozen=True)
class PendingRegistration:
    discord_id: int
    handle: str
    problem: Problem
    started_at: int
    deadline: int


def is_verification(sub: Submission, pending: PendingRegistration) -> bool:
    return (
        sub.verdict == "COMPILATION_ERROR"
        and sub.problem.key == pending.problem.key
        and sub.created_at >= pending.started_at
    )


class RegisterService:
    def __init__(
        self,
        client,
        timeout: int = 300,
        interval: int = 10,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._timeout = timeout
        self._interval = interval
        self._sleep = sleep
        self._clock = clock
        self.pending: dict[int, PendingRegistration] = {}

    def start(self, discord_id: int, handle: str, problem: Problem) -> PendingRegistration:
        if discord_id in self.pending:
            raise RegistrationInProgress()
        now = int(self._clock())
        pending = PendingRegistration(discord_id, handle, problem, now, now + self._timeout)
        self.pending[discord_id] = pending
        return pending

    async def wait_for_verification(self, pending: PendingRegistration) -> bool:
        try:
            while self._clock() <= pending.deadline:
                subs = await self._client.user_status(pending.handle, from_=1, count=10)
                if any(is_verification(s, pending) for s in subs):
                    return True
                await self._sleep(self._interval)
            return False
        finally:
            self.pending.pop(pending.discord_id, None)

    async def fetch_all_accepted(self, handle: str) -> list[Submission]:
        accepted: list[Submission] = []
        start = 1
        while True:
            page = await self._client.user_status(handle, from_=start, count=PAGE_SIZE)
            accepted.extend(s for s in page if s.verdict == "OK")
            if len(page) < PAGE_SIZE:
                return accepted
            start += PAGE_SIZE
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_register_service.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/services/register.py tests/test_register_service.py
git commit -m "feat: add register verification service"
```

---

### Task 10: Daily dan leaderboard service

**Files:**
- Create: `bot/services/daily.py`, `bot/services/leaderboard.py`, `tests/test_daily_service.py`, `tests/test_leaderboard_service.py`

**Interfaces:**
- Produces:
  - `daily.DAILY_RATINGS = (900, 1200, 1600)`
  - `daily.NotEnoughProblems(Exception)`
  - `daily.get_or_create_daily(session, user_id: int, day: date, rng: random.Random | None = None) -> list[Problem]` (commit di dalam saat membuat)
  - `leaderboard.LEADERBOARD_TYPES = ("level", "rating", "solved", "streaks")`
  - `leaderboard.PER_PAGE = 7`
  - `leaderboard.LeaderboardRow(no: int, handle: str, rank_name: str, value: str)`
  - `leaderboard.fetch_page(session, kind: str, page: int) -> tuple[list[LeaderboardRow], int]` (page mulai 1, total_pages minimal 1)

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_daily_service.py`:
```python
import random
from datetime import date, datetime, timezone

import pytest

from bot.cf.models import Problem
from bot.db.repo import problemset, solved, users
from bot.services.daily import NotEnoughProblems, get_or_create_daily

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def P(cid, rating):
    return Problem(cid, "A", f"p{cid}", rating, ("math",))


async def test_daily_excludes_solved_and_is_stable(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(2, 900), P(3, 1200), P(4, 1600)], NOW)
    await solved.add_solved(session, 1, 1, "A", NOW)
    await session.commit()
    day = date(2026, 9, 16)
    first = await get_or_create_daily(session, 1, day, random.Random(0))
    assert [p.rating for p in first] == [900, 1200, 1600]
    assert first[0].key == (2, "A")
    again = await get_or_create_daily(session, 1, day)
    assert [p.key for p in again] == [p.key for p in first]


async def test_daily_excludes_previous_daily(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(2, 900), P(3, 1200), P(4, 1600)], NOW)
    await session.commit()
    d1 = await get_or_create_daily(session, 1, date(2026, 9, 16), random.Random(0))
    d2 = await get_or_create_daily(session, 1, date(2026, 9, 17), random.Random(0))
    assert d1[0].key != d2[0].key


async def test_daily_raises_when_empty(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(session, [P(1, 900), P(3, 1200)], NOW)
    await session.commit()
    with pytest.raises(NotEnoughProblems):
        await get_or_create_daily(session, 1, date(2026, 9, 16))
```

`tests/test_leaderboard_service.py`:
```python
from datetime import datetime, timezone

from bot.cf.models import UserInfo
from bot.db.repo import cf_cache, solved, users
from bot.services.leaderboard import PER_PAGE, fetch_page

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


async def seed(session, n):
    for i in range(1, n + 1):
        u = await users.create_user(session, i, f"h{i}")
        u.exp = i * 100
        u.streak = n - i
        await cf_cache.upsert_cf_cache(session, i, UserInfo(f"h{i}", 1000 + i if i % 2 else None, 1500, "pupil", "pupil", 1, ""), NOW)
        for j in range(i):
            await solved.add_solved(session, i, j, "A", NOW)
    await session.commit()


async def test_level_pages(session):
    await seed(session, 9)
    rows, total = await fetch_page(session, "level", 1)
    assert total == 2 and len(rows) == PER_PAGE
    assert rows[0].handle == "h9" and rows[0].no == 1
    rows2, _ = await fetch_page(session, "level", 2)
    assert [r.handle for r in rows2] == ["h2", "h1"] and rows2[0].no == 8


async def test_rating_null_as_zero(session):
    await seed(session, 4)
    rows, _ = await fetch_page(session, "rating", 1)
    assert [r.handle for r in rows] == ["h3", "h1", "h2", "h4"]
    assert rows[0].value == "1003" and rows[-1].value == "0"


async def test_solved_and_streaks(session):
    await seed(session, 3)
    rows, _ = await fetch_page(session, "solved", 1)
    assert [r.value for r in rows] == ["3", "2", "1"]
    rows, _ = await fetch_page(session, "streaks", 1)
    assert [r.handle for r in rows] == ["h1", "h2", "h3"]


async def test_empty(session):
    rows, total = await fetch_page(session, "level", 1)
    assert rows == [] and total == 1
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_daily_service.py tests/test_leaderboard_service.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/services/daily.py`:
```python
import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.models import Problem
from bot.db.repo import daily, problemset, solved

DAILY_RATINGS: tuple[int, ...] = (900, 1200, 1600)


class NotEnoughProblems(Exception):
    pass


async def get_or_create_daily(session: AsyncSession, user_id: int, day: date, rng: random.Random | None = None) -> list[Problem]:
    existing = await daily.get_daily(session, user_id, day)
    if existing:
        return [Problem(r.contest_id, r.index, r.name, r.rating, tuple(r.tags or [])) for r in existing]
    chooser = rng or random.Random()
    excluded = await solved.solved_keys(session, user_id) | await daily.daily_keys(session, user_id)
    picked: list[Problem] = []
    for rating in DAILY_RATINGS:
        candidates = [p for p in await problemset.list_problems(session, rating=rating) if p.key not in excluded]
        if not candidates:
            raise NotEnoughProblems(f"no unsolved problem with rating {rating}")
        choice = chooser.choice(candidates)
        excluded.add(choice.key)
        picked.append(choice)
    await daily.save_daily(session, user_id, day, picked)
    await session.commit()
    return picked
```

`bot/services/leaderboard.py`:
```python
import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import CfCache, SolvedProblem, User
from bot.services.leveling import level_for, rank_for

LEADERBOARD_TYPES: tuple[str, ...] = ("level", "rating", "solved", "streaks")
PER_PAGE = 7


@dataclass(frozen=True)
class LeaderboardRow:
    no: int
    handle: str
    rank_name: str
    value: str


async def fetch_page(session: AsyncSession, kind: str, page: int) -> tuple[list[LeaderboardRow], int]:
    solved_count = (
        select(SolvedProblem.user_id, func.count().label("cnt"))
        .group_by(SolvedProblem.user_id)
        .subquery()
    )
    rating = func.coalesce(CfCache.rating, 0)
    max_rating = func.coalesce(CfCache.max_rating, 0)
    cnt = func.coalesce(solved_count.c.cnt, 0)
    stmt = (
        select(User.handle, User.exp, User.streak, rating, cnt)
        .outerjoin(CfCache, CfCache.user_id == User.discord_id)
        .outerjoin(solved_count, solved_count.c.user_id == User.discord_id)
    )
    if kind == "level":
        stmt = stmt.order_by(User.exp.desc(), User.discord_id)
    elif kind == "rating":
        stmt = stmt.order_by(rating.desc(), max_rating.desc(), User.discord_id)
    elif kind == "solved":
        stmt = stmt.order_by(cnt.desc(), User.exp.desc(), User.discord_id)
    elif kind == "streaks":
        stmt = stmt.order_by(User.streak.desc(), User.exp.desc(), User.discord_id)
    else:
        raise ValueError(kind)
    total = int((await session.execute(select(func.count()).select_from(User))).scalar_one())
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * PER_PAGE
    rows = (await session.execute(stmt.offset(offset).limit(PER_PAGE))).all()
    out: list[LeaderboardRow] = []
    for i, (handle, exp, streak, rating_value, solved_value) in enumerate(rows, start=offset + 1):
        level = level_for(exp)
        if kind == "level":
            value = str(level)
        elif kind == "rating":
            value = str(int(rating_value))
        elif kind == "solved":
            value = str(int(solved_value))
        else:
            value = str(streak)
        out.append(LeaderboardRow(i, handle, rank_for(level).name, value))
    return out, total_pages
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_daily_service.py tests/test_leaderboard_service.py -q`
Expected: semua passed

- [ ] **Step 5: Commit**

```bash
git add bot/services/daily.py bot/services/leaderboard.py tests/test_daily_service.py tests/test_leaderboard_service.py
git commit -m "feat: add daily problem and leaderboard services"
```

---

### Task 11: Render profile

**Files:**
- Create: `bot/render/profile.py`, `tests/test_render_profile.py`

**Interfaces:**
- Consumes: `fonts.ASSETS_DIR`, `text.fit_text`, `colors.*`
- Produces:
  - `ProfileData(handle, avatar: bytes | None, level: int, rank_name: str, exp_in_level: int, exp_need: int, money: Decimal, rating: int | None, max_rating: int | None, cf_rank: str | None, last_seen: str, last_solved: list[str], solved_count: int, streak: int)`
  - `render_profile(data: ProfileData) -> bytes` (PNG)
  - `format_last_seen(last_online: datetime, now: datetime) -> str`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_render_profile.py`:
```python
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from PIL import Image

from bot.render.profile import ProfileData, format_last_seen, render_profile


def make_avatar() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "red").save(buf, "PNG")
    return buf.getvalue()


def test_render_profile_size():
    data = ProfileData(
        handle="tourist_with_a_very_long_handle_name", avatar=make_avatar(), level=42, rank_name="Specialist",
        exp_in_level=150, exp_need=4200, money=Decimal("123.45"), rating=3800, max_rating=4000,
        cf_rank="legendary grandmaster", last_seen="2h ago",
        last_solved=["1842B · Tenzing and Books With Extremely Long Title", "1A · Theatre Square", "4A · Watermelon"],
        solved_count=1234, streak=7,
    )
    png = render_profile(data)
    im = Image.open(io.BytesIO(png))
    assert im.size == (974, 650)


def test_render_profile_unrated_without_avatar():
    data = ProfileData("nb", None, 1, "Rookie", 0, 100, Decimal("0.00"), None, None, None, "just now", [], 0, 0)
    assert Image.open(io.BytesIO(render_profile(data))).size == (974, 650)


def test_format_last_seen():
    now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    assert format_last_seen(now - timedelta(seconds=30), now) == "just now"
    assert format_last_seen(now - timedelta(minutes=5), now) == "5m ago"
    assert format_last_seen(now - timedelta(hours=3), now) == "3h ago"
    assert format_last_seen(now - timedelta(days=2), now) == "2d ago"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_render_profile.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/render/profile.py`:
```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_render_profile.py -q`
Expected: `3 passed`

- [ ] **Step 5: Cek visual**

Run:
```bash
python -c "
from decimal import Decimal
from bot.render.profile import ProfileData, render_profile
d = ProfileData('tourist', None, 42, 'Specialist', 150, 4200, Decimal('123.45'), 3800, 4000, 'legendary grandmaster', '2h ago', ['1842B · Tenzing and Books', '1A · Theatre Square', '4A · Watermelon'], 1234, 7)
open('preview_profile.png','wb').write(render_profile(d))
"
```
Buka `preview_profile.png`, pastikan teks berada di dalam box dan terbaca. Hapus file setelah cek: `rm preview_profile.png`.

- [ ] **Step 6: Commit**

```bash
git add bot/render/profile.py tests/test_render_profile.py
git commit -m "feat: render profile image"
```

---

### Task 12: Render leaderboard dan daily

**Files:**
- Create: `bot/render/leaderboard.py`, `bot/render/daily.py`, `tests/test_render_boards.py`

**Interfaces:**
- Consumes: `LeaderboardRow`, `Problem`
- Produces:
  - `leaderboard.render_leaderboard(kind: str, rows: list[LeaderboardRow], page: int, total_pages: int) -> bytes`
  - `daily.render_daily(problems: list[Problem]) -> bytes`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_render_boards.py`:
```python
import io

import pytest
from PIL import Image

from bot.cf.models import Problem
from bot.render.daily import render_daily
from bot.render.leaderboard import render_leaderboard
from bot.services.leaderboard import LeaderboardRow


@pytest.mark.parametrize("kind", ["level", "rating", "solved", "streaks"])
def test_render_leaderboard(kind):
    rows = [LeaderboardRow(i, f"handle_number_{i}_that_is_quite_long", "Elite", str(i * 10)) for i in range(1, 8)]
    im = Image.open(io.BytesIO(render_leaderboard(kind, rows, 2, 5)))
    assert im.size == (974, 650)


def test_render_leaderboard_partial_rows():
    assert Image.open(io.BytesIO(render_leaderboard("level", [], 1, 1))).size == (974, 650)


def test_render_daily():
    problems = [
        Problem(1842, "B", "Tenzing and Books With A Really Long Problem Name Here", 900, ("bitmasks", "greedy", "math", "constructive algorithms", "implementation")),
        Problem(4, "A", "Watermelon", 1200, ("math",)),
        Problem(1, "A", "Theatre Square", 1600, ()),
    ]
    assert Image.open(io.BytesIO(render_daily(problems))).size == (974, 650)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_render_boards.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis implementasi**

`bot/render/leaderboard.py`:
```python
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
```

`bot/render/daily.py`:
```python
import io

from PIL import Image, ImageDraw

from bot.cf.models import Problem
from bot.render.colors import MUTED, WHITE, cf_rating_color
from bot.render.fonts import ASSETS_DIR, get_font
from bot.render.text import fit_text, truncate

BOXES: tuple[tuple[int, int, int, int], ...] = ((250, 157, 724, 256), (250, 294, 724, 393), (250, 431, 724, 531))
PADDING = 16
TITLE_Y = 18
TAGS_Y = 58
RATING_WIDTH = 90


def render_daily(problems: list[Problem]) -> bytes:
    base = Image.open(ASSETS_DIR / "daily.png").convert("RGB")
    draw = ImageDraw.Draw(base)
    for problem, (x0, y0, x1, y1) in zip(problems, BOXES):
        left = x0 + PADDING
        right = x1 - PADDING
        title_box = (left, y0 + TITLE_Y - 14, right - RATING_WIDTH, y0 + TITLE_Y + 14)
        fit_text(draw, f"{problem.code} · {problem.name}", title_box, "SemiBold", 22, 14, WHITE, align="left")
        rating_text = "?" if problem.rating is None else str(problem.rating)
        rating_box = (right - RATING_WIDTH, y0 + TITLE_Y - 14, right, y0 + TITLE_Y + 14)
        fit_text(draw, rating_text, rating_box, "Bold", 22, 14, cf_rating_color(problem.rating), align="right")
        tags_font = get_font("Regular", 15)
        tags = " · ".join(problem.tags) if problem.tags else "no tags"
        draw.text((left, y0 + TAGS_Y), truncate(tags_font, tags, right - left), font=tags_font, fill=MUTED, anchor="lm")
    buf = io.BytesIO()
    base.save(buf, "PNG")
    return buf.getvalue()
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_render_boards.py -q`
Expected: `6 passed`

- [ ] **Step 5: Cek visual**

Run:
```bash
python -c "
from bot.cf.models import Problem
from bot.render.daily import render_daily
from bot.render.leaderboard import render_leaderboard
from bot.services.leaderboard import LeaderboardRow
open('preview_lb.png','wb').write(render_leaderboard('level', [LeaderboardRow(i, f'user{i}', 'Expert', str(99-i)) for i in range(1,8)], 1, 3))
open('preview_daily.png','wb').write(render_daily([Problem(1842,'B','Tenzing and Books',900,('math','greedy')), Problem(4,'A','Watermelon',1200,('math',)), Problem(1,'A','Theatre Square',1600,('math',))]))
"
```
Buka kedua file, pastikan kolom sejajar dengan header dan teks di dalam box. Hapus: `rm preview_lb.png preview_daily.png`.

- [ ] **Step 6: Commit**

```bash
git add bot/render/leaderboard.py bot/render/daily.py tests/test_render_boards.py
git commit -m "feat: render leaderboard and daily images"
```

---

### Task 13: Role service dan bot core

**Files:**
- Create: `bot/services/roles.py`, `bot/main.py`, `bot/__main__.py`, `bot/cogs/__init__.py`, `bot/cogs/common.py`, `tests/test_roles_service.py`

**Interfaces:**
- Produces:
  - `roles.ensure_rank_roles(guild: discord.Guild, session) -> dict[str, int]` (buat role yang hilang, simpan ke DB, commit)
  - `roles.apply_rank(member: discord.Member, rank_name: str, role_ids: dict[str, int]) -> None`
  - `roles.set_level_nickname(member: discord.Member, level: int, handle: str) -> None`
  - `roles.nickname_for(level: int, handle: str) -> str`
  - `main.FanClubBot(commands.Bot)` dengan atribut `settings`, `session_factory`, `cf`, `register_service`; `main.run()`
  - `common.error_embed(message: str) -> discord.Embed`, `common.info_embed(title: str, description: str) -> discord.Embed`, `common.send_error(interaction, message) -> None`, `common.image_embed(title: str, filename: str) -> discord.Embed`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_roles_service.py`:
```python
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.services.roles import apply_rank, ensure_rank_roles, nickname_for, set_level_nickname


def test_nickname_for():
    assert nickname_for(12, "tourist") == "【12】tourist"


async def test_ensure_rank_roles_creates_missing(session):
    guild = MagicMock()
    guild.id = 10
    guild.roles = []
    created = []

    async def create_role(name, colour, reason):
        role = MagicMock()
        role.id = 1000 + len(created)
        role.name = name
        created.append(role)
        return role

    guild.create_role = AsyncMock(side_effect=create_role)
    ids = await ensure_rank_roles(guild, session)
    assert len(ids) == 8 and ids["Rookie"] == 1000
    guild.roles = created
    ids2 = await ensure_rank_roles(guild, session)
    assert ids2 == ids and guild.create_role.await_count == 8


async def test_apply_rank_swaps_roles():
    member = MagicMock()
    rookie = MagicMock(); rookie.id = 1
    elite = MagicMock(); elite.id = 2
    member.roles = [rookie]
    member.guild.get_role = lambda rid: {1: rookie, 2: elite}[rid]
    member.remove_roles = AsyncMock()
    member.add_roles = AsyncMock()
    await apply_rank(member, "Elite", {"Rookie": 1, "Elite": 2})
    member.remove_roles.assert_awaited_once_with(rookie, reason="rank change")
    member.add_roles.assert_awaited_once_with(elite, reason="rank change")


async def test_set_level_nickname_ignores_forbidden():
    member = MagicMock()
    member.edit = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "no"))
    await set_level_nickname(member, 3, "h")
    member.edit.assert_awaited_once()
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_roles_service.py -q`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis `bot/services/roles.py`**

```python
import logging

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repo import roles as roles_repo
from bot.services.leveling import RANKS

log = logging.getLogger(__name__)


def nickname_for(level: int, handle: str) -> str:
    return f"【{level}】{handle}"


async def ensure_rank_roles(guild: discord.Guild, session: AsyncSession) -> dict[str, int]:
    stored = await roles_repo.get_role_ids(session, guild.id)
    by_name = {r.name: r for r in guild.roles}
    result: dict[str, int] = {}
    for rank in RANKS:
        role = by_name.get(rank.name)
        if role is None and rank.name in stored:
            role = discord.utils.get(guild.roles, id=stored[rank.name])
        if role is None:
            role = await guild.create_role(name=rank.name, colour=discord.Colour.from_str(rank.color), reason="rank role")
        result[rank.name] = role.id
        if stored.get(rank.name) != role.id:
            await roles_repo.set_role_id(session, guild.id, rank.name, role.id)
    await session.commit()
    return result


async def apply_rank(member: discord.Member, rank_name: str, role_ids: dict[str, int]) -> None:
    target_id = role_ids.get(rank_name)
    rank_ids = set(role_ids.values())
    try:
        for role in list(member.roles):
            if role.id in rank_ids and role.id != target_id:
                await member.remove_roles(role, reason="rank change")
        if target_id is not None and all(r.id != target_id for r in member.roles):
            target = member.guild.get_role(target_id)
            if target is not None:
                await member.add_roles(target, reason="rank change")
    except (discord.Forbidden, discord.HTTPException) as exc:
        log.warning("cannot update roles for %s: %s", member.id, exc)


async def set_level_nickname(member: discord.Member, level: int, handle: str) -> None:
    try:
        await member.edit(nick=nickname_for(level, handle), reason="level update")
    except (discord.Forbidden, discord.HTTPException) as exc:
        log.warning("cannot set nickname for %s: %s", member.id, exc)
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_roles_service.py -q`
Expected: `4 passed`

- [ ] **Step 5: Tulis `bot/cogs/__init__.py` (kosong), `bot/cogs/common.py`, `bot/main.py`, `bot/__main__.py`**

`bot/cogs/common.py`:
```python
import discord

RED = 0xE53935
BLUE = 0x1E88E5
GREEN = 0x43A047


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, colour=RED)


def info_embed(title: str, description: str, colour: int = BLUE) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def image_embed(title: str, filename: str) -> discord.Embed:
    embed = discord.Embed(title=title, colour=BLUE)
    embed.set_image(url=f"attachment://{filename}")
    return embed


async def send_error(interaction: discord.Interaction, message: str) -> None:
    embed = error_embed(message)
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
```

`bot/main.py`:
```python
import asyncio
import logging

import discord
from discord.ext import commands

from bot.cf.client import CodeforcesClient
from bot.config import Settings
from bot.db.session import make_engine, make_session_factory
from bot.services.register import RegisterService

EXTENSIONS = (
    "bot.cogs.register",
    "bot.cogs.profile",
    "bot.cogs.leaderboard",
    "bot.cogs.daily",
    "bot.cogs.poller",
)


class FanClubBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.engine = make_engine(settings.database_url)
        self.session_factory = make_session_factory(self.engine)
        self.cf = CodeforcesClient()
        self.register_service = RegisterService(self.cf)

    async def setup_hook(self) -> None:
        for name in EXTENSIONS:
            await self.load_extension(name)
        guild = discord.Object(id=self.settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def close(self) -> None:
        await self.cf.close()
        await self.engine.dispose()
        await super().close()


def run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bot = FanClubBot(settings)
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    run()
```

`bot/__main__.py`:
```python
from bot.main import run

run()
```

- [ ] **Step 6: Buat cog placeholder agar bot bisa import**

Buat lima file berikut dengan isi yang sama, hanya nama kelas berbeda (`RegisterCog`, `ProfileCog`, `LeaderboardCog`, `DailyCog`, `PollerCog`). Contoh `bot/cogs/register.py`:
```python
from discord.ext import commands


class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RegisterCog(bot))
```

Task 14 sampai 18 mengganti isi file ini.

- [ ] **Step 7: Verifikasi import bot**

Run: `python -c "import bot.main; print('ok')"`
Expected: `ok`

- [ ] **Step 8: Commit**

```bash
git add bot/services/roles.py bot/main.py bot/__main__.py bot/cogs tests/test_roles_service.py
git commit -m "feat: add role service, bot core, cog scaffolds"
```

---

### Task 14: Register cog

**Files:**
- Modify: `bot/cogs/register.py`
- Create: `tests/test_register_cog.py`

**Interfaces:**
- Consumes: `RegisterService`, `users.*`, `solved.bulk_add_solved`, `cf_cache.upsert_cf_cache`, `problemset.list_problems`, `roles.*`, `common.*`
- Produces: slash command `/register handle:<str>`; fungsi murni `build_instruction_embed(pending: PendingRegistration) -> discord.Embed`, `finalize_registration(session, pending, info, accepted, now) -> User` (dipakai ulang oleh test)

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_register_cog.py`:
```python
from datetime import datetime, timezone

from bot.cf.models import Problem, Submission, UserInfo
from bot.cogs.register import build_instruction_embed, finalize_registration
from bot.db.repo import cf_cache, solved, users
from bot.services.register import PendingRegistration

PROBLEM = Problem(1, "A", "Theatre Square", 1000, ("math",))


def test_instruction_embed_contains_link_and_deadline():
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    embed = build_instruction_embed(pending)
    assert PROBLEM.url in embed.description
    assert "<t:400:R>" in embed.description
    assert "Compilation Error" in embed.description


async def test_finalize_registration(session):
    pending = PendingRegistration(1, "tourist", PROBLEM, 100, 400)
    info = UserInfo("tourist", 3800, 4000, "legendary grandmaster", "legendary grandmaster", 1, "https://x/y.png")
    accepted = [
        Submission(1, Problem(2, "B", "x", 800, ()), "OK", 10),
        Submission(2, Problem(2, "B", "x", 800, ()), "OK", 20),
        Submission(3, Problem(3, "C", "y", None, ()), "OK", 30),
    ]
    user = await finalize_registration(session, pending, info, accepted, datetime(2026, 9, 16, tzinfo=timezone.utc))
    assert user.handle == "tourist" and user.exp == 0
    assert await solved.solved_count(session, 1) == 2
    assert (await cf_cache.get_cf_cache(session, 1)).rating == 3800
    assert (await users.get_by_discord(session, 1)) is not None
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_register_cog.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'build_instruction_embed'`

- [ ] **Step 3: Tulis `bot/cogs/register.py`**

```python
import logging
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.client import CodeforcesError
from bot.cf.models import Submission, UserInfo
from bot.cogs.common import GREEN, error_embed, info_embed, send_error
from bot.db.models import User
from bot.db.repo import cf_cache, problemset, solved, users
from bot.services.register import PendingRegistration, RegistrationInProgress
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname

log = logging.getLogger(__name__)


def build_instruction_embed(pending: PendingRegistration) -> discord.Embed:
    description = (
        f"Verify that **{pending.handle}** is yours.\n\n"
        f"Submit any code that gets a **Compilation Error** verdict on "
        f"[{pending.problem.code} - {pending.problem.name}]({pending.problem.url}).\n\n"
        f"Deadline: <t:{pending.deadline}:R>. I check every 10 seconds."
    )
    return info_embed("Codeforces verification", description)


async def finalize_registration(
    session: AsyncSession,
    pending: PendingRegistration,
    info: UserInfo,
    accepted: list[Submission],
    now: datetime,
) -> User:
    user = await users.create_user(session, pending.discord_id, info.handle)
    items = [(s.problem.contest_id, s.problem.index, datetime.fromtimestamp(s.created_at, tz=timezone.utc)) for s in accepted]
    await solved.bulk_add_solved(session, user.discord_id, items)
    await cf_cache.upsert_cf_cache(session, user.discord_id, info, now)
    await session.commit()
    return user


class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="register", description="Link your Codeforces handle to this Discord account")
    @app_commands.describe(handle="Your Codeforces handle")
    async def register(self, interaction: discord.Interaction, handle: str) -> None:
        bot = self.bot
        await interaction.response.defer()
        async with bot.session_factory() as session:
            if await users.get_by_discord(session, interaction.user.id) is not None:
                await send_error(interaction, "You are already registered.")
                return
            if await users.get_by_handle(session, handle) is not None:
                await send_error(interaction, f"Handle **{handle}** is already linked to another Discord account.")
                return
            problems = await problemset.list_problems(session)
        if not problems:
            await send_error(interaction, "Problem list is not ready yet. Try again in a minute.")
            return
        try:
            info = (await bot.cf.user_info([handle]))[0]
        except CodeforcesError:
            await send_error(interaction, f"Codeforces handle **{handle}** was not found.")
            return
        try:
            pending = bot.register_service.start(interaction.user.id, info.handle, random.choice(problems))
        except RegistrationInProgress:
            await send_error(interaction, "You already have a verification in progress.")
            return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Open problem", url=pending.problem.url))
        message = await interaction.followup.send(embed=build_instruction_embed(pending), view=view, wait=True)

        verified = await bot.register_service.wait_for_verification(pending)
        if not verified:
            await message.edit(embed=error_embed("Verification timed out. Run `/register` again."), view=None)
            return
        accepted = await bot.register_service.fetch_all_accepted(info.handle)
        async with bot.session_factory() as session:
            await finalize_registration(session, pending, info, accepted, datetime.now(timezone.utc))
            role_ids = await ensure_rank_roles(interaction.guild, session)
        member = interaction.guild.get_member(interaction.user.id)
        if member is not None:
            await apply_rank(member, "Rookie", role_ids)
            await set_level_nickname(member, 1, info.handle)
        embed = info_embed("Registered", f"**{info.handle}** is now linked to {interaction.user.mention}. Solved problems imported: {len(accepted)}.", colour=GREEN)
        await message.edit(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RegisterCog(bot))
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_register_cog.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/cogs/register.py tests/test_register_cog.py
git commit -m "feat: add /register command"
```

---

### Task 15: Profile cog

**Files:**
- Modify: `bot/cogs/profile.py`
- Create: `tests/test_profile_cog.py`

**Interfaces:**
- Consumes: `render_profile`, `ProfileData`, `format_last_seen`, `exp_progress`, `level_for`, `rank_for`, repo `users`, `solved`, `cf_cache`, `problemset.get_problem`
- Produces: slash command `/profile [user]`; `build_profile_data(session, user: User, avatar: bytes | None, now: datetime) -> ProfileData`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_profile_cog.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

from bot.cf.models import Problem, UserInfo
from bot.cogs.profile import build_profile_data
from bot.db.repo import cf_cache, problemset, solved, users

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


async def test_build_profile_data(session):
    user = await users.create_user(session, 1, "tourist")
    user.exp = 450
    user.money = Decimal("12.50")
    user.streak = 3
    await cf_cache.upsert_cf_cache(session, 1, UserInfo("tourist", 3800, 4000, "legendary grandmaster", "lgm", int(NOW.timestamp()) - 7200, "https://x/y.png"), NOW)
    await problemset.replace_problemset(session, [Problem(1, "A", "Theatre Square", 1000, ())], NOW)
    await solved.add_solved(session, 1, 1, "A", NOW)
    await solved.add_solved(session, 1, 99, "Z", datetime(2020, 1, 1, tzinfo=timezone.utc))
    await session.commit()
    result = await build_profile_data(session, user, b"avatar", NOW)
    assert result.level == 3 and result.exp_in_level == 150 and result.exp_need == 300
    assert result.rank_name == "Rookie"
    assert result.rating == 3800 and result.cf_rank == "legendary grandmaster"
    assert result.last_seen == "2h ago"
    assert result.last_solved == ["1A · Theatre Square", "99Z"]
    assert result.solved_count == 2 and result.streak == 3


async def test_build_profile_data_without_cache(session):
    user = await users.create_user(session, 1, "nb")
    await session.commit()
    result = await build_profile_data(session, user, None, NOW)
    assert result.rating is None and result.last_seen == "unknown" and result.last_solved == []
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_profile_cog.py -q`
Expected: FAIL dengan `ImportError`

- [ ] **Step 3: Tulis `bot/cogs/profile.py`**

```python
import asyncio
import io
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cogs.common import image_embed, send_error
from bot.db.models import User
from bot.db.repo import cf_cache, problemset, solved, users
from bot.render.profile import ProfileData, format_last_seen, render_profile
from bot.services.leveling import exp_progress, level_for, rank_for

log = logging.getLogger(__name__)


async def build_profile_data(session: AsyncSession, user: User, avatar: bytes | None, now: datetime) -> ProfileData:
    cache = await cf_cache.get_cf_cache(session, user.discord_id)
    level = level_for(user.exp)
    exp_in_level, exp_need = exp_progress(user.exp)
    lines: list[str] = []
    for row in await solved.last_solved(session, user.discord_id, limit=3):
        problem = await problemset.get_problem(session, row.contest_id, row.index)
        code = f"{row.contest_id}{row.index}"
        lines.append(f"{code} · {problem.name}" if problem else code)
    return ProfileData(
        handle=user.handle,
        avatar=avatar,
        level=level,
        rank_name=rank_for(level).name,
        exp_in_level=exp_in_level,
        exp_need=exp_need,
        money=user.money,
        rating=cache.rating if cache else None,
        max_rating=cache.max_rating if cache else None,
        cf_rank=cache.rank if cache else None,
        last_seen=format_last_seen(cache.last_online, now) if cache else "unknown",
        last_solved=lines,
        solved_count=await solved.solved_count(session, user.discord_id),
        streak=user.streak,
    )


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Show a player's profile card")
    @app_commands.describe(user="Whose profile to show (default: you)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        await interaction.response.defer()
        async with self.bot.session_factory() as session:
            row = await users.get_by_discord(session, target.id)
            if row is None:
                await send_error(interaction, f"{target.mention} is not registered yet. Use `/register`.")
                return
            cache = await cf_cache.get_cf_cache(session, row.discord_id)
            avatar: bytes | None = None
            if cache and cache.avatar_url:
                try:
                    avatar = await self.bot.cf.fetch_bytes(cache.avatar_url)
                except Exception as exc:
                    log.warning("avatar fetch failed for %s: %s", row.handle, exc)
            data = await build_profile_data(session, row, avatar, datetime.now(timezone.utc))
        png = await asyncio.to_thread(render_profile, data)
        file = discord.File(io.BytesIO(png), filename="profile.png")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="See Profile", url=f"https://codeforces.com/profile/{row.handle}"))
        await interaction.followup.send(embed=image_embed(f"{row.handle}", "profile.png"), file=file, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_profile_cog.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/cogs/profile.py tests/test_profile_cog.py
git commit -m "feat: add /profile command"
```

---

### Task 16: Leaderboard cog dengan pagination

**Files:**
- Modify: `bot/cogs/leaderboard.py`
- Create: `tests/test_leaderboard_cog.py`

**Interfaces:**
- Consumes: `fetch_page`, `render_leaderboard`, `LEADERBOARD_TYPES`
- Produces: slash command `/leaderboard type`; `LeaderboardView(session_factory, kind, owner_id, page, total_pages)` dengan method `async build_message() -> tuple[discord.Embed, discord.File]`, tombol `back` dan `next`, `interaction_check`, `on_timeout`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_leaderboard_cog.py`:
```python
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.leaderboard import LeaderboardView
from bot.db.repo import users


async def seed(session, n):
    for i in range(1, n + 1):
        u = await users.create_user(session, i, f"h{i}")
        u.exp = i * 100
    await session.commit()


async def test_view_buttons_state(session_factory):
    async with session_factory() as s:
        await seed(s, 9)
    view = LeaderboardView(session_factory, "level", owner_id=1, page=1, total_pages=2)
    view.sync_buttons()
    assert view.back.disabled is True and view.next.disabled is False
    view.page = 2
    view.sync_buttons()
    assert view.back.disabled is False and view.next.disabled is True


async def test_view_build_message(session_factory):
    async with session_factory() as s:
        await seed(s, 3)
    view = LeaderboardView(session_factory, "solved", owner_id=1, page=1, total_pages=1)
    embed, file = await view.build_message()
    assert file.filename == "leaderboard.png"
    assert embed.image.url == "attachment://leaderboard.png"


async def test_interaction_check_rejects_others(session_factory):
    view = LeaderboardView(session_factory, "level", owner_id=1, page=1, total_pages=1)
    interaction = MagicMock()
    interaction.user.id = 2
    interaction.response.send_message = AsyncMock()
    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once()
    interaction.user.id = 1
    assert await view.interaction_check(interaction) is True
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_leaderboard_cog.py -q`
Expected: FAIL dengan `ImportError`

- [ ] **Step 3: Tulis `bot/cogs/leaderboard.py`**

```python
import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import error_embed, image_embed
from bot.render.leaderboard import render_leaderboard
from bot.services.leaderboard import LEADERBOARD_TYPES, fetch_page

FILENAME = "leaderboard.png"
TITLES = {"level": "Leaderboard · Level", "rating": "Leaderboard · Rating", "solved": "Leaderboard · Solved", "streaks": "Leaderboard · Streaks"}


class LeaderboardView(discord.ui.View):
    def __init__(self, session_factory, kind: str, owner_id: int, page: int, total_pages: int) -> None:
        super().__init__(timeout=300)
        self.session_factory = session_factory
        self.kind = kind
        self.owner_id = owner_id
        self.page = page
        self.total_pages = total_pages
        self.message: discord.Message | None = None
        self.sync_buttons()

    def sync_buttons(self) -> None:
        self.back.disabled = self.page <= 1
        self.next.disabled = self.page >= self.total_pages

    async def build_message(self) -> tuple[discord.Embed, discord.File]:
        async with self.session_factory() as session:
            rows, self.total_pages = await fetch_page(session, self.kind, self.page)
        png = await asyncio.to_thread(render_leaderboard, self.kind, rows, self.page, self.total_pages)
        self.sync_buttons()
        return image_embed(TITLES[self.kind], FILENAME), discord.File(io.BytesIO(png), filename=FILENAME)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message(embed=error_embed("Only the person who ran this command can turn pages."), ephemeral=True)
        return False

    async def _show(self, interaction: discord.Interaction) -> None:
        embed, file = await self.build_message()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(1, self.page - 1)
        await self._show(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = min(self.total_pages, self.page + 1)
        await self._show(interaction)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Show the server leaderboard")
    @app_commands.describe(type="Which leaderboard to show")
    @app_commands.choices(type=[app_commands.Choice(name=t, value=t) for t in LEADERBOARD_TYPES])
    async def leaderboard(self, interaction: discord.Interaction, type: app_commands.Choice[str]) -> None:
        await interaction.response.defer()
        view = LeaderboardView(self.bot.session_factory, type.value, interaction.user.id, page=1, total_pages=1)
        embed, file = await view.build_message()
        view.message = await interaction.followup.send(embed=embed, file=file, view=view, wait=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaderboardCog(bot))
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_leaderboard_cog.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/cogs/leaderboard.py tests/test_leaderboard_cog.py
git commit -m "feat: add /leaderboard command with pagination"
```

---

### Task 17: Daily cog

**Files:**
- Modify: `bot/cogs/daily.py`
- Create: `tests/test_daily_cog.py`

**Interfaces:**
- Consumes: `get_or_create_daily`, `NotEnoughProblems`, `render_daily`, `today_wib`
- Produces: slash command `/daily`; `build_daily_view(problems: list[Problem]) -> discord.ui.View`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_daily_cog.py`:
```python
import discord

from bot.cf.models import Problem
from bot.cogs.daily import build_daily_view


async def test_daily_view_has_three_link_buttons():
    problems = [Problem(1, "A", "a", 900, ()), Problem(2, "B", "b", 1200, ()), Problem(3, "C", "c", 1600, ())]
    view = build_daily_view(problems)
    buttons = [c for c in view.children if isinstance(c, discord.ui.Button)]
    assert [b.label for b in buttons] == ["900", "1200", "1600"]
    assert buttons[0].url == "https://codeforces.com/problemset/problem/1/A"
    assert all(b.style is discord.ButtonStyle.link for b in buttons)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_daily_cog.py -q`
Expected: FAIL dengan `ImportError`

- [ ] **Step 3: Tulis `bot/cogs/daily.py`**

```python
import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.cf.models import Problem
from bot.cogs.common import image_embed, send_error
from bot.db.repo import users
from bot.render.daily import render_daily
from bot.services.daily import NotEnoughProblems, get_or_create_daily
from bot.services.streak import today_wib

FILENAME = "daily.png"


def build_daily_view(problems: list[Problem]) -> discord.ui.View:
    view = discord.ui.View()
    for problem in problems:
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=str(problem.rating), url=problem.url))
    return view


class DailyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="daily", description="Your three daily problems (900, 1200, 1600)")
    async def daily(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        async with self.bot.session_factory() as session:
            user = await users.get_by_discord(session, interaction.user.id)
            if user is None:
                await send_error(interaction, "You are not registered yet. Use `/register`.")
                return
            try:
                problems = await get_or_create_daily(session, user.discord_id, today_wib())
            except NotEnoughProblems:
                await send_error(interaction, "Could not find enough unsolved problems for you today.")
                return
        png = await asyncio.to_thread(render_daily, problems)
        file = discord.File(io.BytesIO(png), filename=FILENAME)
        embed = image_embed(f"Daily problems for {user.handle}", FILENAME)
        await interaction.followup.send(embed=embed, file=file, view=build_daily_view(problems))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DailyCog(bot))
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_daily_cog.py -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add bot/cogs/daily.py tests/test_daily_cog.py
git commit -m "feat: add /daily command"
```

---

### Task 18: Poller cog (solve detect, notif, cache refresh, streak reset)

**Files:**
- Modify: `bot/cogs/poller.py`
- Create: `tests/test_poller_cog.py`

**Interfaces:**
- Consumes: `process_user`, `SolveResult`, `users.list_users`, `cf_cache.upsert_cf_cache`, `problemset.replace_problemset`, `roles.*`, `is_broken`, `today_wib`
- Produces:
  - `format_solve_notification(result: SolveResult) -> str`
  - `PollerCog` dengan loops `poll_solves` (60 s), `refresh_cf_cache` (10 menit), `refresh_problemset` (6 jam), `reset_streaks` (00:05 WIB) dan method `async poll_once() -> None`, `async apply_side_effects(result: SolveResult) -> None`, `async reset_broken_streaks(today: date) -> int`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_poller_cog.py`:
```python
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from bot.cf.models import Problem
from bot.cogs.poller import PollerCog, format_solve_notification
from bot.db.repo import users
from bot.services.solve_processor import SolveResult


def test_format_solve_notification():
    r = SolveResult(1, "tourist", Problem(1842, "B", "Tenzing", 900, ()), 90, Decimal("4.50"), 1, 1, "Rookie", "Rookie", 3)
    text = format_solve_notification(r)
    assert "**tourist**" in text and "[1842B - Tenzing](https://codeforces.com/problemset/problem/1842/B)" in text
    assert "rating 900" in text and "+90 EXP" in text and "+$4.50" in text


def test_format_unrated_notification():
    r = SolveResult(1, "h", Problem(1, "A", "x", None, ()), 0, Decimal("0.00"), 1, 1, "Rookie", "Rookie", 1)
    text = format_solve_notification(r)
    assert "(unrated)" in text and "+0 EXP" in text and "+$0.00" in text


async def test_reset_broken_streaks(session_factory):
    async with session_factory() as s:
        a = await users.create_user(s, 1, "a")
        a.streak = 5
        a.last_solve_date = date(2026, 9, 10)
        b = await users.create_user(s, 2, "b")
        b.streak = 2
        b.last_solve_date = date(2026, 9, 15)
        await s.commit()
    bot = MagicMock()
    bot.session_factory = session_factory
    cog = PollerCog.__new__(PollerCog)
    cog.bot = bot
    assert await cog.reset_broken_streaks(date(2026, 9, 16)) == 1
    async with session_factory() as s:
        assert (await users.get_by_discord(s, 1)).streak == 0
        assert (await users.get_by_discord(s, 2)).streak == 2
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_poller_cog.py -q`
Expected: FAIL dengan `ImportError`

- [ ] **Step 3: Tulis `bot/cogs/poller.py`**

```python
import datetime as dt
import logging

import discord
from discord.ext import commands, tasks

from bot.config import WIB
from bot.db.repo import cf_cache, problemset, users
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname
from bot.services.solve_processor import SolveResult, process_user
from bot.services.streak import is_broken, today_wib

log = logging.getLogger(__name__)
INFO_BATCH = 100


def format_solve_notification(result: SolveResult) -> str:
    p = result.problem
    rating = "(unrated)" if p.rating is None else f"(rating {p.rating})"
    return f"**{result.handle}** solved [{p.code} - {p.name}]({p.url}) {rating} | +{result.exp_gained} EXP | +${result.money_gained:.2f}"


class PollerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.role_ids: dict[str, int] = {}
        self.poll_solves.start()
        self.refresh_cf_cache.start()
        self.refresh_problemset.start()
        self.reset_streaks.start()

    def cog_unload(self) -> None:
        self.poll_solves.cancel()
        self.refresh_cf_cache.cancel()
        self.refresh_problemset.cancel()
        self.reset_streaks.cancel()

    def _guild(self) -> discord.Guild | None:
        return self.bot.get_guild(self.bot.settings.guild_id)

    async def apply_side_effects(self, result: SolveResult) -> None:
        guild = self._guild()
        if guild is not None:
            member = guild.get_member(result.discord_id)
            if member is not None:
                if result.new_level != result.old_level:
                    await set_level_nickname(member, result.new_level, result.handle)
                if result.new_rank != result.old_rank:
                    if not self.role_ids:
                        async with self.bot.session_factory() as session:
                            self.role_ids = await ensure_rank_roles(guild, session)
                    await apply_rank(member, result.new_rank, self.role_ids)
        channel = self.bot.get_channel(self.bot.settings.notify_channel_id)
        if channel is not None:
            try:
                await channel.send(format_solve_notification(result))
            except discord.HTTPException as exc:
                log.warning("notification failed: %s", exc)

    async def poll_once(self) -> None:
        async with self.bot.session_factory() as session:
            all_users = await users.list_users(session)
        today = today_wib()
        for user in all_users:
            try:
                submissions = await self.bot.cf.user_status(user.handle, from_=1, count=30)
                async with self.bot.session_factory() as session:
                    results = await process_user(session, user.discord_id, submissions, today)
                for result in results:
                    await self.apply_side_effects(result)
            except Exception:
                log.exception("poll failed for %s", user.handle)

    async def reset_broken_streaks(self, today: dt.date) -> int:
        changed = 0
        async with self.bot.session_factory() as session:
            for user in await users.list_users(session):
                if user.streak and is_broken(user.last_solve_date, today):
                    user.streak = 0
                    changed += 1
            await session.commit()
        return changed

    @tasks.loop(seconds=60)
    async def poll_solves(self) -> None:
        await self.poll_once()

    @tasks.loop(minutes=10)
    async def refresh_cf_cache(self) -> None:
        async with self.bot.session_factory() as session:
            all_users = await users.list_users(session)
            by_handle = {u.handle.lower(): u.discord_id for u in all_users}
            handles = list(by_handle)
            now = dt.datetime.now(dt.timezone.utc)
            for start in range(0, len(handles), INFO_BATCH):
                chunk = handles[start:start + INFO_BATCH]
                try:
                    infos = await self.bot.cf.user_info(chunk)
                except Exception:
                    log.exception("user.info refresh failed")
                    continue
                for info in infos:
                    discord_id = by_handle.get(info.handle.lower())
                    if discord_id is not None:
                        await cf_cache.upsert_cf_cache(session, discord_id, info, now)
            await session.commit()

    @tasks.loop(hours=6)
    async def refresh_problemset(self) -> None:
        try:
            problems = await self.bot.cf.problemset_problems()
        except Exception:
            log.exception("problemset refresh failed")
            return
        async with self.bot.session_factory() as session:
            count = await problemset.replace_problemset(session, problems, dt.datetime.now(dt.timezone.utc))
            await session.commit()
        log.info("problemset cache refreshed: %d problems", count)

    @tasks.loop(time=dt.time(hour=0, minute=5, tzinfo=WIB))
    async def reset_streaks(self) -> None:
        changed = await self.reset_broken_streaks(today_wib())
        log.info("streaks reset: %d", changed)

    @poll_solves.before_loop
    @refresh_cf_cache.before_loop
    @refresh_problemset.before_loop
    @reset_streaks.before_loop
    async def wait_ready(self) -> None:
        await self.bot.wait_until_ready()
        guild = self._guild()
        if guild is not None and not self.role_ids:
            async with self.bot.session_factory() as session:
                self.role_ids = await ensure_rank_roles(guild, session)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollerCog(bot))
```

Catatan urutan: `refresh_problemset` harus sudah terisi sebelum `/register` bisa memilih soal. Loop pertama berjalan segera setelah `wait_until_ready`, jadi cache terisi dalam beberapa detik setelah bot online.

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_poller_cog.py -q`
Expected: `3 passed`

- [ ] **Step 5: Jalankan seluruh suite dan cek import bot**

Run: `python -m pytest -q && python -c "import bot.main; print('ok')"`
Expected: semua passed, `ok`

- [ ] **Step 6: Commit**

```bash
git add bot/cogs/poller.py tests/test_poller_cog.py
git commit -m "feat: add solve poller, notifications, cache refresh, streak reset"
```

---

### Task 19: README, .dockerignore, verifikasi Docker

**Files:**
- Create: `README.md`, `.dockerignore`
- Modify: `.gitignore`

- [ ] **Step 1: Tulis `.dockerignore`**

```
.venv
.git
.pytest_cache
__pycache__
*.pyc
tests
docs
.env
preview_*.png
```

- [ ] **Step 2: Tambahkan `preview_*.png` dan `tmp_migrate.db` ke `.gitignore`**

- [ ] **Step 3: Tulis `README.md`**

```markdown
# FanClub Bot

Discord bot for a competitive programming community, linked to Codeforces.

## Features

- `/register <handle>`: link a Codeforces handle. Verify by submitting a Compilation Error on a random problem within 5 minutes.
- `/profile [@user]`: profile card image with level, money, EXP, Codeforces stats, last solved, streak.
- `/leaderboard <level|rating|solved|streaks>`: paginated image leaderboard, 7 per page.
- `/daily`: three personal daily problems (900, 1200, 1600) that you have never solved.
- Background poller: new accepted solves give EXP (`rating / 10`) and money (`rating / 200`), update level, rank role, nickname, streak, and post a notification.

## Setup

1. Create a Discord application, enable the Server Members intent, invite the bot with `applications.commands`, `Manage Roles`, `Manage Nicknames`, `Send Messages`, `Attach Files`.
2. Copy `.env.example` to `.env` and fill `DISCORD_TOKEN`, `GUILD_ID`, `NOTIFY_CHANNEL_ID`.
3. Run:

```bash
docker compose up -d --build
```

The bot role must be above the rank roles it manages in the server role list.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

Run locally against a Postgres instance by setting `DATABASE_URL`, then `alembic upgrade head` and `python -m bot`.
```

- [ ] **Step 4: Build image**

Run: `docker compose build`
Expected: build sukses. Jika Docker tidak tersedia di mesin, catat di laporan dan lanjut.

- [ ] **Step 5: Jalankan stack**

Isi `.env` dengan token asli, lalu:
Run: `docker compose up -d && docker compose logs -f bot`
Expected: log `Running upgrade  -> 0001_initial`, lalu discord.py `logged in as ...`, lalu `problemset cache refreshed: N problems`.
Verifikasi manual di Discord: `/register`, `/profile`, `/leaderboard level`, `/daily`, dan satu solve baru memunculkan notifikasi di channel.

- [ ] **Step 6: Commit**

```bash
git add README.md .dockerignore .gitignore
git commit -m "docs: add README and docker ignore"
```

---

## Self-Review

**Spec coverage**
- 6.1 Level/EXP/rank/role/nickname: Task 2, 13, 18.
- 6.2 Money: Task 3, 8.
- 6.3 Register: Task 9, 14.
- 6.4 Poller: Task 8, 18.
- 6.5 Streak: Task 3, 8, 18.
- 6.6 Daily: Task 10, 12, 17.
- 6.7 Profile: Task 11, 15.
- 6.8 Notifikasi: Task 18.
- 6.9 Leaderboard: Task 10, 12, 16.
- 7 Render: Task 4, 11, 12.
- 8 Config: Task 1.
- 9 Error handling: Task 5 (retry), 13 (Forbidden), 18 (per-user try/except), 14/15/17 (embed error).
- 10 Testing: setiap task.
- 11 Deploy: Task 1, 6, 19.

**Type consistency**
- `Problem.key`, `.code`, `.url` dipakai di detector, processor, daily, render, cogs: konsisten.
- `SolveResult` field dipakai di `format_solve_notification` dan `apply_side_effects`: konsisten.
- `fetch_page` mengembalikan `(rows, total_pages)`: dipakai di `LeaderboardView.build_message`.
- `get_or_create_daily` mengembalikan `list[Problem]`: dipakai di `render_daily` dan `build_daily_view`.
- `ensure_rank_roles(guild, session)` mengembalikan `dict[str, int]`: dipakai di register cog dan poller.
