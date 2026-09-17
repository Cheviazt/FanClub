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


async def fetch_avatar(client, cache: AvatarCache, discord_id: int, url: str) -> bytes | None:
    if not url:
        return None
    try:
        data = await client.fetch_bytes(url)
    except Exception as exc:
        log.warning("avatar fetch failed for %s: %s", discord_id, exc)
        return cache.load(discord_id)
    cache.store(discord_id, data)
    return data
