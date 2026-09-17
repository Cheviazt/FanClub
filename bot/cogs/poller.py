import datetime as dt
import logging

import discord
from discord.ext import commands, tasks

from bot.config import WIB
from bot.db.repo import cf_cache, problemset, users
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname
from bot.services.solve_processor import SolveResult, process_user
from bot.services.streak import is_broken, today_wib

log = logging.getLogger(__name__)
INFO_BATCH = 100


def format_solve_notification(result: SolveResult) -> str:
    p = result.problem
    rating = "(unrated)" if p.rating is None else f"(rating {p.rating})"
    return f"**{result.handle}** solved [{p.code} - {p.name}]({p.url}) {rating} | +{result.exp_gained} EXP | +${result.money_gained:.2f}"


class PollerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.role_ids: dict[str, int] = {}
        self.poll_solves.start()
        self.refresh_cf_cache.start()
        self.refresh_problemset.start()
        self.reset_streaks.start()

    def cog_unload(self) -> None:
        self.poll_solves.cancel()
        self.refresh_cf_cache.cancel()
        self.refresh_problemset.cancel()
        self.reset_streaks.cancel()

    def _guild(self) -> discord.Guild | None:
        return self.bot.get_guild(self.bot.settings.guild_id)

    async def apply_side_effects(self, result: SolveResult) -> None:
        guild = self._guild()
        if guild is not None:
            member = guild.get_member(result.discord_id)
            if member is not None:
                if result.new_level != result.old_level:
                    await set_level_nickname(member, result.new_level, result.handle)
                if result.new_rank != result.old_rank:
                    if not self.role_ids:
                        async with self.bot.session_factory() as session:
                            self.role_ids = await ensure_rank_roles(guild, session)
                    await apply_rank(member, result.new_rank, self.role_ids)
        channel = self.bot.get_channel(self.bot.settings.notify_channel_id)
        if channel is not None:
            try:
                await channel.send(format_solve_notification(result))
            except discord.HTTPException as exc:
                log.warning("notification failed: %s", exc)

    async def poll_once(self) -> None:
        async with self.bot.session_factory() as session:
            all_users = await users.list_users(session)
        today = today_wib()
        for user in all_users:
            try:
                submissions = await self.bot.cf.user_status(user.handle, from_=1, count=30)
                async with self.bot.session_factory() as session:
                    results = await process_user(session, user.discord_id, submissions, today)
                for result in results:
                    await self.apply_side_effects(result)
            except Exception:
                log.exception("poll failed for %s", user.handle)

    async def reset_broken_streaks(self, today: dt.date) -> int:
        changed = 0
        async with self.bot.session_factory() as session:
            for user in await users.list_users(session):
                if user.streak and is_broken(user.last_solve_date, today):
                    user.streak = 0
                    changed += 1
            await session.commit()
        return changed

    @tasks.loop(seconds=60)
    async def poll_solves(self) -> None:
        await self.poll_once()

    @tasks.loop(minutes=10)
    async def refresh_cf_cache(self) -> None:
        async with self.bot.session_factory() as session:
            all_users = await users.list_users(session)
            by_handle = {u.handle.lower(): u.discord_id for u in all_users}
            handles = list(by_handle)
            now = dt.datetime.now(dt.timezone.utc)
            for start in range(0, len(handles), INFO_BATCH):
                chunk = handles[start:start + INFO_BATCH]
                try:
                    infos = await self.bot.cf.user_info(chunk)
                except Exception:
                    log.exception("user.info refresh failed")
                    continue
                for info in infos:
                    discord_id = by_handle.get(info.handle.lower())
                    if discord_id is not None:
                        await cf_cache.upsert_cf_cache(session, discord_id, info, now)
            await session.commit()

    @tasks.loop(hours=6)
    async def refresh_problemset(self) -> None:
        try:
            problems = await self.bot.cf.problemset_problems()
        except Exception:
            log.exception("problemset refresh failed")
            return
        async with self.bot.session_factory() as session:
            count = await problemset.replace_problemset(session, problems, dt.datetime.now(dt.timezone.utc))
            await session.commit()
        log.info("problemset cache refreshed: %d problems", count)

    @tasks.loop(time=dt.time(hour=0, minute=5, tzinfo=WIB))
    async def reset_streaks(self) -> None:
        changed = await self.reset_broken_streaks(today_wib())
        log.info("streaks reset: %d", changed)

    @poll_solves.before_loop
    @refresh_cf_cache.before_loop
    @refresh_problemset.before_loop
    @reset_streaks.before_loop
    async def wait_ready(self) -> None:
        await self.bot.wait_until_ready()
        guild = self._guild()
        if guild is not None and not self.role_ids:
            async with self.bot.session_factory() as session:
                self.role_ids = await ensure_rank_roles(guild, session)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollerCog(bot))
