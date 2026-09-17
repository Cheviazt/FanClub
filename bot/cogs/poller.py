import asyncio
import datetime as dt
import io
import logging

import discord
from discord.ext import commands, tasks

from bot.cf.client import CodeforcesError
from bot.cf.models import UserInfo
from bot.config import WIB
from bot.db.repo import cf_cache, problemset, users
from bot.render.accepted import AcceptedData, render_accepted
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname
from bot.services.solve_processor import SolveResult, process_user
from bot.services.streak import is_broken, today_wib

log = logging.getLogger(__name__)
INFO_BATCH = 100


def accepted_data(result: SolveResult) -> AcceptedData:
    return AcceptedData(
        handle=result.handle,
        rank_name=result.new_rank,
        problem=result.problem,
        exp_gained=result.exp_gained,
        money_gained=result.money_gained,
    )


def accepted_view(result: SolveResult) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=f"Open {result.problem.code}", url=result.problem.url))
    return view


class PollerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.role_ids: dict[str, int] = {}
        self._roles_lock = asyncio.Lock()
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
        if channel is None:
            log.warning("notify channel %s not found", self.bot.settings.notify_channel_id)
            return
        png = await asyncio.to_thread(render_accepted, accepted_data(result))
        file = discord.File(io.BytesIO(png), filename="accepted.png")
        try:
            await channel.send(content=f"<@{result.discord_id}>", file=file, view=accepted_view(result))
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
        try:
            await self.poll_once()
        except Exception:
            log.exception("poll_solves failed")

    async def _user_info_each(self, handles: list[str]) -> list[UserInfo]:
        infos: list[UserInfo] = []
        for handle in handles:
            try:
                infos.extend(await self.bot.cf.user_info([handle]))
            except CodeforcesError as exc:
                log.warning("user.info failed for %s: %s", handle, exc)
        return infos

    @tasks.loop(minutes=10)
    async def refresh_cf_cache(self) -> None:
        try:
            async with self.bot.session_factory() as session:
                all_users = await users.list_users(session)
                by_handle = {u.handle.lower(): u.discord_id for u in all_users}
                handles = list(by_handle)
                now = dt.datetime.now(dt.timezone.utc)
                for start in range(0, len(handles), INFO_BATCH):
                    chunk = handles[start:start + INFO_BATCH]
                    try:
                        infos = await self.bot.cf.user_info(chunk)
                    except CodeforcesError:
                        infos = await self._user_info_each(chunk)
                    except Exception:
                        log.exception("user.info refresh failed")
                        continue
                    for info in infos:
                        discord_id = by_handle.get(info.handle.lower())
                        if discord_id is not None:
                            await cf_cache.upsert_cf_cache(session, discord_id, info, now)
                await session.commit()
        except Exception:
            log.exception("refresh_cf_cache failed")

    @tasks.loop(hours=6)
    async def refresh_problemset(self) -> None:
        try:
            try:
                problems = await self.bot.cf.problemset_problems()
            except Exception:
                log.exception("problemset refresh failed")
                return
            async with self.bot.session_factory() as session:
                count = await problemset.replace_problemset(session, problems, dt.datetime.now(dt.timezone.utc))
                await session.commit()
            log.info("problemset cache refreshed: %d problems", count)
        except Exception:
            log.exception("refresh_problemset failed")

    @tasks.loop(time=dt.time(hour=0, minute=5, tzinfo=WIB))
    async def reset_streaks(self) -> None:
        try:
            changed = await self.reset_broken_streaks(today_wib())
            log.info("streaks reset: %d", changed)
        except Exception:
            log.exception("reset_streaks failed")

    @poll_solves.before_loop
    @refresh_cf_cache.before_loop
    @refresh_problemset.before_loop
    @reset_streaks.before_loop
    async def wait_ready(self) -> None:
        await self.bot.wait_until_ready()
        async with self._roles_lock:
            try:
                guild = self._guild()
                if guild is not None and not self.role_ids:
                    async with self.bot.session_factory() as session:
                        self.role_ids = await ensure_rank_roles(guild, session)
            except Exception:
                log.exception("rank role setup failed")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollerCog(bot))
