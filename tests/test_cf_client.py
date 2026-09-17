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


@respx.mock
async def test_html_then_json_succeeds_on_second_attempt():
    route = respx.get(f"{BASE}/user.info")
    route.side_effect = [
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, json={"status": "OK", "result": [{"handle": "nb", "lastOnlineTimeSeconds": 1, "titlePhoto": "https://a/b.png"}]}),
    ]
    client = make_client()
    infos = await client.user_info(["nb"])
    assert infos[0].handle == "nb" and route.call_count == 2
    await client.close()


@respx.mock
async def test_html_three_times_raises_invalid_json():
    route = respx.get(f"{BASE}/user.info").mock(return_value=httpx.Response(200, text="<html>maintenance</html>"))
    client = make_client()
    with pytest.raises(CodeforcesError, match="invalid JSON response"):
        await client.user_info(["nb"])
    assert route.call_count == 3
    await client.close()


@respx.mock
async def test_retries_on_403_and_429():
    route = respx.get(f"{BASE}/user.info")
    route.side_effect = [
        httpx.Response(403, text="<html>forbidden</html>"),
        httpx.Response(429, text="<html>slow down</html>"),
        httpx.Response(200, json={"status": "OK", "result": [{"handle": "nb", "lastOnlineTimeSeconds": 1, "titlePhoto": "https://a/b.png"}]}),
    ]
    client = make_client()
    infos = await client.user_info(["nb"])
    assert infos[0].handle == "nb" and route.call_count == 3
    await client.close()
