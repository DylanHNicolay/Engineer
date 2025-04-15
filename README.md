# Engineer Discord Bot Documentation

**Engineer** is an open-source Discord bot designed to streamline server setup, user verification, role management, and team tryouts, initially tailored for communities like Team RPI. By automating these processes, Engineer ensures authenticated members gain appropriate roles, maintains server structure, and provides tools for managing specific community activities.

## Table of Contents

- [Features](#features)
  - [Working Features](#working-features)
  - [Features In Progress / TODOs](#features-in-progress--todos)
- [Core Concepts](#core-concepts)
  - [Engineer Role](#engineer-role)
  - [Managed Roles & Channels](#managed-roles--channels)
- [Setup Process](#setup-process)
- [Commands](#commands)
  - [Setup Cog](#setup-cog)
  - [Verification Cog](#verification-cog)
  - [Role Reactions Cog](#role-reactions-cog)
  - [Role Management Cog](#role-management-cog)
  - [Team (Tryouts) Cog](#team-tryouts-cog)
- [Contributing](#contributing)
- [License](#license)

## Features

### Working Features

*   **Automated Server Setup (`/setup`)**:
    *   Creates required roles (Verified, Student, Alumni, Friend, Prospective Student, RPI Admin) if they don't exist.
    *   Handles duplicate existing roles via admin selection.
    *   Positions roles correctly below the Engineer role.
    *   Processes existing members, assigning roles based on current roles or adding them to the database.
    *   Creates dedicated channels (`#verification`, `#modmail`).
    *   Deploys the verification system message.
    *   Loads and syncs operational commands upon completion.
*   **User Verification System**:
    *   Button-based interface in the `#verification` channel.
    *   **Student Verification:** Uses RPI email (`@rpi.edu`) verification via DM. Collects remaining years. Assigns "Student" and "Verified" roles.
    *   **Friend Verification:** Uses a vouching system via DM. Asks the user for an existing member's username, DMs that member for confirmation ("yes"/"no"). Assigns "Friend" and "Verified" roles upon confirmation.
    *   **Alumni Verification:** Assigns a temporary role ("temp") and grants access to `#modmail` for manual verification by administrators.
    *   **Prospective Student Verification:** Uses general email verification via DM. Assigns "Prospective Student" and "Verified" roles.
*   **Role & Channel Monitoring (`RoleChannelListener` Cog)**:
    *   Monitors the position of the "Engineer" role, sending warnings to `#engineer` and admins if it's not at the top.
    *   Monitors managed channels (`#engineer`, `#verification`, `#modmail`) for deletion or permission changes affecting the bot. Attempts to recreate `#engineer` if deleted.
    *   Monitors managed roles for deletion and warns in `#engineer`.
    *   Includes periodic checks for the Engineer role position.
*   **Role Reactions (`RoleReactions` Cog)**:
    *   Allows admins to configure messages where reacting with a specific emoji grants/removes a specified role.
    *   Handles reaction adding and removal automatically.
*   **Basic Semester Scheduling (`RoleManagement` Cog)**:
    *   Commands to set start dates/times for Fall (Aug/Sep) and Spring (Jan/Feb) semesters.
    *   Background task checks hourly to trigger placeholder actions (`NewFallAction`, `NewSpringAction`) and send warnings (1 month, 1 week, 1 day prior) to the `#engineer` channel.

### Features In Progress / TODOs

*   **Advanced Semester Actions**: Implement the actual logic within `NewFallAction` (e.g., decrementing `years_remaining` for students) and `NewSpringAction`.
*   **Tryouts Management (`Team` Cog)**:
    *   **Google Form Integration**: Implement API calls to check if a user has submitted the form (`/tryouts_join`) and potentially extract seeding data. Handle API errors and provide instructions.
    *   **Seeding**: Define and implement seeding logic based on form data or other criteria. Store seeding info in `tryout_participants`.
    *   **Advanced Matchmaking**: Implement matchmaking in `/tryouts_matchmake` based on seeding and/or winrate instead of random shuffling.
    *   **Match Completion Flexibility**: Allow `/match_complete` to accept lists of players instead of just VCs.
*   **Club Leader Elections**: Functionality not yet implemented.
*   **Web-Scraper**: Functionality not yet implemented.
*   **Multi-Server Support**: While functional in multiple servers, cross-server features or data sharing are not implemented.

## Core Concepts

### Engineer Role
This is the role the bot uses to manage permissions. It **must** be the highest role in the server hierarchy for the bot to function correctly. The `RoleChannelListener` cog actively monitors this.

### Managed Roles & Channels
The bot automatically creates and manages certain roles (Verified, Student, Alumni, etc.) and channels (`#engineer`, `#verification`, `#modmail`). Deleting or improperly modifying these can disrupt bot functionality, although the bot attempts self-healing where possible (e.g., recreating `#engineer`).

## Setup Process

1.  **Invite the Bot**: Ensure the bot has necessary permissions (Administrator recommended during setup). The bot creates an "Engineer" role upon joining.
2.  **Position Engineer Role**: Go to Server Settings > Roles and drag the "Engineer" role to the very top of the list. Save changes.
3.  **Run `/setup`**: In any channel, an administrator runs the `/setup` command.
4.  **Follow Prompts**: The bot will guide through role creation/verification and member processing in the `#engineer` channel. It will handle duplicate roles if found.
5.  **Completion**: Once finished, the bot creates `#verification` and `#modmail` channels, deploys the verification message, and syncs operational commands (Verification, Role Reactions, Role Management, Team). Setup-specific commands are removed.

To cancel setup and remove the bot, use `/setup_cancel`.

## Commands

Commands are context-dependent. Setup commands are only available before `/setup` is completed. Operational commands are available after setup.

### Setup Cog
*(Available before `/setup` is complete)*
*   `/ping`: Checks if the bot is responsive. (Admin only)
*   `/setup`: Starts the automated server setup process. Requires the Engineer role to be at the top. (Admin only)
*   `/setup_cancel`: Cancels setup, removes the `#engineer` channel, cleans the database, and removes the bot from the server. (Admin only)

### Verification Cog
*(Functionality accessed via buttons in `#verification` after setup)*
*   No direct user commands. Interaction is through buttons: "Student", "Friend", "Alumni", "Prospective Student".

### Role Reactions Cog
*(Available after setup)*
*   `/addrolereaction [channel] [message_id] [emoji] [role]`: Adds a reaction role to a specific message. (Admin only)
*   `/editrolereaction [channel] [message_id] [emoji] [new_role]`: Changes the role assigned to an existing reaction role. (Admin only)
*   `/delrolereaction [channel] [message_id] [emoji]`: Removes a reaction role from a message. (Admin only)

### Role Management Cog
*(Available after setup)*
*   `/set_new_fall_semester [date] [time] [timezone]`: Sets the date/time for the fall semester start action (must be Aug/Sep). (Admin only)
*   `/set_new_spring_semester [date] [time] [timezone]`: Sets the date/time for the spring semester start action (must be Jan/Feb). (Admin only)

### Team (Tryouts) Cog
*(Available after setup)*
*   `/tryouts_define_role [role]`: Defines which role (besides Admin) can manage tryouts. (Admin only)
*   `/tryouts_create [video_game_category] [role_name] [team_size] [google_form_link]`: Configures a new tryout for a game category, creating the participant role. (Manager/Admin only)
*   `/tryouts_join [video_game_category]`: Allows a student to join the tryouts for a game (requires form completion - TODO). (Student role required)
*   `/tryouts_begin [video_game_category]`: Creates the `#tryouts` text channel, `Lobby` VC, and `Tryouts X` VCs based on participant count and team size. (Manager/Admin only)
*   `/tryouts_matchmake [video_game_category]`: Moves players from the Lobby VC into unoccupied `Tryouts X` VCs for a match (uses random assignment - TODO). (Manager/Admin only)
*   `/match_complete [video_game_category] [winning_vc] [losing_vc]`: Records match results based on players in VCs, updates win/loss stats, and moves players back to Lobby. (Manager/Admin only)
*   `/winrate_list [video_game_category]`: Displays a sorted list of participant win rates for the specified tryout.
*   `/team_add [role] [player1] ... [player8]`: Assigns a specified final team role to a list of players. (Manager/Admin only)
*   `/team_reset [video_game_category]`: Removes the tryout-specific participant role from everyone in that category. (Manager/Admin only)

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1.  **Fork the repository** to your GitHub account.
2.  **Clone the forked repository** to your local machine.
3.  **Create a new branch** for your changes.
    ```bash
    git checkout -b feature/your-feature-name
    ```
4.  Make your changes and commit them.
5.  Push your branch to your fork.
6.  Open a Pull Request against the main repository.

## License

This project is open-source and available under the MIT License.
