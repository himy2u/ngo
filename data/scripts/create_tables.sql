-- Create raw petitions table
CREATE TABLE IF NOT EXISTS raw_petitions (
    petition_id BIGINT PRIMARY KEY,
    action TEXT NOT NULL,
    background TEXT,
    additional_details TEXT,
    status VARCHAR(50),
    signature_count BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    open_at TIMESTAMP,
    closed_at TIMESTAMP,
    government_response_at TIMESTAMP,
    debate_threshold_reached_at TIMESTAMP,
    response_threshold_reached_at TIMESTAMP,
    creator_name VARCHAR(255),
    topics JSONB,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create metrics table for monitoring
CREATE TABLE IF NOT EXISTS pipeline_metrics (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    source VARCHAR(100),
    records_processed INT,
    records_valid INT,
    records_quarantined INT,
    execution_time_ms BIGINT,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_petitions_status ON raw_petitions(status);
CREATE INDEX IF NOT EXISTS idx_petitions_created ON raw_petitions(created_at);
CREATE INDEX IF NOT EXISTS idx_petitions_signatures ON raw_petitions(signature_count DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_pipeline ON pipeline_metrics(pipeline_name, created_at DESC);
