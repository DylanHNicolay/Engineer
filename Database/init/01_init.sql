-- Table for Discord users
CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY, -- 18-digit unique Discord identifier
    verified BOOLEAN DEFAULT FALSE, 
    student BOOLEAN DEFAULT FALSE,
    alumni BOOLEAN DEFAULT FALSE,
    prospective BOOLEAN DEFAULT FALSE,
    friend BOOLEAN DEFAULT FALSE,
    rpi_admin BOOLEAN DEFAULT FALSE,
    CHECK (
        (CASE WHEN student THEN 1 ELSE 0 END +
         CASE WHEN alumni THEN 1 ELSE 0 END +
         CASE WHEN prospective THEN 1 ELSE 0 END +
         CASE WHEN friend THEN 1 ELSE 0 END +
         CASE WHEN rpi_admin THEN 1 ELSE 0 END) <= 1
    ),
    CHECK (
        (student OR alumni OR prospective OR friend OR rpi_admin) = false 
        OR verified = true
    )
);

-- Table for Discord guilds
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    verified_role_id BIGINT,
    student_role_id BIGINT,
    alumni_role_id BIGINT,
    prospective_student_role_id BIGINT,
    friend_role_id BIGINT,
    rpi_admin_role_id BIGINT
);

ALTER TABLE guilds
ADD COLUMN IF NOT EXISTS engineer_role_id BIGINT,
ADD COLUMN IF NOT EXISTS engineer_channel_id BIGINT;

-- Table to map users to guilds
CREATE TABLE IF NOT EXISTS user_guilds (
    discord_id BIGINT REFERENCES users(discord_id),
    guild_id BIGINT REFERENCES guilds(guild_id),
    PRIMARY KEY (discord_id, guild_id)
);
