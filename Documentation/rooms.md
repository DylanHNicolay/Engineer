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

---

## reservations.py

Provides commands for team captains to reserve and cancel room slots, and a public command to view available slots.

#### Overview

This module is the main interface for room booking. Captains can reserve open slots for their team and cancel existing reservations. Anyone can view what slots are still available. Double-booking is prevented both by a `UNIQUE` constraint in the database and by an explicit check before inserting.

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- `utils.db` - Database connection manager

#### Classes

###### `Reservations(commands.Cog)`

Discord cog for room reservations.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance

**Methods:**
- `_get_captain_team()` - Internal helper to find the caller's team
- `reserve()` - Command to book a slot
- `cancel_reservation()` - Command to cancel a booking
- `list_rooms()` - Command to view available slots
- `room_name_autocomplete()` - Autocomplete handler for room names

#### Commands

###### `/reserve`

Reserves a room slot for the caller's team. Caller must be a captain of an active team.

**Parameters:**
- `slot_id` (int): ID of the slot to reserve

**Behavior:**
1. Looks up an active team where the caller is captain
2. Verifies the slot exists
3. Checks the slot has no existing reservation
4. Creates the reservation

**Error Handling:**
- Returns error if caller is not a captain of any active team
- Returns error if slot ID does not exist
- Returns error if slot is already reserved

**Example Usage:**
```
/reserve slot_id:42
```

###### `/cancel_reservation`

Cancels a room reservation. Caller must be the captain of the team that made the reservation.

**Parameters:**
- `slot_id` (int): ID of the slot to cancel

**Behavior:**
1. Looks up the caller's active team
2. Finds the reservation for the given slot
3. Verifies the reservation belongs to the caller's team
4. Deletes the reservation

**Error Handling:**
- Returns error if caller is not a captain
- Returns error if no reservation exists for the slot
- Returns error if the reservation belongs to a different team

**Example Usage:**
```
/cancel_reservation slot_id:42
```

###### `/list_rooms`

Displays all unreserved time slots. Open to everyone.

**Parameters:**
- `room_name` (str, optional): Filter results to a specific room (autocompleted)

**Behavior:**
1. Queries for slots with no matching reservation
2. Optionally filters by room name (case-insensitive)
3. Displays results in a formatted table showing slot ID, room, start, and end times

**Response Format:**
```
Available Room Slots
#      Room                 Start              End
--------------------------------------------------------
1      Lab A                2026-04-20 10:00   12:00
```

**Example Usage:**
```
/list_rooms
/list_rooms room_name:Lab A
```

#### Functions

###### `_get_captain_team(self, user_id) -> dict | None`

Looks up the active team for which the given user is captain.

**Parameters:**
- `user_id` (int): Discord user ID

**Returns:**
- `dict` with `team_id` and `team_nick`, or `None` if not a captain

**Database Operations:**
- SELECT: Queries teams where captain_discord_id matches and archived is FALSE

###### `reserve(self, interaction, slot_id)`

**Database Operations:**
- SELECT (via `_get_captain_team`): Finds caller's team
- SELECT: Fetches slot and room info by slot_id
- SELECT: Checks for existing reservation on slot
- INSERT: Creates reservation in room_reservations

###### `cancel_reservation(self, interaction, slot_id)`

**Database Operations:**
- SELECT (via `_get_captain_team`): Finds caller's team
- SELECT: Finds reservation by slot_id
- DELETE: Removes the reservation

###### `list_rooms(self, interaction, room_name)`

**Database Operations:**
- SELECT: LEFT JOIN between room_slots and room_reservations, filtered to unbooked slots, optionally filtered by room name

###### `room_name_autocomplete(self, interaction, current)`

Provides autocomplete suggestions for room names on the `list_rooms` command.

**Returns:**
- `List[app_commands.Choice[str]]`: Up to 25 matching room names

#### Database Schema Requirements

**rooms table:**
- `room_id` (serial) - Primary key
- `room_name` (varchar, unique) - Room identifier
- `description` (varchar, nullable) - Optional description

**room_slots table:**
- `slot_id` (serial) - Primary key
- `room_id` (int) - Foreign key to rooms (CASCADE on delete)
- `start_time` (timestamptz) - Slot start
- `end_time` (timestamptz) - Slot end, must be after start_time

**room_reservations table:**
- `reservation_id` (serial) - Primary key
- `slot_id` (int, unique) - Foreign key to room_slots (CASCADE on delete); UNIQUE enforces no double-booking
- `team_id` (int) - Foreign key to teams (CASCADE on delete)
