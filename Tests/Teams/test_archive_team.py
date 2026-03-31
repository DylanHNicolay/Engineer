import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import discord

from Teams.archive_team import ArchiveTeam


def _pass_admin_guard(cog, interaction):
    """Configure cog.bot and interaction.user so the admin guard passes."""
    user = MagicMock(spec=discord.Member)
    user.id = 1
    interaction.user = user
    admin_mock = MagicMock()
    admin_mock.is_admin = AsyncMock(return_value=True)
    cog.bot.get_cog = MagicMock(return_value=admin_mock)


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
    _pass_admin_guard(cog, interaction)
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=[])):
        await cog.archive_team.callback(cog, interaction, team_nick="ghost")
    msg = interaction.followup.send.call_args[0][0]
    assert "not found" in msg.lower()


#Multiple teams found

@pytest.mark.asyncio
async def test_archive_multiple_teams_found(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    fake_teams = [
        {"team_id": 1, "team_nick": "dup", "channel_id": 1, "role_id": 1},
        {"team_id": 2, "team_nick": "dup", "channel_id": 2, "role_id": 2},
    ]
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=fake_teams)):
        await cog.archive_team.callback(cog, interaction, team_nick="dup")
    msg = interaction.followup.send.call_args[0][0]
    assert "multiple" in msg.lower()
    

#Successful archive with role and channel

@pytest.mark.asyncio
async def test_archive_success_with_members(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    guild = interaction.guild

    member = MagicMock(spec=discord.Member)
    member.remove_roles = AsyncMock()

    role = MagicMock(spec=discord.Role)
    role.members = [member]
    role.delete = AsyncMock()

    channel = MagicMock(spec=discord.TextChannel)
    channel.overwrites_for = MagicMock(return_value=discord.PermissionOverwrite())
    channel.set_permissions = AsyncMock()
    channel.edit = AsyncMock()
    channel.mention = "#team-channel"

    guild.get_channel = MagicMock(return_value=channel)
    guild.get_role = MagicMock(return_value=role)

    archives_cat = MagicMock(spec=discord.CategoryChannel)
    archives_cat.name = "Archives"
    archives_cat.mention = "#Archives"
    guild.categories = [archives_cat]

    fake_team = [{"team_id": 10, "team_nick": "Falcons", "channel_id": 100, "role_id": 200}]
    db_calls = []

    async def mock_db_execute(query, *args):
        db_calls.append(query)
        if "SELECT" in query:
            return fake_team
        return None

    with patch("Teams.archive_team.db.execute", new=AsyncMock(side_effect=mock_db_execute)):
        await cog.archive_team.callback(cog, interaction, team_nick="Falcons")

    #DB was updated
    assert any("UPDATE" in q for q in db_calls)

    #Role was removed from member
    member.remove_roles.assert_awaited_once_with(role)

    #Channel permissions were set
    channel.set_permissions.assert_awaited_once()

    #Role was deleted
    role.delete.assert_awaited_once()

    #Channel moved to archives
    channel.edit.assert_awaited_once()
    assert channel.edit.call_args[1]["category"] == archives_cat

    msg = interaction.followup.send.call_args[0][0]
    assert "archived" in msg.lower()
    assert "role deleted" in msg.lower()

#Archive without moving to archives

@pytest.mark.asyncio
async def test_archive_no_move_to_archives(cog):
    interaction = make_interaction()
    guild = interaction.guild

    role = MagicMock(spec=discord.Role)
    role.members = []
    role.delete = AsyncMock()

    channel = MagicMock(spec=discord.TextChannel)
    channel.edit = AsyncMock()

    guild.get_channel = MagicMock(return_value=channel)
    guild.get_role = MagicMock(return_value=role)

    fake_team = [{"team_id": 5, "team_nick": "Eagles", "channel_id": 50, "role_id": 60}]

    async def mock_db_execute(query, *args):
        if "SELECT" in query:
            return fake_team
        return None

    with patch("Teams.archive_team.db.execute", new=AsyncMock(side_effect=mock_db_execute)):
        await cog.archive_team.callback(cog, interaction, team_nick="Eagles", move_to_archives=False)

    #Channel should NOT be moved
    channel.edit.assert_not_awaited()

#Channel or role not found in guild

@pytest.mark.asyncio
async def test_archive_channel_not_found(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    guild = interaction.guild
    guild.get_channel = MagicMock(return_value=None)
    guild.get_role = MagicMock(return_value=None)

    fake_team = [{"team_id": 7, "team_nick": "Ghosts", "channel_id": 70, "role_id": 80}]

    async def mock_db_execute(query, *args):
        if "SELECT" in query:
            return fake_team
        return None

    with patch("Teams.archive_team.db.execute", new=AsyncMock(side_effect=mock_db_execute)):
        await cog.archive_team.callback(cog, interaction, team_nick="Ghosts")

    msg = interaction.followup.send.call_args[0][0]
    assert "archived" in msg.lower()
    assert "not found" in msg.lower()


#Autocomplete

@pytest.mark.asyncio
async def test_autocomplete_returns_choices(cog):
    interaction = MagicMock()
    fake_records = [{"team_nick": "Alpha"}, {"team_nick": "Apex"}]
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=fake_records)):
        choices = await cog.archive_team_autocomplete(interaction, "a")
    assert len(choices) == 2
    assert choices[0].name == "Alpha"
    assert choices[1].name == "Apex"


@pytest.mark.asyncio
async def test_autocomplete_empty(cog):
    interaction = MagicMock()
    with patch("Teams.archive_team.db.execute", new=AsyncMock(return_value=[])):
        choices = await cog.archive_team_autocomplete(interaction, "zzz")
    assert choices == []