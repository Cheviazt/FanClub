import discord
from discord import app_commands
from discord.ext import commands

from bot.services.leveling import RANKS

ACCENT = 0x1E88E5


def rank_table() -> str:
    lines = []
    for rank in RANKS:
        top = "and up" if rank.max_level is None else f"to {rank.max_level}"
        lines.append(f"`{rank.min_level:>3} {top:<7}` {rank.name}")
    return "\n".join(lines)


def how_embed() -> discord.Embed:
    embed = discord.Embed(
        title="How this bot works",
        description=(
            "Link your Codeforces handle once. From then on, every problem you solve for the first time "
            "on Codeforces earns EXP and money here, raises your level, and moves you through the server ranks. "
            "Nothing is counted twice: only problems your Codeforces account has never solved before are rewarded."
        ),
        colour=ACCENT,
    )
    embed.add_field(
        name="Rewards per new solve",
        value=(
            "EXP: `problem rating / 10`\n"
            "Money: `problem rating / 200`\n"
            "Unrated problems still count as solved but give nothing.\n"
            "Example: a 1400 rated problem gives 140 EXP and $7.00."
        ),
        inline=False,
    )
    embed.add_field(
        name="Levels",
        value=(
            "Level 1 needs 100 EXP, level 2 needs 200 more, level 3 needs 300 more, and so on. "
            "Your nickname shows your level as `【level】handle` and updates on its own."
        ),
        inline=False,
    )
    embed.add_field(name="Ranks by level", value=rank_table(), inline=False)
    embed.add_field(
        name="Streaks",
        value="Solve at least one new problem every day (Asia/Jakarta) to keep your streak. Miss a day and it resets to zero.",
        inline=False,
    )
    embed.add_field(
        name="Commands",
        value=(
            "`/register handle` link your Codeforces account\n"
            "`/profile [@user]` profile card with level, money, rating and recent solves\n"
            "`/leaderboard type` top players by level, rating, solved or streak\n"
            "`/daily` three personal problems (900, 1200, 1600) that reset every day\n"
            "`/grinding count rating [tags]` random unsolved problems that fit your filters\n"
            "`/refresh [@user]` resync your data if something looks out of date\n"
            "`/unregister` unlink your account and wipe your progress\n"
            "`/howtoregist` step by step registration guide"
        ),
        inline=False,
    )
    embed.add_field(
        name="Notifications",
        value=(
            "Every new accepted solve is posted to the solve channel within a few minutes. "
            "Upcoming contests from Codeforces, CodeChef and AtCoder are announced up to a week ahead, "
            "with a reminder one hour before the start."
        ),
        inline=False,
    )
    embed.set_footer(text="Solves are checked about once a minute per player. If something looks stale, run /refresh.")
    return embed


def howtoregist_embed() -> discord.Embed:
    embed = discord.Embed(
        title="How to register",
        description=(
            "Registration proves that a Codeforces handle belongs to you. It takes about a minute and "
            "you only do it once."
        ),
        colour=ACCENT,
    )
    embed.add_field(
        name="1. Run the command",
        value="Type `/register` and enter your exact Codeforces handle, for example `/register tourist`.",
        inline=False,
    )
    embed.add_field(
        name="2. Open the problem the bot gives you",
        value="The bot replies with a link to a random problem. Only you can see this message.",
        inline=False,
    )
    embed.add_field(
        name="3. Submit code that fails to compile",
        value=(
            "Submit anything that produces a **Compilation Error** on that problem, for example a file "
            "containing just the word `hello`. This does not affect your Codeforces rating or statistics."
        ),
        inline=False,
    )
    embed.add_field(
        name="4. Wait for confirmation",
        value=(
            "The bot checks your submissions every 10 seconds for up to 5 minutes. As soon as it sees the "
            "compilation error, your accounts are linked, your past solves are imported, and your nickname and "
            "rank role are set."
        ),
        inline=False,
    )
    embed.add_field(
        name="Common problems",
        value=(
            "Handle not found: check the spelling on codeforces.com.\n"
            "Timed out: run `/register` again and submit within 5 minutes.\n"
            "Handle already linked: each Codeforces account can be linked to one Discord account. "
            "Use `/unregister` on the other account first."
        ),
        inline=False,
    )
    embed.set_footer(text="Your EXP, money and streak start at zero. Earlier solves count toward your solved total but give no EXP.")
    return embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="how", description="How the bot, levels, ranks and rewards work")
    async def how(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=how_embed())

    @app_commands.command(name="howtoregist", description="Step by step guide to linking your Codeforces handle")
    async def howtoregist(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=howtoregist_embed())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
