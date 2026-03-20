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

# _should_exit
 

def test_should_exit_keywords(cog):
    assert cog._should_exit("exit") is True
    assert cog._should_exit("EXIT") is True
    assert cog._should_exit("(exit)") is True
    assert cog._should_exit("(EXIT)") is True


def test_should_exit_non_keywords(cog):
    assert cog._should_exit("hello") is False
    assert cog._should_exit("") is False
    assert cog._should_exit("yes") is False


def test_should_exit_strips_whitespace(cog):
    assert cog._should_exit("  exit  ") is True


 
# _dedupe_members
 

def test_dedupe_members_removes_duplicates(cog):
    m1 = MagicMock(spec=discord.Member)
    m1.id = 1
    m2 = MagicMock(spec=discord.Member)
    m2.id = 2
    m3 = MagicMock(spec=discord.Member)
    m3.id = 1  # duplicate of m1

    result = cog._dedupe_members([m1, m2, m3])
    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].id == 2


def test_dedupe_members_preserves_order(cog):
    members = []
    for i in [3, 1, 2]:
        m = MagicMock(spec=discord.Member)
        m.id = i
        members.append(m)

    result = cog._dedupe_members(members)
    assert [m.id for m in result] == [3, 1, 2]


def test_dedupe_members_empty(cog):
    assert cog._dedupe_members([]) == []

# _format_summary
 

def test_format_summary_full_draft(cog):
    role = MagicMock(spec=discord.Role)
    role.mention = "@role"
    category = MagicMock(spec=discord.CategoryChannel)
    category.name = "Cat"
    channel = MagicMock(spec=discord.TextChannel)
    channel.mention = "#chan"
    captain = MagicMock(spec=discord.Member)
    captain.mention = "@cap"
    starter = MagicMock(spec=discord.Member)
    starter.display_name = "StarterA"
    sub = MagicMock(spec=discord.Member)
    sub.display_name = "SubB"

    draft = TeamCreationData(
        team_nick="Falcons",
        role=role,
        category=category,
        channel=channel,
        captain=captain,
        starters=[starter],
        substitutes=[sub],
        year=2025,
        semester="Fall",
        seniority=3,
    )

    summary = cog._format_summary(draft)
    assert "Falcons" in summary
    assert "@role" in summary
    assert "Cat" in summary
    assert "#chan" in summary
    assert "@cap" in summary
    assert "StarterA" in summary
    assert "SubB" in summary
    assert "2025" in summary
    assert "Fall" in summary
    assert "3" in summary


def test_format_summary_empty_draft(cog):
    draft = TeamCreationData()
    summary = cog._format_summary(draft)
    assert "N/A" in summary
    assert "Not set" in summary
    assert "None" in summary


 # _ensure_captain_assignment
 

@pytest.mark.asyncio
async def test_ensure_captain_already_starter(cog):
    interaction = make_interaction()
    captain = MagicMock(spec=discord.Member)
    captain.id = 10
    captain.display_name = "Cap"

    starter = MagicMock(spec=discord.Member)
    starter.id = 10

    draft = TeamCreationData(captain=captain, starters=[starter], substitutes=[])
    await cog._ensure_captain_assignment(interaction, draft)

    interaction.followup.send.assert_not_awaited()
    assert len(draft.starters) == 1


@pytest.mark.asyncio
async def test_ensure_captain_already_substitute(cog):
    interaction = make_interaction()
    captain = MagicMock(spec=discord.Member)
    captain.id = 10
    captain.display_name = "Cap"

    sub = MagicMock(spec=discord.Member)
    sub.id = 10

    draft = TeamCreationData(captain=captain, starters=[], substitutes=[sub])
    await cog._ensure_captain_assignment(interaction, draft)

    interaction.followup.send.assert_not_awaited()
    assert len(draft.starters) == 0


@pytest.mark.asyncio
async def test_ensure_captain_added_to_starters(cog):
    interaction = make_interaction()
    captain = MagicMock(spec=discord.Member)
    captain.id = 10
    captain.display_name = "Cap"

    draft = TeamCreationData(captain=captain, starters=[], substitutes=[])
    await cog._ensure_captain_assignment(interaction, draft)

    interaction.followup.send.assert_awaited_once()
    assert captain in draft.starters


@pytest.mark.asyncio
async def test_ensure_captain_none_captain(cog):
    interaction = make_interaction()
    draft = TeamCreationData(captain=None, starters=[], substitutes=[])
    await cog._ensure_captain_assignment(interaction, draft)
    interaction.followup.send.assert_not_awaited()


 
# _wait_for_reply
 

@pytest.mark.asyncio
async def test_wait_for_reply_returns_message(cog, bot):
    interaction = make_interaction()
    msg = make_message("hello")
    bot.wait_for = AsyncMock(return_value=msg)

    result = await cog._wait_for_reply(interaction)
    assert result is msg


@pytest.mark.asyncio
async def test_wait_for_reply_timeout_raises_cancelled(cog, bot):
    interaction = make_interaction()
    bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

    with pytest.raises(ConversationCancelled):
        await cog._wait_for_reply(interaction)
