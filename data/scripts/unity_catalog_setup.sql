-- ===================================================================
-- UNITY CATALOG STYLE GOVERNANCE FOR POSTGRES
-- Implements medallion architecture with schema-based access control
-- ===================================================================

-- ===================================================================
-- STEP 1: CREATE SCHEMAS (Similar to Unity Catalog Catalogs)
-- ===================================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS governance;

COMMENT ON SCHEMA bronze IS 'Raw data layer - data as received from sources';
COMMENT ON SCHEMA silver IS 'Cleaned and enriched data layer';
COMMENT ON SCHEMA gold IS 'Business-ready aggregated metrics';
COMMENT ON SCHEMA governance IS 'Data governance metadata and audit tables';

-- ===================================================================
-- STEP 2: CREATE ROLES (Similar to Unity Catalog Access Control)
-- ===================================================================

-- Data Engineer: Full access to bronze/silver, read on gold
CREATE ROLE IF NOT EXISTS data_engineer;

-- Data Analyst: Read-only access to silver/gold
CREATE ROLE IF NOT EXISTS data_analyst;

-- Data Scientist: Read access to silver, write to gold (for ML features)
CREATE ROLE IF NOT EXISTS data_scientist;

-- Read-only: Query access to gold layer only
CREATE ROLE IF NOT EXISTS read_only_user;

-- Admin: Full access to everything
CREATE ROLE IF NOT EXISTS data_admin;

-- ===================================================================
-- STEP 3: GRANT SCHEMA PERMISSIONS
-- ===================================================================

-- Data Engineer permissions
GRANT USAGE ON SCHEMA bronze TO data_engineer;
GRANT USAGE ON SCHEMA silver TO data_engineer;
GRANT USAGE ON SCHEMA gold TO data_engineer;
GRANT ALL ON ALL TABLES IN SCHEMA bronze TO data_engineer;
GRANT ALL ON ALL TABLES IN SCHEMA silver TO data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO data_engineer;
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT ALL ON TABLES TO data_engineer;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL ON TABLES TO data_engineer;

-- Data Analyst permissions
GRANT USAGE ON SCHEMA silver TO data_analyst;
GRANT USAGE ON SCHEMA gold TO data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA silver TO data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO data_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT SELECT ON TABLES TO data_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO data_analyst;

-- Data Scientist permissions
GRANT USAGE ON SCHEMA silver TO data_scientist;
GRANT USAGE ON SCHEMA gold TO data_scientist;
GRANT SELECT ON ALL TABLES IN SCHEMA silver TO data_scientist;
GRANT ALL ON ALL TABLES IN SCHEMA gold TO data_scientist;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT SELECT ON TABLES TO data_scientist;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL ON TABLES TO data_scientist;

-- Read-only user permissions
GRANT USAGE ON SCHEMA gold TO read_only_user;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO read_only_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO read_only_user;

-- Admin permissions
GRANT ALL ON SCHEMA bronze TO data_admin;
GRANT ALL ON SCHEMA silver TO data_admin;
GRANT ALL ON SCHEMA gold TO data_admin;
GRANT ALL ON SCHEMA governance TO data_admin;
GRANT ALL ON ALL TABLES IN SCHEMA bronze TO data_admin;
GRANT ALL ON ALL TABLES IN SCHEMA silver TO data_admin;
GRANT ALL ON ALL TABLES IN SCHEMA gold TO data_admin;

-- ===================================================================
-- STEP 4: CREATE BRONZE LAYER TABLES (Raw Data)
-- ===================================================================

CREATE TABLE IF NOT EXISTS bronze.petitions (
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
    -- Metadata fields for governance
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source VARCHAR(100) DEFAULT 'uk_parliament_api',
    _ingestion_id UUID DEFAULT gen_random_uuid()
);

COMMENT ON TABLE bronze.petitions IS 'Raw petition data from UK Parliament API';
COMMENT ON COLUMN bronze.petitions._ingested_at IS 'Timestamp when data was ingested';
COMMENT ON COLUMN bronze.petitions._source IS 'Source system identifier';
COMMENT ON COLUMN bronze.petitions._ingestion_id IS 'Unique identifier for this ingestion batch';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bronze_petitions_status ON bronze.petitions(status);
CREATE INDEX IF NOT EXISTS idx_bronze_petitions_created ON bronze.petitions(created_at);
CREATE INDEX IF NOT EXISTS idx_bronze_petitions_signatures ON bronze.petitions(signature_count DESC);

-- ===================================================================
-- STEP 5: CREATE SILVER LAYER TABLES (Cleaned & Enriched)
-- ===================================================================

CREATE TABLE IF NOT EXISTS silver.petitions (
    petition_id BIGINT PRIMARY KEY,
    petition_title TEXT NOT NULL,
    petition_background TEXT,
    status VARCHAR(50),
    signature_count BIGINT,
    created_date TIMESTAMP,
    updated_date TIMESTAMP,
    closed_date TIMESTAMP,
    response_date TIMESTAMP,
    debate_reached_date TIMESTAMP,
    -- Derived dimensions
    signature_tier VARCHAR(50),
    has_government_response BOOLEAN,
    reached_debate_threshold BOOLEAN,
    created_year INT,
    created_month INT,
    created_day DATE,
    -- Metadata
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_table VARCHAR(100) DEFAULT 'bronze.petitions',
    -- Data Quality Score (0-100)
    _data_quality_score NUMERIC(5,2)
);

