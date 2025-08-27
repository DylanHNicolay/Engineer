# EngineerToo - Discord Verification Bot

A comprehensive Discord bot designed for communities, particularly those associated with universities or organizations, to manage member verification and role assignments. The bot features a robust, multi-path verification system, automated role management, and powerful administrative tools, all containerized with Docker for easy deployment.

## Key Features

- **Multi-Path Verification System:**
    - **🎓 Student:** Verifies users with a university-specific email (`@rpi.edu`).
    - **🎊 Alumni:** A two-step process involving email verification and manual document submission for admin approval.
    - **👥 Friend:** Allows new users to get verified by requesting confirmation from an existing, verified member.
    - **🔍 General:** A fallback option for guests to verify with any personal email address.
- **Automated Role Management:**
    - Ensures users can only hold one primary status role (Student, Alumni, etc.) at a time.
    - Automatically cleans up old status roles when a user re-verifies.
- **Administrative Commands:**
    - `/year`: A command to advance the academic year, automatically graduating students to alumni and cleaning the database.
    - `/backfill`: A powerful tool to populate the database with a server's existing members, granting a "Verified" role to those without a specific status.
- **Secure by Design:**
    - **Local Malware Scanning:** Alumni-submitted documents are scanned locally using ClamAV before being presented to admins.
    - **Rate Limiting:** All verification buttons have a 10-minute cooldown and a process lock to prevent spam and abuse.
    - **Privacy-Focused:** The bot only stores a user's Discord ID and their academic status (years remaining), with clear privacy notices sent to users.
- **Easy Deployment:**
    - Fully containerized with Docker and Docker Compose for a one-command setup.
    - Includes a pgAdmin service for easy, web-based database management.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.
- A Discord Bot Application created in the [Discord Developer Portal](https://discord.com/developers/applications).
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) for sending verification emails.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd EngineerToo
    ```

2.  **Configure Environment Variables:**
    Create a file named `.env` in the root of the project directory. Fill in your credentials as shown below.

    ```env
    # Discord Bot Token
    DISCORD_TOKEN=your_discord_bot_token

    # PostgreSQL Database Settings
    POSTGRES_DB=bot_db
    POSTGRES_USER=bot_user
    POSTGRES_PASSWORD=generate_a_strong_and_secure_password

    # pgAdmin Login
    PGADMIN_DEFAULT_EMAIL=admin@example.com
    PGADMIN_DEFAULT_PASSWORD=generate_a_strong_pgadmin_password

    # Gmail SMTP Settings for Verification Emails
    GMAIL_ADDRESS=your_email@gmail.com
    GMAIL_APP_PASSWORD=your_16_character_gmail_app_password
    ```

3.  **Enable Privileged Intents:**
    In the Discord Developer Portal for your bot, navigate to the "Bot" tab and ensure all three **Privileged Gateway Intents** are enabled:
    - Presence Intent
    - Server Members Intent
    - Message Content Intent

4.  **Build and Run the Bot:**
    Use Docker Compose to build the images and start the services in the background.

    ```bash
    docker-compose up -d --build
    ```

## Usage

### Server Setup

1.  **Invite the Bot:** Invite the bot to your Discord server. It will automatically create the necessary roles (`Student`, `Alumni`, etc.) and private channels (`#engineer`, `#verify`).

2.  **Set Role Hierarchy:** This is a **critical** step. Go to `Server Settings > Roles` and drag the bot's role to be **above** the `Student`, `Alumni`, `Friend`, and `Verified` roles. The bot cannot assign roles that are higher than its own.

3.  **(REQUIRED) Backfill Existing Members:** If you are adding the bot to a server with existing members, you can use the `/backfill` command. This will check all members and assign them the "Verified" role if they don't already have a status role, adding them to the database.

### User Verification

-   Users can go to the `#verify` channel and click the button that corresponds to their status to begin the verification process in their DMs.

### Bot Permissions

When inviting the bot to your server, you must grant it a specific set of permissions for it to function correctly. The easiest way to do this is to generate an invite link from the Discord Developer Portal (`OAuth2` > `URL Generator`) with the `bot` and `applications.commands` scopes, and then select the following permissions:

-   **Manage Roles:** **(Critical)** Needed to assign the `Student`, `Alumni`, `Friend`, and `Verified` roles.
-   **Manage Channels:** Needed to create the `#engineer` and `#verify` channels on server join.
-   **Send Messages:** Required for all bot communication.
-   **Embed Links:** Needed to post the formatted verification message.
-   **Attach Files:** Required for forwarding alumni verification documents.
-   **Read Message History:** Needed to find and delete old verification messages on restart.