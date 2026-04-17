# Setup Module Documentation

## setup.py
Contains the methods related to creating and managing server roles and channels.
- **_create_initial_engineer_channel**: The bot will create or use an existing channel named `engineer` to be used for database changes log.
- **_setup_roles**: The bot will create or use existing roles like co-president, representatives, and other verified roles for the server to use.
- **_update_engineer_channel_perms**: The bot will overwrite the `engineer` channel read and send message permissions for only leadership roles and itself.
- **_create_verify_channel**: The bot will create or use an existing channel named `verify` to be used for starting the verification process.
- **_update_verify_channel_perms**: The bot will overwrite the `verify` channel permissions to read-only for everyone except leadership roles.
- **setup_guild**: Utilizes the previous functions and runs all of them to set up the guild.

## backfill.py
Contains the logic for managing and updating user data in the database.
- **add_user**: The bot will add the user's Discord ID and years remaining into the database.
- **_backfill_users**: The bot will search through the server's member list and record any missing members in the database. This has an optional argument to assign verified status to all undocumented members when run.
- **backfill**: The bot command which will run `_backfill_users` and log all changes in the `engineer` channel.

## year.py
Contains the logic for managing member statuses based on years remaining.
- **year_command_logic**: The bot will decrease years remaining of all members in the database whose value is above 0. If any member results in 0 years remaining, their status in the server becomes `alumni`.