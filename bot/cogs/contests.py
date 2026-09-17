import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from bot.contests.models import PLATFORM_COLORS, Contest, format_duration
from bot.contests.sources import ATCODER_URL, CODECHEF_URL, parse_atcoder, parse_codechef, parse_codeforces
from bot.db.repo import contests as notices

log = logging.getLogger(__name__)

ANNOUNCE_WINDOW = timedelta(days=7)
REMIND_WINDOW = timedelta(minutes=60)
POLL_MINUTES = 30


def contest_view(contest: Contest) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=f"Open on {contest.platform}", url=contest.url))
    return view


def announcement_embed(contest: Contest) -> discord.Embed:
    start = int(contest.start.timestamp())
    end = int(contest.end.timestamp())
    embed = discord.Embed(
        title=f"★ {discord.utils.escape_markdown(contest.name)}",
        url=contest.url,
        description=f"A new contest is on the calendar. Starts <t:{start}:R>.",
        colour=PLATFORM_COLORS.get(contest.platform, 0x1E88E5),
    )
    embed.set_author(name=f"◆ {contest.platform}")
    embed.add_field(name="▸ Starts", value=f"<t:{start}:F>", inline=True)
    embed.add_field(name="▸ Ends", value=f"<t:{end}:F>", inline=True)
    embed.add_field(name="▸ Duration", value=format_duration(contest.duration), inline=True)
    if contest.rated_range:
        embed.add_field(name="▸ Rated range", value=contest.rated_range, inline=True)
    embed.set_footer(text=f"{contest.platform} · {contest.key} · just think then code it")
    return embed


def reminder_embed(contest: Contest) -> discord.Embed:
    start = int(contest.start.timestamp())
    embed = discord.Embed(
        title=f"⏳ Starting soon: {discord.utils.escape_markdown(contest.name)}",
        url=contest.url,
        description=(
            f"▸ Begins <t:{start}:R> at <t:{start}:t>\n"
            f"▸ Duration {format_duration(contest.duration)}\n"
            "▸ Register now if you have not yet. Good luck!"
        ),
        colour=PLATFORM_COLORS.get(contest.platform, 0x1E88E5),
    )
    embed.set_author(name=f"◆ {contest.platform}")
    embed.set_footer(text=f"{contest.platform} · {contest.key} · just think then code it")
    return embed


def select_due(contests: list[Contest], seen: dict, now: datetime) -> tuple[list[Contest], list[Contest]]:
    announce: list[Contest] = []
    remind: list[Contest] = []
    for contest in sorted(contests, key=lambda c: c.start):
        if contest.start <= now:
            continue
        until = contest.start - now
        row = seen.get((contest.platform, contest.key))
        if until <= ANNOUNCE_WINDOW and (row is None or row.announced_at is None):
            announce.append(contest)
        if until <= REMIND_WINDOW and (row is None or row.reminded_at is None):
            remind.append(contest)
    return announce, remind


class ContestsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        if bot.settings.contest_channel_id:
            self.check_contests.start()

    def cog_unload(self) -> None:
        self.check_contests.cancel()

    async def fetch_all(self) -> list[Contest]:
        contests: list[Contest] = []
        try:
            contests.extend(parse_codeforces(await self.bot.cf.contest_list()))
        except Exception as exc:
            log.warning("codeforces contests unavailable: %s", exc)
        try:
            contests.extend(parse_codechef(await self.bot.cf.fetch_json(CODECHEF_URL)))
        except Exception as exc:
            log.warning("codechef contests unavailable: %s", exc)
        try:
            contests.extend(parse_atcoder(await self.bot.cf.fetch_text(ATCODER_URL)))
        except Exception as exc:
            log.warning("atcoder contests unavailable: %s", exc)
        return contests

    async def notify_once(self) -> None:
        channel = self.bot.get_channel(self.bot.settings.contest_channel_id)
        if channel is None:
            log.warning("contest channel %s not found", self.bot.settings.contest_channel_id)
            return
        contests = await self.fetch_all()
        now = datetime.now(timezone.utc)
        async with self.bot.session_factory() as session:
            seen = await notices.list_notices(session)
            announce, remind = select_due(contests, seen, now)
            for contest in announce:
                await channel.send(embed=announcement_embed(contest), view=contest_view(contest))
                await notices.mark(session, contest.platform, contest.key, now, announced=True)
                await session.commit()
            for contest in remind:
                await channel.send(embed=reminder_embed(contest), view=contest_view(contest))
                await notices.mark(session, contest.platform, contest.key, now, reminded=True)
                await session.commit()

    @tasks.loop(minutes=POLL_MINUTES)
    async def check_contests(self) -> None:
        try:
            await self.notify_once()
        except Exception:
            log.exception("contest check failed")

    @check_contests.before_loop
    async def wait_ready(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ContestsCog(bot))
