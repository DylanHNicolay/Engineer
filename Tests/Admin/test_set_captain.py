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


# --- logic tests ---

@pytest.mark.asyncio
async def test_set_captain_team_not_found(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    with patch("Admin.set_captain.db.execute", new=AsyncMock(return_value=[])):
        await cog.set_captain.callback(cog, interaction, team_nick="Ghost", member=make_member())
    msg = interaction.followup.send.call_args[0][0]
    assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_set_captain_success(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    member = make_member(user_id=99)
    with patch("Admin.set_captain.db.execute", new=AsyncMock(side_effect=[
        [{"team_id": 5}],
        None,
        None,
    ])):
        await cog.set_captain.callback(cog, interaction, team_nick="Dragons", member=member)
    msg = interaction.followup.send.call_args[0][0]
    assert "captain" in msg.lower()
    assert "dragons" in msg.lower()


@pytest.mark.asyncio
async def test_set_captain_db_error(cog):
    interaction = make_interaction()
    _pass_admin_guard(cog, interaction)
    with patch("Admin.set_captain.db.execute", new=AsyncMock(side_effect=Exception("DB down"))):
        await cog.set_captain.callback(cog, interaction, team_nick="Dragons", member=make_member())
    msg = interaction.followup.send.call_args[0][0]
    assert "error" in msg.lower()


# --- autocomplete ---

@pytest.mark.asyncio
async def test_team_nick_autocomplete_returns_choices(cog):
    interaction = MagicMock()
    fake_records = [{"team_nick": "Dragons"}, {"team_nick": "Drakes"}]
    with patch("Admin.set_captain.db.execute", new=AsyncMock(return_value=fake_records)):
        choices = await cog.team_nick_autocomplete(interaction, "dr")
    assert len(choices) == 2
    assert choices[0].name == "Dragons"


@pytest.mark.asyncio
async def test_team_nick_autocomplete_empty(cog):
    interaction = MagicMock()
    with patch("Admin.set_captain.db.execute", new=AsyncMock(return_value=[])):
        choices = await cog.team_nick_autocomplete(interaction, "zzz")
    assert choices == []
