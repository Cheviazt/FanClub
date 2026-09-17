import logging
from pathlib import Path

log = logging.getLogger(__name__)


class AvatarCache:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, discord_id: int) -> Path:
        return self._directory / f"{discord_id}.img"

    def load(self, discord_id: int) -> bytes | None:
        path = self._path(discord_id)
        if not path.is_file():
            return None
        return path.read_bytes()

    def store(self, discord_id: int, data: bytes) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        self._path(discord_id).write_bytes(data)

    def delete(self, discord_id: int) -> None:
        self._path(discord_id).unlink(missing_ok=True)


USERPIC_HOST = "https://userpic.codeforces.org/"
MIRROR_PREFIX = "https://codeforces.com/userpic.codeforces.org/"


def avatar_candidates(url: str) -> list[str]:
    if not url:
        return []
    if url.startswith(USERPIC_HOST):
        return [url, MIRROR_PREFIX + url[len(USERPIC_HOST):]]
    return [url]


async def fetch_avatar(client, cache: AvatarCache, discord_id: int, url: str, fallback_url: str = "") -> bytes | None:
    for candidate in avatar_candidates(url):
        try:
            data = await client.fetch_bytes(candidate)
        except Exception as exc:
            log.warning("avatar fetch failed for %s: %s", discord_id, exc)
            continue
        cache.store(discord_id, data)
        return data
    cached = cache.load(discord_id)
    if cached is not None or not fallback_url:
        return cached
    try:
        return await client.fetch_bytes(fallback_url)
    except Exception as exc:
        log.warning("fallback avatar fetch failed for %s: %s", discord_id, exc)
        return None
