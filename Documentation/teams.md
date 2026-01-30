# Teams

## archive_team.py

Handles archiving of Discord teams by updating database status, managing member permissions, deleting roles, and optionally moving channels to an Archives category.

#### Overview

This module provides a Discord bot command for archiving teams. When a team is archived:
1. Database is updated to mark team as archived
2. Team members retain read-only channel access
3. Team role is removed from all members and deleted
4. Channel is optionally moved to an "Archives" category

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- `utils.db` - Database connection manager
- `Admin` cog - Permission verification

#### Classes

###### `ArchiveTeam(commands.Cog)`

Discord cog that manages team archival functionality.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance

**Methods:**
- `archive_team()` - Main command to archive a team
- `archive_team_autocomplete()` - Autocomplete handler for team selection

#### Commands

###### `/archive_team`

Archives an existing active team.

**Parameters:**
- `team_nick` (str): The nickname of the team to archive
- `move_to_archives` (bool, optional): Whether to move the channel to Archives category (default: True)

**Permissions:**
- Requires admin privileges (checked via Admin cog)

**Behavior:**
1. Verifies user has admin permissions
2. Queries database for active team matching `team_nick`
3. Updates team status to archived in database
4. Grants view-only channel access to all team members
5. Removes team role from all members
6. Deletes the team role
7. Moves channel to "Archives" category (if `move_to_archives` is True)

**Error Handling:**
- Returns error if command used outside a server
- Returns error if user lacks admin permissions
- Returns error if team not found or multiple teams match
- Continues operation even if individual member updates fail
- Reports failures for role deletion or channel moving

**Example Usage:**
```
/archive_team team_nick:pandas move_to_archives:True
```

#### Functions

###### `archive_team(self, interaction, team_nick, move_to_archives=True)`

Main command handler for archiving teams.

**Parameters:**
- `self`: Reference to ArchiveTeam cog instance
- `interaction` (discord.Interaction): Discord interaction object from command invocation
- `team_nick` (str): Nickname of team to archive
- `move_to_archives` (bool): Whether to move channel to Archives (default: True)

**Returns:**
- None (sends response via interaction followup)

**Database Operations:**
- SELECT: Queries teams table for matching active team
- UPDATE: Sets archived=TRUE for team

**Actions:**
- Modifies Discord channel permissions for team members
- Removes Discord role from members
- Deletes Discord role
- Moves channel to Archives category

###### `archive_team_autocomplete(self, interaction, current)`

Provides autocomplete suggestions for team nicknames.

**Parameters:**
- `self`: Reference to ArchiveTeam cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `current` (str): Current text typed by user

**Returns:**
- `List[app_commands.Choice[str]]`: List of up to 25 matching team nicknames

**Database Operations:**
- SELECT: Case-insensitive search on team_nick for active teams



## list_teams.py

Provides a Discord command to display all active teams with their metadata in a formatted embed.

#### Overview

This module implements a simple read-only command that queries the database for active teams and displays them in an organized Discord embed, sorted by year, semester, and seniority.

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- `utils.db` - Database connection manager

#### Classes

###### `ListTeams(commands.Cog)`

Discord cog that provides team listing functionality.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance

**Methods:**
- `list_teams()` - Command to display all active teams

#### Commands

###### `/list_teams`

Displays all active teams in a formatted embed.

**Parameters:**
- None

**Permissions:**
- Available to all users

**Behavior:**
1. Queries database for all active (non-archived) teams
2. Sorts results by year (descending), semester (descending), seniority (descending), team nickname (ascending)
3. Formats teams into a Discord embed with blue color
4. Displays team nickname, semester, year, and seniority level

**Response Format:**
```
Active Teams
- Team Alpha (Fall 2025) - Seniority: 3
- Team Beta (Fall 2025) - Seniority: 2
- Team Gamma (Spring 2025) - Seniority: 1
```

**Error Handling:**
- Returns message if no active teams exist
- Catches and reports database errors

**Example Usage:**
```
/list_teams
```

#### Functions

###### `list_teams(self, interaction)`

Queries and displays all active teams.

**Parameters:**
- `self`: Reference to ListTeams cog instance
- `interaction` (discord.Interaction): Discord interaction object from command invocation

**Returns:**
- None (sends response via interaction followup)

**Database Operations:**
- SELECT: Retrieves team_nick, year, semester, seniority from teams table where archived=FALSE
- ORDER BY: year DESC, semester DESC, seniority DESC, team_nick ASC

**Side Effects:**
- Sends ephemeral embed message visible only to command user

#### Database Schema Requirements

**teams table:**
- `team_nick` (str) - Team nickname/identifier
- `year` (int) - Academic year
- `semester` (str) - Semester (e.g., "Fall", "Spring")
- `seniority` (int) - Team seniority level
- `archived` (bool) - Archive status flag
