-- Table for Discord users
CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY, -- 18-digit unique Discord identifier
    verified BOOLEAN DEFAULT FALSE -- Indicates if the user is verified
);

-- Table for Discord guilds
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY
);

-- Table to map users to guilds
CREATE TABLE IF NOT EXISTS user_guilds (
    discord_id BIGINT REFERENCES users(discord_id),
    guild_id BIGINT REFERENCES guilds(guild_id),
    PRIMARY KEY (discord_id, guild_id)
);
