CREATE TABLE users (
    discord_id BIGINT PRIMARY KEY,
    years_remaining INT
);

CREATE TABLE server_settings (
    guild_id BIGINT PRIMARY KEY,
    co_president_id BIGINT,
    representative_id BIGINT,
    student_id BIGINT,
    alumni_id BIGINT,
    friend_id BIGINT,
    verified_id BIGINT,
    verify_channel_id BIGINT,
    engineer_channel_id BIGINT
);

CREATE TABLE role_reaction_messages (
    message_id BIGINT PRIMARY KEY
);

CREATE TABLE role_reactions (
    message_id BIGINT REFERENCES role_reaction_messages(message_id) ON DELETE CASCADE,
    guild_id BIGINT,
    role_id BIGINT,
    emoji TEXT,
    PRIMARY KEY (message_id, emoji)
);
