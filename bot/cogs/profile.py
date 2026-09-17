import asyncio
import io
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cogs.common import send_error
from bot.db.models import User
from bot.db.repo import cf_cache, problemset, solved, users
from bot.render.profile import ProfileData, format_last_seen, render_profile
from bot.services.avatars import fetch_avatar
from bot.services.leveling import exp_progress, level_for, rank_for


async def build_profile_data(session: AsyncSession, user: User, avatar: bytes | None, now: datetime) -> ProfileData:
    cache = await cf_cache.get_cf_cache(session, user.discord_id)
    last_online = None
    if cache is not None:
        last_online = cache.last_online
        if last_online.tzinfo is None:
            last_online = last_online.replace(tzinfo=timezone.utc)
    level = level_for(user.exp)
    exp_in_level, exp_need = exp_progress(user.exp)
    lines: list[str] = []
    for row in await solved.last_solved(session, user.discord_id, limit=3):
        problem = await problemset.get_problem(session, row.contest_id, row.index)
        code = f"{row.contest_id}{row.index}"
        lines.append(f"{code} · {problem.name}" if problem else code)
    return ProfileData(
        handle=user.handle,
        avatar=avatar,
        level=level,
        rank_name=rank_for(level).name,
        exp_in_level=exp_in_level,
        exp_need=exp_need,
        money=user.money,
        rating=cache.rating if cache else None,
        max_rating=cache.max_rating if cache else None,
        cf_rank=cache.rank if cache else None,
        last_seen=format_last_seen(last_online, now) if cache else "unknown",
        last_solved=lines,
        solved_count=await solved.solved_count(session, user.discord_id),
        streak=user.streak,
    )


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="profile", description="Show a player's profile card")
    @app_commands.describe(user="Whose profile to show (default: you)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        async with self.bot.session_factory() as session:
            row = await users.get_by_discord(session, target.id)
            if row is None:
                await send_error(interaction, f"{target.mention} is not registered yet. Use `/register`.")
                return
            await interaction.response.defer()
            cache = await cf_cache.get_cf_cache(session, row.discord_id)
            avatar = await fetch_avatar(self.bot.cf, self.bot.avatars, row.discord_id, cache.avatar_url if cache else "")
            data = await build_profile_data(session, row, avatar, datetime.now(timezone.utc))
        png = await asyncio.to_thread(render_profile, data)
        file = discord.File(io.BytesIO(png), filename="profile.png")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="See Profile", url=f"https://codeforces.com/profile/{row.handle}"))
        await interaction.followup.send(file=file, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
