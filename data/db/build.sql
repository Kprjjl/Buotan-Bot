CREATE TABLE IF NOT EXISTS guilds (
    GuildID INTEGER PRIMARY KEY,
    Prefix text DEFAULT "b-",
    announcementChannelID INTEGER UNIQUE
);

--SCHEDULER
CREATE TABLE IF NOT EXISTS frequencies (
    id INTEGER PRIMARY KEY,
    freq TEXT UNIQUE
);

INSERT INTO frequencies ('freq') VALUES ('Sunday');
INSERT INTO frequencies ('freq') VALUES ('Monday');
INSERT INTO frequencies ('freq') VALUES ('Tuesday');
INSERT INTO frequencies ('freq') VALUES ('Wednesday');
INSERT INTO frequencies ('freq') VALUES ('Thursday');
INSERT INTO frequencies ('freq') VALUES ('Friday');
INSERT INTO frequencies ('freq') VALUES ('Saturday');
INSERT INTO frequencies ('freq') VALUES ('Once');

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    guildID INTEGER,
    title TEXT UNIQUE NOT NULL,
    start TIMESTAMP NOT NULL,
    "end" TIMESTAMP NOT NULL,
    --freq TEXT NOT NULL,
    freqID INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY ("freqID") REFERENCES frequencies("id"),
    FOREIGN KEY ("guildID") REFERENCES guilds("GuildID") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendees (
    discordID INTEGER PRIMARY KEY,
    mention TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS involvements (
    id INTEGER PRIMARY KEY,
    attendeeID INTEGER NOT NULL,
    eventID INTEGER NOT NULL,
    FOREIGN KEY ("attendeeID") REFERENCES attendees("discordID") ON DELETE CASCADE,
    FOREIGN KEY ("eventID") REFERENCES events("id") ON DELETE CASCADE
    UNIQUE (attendeeID, eventID)
);

--POMODORO
CREATE TABLE IF NOT EXISTS pomoChannels (
    guildID INTEGER,
    discordID INTEGER NOT NULL UNIQUE,
    state INTEGER NOT NULL,
    "work" INTEGER NOT NULL,  --state: 0
    shortbreak INTEGER NOT NULL,  --state: 1
    longbreak INTEGER,  --state: 2
    tomatocount INTEGER NOT NULL DEFAULT 0,
    maxtomato INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY ("guildID") REFERENCES guilds("GuildID") ON DELETE CASCADE
);

--GENSHIN
CREATE TABLE IF NOT EXISTS weightPresets (
    id INTEGER PRIMARY KEY,
    guildID INTEGER NOT NULL,
    name TEXT NOT NULL,
    hp REAL NOT NULL DEFAULT 0,
    def REAL NOT NULL DEFAULT 0,
    atk REAL NOT NULL DEFAULT 0,
    hp96 REAL NOT NULL DEFAULT 0,
    def96 REAL NOT NULL DEFAULT 0,
    atk96 REAL NOT NULL DEFAULT 0,
    em REAL NOT NULL DEFAULT 0,
    er REAL NOT NULL DEFAULT 0,
    cr REAL NOT NULL DEFAULT 0,
    cd REAL NOT NULL DEFAULT 0,
    FOREIGN KEY ("guildID") REFERENCES guilds("GuildID") ON DELETE CASCADE
    UNIQUE (guildID, name)
);
