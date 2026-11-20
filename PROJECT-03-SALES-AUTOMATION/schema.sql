-- Project 3: AI sales lead management
-- A lead keeps its score and the reason for that score, so a salesperson can
-- argue with the ranking instead of guessing where it came from.

CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    company         TEXT,
    source          TEXT,
    role            TEXT,
    employees       INTEGER,
    budget          REAL,
    timeline        TEXT,
    message         TEXT,
    segment         TEXT,
    score           INTEGER NOT NULL DEFAULT 0,
    band            TEXT,
    score_reason    TEXT,
    status          TEXT NOT NULL DEFAULT 'new',
    last_contact_at TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    channel     TEXT NOT NULL DEFAULT 'email',
    subject     TEXT,
    body        TEXT NOT NULL,
    source      TEXT NOT NULL,
    approved    INTEGER NOT NULL DEFAULT 0,
    approved_by TEXT,
    approved_at TEXT,
    sent        INTEGER NOT NULL DEFAULT 0,
    sent_at     TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    kind    TEXT NOT NULL,
    detail  TEXT,
    at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rejected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    payload     TEXT NOT NULL,
    problems    TEXT NOT NULL,
    at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leads_band ON leads(band, score);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_activities_lead ON activities(lead_id);
