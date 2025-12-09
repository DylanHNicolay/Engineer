# Engineer - Team & Dues Management Bot

A specialized Discord bot designed to manage e-sports teams, clubs, or competitive groups. It handles team creation, roster management, channel organization, and dues tracking with automated Excel reporting.

## Key Features

- **Interactive Team Creation:**
    - A step-by-step wizard (`/create_team`) to set up new teams.
    - Automatically creates or links Discord Roles, Categories, and Text Channels.
    - Assigns Captains, Starters, and Substitutes.
    - Tracks competition Year, Semester, and Team Seniority.
- **Roster & Role Management:**
    - Automatically assigns team roles to players upon team creation.
    - Tracks player status (Starter vs. Substitute).
- **Dues Management:**
    - Configure dues amounts for Starters, Substitutes, and Non-players.
    - **`/generate_dues`**: Generates a formatted Excel (`.xlsx`) report listing all teams, rosters, and calculated dues, grouped by category.
- **Team Archival:**
    - **`/archive_team`**: Cleanly archives a team by removing roles, moving the channel to an "Archives" category, and updating the database status.
- **Database Integration:**
    - Robust PostgreSQL backend to store teams, players, and configuration.

## Commands

### Team Management
- `/create_team`: Starts the interactive wizard to create a new team.
- `/archive_team [team_nick] [move_to_archives]`: Archives an active team.
- `/list_teams`: Displays a list of all active teams, sorted by Year, Semester, and Seniority.

### Dues
- `/set_dues_starters [amount]`: Set the dues amount for starters.
- `/set_dues_substitutes [amount]`: Set the dues amount for substitutes.
- `/set_dues_non_players [amount]`: Set the dues amount for non-players.
- `/generate_dues`: Generates and uploads the Dues Excel report.

### Administration
- `/admin define [role]`: Designates a Discord role as an "Admin" role, granting access to sensitive bot commands.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.
- A Discord Bot Application created in the [Discord Developer Portal](https://discord.com/developers/applications).

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Engineer
    ```

2.  **Configure Environment Variables:**
    Create a file named `.env` in the root of the project directory.

    ```env
    # Discord Bot Token
    DISCORD_TOKEN=your_discord_bot_token

    # PostgreSQL Database Settings
    POSTGRES_DB=bot_db
    POSTGRES_USER=bot_user
    POSTGRES_PASSWORD=secure_password
    ```

3.  **Build and Run:**
    Use Docker Compose to build the images and start the services.

    ```bash
    docker-compose up -d --build
    ```

### Initial Setup

1.  **Invite the Bot:** Invite the bot to your server with `applications.commands` and `bot` scopes.
2.  **Permissions:** Ensure the bot has the "Manage Roles" and "Manage Channels" permissions and that its role is **higher** in the hierarchy than the roles it needs to manage.
3.  **Set Admin Role:** The server owner should run `/admin define @YourAdminRole` to allow other admins to use the bot commands.

## Development

The bot is built with `discord.py` and uses `asyncpg` for database interactions.
- **`Bot/`**: Contains the Python source code.
    - **`Teams/`**: Cogs for team management.
    - **`Dues/`**: Cogs for dues and reporting.
    - **`Admin/`**: Admin configuration.
    - **`utils/`**: Database utilities.
- **`init.sql`**: Database schema initialization.
