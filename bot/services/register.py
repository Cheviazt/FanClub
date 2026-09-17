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
        if any(p.handle.lower() == handle.lower() for p in self.pending.values()):
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
