-- Quarantine tables for failed records

CREATE TABLE IF NOT EXISTS bronze.quarantine_petitions (
    id SERIAL PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    source VARCHAR(50) NOT NULL,
    schema_name VARCHAR(100),
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retried BOOLEAN DEFAULT FALSE,
    retry_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bronze.quarantine_user_events (
    id SERIAL PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    source VARCHAR(50) NOT NULL,
    schema_name VARCHAR(100),
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retried BOOLEAN DEFAULT FALSE,
    retry_count INT DEFAULT 0
);

-- Indexes for monitoring queries
CREATE INDEX IF NOT EXISTS idx_quarantine_petitions_failed_at
    ON bronze.quarantine_petitions(failed_at);
CREATE INDEX IF NOT EXISTS idx_quarantine_petitions_error_type
    ON bronze.quarantine_petitions(error_type);

CREATE INDEX IF NOT EXISTS idx_quarantine_user_events_failed_at
    ON bronze.quarantine_user_events(failed_at);
CREATE INDEX IF NOT EXISTS idx_quarantine_user_events_error_type
    ON bronze.quarantine_user_events(error_type);
