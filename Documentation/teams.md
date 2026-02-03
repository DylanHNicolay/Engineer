# Teams

## create-team.py

Provides an interactive wizard for creating Discord teams through a conversational interface, handling role/channel creation, member assignment, and database persistence.

#### Overview

This module implements a multi-step conversational workflow for team creation. Users are guided through providing team details, selecting or creating Discord resources (roles, channels, categories), assigning members, and configuring metadata. The wizard supports exit at any point, validation, review/editing, and automatic role assignment.

#### Dependencies

**External:**
- `discord.py` - Discord bot API wrapper
- `asyncpg` - Async PostgreSQL driver (via utils.db)

**Internal:**
- [`utils.db`](Bot/utils/db.py) - Database connection manager
- [`Admin`](Bot/Admin/admin.py) cog - Permission verification

#### Classes

###### `TeamCreationData`

Dataclass to hold all team information during the creation process.

**Attributes:**
- `team_nick` (Optional[str]): Team nickname/short identifier
- `role` (Optional[discord.Role]): Discord role for the team
- `category` (Optional[discord.CategoryChannel]): Category channel housing the team channel
- `channel` (Optional[discord.TextChannel]): Team's text channel
- `captain` (Optional[discord.Member]): Team captain
- `starters` (List[discord.Member]): List of starter players
- `substitutes` (List[discord.Member]): List of substitute players
- `year` (Optional[int]): Competition year
- `semester` (Optional[str]): Semester (Fall/Summer/Spring)
- `seniority` (Optional[int]): Team seniority level

###### `ValidationError(Exception)`

Raised when user input fails validation during the wizard.

###### `ConversationCancelled(Exception)`

Raised when the user exits the wizard or a timeout occurs.

###### `TeamCreationError(Exception)`

Raised when team creation cannot proceed (e.g., duplicate team resources).

###### `SemesterSelect(discord.ui.View)`

Discord UI select menu for choosing semester.

**Attributes:**
- `user_id` (int): ID of user who initiated the command
- `value` (Optional[str]): Selected semester value

**Methods:**
- `_select_callback()` - Handles semester selection

###### `create_team(commands.Cog)`

Discord cog that implements the interactive team creation wizard.

**Attributes:**
- `bot` (commands.Bot): Reference to the Discord bot instance
- `REPLY_TIMEOUT` (int): Timeout in seconds for user replies (180)

**Methods:**
- `create_team()` - Main command entry point
- `_collect_team_data()` - Orchestrates data collection workflow
- `_prompt_team_nick()` - Prompts for team nickname
- `_prompt_role()` - Prompts for role selection/creation
- `_prompt_category()` - Prompts for category selection/creation
- `_prompt_channel()` - Prompts for channel selection/creation
- `_prompt_member()` - Prompts for single member selection
- `_prompt_member_group()` - Prompts for multiple member selection
- `_prompt_year()` - Prompts for competition year
- `_prompt_semester()` - Prompts for semester via UI select
- `_prompt_seniority()` - Prompts for seniority level
- `_review_answers()` - Allows editing collected data before finalization
- `_finalize_team()` - Persists team to database and assigns roles
- `_ask_question()` - Generic prompt handler with validation
- `_confirm()` - Yes/no confirmation prompt
- `_wait_for_reply()` - Waits for user message response
- `_wait_for_exit_signal()` - Listens for exit command
- `_should_exit()` - Checks if message is an exit keyword
- `_format_summary()` - Formats team data for display
- `_dedupe_members()` - Removes duplicate members from list
- `_ensure_captain_assignment()` - Ensures captain is in starters or substitutes

#### Commands

###### `/create_team`

Launches the interactive team creation wizard.

**Parameters:**
- None

**Permissions:**
- Requires admin privileges (checked via Admin cog)

**Behavior:**
1. Verifies user has admin permissions
2. Initiates conversational workflow to collect:
   - Team nickname (optional)
   - Discord role (select existing or create new)
   - Category channel (select existing or create new)
   - Team text channel (select existing or create new)
   - Captain (mention or ID)
   - Starters (mentions or IDs)
   - Substitutes (mentions or IDs, optional)
   - Competition year
   - Semester (via UI select menu)
   - Seniority level
