from unittest.mock import AsyncMock, MagicMock

from bot.cogs.unregister import ConfirmUnregisterView, unregister_user
from bot.db.repo import users
from bot.services.avatars import AvatarCache
from bot.services.leveling import RANKS


def make_bot(session_factory, tmp_path):
    bot = MagicMock()
    bot.session_factory = session_factory
    bot.avatars = AvatarCache(tmp_path / "avatars")
    bot.settings.guild_id = 10
    roles = []
    for i, rank in enumerate(RANKS):
        role = MagicMock()
        role.id = 100 + i
        role.name = rank.name
        roles.append(role)
    rookie = roles[0]
    member = MagicMock()
    member.roles = [rookie]
    member.guild.get_role = lambda rid: rookie if rid == 100 else None
    member.remove_roles = AsyncMock()
    member.add_roles = AsyncMock()
    member.edit = AsyncMock()
    guild = MagicMock()
    guild.id = 10
    guild.roles = roles
    guild.get_member = MagicMock(return_value=member)
    bot.get_guild = MagicMock(return_value=guild)
    return bot, member, rookie


async def test_unregister_user_removes_everything(session_factory, tmp_path):
    async with session_factory() as s:
        await users.create_user(s, 1, "a")
        await s.commit()
    bot, member, rookie = make_bot(session_factory, tmp_path)
    bot.avatars.store(1, b"img")
    assert await unregister_user(bot, 1) is True
    async with session_factory() as s:
        assert await users.get_by_discord(s, 1) is None
    assert bot.avatars.load(1) is None
    member.remove_roles.assert_awaited_once_with(rookie, reason="rank change")
    member.add_roles.assert_not_awaited()
    member.edit.assert_awaited_once_with(nick=None, reason="unregister")


async def test_unregister_user_not_registered(session_factory, tmp_path):
    bot, _, _ = make_bot(session_factory, tmp_path)
    assert await unregister_user(bot, 5) is False


async def test_confirm_view_rejects_other_users(session_factory):
    view = ConfirmUnregisterView(MagicMock(), owner_id=1)
    interaction = MagicMock()
    interaction.user.id = 2
    assert await view.interaction_check(interaction) is False
    interaction.user.id = 1
    assert await view.interaction_check(interaction) is True
