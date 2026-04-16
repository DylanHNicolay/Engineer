import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from Rooms.reservations import Reservations


@pytest.fixture
def cog():
    return Reservations(MagicMock())


def make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 100
    return interaction


def make_fake_slot():
    start = MagicMock()
    start.strftime = MagicMock(return_value="2026-04-20 10:00")
    end = MagicMock()
    end.strftime = MagicMock(return_value="12:00")
    return {"slot_id": 1, "room_name": "Lab A", "start_time": start, "end_time": end}


# --- reserve ---

@pytest.mark.asyncio
async def test_reserve_not_captain(cog):
    interaction = make_interaction()
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=None)):
        await cog.reserve.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "captain" in msg.lower()


@pytest.mark.asyncio
async def test_reserve_slot_not_found(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(return_value=[])):
            await cog.reserve.callback(cog, interaction, slot_id=99)
    msg = interaction.followup.send.call_args[0][0]
    assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_reserve_already_reserved(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(side_effect=[
            [make_fake_slot()],
            [{"reservation_id": 5}],
        ])):
            await cog.reserve.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "already reserved" in msg.lower()


@pytest.mark.asyncio
async def test_reserve_success(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(side_effect=[
            [make_fake_slot()],
            [],
            None,
        ])):
            await cog.reserve.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "reserved" in msg.lower()
    assert "dragons" in msg.lower()


@pytest.mark.asyncio
async def test_reserve_db_error(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(side_effect=Exception("DB down"))):
            await cog.reserve.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "error" in msg.lower()


# --- cancel_reservation ---

@pytest.mark.asyncio
async def test_cancel_not_captain(cog):
    interaction = make_interaction()
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=None)):
        await cog.cancel_reservation.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "captain" in msg.lower()


@pytest.mark.asyncio
async def test_cancel_no_reservation(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(return_value=[])):
            await cog.cancel_reservation.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "no reservation" in msg.lower()


@pytest.mark.asyncio
async def test_cancel_wrong_team(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    fake_reservation = [{"reservation_id": 3, "team_id": 99}]
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(return_value=fake_reservation)):
            await cog.cancel_reservation.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "own team" in msg.lower()


@pytest.mark.asyncio
async def test_cancel_success(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    fake_reservation = [{"reservation_id": 3, "team_id": 10}]
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(side_effect=[fake_reservation, None])):
            await cog.cancel_reservation.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "cancelled" in msg.lower()


@pytest.mark.asyncio
async def test_cancel_db_error(cog):
    interaction = make_interaction()
    fake_team = {"team_id": 10, "team_nick": "Dragons"}
    with patch.object(cog, "_get_captain_team", new=AsyncMock(return_value=fake_team)):
        with patch("Rooms.reservations.db.execute", new=AsyncMock(side_effect=Exception("DB down"))):
            await cog.cancel_reservation.callback(cog, interaction, slot_id=1)
    msg = interaction.followup.send.call_args[0][0]
    assert "error" in msg.lower()
