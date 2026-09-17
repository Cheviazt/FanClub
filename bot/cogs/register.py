import logging
import random
import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cf.client import CodeforcesError
from bot.cf.models import Submission, UserInfo
from bot.cogs.common import GREEN, error_embed, info_embed, send_error
from bot.db.models import User
from bot.db.repo import cf_cache, problemset, solved, users
from bot.services.register import PendingRegistration, RegistrationInProgress
from bot.services.roles import apply_rank, ensure_rank_roles, set_level_nickname

log = logging.getLogger(__name__)
HANDLE_RE = re.compile(r"^[A-Za-z0-9_.-]{3,24}$")


class AlreadyRegistered(Exception):
    pass


def is_valid_handle(handle: str) -> bool:
    return HANDLE_RE.fullmatch(handle) is not None


def build_instruction_embed(pending: PendingRegistration) -> discord.Embed:
    description = (
        f"Verify that **{pending.handle}** is yours.\n\n"
        f"Submit any code that gets a **Compilation Error** verdict on "
        f"[{pending.problem.code} - {pending.problem.name}]({pending.problem.url}).\n\n"
        f"Deadline: <t:{pending.deadline}:R>. I check every 10 seconds."
    )
    return info_embed("Codeforces verification", description)


async def finalize_registration(
    session: AsyncSession,
    pending: PendingRegistration,
    info: UserInfo,
    accepted: list[Submission],
    now: datetime,
) -> User:
    if await users.get_by_discord(session, pending.discord_id) is not None:
        raise AlreadyRegistered()
    if await users.get_by_handle(session, info.handle) is not None:
        raise AlreadyRegistered()
    user = await users.create_user(session, pending.discord_id, info.handle)
    items = [(s.problem.contest_id, s.problem.index, datetime.fromtimestamp(s.created_at, tz=timezone.utc)) for s in accepted]
    await solved.bulk_add_solved(session, user.discord_id, items)
    await cf_cache.upsert_cf_cache(session, user.discord_id, info, now)
    await session.commit()
    return user


class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="register", description="Link your Codeforces handle to this Discord account")
    @app_commands.describe(handle="Your Codeforces handle")
    async def register(self, interaction: discord.Interaction, handle: str) -> None:
        bot = self.bot
        if not is_valid_handle(handle):
            await send_error(interaction, "Invalid Codeforces handle.")
            return
        async with bot.session_factory() as session:
            if await users.get_by_discord(session, interaction.user.id) is not None:
                await send_error(interaction, "You are already registered.")
                return
            if await users.get_by_handle(session, handle) is not None:
                await send_error(interaction, f"Handle **{handle}** is already linked to another Discord account.")
                return
            problems = await problemset.list_problems(session)
        if not problems:
            await send_error(interaction, "Problem list is not ready yet. Try again in a minute.")
            return
        await interaction.response.defer(ephemeral=True)
        try:
            info = (await bot.cf.user_info([handle]))[0]
        except CodeforcesError as exc:
            if "not found" in str(exc):
                await send_error(interaction, f"Codeforces handle **{handle}** was not found.")
            else:
                await send_error(interaction, "Codeforces is unavailable right now. Try again later.")
            return
        try:
            pending = bot.register_service.start(interaction.user.id, info.handle, random.choice(problems))
        except RegistrationInProgress:
            await send_error(interaction, "You already have a verification in progress.")
            return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Open problem", url=pending.problem.url))
        message = await interaction.followup.send(embed=build_instruction_embed(pending), view=view, wait=True)

        verified = await bot.register_service.wait_for_verification(pending)
        if not verified:
            await message.edit(embed=error_embed("Verification timed out. Run `/register` again."), view=None)
            return
        accepted = await bot.register_service.fetch_all_accepted(info.handle)
        async with bot.session_factory() as session:
            try:
                await finalize_registration(session, pending, info, accepted, datetime.now(timezone.utc))
            except AlreadyRegistered:
                await message.edit(embed=error_embed("This handle or account was registered in the meantime."), view=None)
                return
            role_ids = await ensure_rank_roles(interaction.guild, session)
        member = interaction.guild.get_member(interaction.user.id)
        if member is not None:
            await apply_rank(member, "Rookie", role_ids)
            await set_level_nickname(member, 1, info.handle)
        embed = info_embed("Registered", f"**{info.handle}** is now linked to {interaction.user.mention}. Solved problems imported: {len(accepted)}.", colour=GREEN)
        await message.edit(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RegisterCog(bot))
