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
