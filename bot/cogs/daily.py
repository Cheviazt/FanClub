import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.cf.models import Problem
from bot.cogs.common import image_embed, send_error
from bot.db.repo import users
from bot.render.daily import render_daily
from bot.services.daily import NotEnoughProblems, get_or_create_daily
from bot.services.streak import today_wib

FILENAME = "daily.png"


def build_daily_view(problems: list[Problem]) -> discord.ui.View:
    view = discord.ui.View()
    for problem in problems:
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=str(problem.rating), url=problem.url))
    return view


class DailyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="daily", description="Your three daily problems (900, 1200, 1600)")
    async def daily(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        async with self.bot.session_factory() as session:
            user = await users.get_by_discord(session, interaction.user.id)
            if user is None:
                await send_error(interaction, "You are not registered yet. Use `/register`.")
                return
            try:
                problems = await get_or_create_daily(session, user.discord_id, today_wib())
            except NotEnoughProblems:
                await send_error(interaction, "Could not find enough unsolved problems for you today.")
                return
        png = await asyncio.to_thread(render_daily, problems)
        file = discord.File(io.BytesIO(png), filename=FILENAME)
        embed = image_embed(f"Daily problems for {user.handle}", FILENAME)
        await interaction.followup.send(embed=embed, file=file, view=build_daily_view(problems))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DailyCog(bot))
