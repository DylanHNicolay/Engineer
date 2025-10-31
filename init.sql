CREATE TYPE semester_type AS ENUM ('Fall', 'Summer', 'Spring');

CREATE TABLE team (
    teamid BIGINT NOT NULL PRIMARY KEY,
    teamname VARCHAR(100) NOT NULL,
    roleid BIGINT NOT NULL,
    channelid BIGINT NOT NULL,
    categoryid BIGINT NOT NULL,
    categoryname VARCHAR(100) NOT NULL,
    discordid BIGINT NOT NULL,
    yr INT NOT NULL,
    semester semester_type NOT NULL
);

CREATE TABLE player (
    discordid BIGINT NOT NULL PRIMARY KEY,
    rcsid VARCHAR(50) NOT NULL
);

CREATE TABLE dues (
    starters int,
    substitues int,
    non-player int
);