3. Displays summary and allows editing any field
4. Creates database records in transaction
5. Assigns team role to all members
6. Reports success with warnings for any failures

**Exit Behavior:**
- User can type `(Exit)` or `exit` at any prompt to cancel
- Timeouts (180s per prompt) automatically cancel

**Error Handling:**
- Validates all inputs before proceeding
- Re-prompts on validation errors
- Prevents duplicate team resources
- Reports permission errors for role/channel operations
- Warns if role assignment fails for individual members
- Rolls back database changes on transaction failure

**Example Usage:**
```
/create_team
[Follow prompts]
Provide a team nickname: Dragons
Mention the role to use: @Dragons
...
```

#### Functions

###### `create_team(self, interaction)`

Main command handler that orchestrates the team creation workflow.

**Parameters:**
- `self`: Reference to create_team cog instance
- `interaction` (discord.Interaction): Discord interaction object from command invocation

**Returns:**
- None (sends responses via interaction followup)

**Flow:**
1. Validates guild context and admin permissions
2. Calls `_collect_team_data()` to gather information
3. Calls `_finalize_team()` to persist to database
4. Sends final summary with any warnings

###### `_collect_team_data(self, interaction) -> TeamCreationData`

Orchestrates the data collection workflow by calling individual prompt methods.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `TeamCreationData`: Populated team data object

**Workflow:**
1. Team nickname
2. Role
3. Category
4. Channel
5. Captain
6. Starters
7. Substitutes
8. Deduplicate member lists
9. Ensure captain is assigned
10. Year
11. Semester
12. Seniority
13. Review and confirm

###### `_prompt_team_nick(self, interaction) -> Optional[str]`

Prompts for team nickname with N/A option.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `Optional[str]`: Team nickname or None if N/A

###### `_prompt_role(self, interaction) -> discord.Role`

Prompts for role mention/name with automatic creation if needed.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `discord.Role`: Selected or created role

**Actions:**
- Detects role mentions or searches by name
- Confirms existing role selection
- Creates new role if name doesn't exist

###### `_prompt_category(self, interaction) -> discord.CategoryChannel`

Prompts for category ID/name with automatic creation if needed.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `discord.CategoryChannel`: Selected or created category

**Actions:**
- Searches by ID (if numeric) or name
- Confirms existing category selection
- Creates new category if not found

###### `_prompt_channel(self, interaction, category) -> discord.TextChannel`

Prompts for channel mention/ID/name with automatic creation if needed.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `category` (discord.CategoryChannel): Target category for new channels

**Returns:**
- `discord.TextChannel`: Selected or created text channel

**Actions:**
- Detects channel mentions or searches by ID/name
- Confirms existing channel selection
- Creates new text channel in specified category

###### `_prompt_member(self, interaction, label) -> discord.Member`

Prompts for single member by mention or ID.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `label` (str): Role label for the member (e.g., "captain")

**Returns:**
- `discord.Member`: Selected member

**Actions:**
- Resolves member from mention or Discord ID
- Fetches member from API if not in cache
- Confirms selection with user

###### `_prompt_member_group(self, interaction, label, require_entry) -> List[discord.Member]`

Prompts for multiple members by mentions or IDs.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `label` (str): Role label for members (e.g., "starter", "substitute")
- `require_entry` (bool): Whether at least one member is required

**Returns:**
- `List[discord.Member]`: List of selected members (may be empty if N/A allowed)

**Actions:**
- Parses mentions and space/comma-separated IDs
- Fetches members from API if not in cache
- Deduplicates automatically
- Allows N/A if not required

###### `_prompt_year(self, interaction) -> int`

Prompts for numeric year with range validation (2000-2100).

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `int`: Competition year

###### `_prompt_semester(self, interaction) -> str`

Displays UI select menu for semester choice with exit monitoring.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `str`: Selected semester ("Fall", "Summer", or "Spring")

**Actions:**
- Creates `SemesterSelect` view
- Races between view selection and exit signal
- Cancels on timeout or exit

###### `_prompt_seniority(self, interaction) -> int`

Prompts for numeric seniority level.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `int`: Seniority level

###### `_review_answers(self, interaction, draft) -> None`

Displays summary and allows editing individual fields before finalization.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `draft` (TeamCreationData): Current team data

