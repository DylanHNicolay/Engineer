import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from Rooms.rooms import Rooms


def _pass_admin_guard(cog, interaction):
    user = MagicMock(spec=discord.Member)
    user.id = 1
    interaction.user = user
    admin_mock = MagicMock()
    admin_mock.is_admin = AsyncMock(return_value=True)
    cog.bot.get_cog = MagicMock(return_value=admin_mock)


@pytest.fixture
def cog():
    return Rooms(MagicMock())


def make_interaction(*, is_admin=True):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock(spec=discord.Member)

    admin_cog = MagicMock()
    admin_cog.is_admin = AsyncMock(return_value=is_admin)
    return interaction


# --- guard tests ---

@pytest.mark.asyncio
async def test_add_room_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    cog.bot.get_cog = MagicMock(return_value=MagicMock(is_admin=AsyncMock(return_value=False)))
    await cog.add_room.callback(cog, interaction, name="Lab A", description="")
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()


@pytest.mark.asyncio
async def test_add_slot_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    cog.bot.get_cog = MagicMock(return_value=MagicMock(is_admin=AsyncMock(return_value=False)))
    await cog.add_slot.callback(cog, interaction, room_name="Lab A", start_time="2026-04-20 10:00", end_time="2026-04-20 12:00")
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()


@pytest.mark.asyncio
async def test_remove_slot_no_permission(cog):
    interaction = make_interaction(is_admin=False)
    cog.bot.get_cog = MagicMock(return_value=MagicMock(is_admin=AsyncMock(return_value=False)))
    await cog.remove_slot.callback(cog, interaction, slot_id=1)
    interaction.response.send_message.assert_awaited_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "permission" in msg.lower()
