import discord

RED = 0xE53935
BLUE = 0x1E88E5
GREEN = 0x43A047


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, colour=RED)


def info_embed(title: str, description: str, colour: int = BLUE) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def image_embed(title: str, filename: str) -> discord.Embed:
    embed = discord.Embed(title=title, colour=BLUE)
    embed.set_image(url=f"attachment://{filename}")
    return embed


async def send_error(interaction: discord.Interaction, message: str) -> None:
    embed = error_embed(message)
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
