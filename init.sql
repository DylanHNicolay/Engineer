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
