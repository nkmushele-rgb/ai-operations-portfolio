-- Project 2: AI inventory management
-- Products hold a running balance and a moving average cost. Every change to
-- stock is a row in movements, so the balance can always be rebuilt from history.

CREATE TABLE IF NOT EXISTS products (
    sku           TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    unit          TEXT NOT NULL DEFAULT 'unit',
    category      TEXT,
    reorder_level REAL NOT NULL DEFAULT 0,
    qty           REAL NOT NULL DEFAULT 0,
    avg_cost      REAL NOT NULL DEFAULT 0,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT NOT NULL REFERENCES products(sku),
    kind            TEXT NOT NULL CHECK (kind IN ('receipt', 'issue', 'adjustment')),
    qty             REAL NOT NULL,
    unit_cost       REAL,
    value           REAL NOT NULL DEFAULT 0,
    reference       TEXT,
    note            TEXT,
    at              TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('low_stock', 'out_of_stock', 'anomaly')),
    message      TEXT NOT NULL,
    detail       TEXT,
    at           TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rejected (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    payload  TEXT NOT NULL,
    problems TEXT NOT NULL,
    at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movements_sku ON movements(sku, at);
CREATE INDEX IF NOT EXISTS idx_movements_at ON movements(at);

-- Only one open alert of each kind per product, so a nightly run cannot spam.
CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_open
    ON alerts(sku, kind) WHERE acknowledged = 0;
