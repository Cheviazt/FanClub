import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import GREEN, info_embed, send_error
from bot.db.repo import cf_cache, users
from bot.services.avatars import fetch_avatar
from bot.services.leveling import level_for, rank_for
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname
from bot.services.solve_processor import process_user
from bot.services.streak import today_wib

COOLDOWN_SECONDS = 60.0


@dataclass(frozen=True)
class RefreshReport:
    handle: str
    rating: int | None
    level: int
    new_solves: int


def is_allowed(caller_id: int, target_id: int, manage_guild: bool) -> bool:
    return caller_id == target_id or manage_guild


def can_refresh(last: dict[int, float], target_id: int, now: float, cooldown: float = COOLDOWN_SECONDS) -> bool:
    previous = last.get(target_id)
    return previous is None or now - previous >= cooldown


async def refresh_user(bot, discord_id: int, today: date) -> RefreshReport | None:
    async with bot.session_factory() as session:
        user = await users.get_by_discord(session, discord_id)
        if user is None:
            return None
        handle = user.handle
        info = (await bot.cf.user_info([handle]))[0]
        await cf_cache.upsert_cf_cache(session, discord_id, info, datetime.now(timezone.utc))
        await session.commit()
    await fetch_avatar(bot.cf, bot.avatars, discord_id, info.avatar_url)
    accepted = await bot.register_service.fetch_all_accepted(handle)
    async with bot.session_factory() as session:
        results = await process_user(session, discord_id, accepted, today)
        user = await users.get_by_discord(session, discord_id)
        exp = user.exp
    poller = bot.get_cog("PollerCog")
    for result in results:
        await poller.apply_side_effects(result)
    level = level_for(exp)
    guild = bot.get_guild(bot.settings.guild_id)
    member = guild.get_member(discord_id) if guild is not None else None
    if member is not None:
        if not poller.role_ids:
            async with bot.session_factory() as session:
                poller.role_ids = await ensure_rank_roles(guild, session)
        await apply_rank(member, rank_for(level).name, poller.role_ids)
        await set_level_nickname(member, level, handle)
    return RefreshReport(handle=handle, rating=info.rating, level=level, new_solves=len(results))


class RefreshCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_refresh: dict[int, float] = {}

    @app_commands.guild_only()
    @app_commands.command(name="refresh", description="Resync Codeforces data, missed solves, level, role, and nickname")
    @app_commands.describe(user="Whose data to refresh (Manage Server only)")
    async def refresh(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        if not is_allowed(interaction.user.id, target.id, interaction.user.guild_permissions.manage_guild):
            await send_error(interaction, "Only members with Manage Server can refresh other users.")
            return
        now = time.monotonic()
        if not can_refresh(self.last_refresh, target.id, now):
            remaining = int(COOLDOWN_SECONDS - (now - self.last_refresh[target.id]))
            await send_error(interaction, f"Please wait {remaining} seconds before refreshing again.")
            return
        self.last_refresh[target.id] = now
        await interaction.response.defer(ephemeral=True)
        report = await refresh_user(self.bot, target.id, today_wib())
        if report is None:
            await send_error(interaction, f"{target.mention} is not registered yet.")
            return
        rating = "Unrated" if report.rating is None else str(report.rating)
        description = f"**{report.handle}**: rating {rating}, level {report.level}, {report.new_solves} new solves."
        await interaction.followup.send(embed=info_embed("Refreshed", description, colour=GREEN), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RefreshCog(bot))
