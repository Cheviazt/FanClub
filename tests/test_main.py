import logging
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.main import FanClubBot


def make_bot() -> FanClubBot:
    return FanClubBot.__new__(FanClubBot)


async def test_on_app_command_error_logs_and_replies_ephemeral(caplog):
    bot = make_bot()
    interaction = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()
    with caplog.at_level(logging.ERROR, logger="bot.main"):
        await bot.on_app_command_error(interaction, RuntimeError("boom"))
    interaction.response.send_message.assert_awaited_once()
    assert interaction.response.send_message.await_args.kwargs["ephemeral"] is True
    assert "command failed" in caplog.text and "boom" in caplog.text


async def test_on_app_command_error_edits_when_deferred():
    bot = make_bot()
    interaction = MagicMock()
    interaction.response.is_done = MagicMock(return_value=True)
    interaction.edit_original_response = AsyncMock()
    await bot.on_app_command_error(interaction, RuntimeError("boom"))
    interaction.edit_original_response.assert_awaited_once()


async def test_on_app_command_error_swallows_http_errors():
    bot = make_bot()
    interaction = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=404), "unknown interaction"))
    await bot.on_app_command_error(interaction, RuntimeError("boom"))
