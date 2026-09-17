import asyncio
import logging

import discord
from discord.ext import commands

from bot.cf.client import CodeforcesClient
from bot.config import Settings
from bot.db.session import make_engine, make_session_factory
from bot.services.register import RegisterService

EXTENSIONS = (
    "bot.cogs.register",
    "bot.cogs.profile",
    "bot.cogs.leaderboard",
    "bot.cogs.daily",
    "bot.cogs.poller",
)


class FanClubBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.engine = make_engine(settings.database_url)
        self.session_factory = make_session_factory(self.engine)
        self.cf = CodeforcesClient()
        self.register_service = RegisterService(self.cf)

    async def setup_hook(self) -> None:
        for name in EXTENSIONS:
            await self.load_extension(name)
        guild = discord.Object(id=self.settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def close(self) -> None:
        await self.cf.close()
        await self.engine.dispose()
        await super().close()


def run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bot = FanClubBot(settings)
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    run()
