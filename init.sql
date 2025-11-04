CREATE TYPE semester_type AS ENUM ('Fall', 'Summer', 'Spring');

CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_nick VARCHAR(100),
    role_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    captain_discord_id BIGINT NOT NULL,
    year INT NOT NULL,
    semester semester_type NOT NULL,
    archived BOOLEAN DEFAULT FALSE
);

CREATE TABLE players (
    player_discord_id BIGINT PRIMARY KEY,
    rcsid VARCHAR(50)
);

CREATE TABLE team_members (
    team_id INT REFERENCES teams(team_id) ON DELETE CASCADE,
    player_discord_id BIGINT REFERENCES players(player_discord_id) ON DELETE CASCADE,
    is_starter BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (team_id, player_discord_id)
);

CREATE TABLE admin_roles(
    role_id BIGINT PRIMARY KEY
);

CREATE TABLE dues (
    starters int,
    substitues int,
    non_player int
);