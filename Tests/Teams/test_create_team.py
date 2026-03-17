import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import discord

from Teams.create_team import create_team, TeamCreationData, ConversationCancelled, ValidationError



#Fixtures

@pytest.fixture
def bot():
    b = MagicMock()
    b.wait_for = AsyncMock()
    return b


@pytest.fixture
def cog(bot):
    return create_team(bot)


def make_interaction(*, has_guild=True, is_admin=True):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.channel_id = 999

    if has_guild:
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.roles = []
        interaction.guild.categories = []
        interaction.guild.text_channels = []
    else:
        interaction.guild = None

    admin_cog = MagicMock()
    admin_cog.is_admin = AsyncMock(return_value=is_admin)
    interaction.client = MagicMock()
    interaction.client.get_cog = MagicMock(return_value=admin_cog)

    user = MagicMock()
    user.id = 1
    interaction.user = user

    return interaction


def make_message(content: str, author_id: int = 1, channel_id: int = 999, mentions=None, role_mentions=None, channel_mentions=None):
    msg = MagicMock(spec=discord.Message)
    msg.content = content
    author = MagicMock()
    author.id = author_id
    msg.author = author
    channel = MagicMock()
    channel.id = channel_id
    msg.channel = channel
    msg.mentions = mentions or []
    msg.role_mentions = role_mentions or []
    msg.channel_mentions = channel_mentions or []
    return msg

# Guard tests – create_team command


@pytest.mark.asyncio
async def test_create_team_no_guild(cog):
    interaction = make_interaction(has_guild=False)
    interaction.client.get_cog = MagicMock(return_value=None)
    await cog.create_team.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "server" in msg.lower()


@pytest.mark.asyncio
async def test_create_team_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    await cog.create_team.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()


@pytest.mark.asyncio
async def test_create_team_no_admin_cog(cog):
    interaction = make_interaction()
    interaction.client.get_cog = MagicMock(return_value=None)
    await cog.create_team.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()


 
