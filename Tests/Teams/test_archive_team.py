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

#Team not found 

@pytest.mark.asyncio
async def test_archive_team_not_found(cog):
    interaction = make_interaction()
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=[])):
        await cog.archive_team.callback(cog, interaction, team_nick="ghost")
    msg = interaction.followup.send.call_args[0][0]
    assert "not found" in msg.lower()


#Multiple teams found

@pytest.mark.asyncio
async def test_archive_multiple_teams_found(cog):
    interaction = make_interaction()
    fake_teams = [
        {"team_id": 1, "team_nick": "dup", "channel_id": 1, "role_id": 1},
        {"team_id": 2, "team_nick": "dup", "channel_id": 2, "role_id": 2},
    ]
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=fake_teams)):
        await cog.archive_team.callback(cog, interaction, team_nick="dup")
    msg = interaction.followup.send.call_args[0][0]
    assert "multiple" in msg.lower()