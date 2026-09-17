import html
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bot.contests.models import ATCODER, CODECHEF, CODEFORCES, Contest

CODECHEF_URL = "https://www.codechef.com/api/list/contests/all"
ATCODER_URL = "https://atcoder.jp/contests/?lang=en"
JST = ZoneInfo("Asia/Tokyo")

ATCODER_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
ATCODER_TIME = re.compile(r"<time[^>]*>(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})([+-]\d{4})</time>")
ATCODER_LINK = re.compile(r'<a href="/contests/([^"]+)">([^<]+)</a>')
ATCODER_CELL = re.compile(r'<td class="text-center">\s*([^<]*?)\s*</td>')


def parse_codeforces(result: list[dict]) -> list[Contest]:
    contests = []
    for item in result:
        if item.get("phase") != "BEFORE" or "startTimeSeconds" not in item:
            continue
        contests.append(
            Contest(
                platform=CODEFORCES,
                key=str(item["id"]),
                name=str(item["name"]),
                start=datetime.fromtimestamp(int(item["startTimeSeconds"]), tz=timezone.utc),
                duration=timedelta(seconds=int(item.get("durationSeconds", 0))),
                url=f"https://codeforces.com/contests/{item['id']}",
            )
        )
    return contests


def parse_codechef(payload: dict) -> list[Contest]:
    contests = []
    for item in payload.get("future_contests", []):
        try:
            start = datetime.fromisoformat(item["contest_start_date_iso"]).astimezone(timezone.utc)
            end = datetime.fromisoformat(item["contest_end_date_iso"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        code = str(item.get("contest_code", "")).strip()
        if not code:
            continue
        contests.append(
            Contest(
                platform=CODECHEF,
                key=code,
                name=str(item.get("contest_name", code)),
                start=start,
                duration=end - start,
                url=f"https://www.codechef.com/{code}",
            )
        )
    return contests


def parse_atcoder(page: str) -> list[Contest]:
    marker = page.find('id="contest-table-upcoming"')
    if marker < 0:
        return []
    section = page[marker:]
    end = section.find("</table>")
    if end > 0:
        section = section[:end]
    contests = []
    for row in ATCODER_ROW.findall(section):
        time_match = ATCODER_TIME.search(row)
        link_match = ATCODER_LINK.search(row)
        if not time_match or not link_match:
            continue
        cells = ATCODER_CELL.findall(row)
        duration_text = next((c for c in cells if re.fullmatch(r"\d+:\d{2}", c)), "0:00")
        hours, minutes = duration_text.split(":")
        rated = cells[-1].strip() if cells else ""
        start = datetime.strptime(time_match.group(1) + time_match.group(2), "%Y-%m-%d %H:%M:%S%z").astimezone(timezone.utc)
        contests.append(
            Contest(
                platform=ATCODER,
                key=link_match.group(1),
                name=html.unescape(link_match.group(2)).strip(),
                start=start,
                duration=timedelta(hours=int(hours), minutes=int(minutes)),
                url=f"https://atcoder.jp/contests/{link_match.group(1)}",
                rated_range=rated or None,
            )
        )
    return contests
