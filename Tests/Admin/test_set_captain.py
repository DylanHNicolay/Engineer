import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from Admin.set_captain import SetCaptain


def _pass_admin_guard(cog, interaction):
    user = MagicMock(spec=discord.Member)
    user.id = 1
    interaction.user = user
    admin_mock = MagicMock()
    admin_mock.is_admin = AsyncMock(return_value=True)
    cog.bot.get_cog = MagicMock(return_value=admin_mock)


@pytest.fixture
def cog():
    return SetCaptain(MagicMock())


def make_interaction(*, has_guild=True, is_admin=True):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    interaction.guild = MagicMock(spec=discord.Guild) if has_guild else None

    admin_cog = MagicMock()
    admin_cog.is_admin = AsyncMock(return_value=is_admin)
    interaction.client = MagicMock()
    interaction.client.get_cog = MagicMock(return_value=admin_cog if has_guild else None)

    return interaction


def make_member(user_id=42):
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.mention = f"<@{user_id}>"
    return member


# --- guard tests ---

@pytest.mark.asyncio
async def test_set_captain_no_guild(cog):
    interaction = make_interaction(has_guild=False)
    await cog.set_captain.callback(cog, interaction, team_nick="Dragons", member=make_member())
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "server" in msg.lower()


@pytest.mark.asyncio
async def test_set_captain_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    await cog.set_captain.callback(cog, interaction, team_nick="Dragons", member=make_member())
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()
