import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import GREEN, error_embed, info_embed, send_error
from bot.db.repo import users
from bot.services.roles import apply_rank, clear_nickname, ensure_rank_roles


async def unregister_user(bot, discord_id: int) -> bool:
    async with bot.session_factory() as session:
        removed = await users.delete_user(session, discord_id)
        await session.commit()
    if not removed:
        return False
    bot.avatars.delete(discord_id)
    guild = bot.get_guild(bot.settings.guild_id)
    member = guild.get_member(discord_id) if guild is not None else None
    if member is not None:
        async with bot.session_factory() as session:
            role_ids = await ensure_rank_roles(guild, session)
        await apply_rank(member, "", role_ids)
        await clear_nickname(member)
    return True


class ConfirmUnregisterView(discord.ui.View):
    def __init__(self, bot, owner_id: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        removed = await unregister_user(self.bot, interaction.user.id)
        if removed:
            embed = info_embed("Unregistered", "Your Codeforces link and all progress were removed. Use `/register` to start again.", colour=GREEN)
        else:
            embed = error_embed("You are not registered.")
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(embed=info_embed("Cancelled", "Nothing was changed."), view=None)


class UnregisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="unregister", description="Unlink your Codeforces handle and delete all your progress")
    async def unregister(self, interaction: discord.Interaction) -> None:
        async with self.bot.session_factory() as session:
            user = await users.get_by_discord(session, interaction.user.id)
        if user is None:
            await send_error(interaction, "You are not registered.")
            return
        embed = info_embed(
            "Unregister?",
            f"This deletes the link to **{user.handle}**, your EXP, money, streak, and solve history. This cannot be undone.",
        )
        await interaction.response.send_message(embed=embed, view=ConfirmUnregisterView(self.bot, interaction.user.id), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UnregisterCog(bot))