COMMENT ON TABLE silver.petitions IS 'Cleaned and enriched petition data';
COMMENT ON COLUMN silver.petitions.signature_tier IS 'Categorization: Low, Medium, High, Viral';
COMMENT ON COLUMN silver.petitions._data_quality_score IS 'Data quality score: 0-100 (100 = perfect quality)';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_silver_petitions_tier ON silver.petitions(signature_tier);
CREATE INDEX IF NOT EXISTS idx_silver_petitions_year ON silver.petitions(created_year);
CREATE INDEX IF NOT EXISTS idx_silver_petitions_status ON silver.petitions(status);

-- ===================================================================
-- STEP 6: CREATE GOLD LAYER TABLES (Business Metrics)
-- ===================================================================

CREATE TABLE IF NOT EXISTS gold.petition_metrics (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50),
    signature_tier VARCHAR(50),
    petition_count INT,
    total_signatures BIGINT,
    avg_signatures NUMERIC,
    min_signatures BIGINT,
    max_signatures BIGINT,
    govt_responses INT,
    debates_reached INT,
    response_rate_pct NUMERIC,
    -- Metadata
    _calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _metric_date DATE DEFAULT CURRENT_DATE
);

COMMENT ON TABLE gold.petition_metrics IS 'Aggregated petition performance metrics';

CREATE TABLE IF NOT EXISTS gold.daily_petition_summary (
    summary_date DATE PRIMARY KEY,
    new_petitions_count INT,
    total_signatures_added BIGINT,
    avg_signatures_per_petition NUMERIC,
    viral_petitions_count INT,
    government_responses_count INT,
    _calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE gold.daily_petition_summary IS 'Daily petition activity summary';

-- ===================================================================
-- STEP 7: GOVERNANCE TABLES (Data Lineage & Audit)
-- ===================================================================

CREATE TABLE IF NOT EXISTS governance.data_lineage (
    lineage_id SERIAL PRIMARY KEY,
    source_table VARCHAR(200),
    target_table VARCHAR(200),
    transformation_type VARCHAR(50),
    transformation_sql TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(100) DEFAULT CURRENT_USER,
    rows_processed BIGINT,
    status VARCHAR(20)
);

COMMENT ON TABLE governance.data_lineage IS 'Tracks data transformations across layers';

CREATE TABLE IF NOT EXISTS governance.data_access_log (
    access_id SERIAL PRIMARY KEY,
    user_name VARCHAR(100),
    table_accessed VARCHAR(200),
    access_type VARCHAR(20), -- SELECT, INSERT, UPDATE, DELETE
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    row_count INT,
    ip_address INET
);

COMMENT ON TABLE governance.data_access_log IS 'Audit log for data access';

CREATE TABLE IF NOT EXISTS governance.data_quality_checks (
    check_id SERIAL PRIMARY KEY,
    table_name VARCHAR(200),
    check_name VARCHAR(100),
    check_type VARCHAR(50), -- uniqueness, completeness, validity, consistency
    expected_value TEXT,
    actual_value TEXT,
    passed BOOLEAN,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE governance.data_quality_checks IS 'Data quality validation results';

CREATE TABLE IF NOT EXISTS governance.pii_tags (
    tag_id SERIAL PRIMARY KEY,
    table_name VARCHAR(200),
    column_name VARCHAR(100),
    pii_type VARCHAR(50), -- email, name, address, phone, etc
    sensitivity_level VARCHAR(20), -- low, medium, high, critical
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT CURRENT_USER
);

COMMENT ON TABLE governance.pii_tags IS 'PII classification tags for columns';

-- ===================================================================
-- STEP 8: ROW-LEVEL SECURITY EXAMPLE
-- ===================================================================

-- Enable RLS on silver layer
ALTER TABLE silver.petitions ENABLE ROW LEVEL SECURITY;

-- Policy: Data analysts can only see closed petitions (example restriction)
CREATE POLICY analyst_closed_petitions ON silver.petitions
    FOR SELECT
    TO data_analyst
    USING (status = 'closed');

-- Policy: Data engineers can see everything
CREATE POLICY engineer_all_petitions ON silver.petitions
    FOR ALL
    TO data_engineer
    USING (true);

-- Policy: Read-only users via gold layer (no RLS needed since gold is aggregated)

-- ===================================================================
-- STEP 9: TAG PII COLUMNS
-- ===================================================================

INSERT INTO governance.pii_tags (table_name, column_name, pii_type, sensitivity_level)
VALUES
    ('bronze.petitions', 'creator_name', 'name', 'medium'),
    ('silver.petitions', 'petition_title', 'user_generated_content', 'low')
ON CONFLICT DO NOTHING;

-- ===================================================================
-- STEP 10: CREATE VIEWS FOR DATA LINEAGE VISIBILITY
-- ===================================================================

CREATE OR REPLACE VIEW governance.schema_inventory AS
SELECT
    schemaname as schema_name,
    tablename as table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = schemaname AND table_name = tablename) as column_count
FROM pg_tables
WHERE schemaname IN ('bronze', 'silver', 'gold')
ORDER BY schemaname, tablename;

COMMENT ON VIEW governance.schema_inventory IS 'Catalog of all tables in medallion architecture';

-- ===================================================================
-- COMPLETION MESSAGE
-- ===================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Unity Catalog style governance setup complete!';
    RAISE NOTICE 'Schemas created: bronze, silver, gold, governance';
    RAISE NOTICE 'Roles created: data_engineer, data_analyst, data_scientist, read_only_user, data_admin';
    RAISE NOTICE 'Governance tables: data_lineage, data_access_log, data_quality_checks, pii_tags';
END $$;
