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
