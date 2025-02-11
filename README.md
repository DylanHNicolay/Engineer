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
- **Student Verification:**
  1. User clicks the "Student" button.
  2. Bot sends a DM asking for the user's RCSID.
  3. User provides their RCSID.
  4. Bot generates a verification code and sends it to the user's RPI email.
  5. User enters the verification code in the DM.
  6. Bot verifies the code and asks for the number of years remaining at RPI.
  7. User provides the number of years.
  8. Bot assigns the "Student" role to the user.

- **Friend Verification:**
  1. User clicks the "Friend" button.
  2. Bot sends a DM asking for the friend's unique Discord username.
  3. User provides the friend's username.
  4. Bot sends a DM to the friend asking for verification.
  5. Friend responds with "yes" or "no".
  6. If "yes", bot assigns the "Friend" role to the user.

- **Alumni Verification:**
  1. User clicks the "Alumni" button.
  2. Bot assigns a temporary role and directs the user to the **#modmail** channel.
  3. User provides additional information in the **#modmail** channel.
  4. Admins verify the user and assign the "Alumni" role.

- **Prospective Student Verification:**
  1. User clicks the "Prospective Student" button.
  2. Bot sends a DM asking for the user's email address.
  3. User provides their email address.
  4. Bot generates a verification code and sends it to the provided email.
  5. User enters the verification code in the DM.
  6. Bot verifies the code and assigns the "Prospective Student" role to the user.

### Features in Progress
#### Role Management
Automatically assign roles based on user status (current club member/current team), manage roles as students transition from students to alumni, and keep track of students ‘retiring’ from a club.

#### Tryouts Management
Facilitate tryouts and relevant role assignment. 

#### Club Leader Elections
Facilitate the organization and execution of club leader elections within Discord servers, enabling voting via various mediums (text, email, google form, discord vote). 

#### Web-Scraper
Scrape union website to automate member due assignment and club leader appointment. 

#### Management Tools
Miscellaneous commands that enable board members and moderators to manage niche cases. 

#### Multi-Server
Enable the bot to work across multiple RPI discord servers. 

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
