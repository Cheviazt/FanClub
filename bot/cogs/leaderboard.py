import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.common import error_embed, image_embed
from bot.render.leaderboard import render_leaderboard
from bot.services.leaderboard import LEADERBOARD_TYPES, fetch_page

FILENAME = "leaderboard.png"
TITLES = {"level": "Leaderboard · Level", "rating": "Leaderboard · Rating", "solved": "Leaderboard · Solved", "streaks": "Leaderboard · Streaks"}


class LeaderboardView(discord.ui.View):
    def __init__(self, session_factory, kind: str, owner_id: int, page: int, total_pages: int) -> None:
        super().__init__(timeout=300)
        self.session_factory = session_factory
        self.kind = kind
        self.owner_id = owner_id
        self.page = page
        self.total_pages = total_pages
        self.message: discord.Message | None = None
        self.sync_buttons()

    def sync_buttons(self) -> None:
        self.back.disabled = self.page <= 1
        self.next.disabled = self.page >= self.total_pages

    async def build_message(self) -> tuple[discord.Embed, discord.File]:
        async with self.session_factory() as session:
            rows, self.total_pages = await fetch_page(session, self.kind, self.page)
        png = await asyncio.to_thread(render_leaderboard, self.kind, rows, self.page, self.total_pages)
        self.sync_buttons()
        return image_embed(TITLES[self.kind], FILENAME), discord.File(io.BytesIO(png), filename=FILENAME)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message(embed=error_embed("Only the person who ran this command can turn pages."), ephemeral=True)
        return False

    async def _show(self, interaction: discord.Interaction) -> None:
        embed, file = await self.build_message()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(1, self.page - 1)
        await self._show(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = min(self.total_pages, self.page + 1)
        await self._show(interaction)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="leaderboard", description="Show the server leaderboard")
    @app_commands.describe(type="Which leaderboard to show")
    @app_commands.choices(type=[app_commands.Choice(name=t, value=t) for t in LEADERBOARD_TYPES])
    async def leaderboard(self, interaction: discord.Interaction, type: app_commands.Choice[str]) -> None:
        await interaction.response.defer()
        view = LeaderboardView(self.bot.session_factory, type.value, interaction.user.id, page=1, total_pages=1)
        embed, file = await view.build_message()
        view.message = await interaction.followup.send(embed=embed, file=file, view=view, wait=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaderboardCog(bot))