**Actions:**
- Displays formatted summary
- Accepts field name to re-prompt for that field
- Loops until user types "confirm"

###### `_finalize_team(self, interaction, draft) -> List[str]`

Persists team to database and assigns roles to members.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `draft` (TeamCreationData): Complete team data

**Returns:**
- `List[str]`: Warning messages for any role assignment failures

**Database Operations:**
- SELECT: Checks for conflicting active teams with same resources
- INSERT: Creates team record in teams table
- INSERT: Upserts players in players table
- INSERT: Creates team_members entries with status

**Actions:**
- Validates no duplicate active team exists
- Runs all database operations in single transaction
- Assigns team role to captain, starters, and substitutes
- Collects warnings for failed role assignments

**Raises:**
- `TeamCreationError`: If duplicate team detected

###### `_ask_question(self, interaction, prompt, allow_na, parser) -> Any`

Generic prompt handler with optional validation parser.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `prompt` (str): Question to display
- `allow_na` (bool): Whether N/A is an acceptable response
- `parser` (Optional[Callable]): Async function to parse and validate response

**Returns:**
- `Any`: Parsed response or raw string if no parser

**Actions:**
- Waits for user message reply
- Checks for exit keywords
- Returns None if N/A and allowed
- Calls parser if provided, re-prompts on ValidationError

###### `_confirm(self, interaction, prompt) -> bool`

Yes/no confirmation prompt.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `prompt` (str): Confirmation question

**Returns:**
- `bool`: True if yes, False if no

**Actions:**
- Waits for message reply
- Accepts yes/y/no/n (case-insensitive)
- Re-prompts if invalid response

###### `_wait_for_reply(self, interaction) -> discord.Message`

Waits for message from command user in command channel.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `discord.Message`: User's message

**Raises:**
- `ConversationCancelled`: On timeout (180s)

###### `_wait_for_exit_signal(self, interaction) -> bool`

Listens for exit keyword message from user.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object

**Returns:**
- `bool`: True if exit keyword received, False on timeout

###### `_should_exit(self, content) -> bool`

Checks if message content is an exit keyword.

**Parameters:**
- `self`: Reference to cog instance
- `content` (str): Message content to check

**Returns:**
- `bool`: True if content is "exit" or "(exit)" (case-insensitive)

###### `_format_summary(self, draft) -> str`

Formats team data into readable summary string.

**Parameters:**
- `self`: Reference to cog instance
- `draft` (TeamCreationData): Team data to format

**Returns:**
- `str`: Markdown-formatted summary

###### `_dedupe_members(self, members) -> List[discord.Member]`

Removes duplicate members from list while preserving order.

**Parameters:**
- `self`: Reference to cog instance
- `members` (Iterable[discord.Member]): Member list possibly containing duplicates

**Returns:**
- `List[discord.Member]`: Deduplicated member list

###### `_ensure_captain_assignment(self, interaction, draft) -> None`

Ensures captain is assigned to starters or substitutes, defaulting to starters.

**Parameters:**
- `self`: Reference to cog instance
- `interaction` (discord.Interaction): Discord interaction object
- `draft` (TeamCreationData): Team data to validate

**Actions:**
- Checks if captain is in starters or substitutes
- Adds captain to starters if not present in either
- Notifies user of automatic assignment

#### Database Schema Requirements

**teams table:**
- `team_id` (serial) - Primary key
- `team_nick` (varchar) - Team nickname
- `role_id` (bigint) - Discord role ID
- `channel_id` (bigint) - Discord channel ID
- `category_id` (bigint) - Discord category ID
- `captain_discord_id` (bigint) - Captain's Discord ID
- `year` (int) - Competition year
- `semester` (semester_type) - Semester enum
- `seniority` (int) - Seniority level
- `archived` (bool) - Archive status

**players table:**
- `player_discord_id` (bigint) - Primary key, Discord user ID
- `rcsid` (varchar) - Optional RCS ID

**team_members table:**
- `team_id` (int) - Foreign key to teams
- `player_discord_id` (bigint) - Foreign key to players
- `member_status` (member_status_type) - Status enum ('starter' or 'sub')
- Primary key: (team_id, player_discord_id)

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
