# Engineer Discord Bot Documentation

**Engineer** is an open-source Discord bot designed to streamline authentication, manage user roles, and facilitate elections within the Team RPI Discord server. By automating these processes, Engineer ensures that only authenticated members gain access to specific server roles and channels, while also providing tools to conduct fair and transparent elections.

## Table of Contents

- [Features](#features)
- [Commands](#commands)
- [Contributing](#contributing)
- [License](#license)

## Features

### Working Features
#### Authentication
Verify user’s status as current students, alumni, ‘friend’, or prospective using RPI email verification and other means.

### Features in Progress
#### Role Management
Automatically assign roles based on user status (current club member/current team), manage roles as students transition from students to alumni, and keep track of students ‘retiring’ from a club.

#### Tryouts Management
Facilitate tryouts and relevant role assignment. *(Work in Progress)*

#### Club Leader Elections
Facilitate the organization and execution of club leader elections within Discord servers, enabling voting via various mediums (text, email, google form, discord vote). *(Work in Progress)*

#### Web-Scraper
Scrape union website to automate member due assignment and club leader appointment. *(Work in Progress)*

#### Management Tools
Miscellaneous commands that enable board members and moderators to manage niche cases. *(Work in Progress)*

#### Multi-Server
Enable the bot to work across multiple RPI discord servers. *(Work in Progress)*

## Commands

### `!ping`
Responds with "pong!" to check if the bot is active.

### `!remove_student_roles`
Removes the student roles from members who are no longer students and assigns them the alumni role.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. **Fork the repository** to your GitHub account.
2. **Clone the forked repository** to your local machine.
3. **Create a new branch** for your changes.
   ```bash
   git checkout -b feature/your-feature-name
   ```

## License
This project is open-source and available under the MIT License.
