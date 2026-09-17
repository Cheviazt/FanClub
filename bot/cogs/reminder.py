import datetime as dt
import logging

import discord
from discord.ext import commands, tasks

from bot.config import WIB

log = logging.getLogger(__name__)

REMINDER_GIF = "https://tenor.com/view/codeforces-bro-code-programming-competitive-programming-practice-gif-12606490193516357696"
REMINDER_TIME = dt.time(hour=9, minute=0, tzinfo=WIB)


class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        if bot.settings.reminder_channel_id:
            self.daily_reminder.start()

    def cog_unload(self) -> None:
        self.daily_reminder.cancel()

    async def send_reminder(self) -> None:
        channel = self.bot.get_channel(self.bot.settings.reminder_channel_id)
        if channel is None:
            log.warning("reminder channel %s not found", self.bot.settings.reminder_channel_id)
            return
        await channel.send(f"@everyone\n{REMINDER_GIF}", allowed_mentions=discord.AllowedMentions(everyone=True))

    @tasks.loop(time=REMINDER_TIME)
    async def daily_reminder(self) -> None:
        try:
            await self.send_reminder()
        except Exception:
            log.exception("daily reminder failed")

    @daily_reminder.before_loop
    async def wait_ready(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))
