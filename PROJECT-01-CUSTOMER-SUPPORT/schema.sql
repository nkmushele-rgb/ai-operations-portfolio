-- Project 1: AI customer support triage
-- SQLite schema. One ticket per inbound message, one draft reply per ticket.

CREATE TABLE IF NOT EXISTS tickets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id       TEXT NOT NULL UNIQUE,
    channel           TEXT NOT NULL,
    customer_name     TEXT,
    customer_email    TEXT NOT NULL,
    subject           TEXT,
    body              TEXT NOT NULL,
    received_at       TEXT,
    category          TEXT,
    urgency           TEXT,
    sentiment         TEXT,
    escalated         INTEGER NOT NULL DEFAULT 0,
    escalation_reason TEXT,
    status            TEXT NOT NULL DEFAULT 'new',
    needs_review      INTEGER NOT NULL DEFAULT 0,
    classifier        TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    subject     TEXT,
    body        TEXT NOT NULL,
    source      TEXT NOT NULL,
    approved    INTEGER NOT NULL DEFAULT 0,
    approved_by TEXT,
    approved_at TEXT,
    sent        INTEGER NOT NULL DEFAULT 0,
    sent_at     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    kind      TEXT NOT NULL,
    detail    TEXT,
    at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rejected (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    payload     TEXT NOT NULL,
    problems    TEXT NOT NULL,
    at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS idx_events_ticket ON events(ticket_id);
