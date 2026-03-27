import pytest 
from unittest.mock import AsyncMock, MagicMock, patch
import discord 

from Teams.list_teams import ListTeams

@pytest.fixture
def cog():
    return ListTeams(MagicMock())

def make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_list_no_teams_sends_empty_message(cog):
    interaction = make_interaction()
    fake_teams = [
        {"team_nick": "Falcons", "year": 2025, "semester": "Fall", "seniority": 1}
    ]
    with patch("Teams.list_teams.db.execute", new=AsyncMock(return_value=fake_teams)):
        await cog.list_teams.callback(cog, interaction)
        
    call_kwargs = interaction.followup.send.call_args[1]
    assert "embed" in call_kwargs

@pytest.mark.asyncio
async def test_list_teams_embed_contains_team_data(cog):
    interaction = make_interaction()
    fake_teams = [
        {"team_nick": "NAVI", "year": 2025, "semester": "Fall", "seniority": 1},
        {"team_nick": "Team Liquid", "year": 2025, "semester": "Fall", "seniority": 1},
        {"team_nick": "Faze", "year": 2025, "semester": "Fall", "seniority": 1}
    ]
    with patch("Teams.list_teams.db.execute", new=AsyncMock(return_value=fake_teams)):
        await cog.list_teams.callback(cog, interaction)
    embed = interaction.followup.send.call_args.kwargs["embed"]
    assert "NAVI" in embed.description
    assert "Team Liquid" in embed.description
    assert "Faze" in embed.description
    assert "2025" in embed.description
    assert "Fall" in embed.description
    
@pytest.mark.asyncio
async def test_list_teams_db_exception_sends_error(cog):
    interaction = make_interaction()
    with patch("Teams.list_teams.db.execute", new=AsyncMock(side_effect=Exception("Connection Lost"))):
        await cog.list_teams.callback(cog, interaction)
        
    msg = interaction.followup.send.call_args[0][0]
    assert "error" in msg.lower()
    
    