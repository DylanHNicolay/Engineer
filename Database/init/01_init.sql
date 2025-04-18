-- Table for Discord users
CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY, -- 18-digit unique Discord identifier
    verified BOOLEAN DEFAULT FALSE, 
    student BOOLEAN DEFAULT FALSE,
    alumni BOOLEAN DEFAULT FALSE,
    prospective BOOLEAN DEFAULT FALSE,
    friend BOOLEAN DEFAULT FALSE,
    rpi_admin BOOLEAN DEFAULT FALSE,
    rcsid VARCHAR(255),
    years_remaining INT CHECK (years_remaining >= 0 AND years_remaining <= 8),
    verification_code INT,
    verification_type VARCHAR(50),
    verification_email VARCHAR(255),
    verification_attempt_count INT DEFAULT 0,
    last_verification_attempt BIGINT DEFAULT 0,
    CHECK (
        (CASE WHEN student THEN 1 ELSE 0 END +
         CASE WHEN alumni THEN 1 ELSE 0 END +
         CASE WHEN prospective THEN 1 ELSE 0 END +
         CASE WHEN friend THEN 1 ELSE 0 END +
         CASE WHEN rpi_admin THEN 1 ELSE 0 END +
         CASE WHEN verified THEN 1 ELSE 0 END) <= 1
    )
);

-- Table for Discord guilds
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    engineer_channel_id BIGINT,
    setup BOOLEAN DEFAULT TRUE,
    verified_role_id BIGINT,
    student_role_id BIGINT,
    alumni_role_id BIGINT,
    prospective_student_role_id BIGINT,
    friend_role_id BIGINT,
    rpi_admin_role_id BIGINT,
    engineer_role_id BIGINT,
    last_warning_time BIGINT DEFAULT 0,
    role_enforcement_triggered BOOLEAN DEFAULT FALSE,
    verification_channel_id BIGINT,
    modmail_channel_id BIGINT,
    verification_message_id BIGINT,
    -- New columns for Role Management
    fall_semester_start TIMESTAMP WITH TIME ZONE,
    spring_semester_start TIMESTAMP WITH TIME ZONE,
    last_fall_action_year INT,
    last_spring_action_year INT,
    fall_warning_1m_sent_year INT,
    fall_warning_1w_sent_year INT,
    fall_warning_1d_sent_year INT,
    spring_warning_1m_sent_year INT,
    spring_warning_1w_sent_year INT,
    spring_warning_1d_sent_year INT,
    -- New column for Team/Tryouts
    tryout_manager_role_id BIGINT
);

-- Table to map users to guilds
CREATE TABLE IF NOT EXISTS user_guilds (
    discord_id BIGINT REFERENCES users(discord_id),
    guild_id BIGINT REFERENCES guilds(guild_id),
    PRIMARY KEY (discord_id, guild_id)
);

-- Table for verification cooldowns 
CREATE TABLE IF NOT EXISTS verification_cooldowns (
    discord_id BIGINT REFERENCES users(discord_id),
    guild_id BIGINT REFERENCES guilds(guild_id),
    last_attempt BIGINT NOT NULL,
    attempt_count INT DEFAULT 0,
    PRIMARY KEY (discord_id, guild_id)
);

-- Table for role reactions
CREATE TABLE IF NOT EXISTS role_reactions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    UNIQUE(guild_id, message_id, emoji)
);

-- Table for Tryouts Configuration
CREATE TABLE IF NOT EXISTS tryouts (
    tryout_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL, -- Discord Category ID
    category_name TEXT NOT NULL, -- Store name for easier lookup/display
    role_id BIGINT NOT NULL, -- Role assigned to participants
    role_name TEXT NOT NULL, -- Store name for easier lookup/display
    team_size INT NOT NULL CHECK (team_size > 0),
    google_form_link TEXT,
    google_form_id TEXT, -- Extracted ID
    is_active BOOLEAN DEFAULT TRUE, -- To easily enable/disable tryouts
    UNIQUE(guild_id, category_id) -- Only one tryout config per category per guild
);

-- Table for Tryout Participants
CREATE TABLE IF NOT EXISTS tryout_participants (
    participant_id SERIAL PRIMARY KEY,
    tryout_id INT NOT NULL REFERENCES tryouts(tryout_id) ON DELETE CASCADE,
    discord_id BIGINT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    UNIQUE(tryout_id, discord_id) -- User can only participate once per tryout
);

-- Table for Tryout Match History (Optional but recommended)
CREATE TABLE IF NOT EXISTS tryout_matches (
    match_id SERIAL PRIMARY KEY,
    tryout_id INT NOT NULL REFERENCES tryouts(tryout_id) ON DELETE CASCADE,
    match_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    winning_team_discord_ids BIGINT[],
    losing_team_discord_ids BIGINT[]
);
