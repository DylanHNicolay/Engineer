# Engineer Discord Bot Documentation

**Engineer** is an open-source Discord bot designed to streamline authentication, manage user roles, and facilitate elections within the Team RPI Discord server. By automating these processes, Engineer ensures that only authenticated members gain access to specific server roles and channels, while also providing tools to conduct fair and transparent elections.

## Table of Contents

- [Features](#features)
- [Commands](#commands)
- [Contributing](#contributing)
- [License](#license)

## Features

- **User Verification**: Authenticate users through their RCSID and assign appropriate roles.
- **Role Management**: Automatically assign the "Student" role upon successful verification.
- **Secure Authentication**: Generate and verify unique codes sent via email.
- **Database Integration**: Store and manage user information securely.



## Commands

- `!ping`

  - **Description**: Checks if the bot is responsive.
  - **Usage**: Simply type `!ping` in the designated channel.
  - **Example**:

    ```
    User: !ping
    Bot: pong!
    ```

- `!init`

  - **Description**: Initializes user data and creates necessary database tables.
  - **Usage**: Run `!init` to set up the user information table in the database.
  - **Note**: This command should be run by an administrator.

- `!verify`

  - **Description**: Starts the user verification process.
  - **Usage**: Users type `!verify` and follow the instructions provided.
  - **Process**:
    1. Click the "Start Verification" button prompted by the bot.
    2. Check your DMs for further instructions.
    3. Provide your RCSID when prompted.
    4. Enter the 6-digit verification code sent to your email.
    5. Specify the number of years remaining at RPI.
    6. Upon successful verification, the "Student" role will be assigned.


## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. **Fork the repository** to your GitHub account.
2. **Clone the forked repository** to your local machine.
3. **Create a new branch** for your changes.
   ```bash
   git checkout -b feature/your-feature-name


## License
This project is open-source and available under the MIT License.