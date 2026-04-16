# Rooms & Reservations

## set_captain.py

Provides an admin command to update the captain of an existing active team.

#### Overview

This module allows admins to reassign team captains without going through the full team creation wizard. It updates `captain_discord_id` in the teams table and ensures the new captain exists in the players table.

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- `utils.db` - Database connection manager
- `Admin` cog - Permission verification

#### Classes

###### `SetCaptain(commands.Cog)`

Discord cog for updating team captains.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance

**Methods:**
- `set_captain()` - Command to update a team's captain
- `team_nick_autocomplete()` - Autocomplete handler for team selection

#### Commands

###### `/set_captain`

Updates the captain of an existing active team.

**Parameters:**
- `team_nick` (str): Nickname of the team to update
- `member` (discord.Member): The new captain

**Permissions:**
- Requires admin privileges (checked via Admin cog)

**Behavior:**
1. Verifies user has admin permissions
2. Looks up the active team by nickname
3. Upserts the new captain into the players table
4. Updates `captain_discord_id` on the team

**Error Handling:**
- Returns error if command used outside a server
- Returns error if user lacks admin permissions
- Returns error if no active team matches the given nickname

**Example Usage:**
```
/set_captain team_nick:Dragons member:@JohnDoe
```

#### Functions

###### `set_captain(self, interaction, team_nick, member)`

**Parameters:**
- `self`: Reference to SetCaptain cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `team_nick` (str): Nickname of the team
- `member` (discord.Member): New captain

**Returns:**
- None (sends response via interaction followup)

**Database Operations:**
- SELECT: Finds active team by team_nick
- INSERT: Upserts member into players table (ON CONFLICT DO NOTHING)
- UPDATE: Sets captain_discord_id on the team

###### `team_nick_autocomplete(self, interaction, current)`

Provides autocomplete suggestions for active team nicknames.

**Parameters:**
- `self`: Reference to SetCaptain cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `current` (str): Current text typed by user

**Returns:**
- `List[app_commands.Choice[str]]`: Up to 25 matching team nicknames
