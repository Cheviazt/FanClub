import logging
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.leaderboard import LeaderboardView
from bot.db.repo import users


async def seed(session, n):
    for i in range(1, n + 1):
        u = await users.create_user(session, i, f"h{i}")
        u.exp = i * 100
    await session.commit()


async def test_view_buttons_state(session_factory):
    async with session_factory() as s:
        await seed(s, 9)
    view = LeaderboardView(session_factory, "level", owner_id=1, page=1, total_pages=2)
    view.sync_buttons()
    assert view.back.disabled is True and view.next.disabled is False
    view.page = 2
    view.sync_buttons()
    assert view.back.disabled is False and view.next.disabled is True


async def test_view_build_message(session_factory):
    async with session_factory() as s:
        await seed(s, 3)
    view = LeaderboardView(session_factory, "solved", owner_id=1, page=1, total_pages=1)
    embed, file = await view.build_message()
    assert file.filename == "leaderboard.png"
    assert embed.image.url == "attachment://leaderboard.png"


async def test_interaction_check_rejects_others(session_factory):
    view = LeaderboardView(session_factory, "level", owner_id=1, page=1, total_pages=1)
    interaction = MagicMock()
    interaction.user.id = 2
    interaction.response.send_message = AsyncMock()
    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once()
    interaction.user.id = 1
    assert await view.interaction_check(interaction) is True


async def test_view_on_error_sends_ephemeral_error(session_factory, caplog):
    view = LeaderboardView(session_factory, "level", owner_id=1, page=1, total_pages=1)
    interaction = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.send_message = AsyncMock()
    with caplog.at_level(logging.ERROR, logger="bot.cogs.leaderboard"):
        await view.on_error(interaction, RuntimeError("boom"), view.next)
    interaction.response.send_message.assert_awaited_once()
    assert interaction.response.send_message.await_args.kwargs["ephemeral"] is True
    assert "leaderboard view failed" in caplog.text and "boom" in caplog.text
