import logging
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import GREEN, info_embed, send_error

log = logging.getLogger(__name__)


@dataclass
class ResetReport:
    members: int = 0
    roles_removed: int = 0
    nicknames_cleared: int = 0
    failed: int = 0


def roles_to_strip(member: discord.Member, keep: set[int]) -> list[discord.Role]:
    return [
        role
        for role in member.roles
        if not role.is_default() and not role.managed and role.id not in keep and role < member.guild.me.top_role
    ]


async def reset_member(member: discord.Member, keep: set[int], report: ResetReport) -> None:
    if member.bot:
        return
    report.members += 1
    strip = roles_to_strip(member, keep)
    try:
        if strip:
            await member.remove_roles(*strip, reason="resetall")
            report.roles_removed += len(strip)
        if member.nick is not None:
            await member.edit(nick=None, reason="resetall")
            report.nicknames_cleared += 1
    except (discord.Forbidden, discord.HTTPException) as exc:
        report.failed += 1
        log.warning("resetall failed for %s: %s", member.id, exc)


async def reset_guild(guild: discord.Guild, keep: set[int]) -> ResetReport:
    report = ResetReport()
    async for member in guild.fetch_members(limit=None):
        await reset_member(member, keep, report)
    return report


class ConfirmResetView(discord.ui.View):
    def __init__(self, bot, owner_id: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id

    @discord.ui.button(label="Reset everyone", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(embed=info_embed("Resetting", "Working through every member. This can take a while."), view=None)
        report = await reset_guild(interaction.guild, self.bot.settings.keep_role_ids)
        description = (
            f"Members processed: {report.members}\n"
            f"Roles removed: {report.roles_removed}\n"
            f"Nicknames cleared: {report.nicknames_cleared}\n"
            f"Failed (missing permission or above the bot): {report.failed}"
        )
        await interaction.edit_original_response(embed=info_embed("Reset complete", description, colour=GREEN))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(embed=info_embed("Cancelled", "Nothing was changed."), view=None)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="resetall", description="Admin: strip roles and nicknames from every member")
    async def resetall(self, interaction: discord.Interaction) -> None:
        keep = self.bot.settings.keep_role_ids
        kept = ", ".join(f"<@&{role_id}>" for role_id in sorted(keep)) or "none"
        embed = info_embed(
            "Reset every member?",
            "This removes every role the bot can manage from every member and clears all nicknames. "
            f"Roles kept: {kept}. Registrations and progress in the bot are not touched.",
        )
        await interaction.response.send_message(embed=embed, view=ConfirmResetView(self.bot, interaction.user.id), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
