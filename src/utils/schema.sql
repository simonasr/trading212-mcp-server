-- Trading212 MCP Server - Local Cache Schema
-- This schema stores immutable historical data for offline analysis

-- Orders (immutable once FILLED/CANCELLED)
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    ticker TEXT,
    type TEXT,
    status TEXT,
    executor TEXT,
    ordered_quantity REAL,
    filled_quantity REAL,
    limit_price REAL,
    stop_price REAL,
    fill_price REAL,
    fill_cost REAL,
    fill_result REAL,
    fill_id INTEGER,
    fill_type TEXT,
    filled_value REAL,
    ordered_value REAL,
    parent_order INTEGER,
    time_validity TEXT,
    date_created TEXT,
    date_executed TEXT,
    date_modified TEXT,
    taxes_json TEXT,
    raw_json TEXT,
    PRIMARY KEY (id, account_id)
);

-- Dividends (immutable - already paid)
CREATE TABLE IF NOT EXISTS dividends (
    reference TEXT NOT NULL,
    account_id INTEGER NOT NULL,
    ticker TEXT,
    amount REAL,
    amount_eur REAL,
    gross_per_share REAL,
    quantity REAL,
    type TEXT,
    paid_on TEXT,
    raw_json TEXT,
    PRIMARY KEY (reference, account_id)
);

-- Transactions (immutable - deposits, withdrawals, fees)
CREATE TABLE IF NOT EXISTS transactions (
    reference TEXT NOT NULL,
    account_id INTEGER NOT NULL,
    type TEXT,
    amount REAL,
    datetime TEXT,
    raw_json TEXT,
    PRIMARY KEY (reference, account_id)
);

-- Sync metadata - tracks last sync state for incremental updates
CREATE TABLE IF NOT EXISTS sync_metadata (
    table_name TEXT NOT NULL,
    account_id INTEGER NOT NULL,
    last_sync TEXT,
    last_cursor TEXT,
    record_count INTEGER DEFAULT 0,
    PRIMARY KEY (table_name, account_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_id);
CREATE INDEX IF NOT EXISTS idx_orders_ticker ON orders(ticker);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(date_created);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_dividends_account ON dividends(account_id);
CREATE INDEX IF NOT EXISTS idx_dividends_ticker ON dividends(ticker);
CREATE INDEX IF NOT EXISTS idx_dividends_paid_on ON dividends(paid_on);

CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_datetime ON transactions(datetime);
