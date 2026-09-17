import httpx
import pytest
import respx

from bot.cf.client import CodeforcesClient
from bot.services.avatars import AvatarCache, fetch_avatar


async def no_sleep(_: float) -> None:
    return None


def make_client() -> CodeforcesClient:
    return CodeforcesClient(http=httpx.AsyncClient(), min_interval=0, sleep=no_sleep)


def test_cache_miss_returns_none(tmp_path):
    cache = AvatarCache(tmp_path / "avatars")
    assert cache.load(1) is None


def test_cache_store_and_load(tmp_path):
    cache = AvatarCache(tmp_path / "avatars")
    cache.store(1, b"img")
    assert cache.load(1) == b"img"
    cache.store(1, b"new")
    assert cache.load(1) == b"new"


@respx.mock
async def test_fetch_bytes_sends_browser_headers_and_retries():
    route = respx.get("https://userpic.codeforces.org/a.jpg")
    route.side_effect = [httpx.Response(503, text="busy"), httpx.Response(200, content=b"jpg")]
    client = make_client()
    data = await client.fetch_bytes("https://userpic.codeforces.org/a.jpg")
    assert data == b"jpg" and route.call_count == 2
    request = route.calls[0].request
    assert "Mozilla" in request.headers["user-agent"]
    assert request.headers["referer"] == "https://codeforces.com/"
    await client.close()


@respx.mock
async def test_fetch_bytes_gives_up_after_three_attempts():
    respx.get("https://userpic.codeforces.org/a.jpg").mock(return_value=httpx.Response(503, text="busy"))
    client = make_client()
    with pytest.raises(httpx.HTTPStatusError):
        await client.fetch_bytes("https://userpic.codeforces.org/a.jpg")
    await client.close()


@respx.mock
async def test_fetch_avatar_stores_on_success(tmp_path):
    respx.get("https://userpic.codeforces.org/a.jpg").mock(return_value=httpx.Response(200, content=b"jpg"))
    cache = AvatarCache(tmp_path / "avatars")
    client = make_client()
    assert await fetch_avatar(client, cache, 1, "https://userpic.codeforces.org/a.jpg") == b"jpg"
    assert cache.load(1) == b"jpg"
    await client.close()


@respx.mock
async def test_fetch_avatar_falls_back_to_cache(tmp_path):
    respx.get("https://userpic.codeforces.org/a.jpg").mock(return_value=httpx.Response(503, text="busy"))
    cache = AvatarCache(tmp_path / "avatars")
    cache.store(1, b"old")
    client = make_client()
    assert await fetch_avatar(client, cache, 1, "https://userpic.codeforces.org/a.jpg") == b"old"
    assert await fetch_avatar(client, cache, 2, "https://userpic.codeforces.org/a.jpg") is None
    assert await fetch_avatar(client, cache, 3, "") is None
    await client.close()


@respx.mock
async def test_fetch_avatar_uses_discord_fallback(tmp_path):
    respx.get("https://userpic.codeforces.org/a.jpg").mock(return_value=httpx.Response(503, text="busy"))
    respx.get("https://cdn.discordapp.com/x.png").mock(return_value=httpx.Response(200, content=b"discord"))
    cache = AvatarCache(tmp_path / "avatars")
    client = make_client()
    data = await fetch_avatar(client, cache, 1, "https://userpic.codeforces.org/a.jpg", "https://cdn.discordapp.com/x.png")
    assert data == b"discord"
    assert cache.load(1) is None
    cache.store(2, b"old")
    assert await fetch_avatar(client, cache, 2, "https://userpic.codeforces.org/a.jpg", "https://cdn.discordapp.com/x.png") == b"old"
    await client.close()


def test_fit_text_strike_draws_line():
    from PIL import Image, ImageDraw

    from bot.render.text import fit_text

    im = Image.new("RGB", (300, 60))
    fit_text(ImageDraw.Draw(im), "done", (0, 0, 300, 60), "SemiBold", 26, 14, "#FFFFFF", align="left", strike=True)
    assert im.getpixel((5, 30)) == (255, 255, 255)


def test_avatar_candidates_adds_codeforces_mirror():
    from bot.services.avatars import avatar_candidates

    assert avatar_candidates("") == []
    assert avatar_candidates("https://cdn/x.png") == ["https://cdn/x.png"]
    assert avatar_candidates("https://userpic.codeforces.org/1/title/a.jpg") == [
        "https://userpic.codeforces.org/1/title/a.jpg",
        "https://codeforces.com/userpic.codeforces.org/1/title/a.jpg",
    ]


@respx.mock
async def test_fetch_avatar_uses_mirror_when_cdn_fails(tmp_path):
    respx.get("https://userpic.codeforces.org/1/title/a.jpg").mock(return_value=httpx.Response(503, text="busy"))
    respx.get("https://codeforces.com/userpic.codeforces.org/1/title/a.jpg").mock(return_value=httpx.Response(200, content=b"mirror"))
    cache = AvatarCache(tmp_path / "avatars")
    client = make_client()
    assert await fetch_avatar(client, cache, 1, "https://userpic.codeforces.org/1/title/a.jpg", "https://cdn.discordapp.com/x.png") == b"mirror"
    assert cache.load(1) == b"mirror"
    await client.close()


def test_cache_delete(tmp_path):
    cache = AvatarCache(tmp_path / "avatars")
    cache.store(1, b"img")
    cache.delete(1)
    cache.delete(1)
    assert cache.load(1) is None
