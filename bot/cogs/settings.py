import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import BLUE, send_error
from bot.db.repo import settings as settings_repo
from bot.db.repo import users
from bot.services.settings import SETTINGS

ON = "▸ On"
OFF = "▸ Off"


def settings_embed(handle: str, flags: dict[str, bool]) -> discord.Embed:
    embed = discord.Embed(
        title="★ Your settings",
        description=f"Preferences for **{handle}**. Use the buttons below to switch anything on or off.",
        colour=BLUE,
    )
    for setting in SETTINGS:
        state = ON if flags[setting.key] else OFF
        embed.add_field(name=f"{setting.label} · {state}", value=setting.description, inline=False)
    embed.set_footer(text="Only you can see this message.")
    return embed


class SettingToggle(discord.ui.Button):
    def __init__(self, view_owner: int, key: str, label: str, enabled: bool) -> None:
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
        )
        self.view_owner = view_owner
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SettingsView = self.view
        async with view.bot.session_factory() as session:
            flags = await settings_repo.toggle_flag(session, view.owner_id, self.key)
            await session.commit()
        view.refresh(flags)
        await interaction.response.edit_message(embed=settings_embed(view.handle, flags), view=view)


class SettingsView(discord.ui.View):
    def __init__(self, bot, owner_id: int, handle: str, flags: dict[str, bool]) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.owner_id = owner_id
        self.handle = handle
        self.refresh(flags)

    def refresh(self, flags: dict[str, bool]) -> None:
        self.clear_items()
        for setting in SETTINGS:
            self.add_item(SettingToggle(self.owner_id, setting.key, setting.label, flags[setting.key]))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    @app_commands.command(name="settings", description="Change how the bot treats you: announcements, mentions, nickname")
    async def settings(self, interaction: discord.Interaction) -> None:
        async with self.bot.session_factory() as session:
            user = await users.get_by_discord(session, interaction.user.id)
            if user is None:
                await send_error(interaction, "You are not registered yet. Use `/register`.")
                return
            flags = await settings_repo.get_flags(session, user.discord_id)
        view = SettingsView(self.bot, interaction.user.id, user.handle, flags)
        await interaction.response.send_message(embed=settings_embed(user.handle, flags), view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
