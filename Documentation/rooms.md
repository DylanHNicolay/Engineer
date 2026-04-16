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

---

## rooms.py

Provides admin commands for managing rooms and available time slots.

#### Overview

This module lets admins define what rooms exist and when they are available for booking. Rooms are a simple registry; slots are time windows attached to a room that captains can later reserve. Deleting a slot automatically removes any reservation on it.

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- `utils.db` - Database connection manager
- `Admin` cog - Permission verification

#### Classes

###### `Rooms(commands.Cog)`

Discord cog for room and slot management.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance

**Methods:**
- `_is_admin()` - Internal admin permission check
- `add_room()` - Command to register a new room
- `add_slot()` - Command to add an available time slot
- `remove_slot()` - Command to remove a time slot
- `room_name_autocomplete()` - Autocomplete handler for room names

#### Commands

All commands are grouped under `/room` and require admin privileges.

###### `/room add_room`

Registers a new room that can have time slots assigned to it.

**Parameters:**
- `name` (str): Unique room name
- `description` (str, optional): Description of the room

**Behavior:**
1. Checks the room doesn't already exist
2. Inserts a new row into the rooms table

**Example Usage:**
```
/room add_room name:Lab A description:Computer lab on floor 2
```

###### `/room add_slot`

Adds an available time slot to a room.

**Parameters:**
- `room_name` (str): Name of the room (autocompleted)
- `start_time` (str): Start time in `YYYY-MM-DD HH:MM` format
- `end_time` (str): End time in `YYYY-MM-DD HH:MM` format

**Behavior:**
1. Parses and validates the time strings
2. Ensures end time is after start time
3. Looks up the room by name
4. Inserts a new slot and returns its ID

**Error Handling:**
- Returns error if time strings are not valid ISO format
- Returns error if end time is not after start time
- Returns error if the room does not exist

**Example Usage:**
```
/room add_slot room_name:Lab A start_time:2026-04-20 10:00 end_time:2026-04-20 12:00
```

###### `/room remove_slot`

Removes a time slot. If the slot has a reservation, the reservation is deleted automatically via cascade.

**Parameters:**
- `slot_id` (int): ID of the slot to remove

**Behavior:**
1. Verifies the slot exists
2. Deletes the slot (cascades to room_reservations)

**Example Usage:**
```
/room remove_slot slot_id:42
```

#### Functions

###### `_is_admin(self, interaction) -> bool`

Checks if the interaction user has an admin role.

**Parameters:**
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `bool`: True if user is an admin, False otherwise

###### `add_room(self, interaction, name, description)`

**Database Operations:**
- SELECT: Checks for existing room with same name
- INSERT: Adds row to rooms table

###### `add_slot(self, interaction, room_name, start_time, end_time)`

**Database Operations:**
- SELECT: Looks up room_id by room_name
- INSERT: Adds row to room_slots, returns slot_id

###### `remove_slot(self, interaction, slot_id)`

**Database Operations:**
- SELECT: Verifies slot exists
- DELETE: Removes slot (cascades to room_reservations)

###### `room_name_autocomplete(self, interaction, current)`

Provides autocomplete suggestions for room names on the `add_slot` command.

**Returns:**
- `List[app_commands.Choice[str]]`: Up to 25 matching room names
