from dataclasses import dataclass
from datetime import datetime, timedelta

CODEFORCES = "Codeforces"
CODECHEF = "CodeChef"
ATCODER = "AtCoder"

PLATFORM_COLORS = {CODEFORCES: 0x1F8ACB, CODECHEF: 0x7B4B2A, ATCODER: 0x3A3A3A}
PLATFORM_HOMES = {
    CODEFORCES: "https://codeforces.com/contests",
    CODECHEF: "https://www.codechef.com/contests",
    ATCODER: "https://atcoder.jp/contests/",
}


@dataclass(frozen=True)
class Contest:
    platform: str
    key: str
    name: str
    start: datetime
    duration: timedelta
    url: str
    rated_range: str | None = None

    @property
    def end(self) -> datetime:
        return self.start + self.duration


def format_duration(duration: timedelta) -> str:
    minutes = int(duration.total_seconds() // 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)
