import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.cf.models import Problem
from bot.cogs.common import send_error
from bot.db.repo import users
from bot.render.grinding import render_grinding
from bot.services.daily import NotEnoughProblems
from bot.services.grinding import MAX_COUNT, MAX_RATING, MIN_COUNT, MIN_RATING, UnknownTags, is_valid_rating, parse_tags, pick_problems

FILENAME = "grinding.png"


def build_grinding_view(problems: list[Problem]) -> discord.ui.View:
    view = discord.ui.View()
    for problem in problems:
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=f"Open {problem.code}", url=problem.url))
    return view


class GrindingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    @app_commands.command(name="grinding", description="Random unsolved problems by rating and tags")
    @app_commands.describe(
        count="How many problems (1 to 4)",
        rating="Problem rating (800 to 3500, multiple of 100)",
        tags="Required tags, comma separated (optional)",
    )
    async def grinding(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, MIN_COUNT, MAX_COUNT],
        rating: app_commands.Range[int, MIN_RATING, MAX_RATING],
        tags: str | None = None,
    ) -> None:
        if not is_valid_rating(rating):
            await send_error(interaction, "Rating must be a multiple of 100 between 800 and 3500.")
            return
        wanted = parse_tags(tags)
        async with self.bot.session_factory() as session:
            user = await users.get_by_discord(session, interaction.user.id)
            if user is None:
                await send_error(interaction, "You are not registered yet. Use `/register`.")
                return
            await interaction.response.defer()
            try:
                problems = await pick_problems(session, user.discord_id, count, rating, wanted)
            except UnknownTags as exc:
                await send_error(interaction, f"Unknown tags: {', '.join(exc.tags)}. Examples: dp, greedy, math, graphs, binary search.")
                return
            except NotEnoughProblems:
                await send_error(interaction, "Not enough unsolved problems match that rating and tags.")
                return
        png = await asyncio.to_thread(render_grinding, problems)
        file = discord.File(io.BytesIO(png), filename=FILENAME)
        await interaction.followup.send(file=file, view=build_grinding_view(problems))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GrindingCog(bot))
