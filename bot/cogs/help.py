import discord
from discord.ext import commands

from bot.db.repo import roles as roles_repo
from bot.services.leveling import RANKS, threshold

ACCENT = 0x1E88E5


def rank_lines(role_ids: dict[str, int]) -> str:
    lines = []
    for rank in RANKS:
        role_id = role_ids.get(rank.name)
        label = f"<@&{role_id}>" if role_id else f"**{rank.name}**"
        low = threshold(rank.min_level)
        if rank.max_level is None:
            levels = f"Level {rank.min_level}+"
            exp = f"{low:,} EXP and beyond"
        else:
            levels = f"Level {rank.min_level} to {rank.max_level}"
            exp = f"{low:,} to {threshold(rank.max_level + 1) - 1:,} EXP"
        lines.append(f"◆ {label}\n　{levels} · {exp}")
    return "\n".join(lines)


def how_embed(role_ids: dict[str, int]) -> discord.Embed:
    embed = discord.Embed(
        title="★ Welcome to FanClub ★",
        description=(
            "FanClub is the home of competitive programming enthusiasts at Universitas Brawijaya. "
            "We solve problems together, share what we learn, and grow from our first accepted verdict "
            "to our first red handle.\n\n"
            "Link your Codeforces account with `/register` and every new problem you solve earns EXP and money "
            "right here. Climb the levels, unlock ranks, and see your name on the leaderboard."
        ),
        colour=ACCENT,
    )
    embed.add_field(name="▸ Ranks", value=rank_lines(role_ids), inline=False)
    embed.add_field(
        name="▸ Commands",
        value=(
            "`/register handle` ⟶ link your Codeforces account\n"
            "`/howtoregist` ⟶ short registration guide\n"
            "`/profile [@user]` ⟶ your profile card\n"
            "`/leaderboard type` ⟶ top players by level, rating, solved or streak\n"
            "`/daily` ⟶ three fresh problems every day\n"
            "`/grinding count rating [tags]` ⟶ practice set tailored to you\n"
            "`/refresh` ⟶ resync your profile\n"
            "`/unregister` ⟶ unlink your account"
        ),
        inline=False,
    )
    embed.set_footer(text="FanClub · Universitas Brawijaya · just think then code it")
    return embed


def howtoregist_embed() -> discord.Embed:
    embed = discord.Embed(
        title="★ How to register ★",
        description="Three quick steps and you are in.",
        colour=ACCENT,
    )
    embed.add_field(
        name="1 ▸ Get a Codeforces account",
        value="Sign up at https://codeforces.com/register if you do not have one yet.",
        inline=False,
    )
    embed.add_field(
        name="2 ▸ Run the command here",
        value="Type `/register` with your handle, for example `/register tourist`, and follow the short verification the bot gives you.",
        inline=False,
    )
    embed.add_field(
        name="3 ▸ Done",
        value="Your accounts are linked. Solve problems on Codeforces and watch your level rise here.",
        inline=False,
    )
    embed.set_footer(text="Stuck? Ask in the server and someone will help.")
    return embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def role_ids_for(self, guild: discord.Guild | None) -> dict[str, int]:
        if guild is None:
            return {}
        async with self.bot.session_factory() as session:
            return await roles_repo.get_role_ids(session, guild.id)

    @commands.hybrid_command(name="how", description="Welcome to FanClub: ranks and commands")
    async def how(self, ctx: commands.Context) -> None:
        await ctx.send(embed=how_embed(await self.role_ids_for(ctx.guild)))

    @commands.hybrid_command(name="howtoregist", description="Three steps to link your Codeforces account")
    async def howtoregist(self, ctx: commands.Context) -> None:
        await ctx.send(embed=howtoregist_embed())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
