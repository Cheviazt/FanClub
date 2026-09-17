from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.contests import ContestsCog, announcement_embed, contest_view, reminder_embed, select_due
from bot.cogs.help import how_embed, howtoregist_embed
from bot.cogs.reminder import REMINDER_GIF, ReminderCog
from bot.contests.models import ATCODER, CODECHEF, CODEFORCES, Contest, format_duration
from bot.contests.sources import parse_atcoder, parse_codechef, parse_codeforces
from bot.db.repo import contests as notices

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)

ATCODER_HTML = """
<div id="contest-table-upcoming"><table><tbody>
<tr><td class="text-center"><a href='x'><time class='fixtime fixtime-full'>2026-09-19 21:00:00+0900</time></a></td>
<td><span>&#9398;</span> <a href="/contests/abc476">JIJ Programming Contest 2026（AtCoder Beginner Contest 476）</a></td>
<td class="text-center">01:40</td> <td class="text-center"> - 1999</td></tr>
<tr><td class="text-center"><time class='fixtime fixtime-full'>2026-09-20 21:00:00+0900</time></td>
<td><a href="/contests/arc230">AtCoder Regular Contest 230</a></td>
<td class="text-center">02:30</td> <td class="text-center">1600 - 2999</td></tr>
</tbody></table></div>
<div id="contest-table-recent"><table><tr><td><time class='fixtime fixtime-full'>2026-09-01 21:00:00+0900</time></td><td><a href="/contests/old">Old</a></td><td class="text-center">01:00</td><td class="text-center">-</td></tr></table></div>
"""


def test_parse_codeforces_keeps_upcoming_only():
    result = [
        {"id": 1, "name": "Round A", "phase": "BEFORE", "durationSeconds": 7200, "startTimeSeconds": 1792247700},
        {"id": 2, "name": "Round B", "phase": "FINISHED", "durationSeconds": 7200, "startTimeSeconds": 1700000000},
    ]
    contests = parse_codeforces(result)
    assert [c.key for c in contests] == ["1"]
    assert contests[0].platform == CODEFORCES and contests[0].url == "https://codeforces.com/contests/1"
    assert contests[0].duration == timedelta(hours=2)


def test_parse_codechef():
    payload = {
        "future_contests": [
            {
                "contest_code": "START200",
                "contest_name": "Starters 200",
                "contest_start_date_iso": "2026-09-24T20:00:00+05:30",
                "contest_end_date_iso": "2026-09-24T22:00:00+05:30",
            },
            {"contest_code": "", "contest_name": "broken"},
        ]
    }
    contests = parse_codechef(payload)
    assert len(contests) == 1
    c = contests[0]
    assert c.platform == CODECHEF and c.url == "https://www.codechef.com/START200"
    assert c.start == datetime(2026, 9, 24, 14, 30, tzinfo=timezone.utc) and c.duration == timedelta(hours=2)


def test_parse_atcoder_reads_upcoming_table_only():
    contests = parse_atcoder(ATCODER_HTML)
    assert [c.key for c in contests] == ["abc476", "arc230"]
    first = contests[0]
    assert first.platform == ATCODER
    assert first.start == datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    assert first.duration == timedelta(hours=1, minutes=40)
    assert first.rated_range == "- 1999"
    assert first.name.startswith("JIJ Programming Contest 2026")
    assert parse_atcoder("<html></html>") == []


def test_format_duration():
    assert format_duration(timedelta(hours=2)) == "2h"
    assert format_duration(timedelta(hours=2, minutes=30)) == "2h 30m"
    assert format_duration(timedelta(days=2, minutes=5)) == "2d 5m"
    assert format_duration(timedelta(0)) == "0m"


def make(key, hours_ahead, platform=CODEFORCES, base=NOW):
    return Contest(platform, key, f"Contest {key}", base + timedelta(hours=hours_ahead), timedelta(hours=2), "https://x")


def test_select_due_windows():
    contests = [make("far", 24 * 10), make("week", 24 * 3), make("soon", 0.5), make("past", -1)]
    seen = {
        (CODEFORCES, "week"): SimpleNamespace(announced_at=NOW, reminded_at=None),
    }
    announce, remind = select_due(contests, seen, NOW)
    assert [c.key for c in announce] == ["soon"]
    assert [c.key for c in remind] == ["soon"]


def test_embeds_and_view():
    c = Contest(ATCODER, "abc1", "Beginner *Contest* 1", NOW + timedelta(days=1), timedelta(minutes=100), "https://atcoder.jp/contests/abc1", "- 1999")
    embed = announcement_embed(c)
    assert embed.title.endswith("Beginner \*Contest\* 1") and embed.url == c.url
    names = [f.name for f in embed.fields]
    assert [n.split(" ", 1)[1] for n in names] == ["Starts", "Ends", "Duration", "Rated range"]
    assert "<t:" in embed.fields[0].value and "<t:" in embed.description
    reminder = reminder_embed(c)
    assert "Starting soon:" in reminder.title
    button = contest_view(c).children[0]
    assert button.url == c.url and button.label == "Open on AtCoder"


async def test_notify_once_announces_and_marks(session_factory):
    bot = MagicMock()
    bot.session_factory = session_factory
    bot.settings.contest_channel_id = 42
    channel = MagicMock()
    channel.send = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel)
    cog = ContestsCog.__new__(ContestsCog)
    cog.bot = bot
    real_now = datetime.now(timezone.utc)
    cog.fetch_all = AsyncMock(return_value=[make("a", 24, base=real_now), make("b", 0.5, base=real_now)])
    await cog.notify_once()
    assert channel.send.await_count == 3
    async with session_factory() as s:
        seen = await notices.list_notices(s)
    assert seen[(CODEFORCES, "a")].announced_at is not None and seen[(CODEFORCES, "a")].reminded_at is None
    assert seen[(CODEFORCES, "b")].reminded_at is not None
    channel.send.reset_mock()
    await cog.notify_once()
    channel.send.assert_not_awaited()


async def test_reminder_sends_everyone_and_gif():
    bot = MagicMock()
    bot.settings.reminder_channel_id = 7
    channel = MagicMock()
    channel.send = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel)
    cog = ReminderCog.__new__(ReminderCog)
    cog.bot = bot
    await cog.send_reminder()
    args, kwargs = channel.send.await_args
    assert args[0] == f"@everyone\n{REMINDER_GIF}"
    assert kwargs["allowed_mentions"].everyone is True


def test_help_embeds_render():
    how = how_embed({"Rookie": 123})
    ranks = next(f for f in how.fields if f.name == "▸ Ranks")
    assert "<@&123>" in ranks.value and "**Elite**" in ranks.value
    assert "0 to 20,999 EXP" in ranks.value and "4,515,000 EXP and beyond" in ranks.value
    assert "FanClub" in how.title and "Universitas Brawijaya" in how.description
    assert len(ranks.value) <= 1024 and sum(len(f.value) for f in how.fields) < 6000
    guide = howtoregist_embed()
    assert len(guide.fields) == 3 and "/register" in guide.fields[1].value
