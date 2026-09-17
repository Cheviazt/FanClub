import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from bot.cf.models import Problem, Submission, UserInfo, problem_from_api, submission_from_api, user_info_from_api

BASE_URL = "https://codeforces.com/api"
MAX_ATTEMPTS = 3
RETRY_STATUSES = frozenset({403, 429})


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
                if response.status_code >= 500 or response.status_code in RETRY_STATUSES:
                    last_error = CodeforcesError(f"HTTP {response.status_code}")
                    await self._sleep(2**attempt)
                    continue
                try:
                    payload = response.json()
                except ValueError:
                    last_error = CodeforcesError("invalid JSON response")
                    await self._sleep(2**attempt)
                    continue
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
