import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import discord

from Teams.archive_team import ArchiveTeam


@pytest.fixture
def cog():
    return ArchiveTeam(MagicMock())


def make_interaction(*, has_guild=True, is_admin=True):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    if has_guild:
        interaction.guild = MagicMock(spec=discord.Guild)
    else:
        interaction.guild = None

    admin_cog = MagicMock()
    admin_cog.is_admin = AsyncMock(return_value=is_admin)
    interaction.client = MagicMock()
    interaction.client.get_cog = MagicMock(return_value=admin_cog if has_guild else None)

    return interaction


#Guard Tests

@pytest.mark.asyncio
async def test_archive_no_guild(cog):
    interaction = make_interaction(has_guild=False)
    await cog.archive_team.callback(cog, interaction, team_nick="test")
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "server" in msg.lower()


@pytest.mark.asyncio
async def test_archive_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    await cog.archive_team.callback(cog, interaction, team_nick="test")
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()


@pytest.mark.asyncio
async def test_archive_no_admin_cog(cog):
    interaction = make_interaction()
    interaction.client.get_cog = MagicMock(return_value=None)
    await cog.archive_team.callback(cog, interaction, team_nick="test")
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()

