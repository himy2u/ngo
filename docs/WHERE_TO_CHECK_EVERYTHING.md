# 🔍 WHERE TO CHECK EVERYTHING - Complete Guide

## ✅ **1. RAW DATA (Bronze Layer)**

### Check Raw Petitions Data
```bash
# Connect to database
docker exec -it dev-postgres-1 psql -U postgres -d petitions

# Or from your machine (if psql installed)
psql -h localhost -p 5432 -U postgres -d petitions
```

### Sample Queries

#### Total Petitions & Signatures
```sql
SELECT
    COUNT(*) as total_petitions,
    SUM(signature_count) as total_signatures,
    AVG(signature_count)::int as avg_signatures,
    MAX(signature_count) as max_signatures
FROM raw_petitions;
```

**Expected Output:**
```
 total_petitions | total_signatures | avg_signatures | max_signatures
-----------------+------------------+----------------+----------------
             150 |         18272337 |        121815  |        3084715
```

#### Top 10 Petitions by Signatures
```sql
SELECT
    petition_id,
    action,
    signature_count,
    status,
    created_at
FROM raw_petitions
ORDER BY signature_count DESC
LIMIT 10;
```

#### Petitions by Status
```sql
SELECT
    status,
    COUNT(*) as count,
    SUM(signature_count) as total_signatures,
    ROUND(AVG(signature_count), 0) as avg_signatures
FROM raw_petitions
GROUP BY status
ORDER BY count DESC;
```

#### Recent Petitions (Last 90 Days)
```sql
SELECT
    petition_id,
    action,
    signature_count,
    status,
    created_at,
    AGE(NOW(), created_at::timestamp) as age
FROM raw_petitions
WHERE created_at > NOW() - INTERVAL '90 days'
ORDER BY signature_count DESC
LIMIT 20;
```

#### Petitions with Government Response
```sql
SELECT
    COUNT(*) as total_petitions,
    SUM(CASE WHEN government_response_at IS NOT NULL THEN 1 ELSE 0 END) as with_response,
    ROUND(100.0 * SUM(CASE WHEN government_response_at IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as response_rate_pct
FROM raw_petitions;
```

---

## 📊 **2. SILVER/GOLD TABLES (Transformations)**

### Create Silver Layer Manually (Since dbt had issues)

```sql
-- Connect to database first
\c petitions

-- Create silver layer: Cleaned & enriched petitions
CREATE TABLE IF NOT EXISTS silver_petitions AS
SELECT
    petition_id,
    action as petition_title,
    background as petition_background,
    status,
    signature_count,
    created_at::timestamp as created_date,
    updated_at::timestamp as updated_date,
    closed_at::timestamp as closed_date,
    government_response_at::timestamp as response_date,
    debate_threshold_reached_at::timestamp as debate_reached_date,
    -- Derived fields
    CASE
        WHEN signature_count >= 100000 THEN 'Viral (100K+)'
        WHEN signature_count >= 10000 THEN 'High (10K-100K)'
        WHEN signature_count >= 1000 THEN 'Medium (1K-10K)'
        ELSE 'Low (<1K)'
    END as signature_tier,
    CASE
        WHEN government_response_at IS NOT NULL THEN TRUE
        ELSE FALSE
    END as has_government_response,
    CASE
        WHEN debate_threshold_reached_at IS NOT NULL THEN TRUE
        ELSE FALSE
    END as reached_debate_threshold,
    EXTRACT(YEAR FROM created_at::timestamp) as created_year,
    EXTRACT(MONTH FROM created_at::timestamp) as created_month,
    DATE_TRUNC('day', created_at::timestamp) as created_day,
    ingested_at as data_loaded_at
FROM raw_petitions;

-- Create gold layer: Petition performance metrics
CREATE TABLE IF NOT EXISTS gold_petition_metrics AS
SELECT
    status,
    signature_tier,
    COUNT(*) as petition_count,
    SUM(signature_count) as total_signatures,
    ROUND(AVG(signature_count), 0) as avg_signatures,
    MIN(signature_count) as min_signatures,
    MAX(signature_count) as max_signatures,
    COUNT(CASE WHEN has_government_response THEN 1 END) as govt_responses,
    COUNT(CASE WHEN reached_debate_threshold THEN 1 END) as debates_reached,
    ROUND(100.0 * COUNT(CASE WHEN has_government_response THEN 1 END) / COUNT(*), 1) as response_rate_pct
FROM silver_petitions
GROUP BY status, signature_tier
ORDER BY total_signatures DESC;

-- View the results
SELECT * FROM gold_petition_metrics;
```

### Query Silver Layer
```sql
-- Viral petitions (100K+ signatures)
SELECT
    petition_title,
    signature_count,
    status,
    created_date,
    has_government_response,
    reached_debate_threshold
FROM silver_petitions
WHERE signature_tier = 'Viral (100K+)'
ORDER BY signature_count DESC;
```

### Query Gold Layer
```sql
-- Overall performance by tier
SELECT * FROM gold_petition_metrics ORDER BY total_signatures DESC;

-- Closed vs Open petitions performance
SELECT
    status,
    SUM(petition_count) as total_petitions,
    SUM(total_signatures) as total_signatures,
    ROUND(AVG(avg_signatures), 0) as avg_signatures_per_petition
FROM gold_petition_metrics
GROUP BY status;
```

---

## 🗂️ **3. UNSTRUCTURED DATA & SCHEMA REGISTRY**

### Check JSON Structure
```sql
-- View topics (stored as JSONB)
SELECT
    petition_id,
    action,
    topics
FROM raw_petitions
WHERE topics::text != '[]'
LIMIT 5;

-- Extract JSON fields
SELECT
    petition_id,
    action,
    jsonb_array_length(topics) as topic_count,
    topics
FROM raw_petitions
WHERE jsonb_array_length(topics) > 0
LIMIT 10;
```

### Schema Registry (Data Contracts)

```sql
-- Get table schema
\d raw_petitions

-- Get column details
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'raw_petitions'
ORDER BY ordinal_position;

-- Check data types and nullability
SELECT
    column_name,
    data_type,
    COUNT(*) FILTER (WHERE column_name IS NULL) as null_count,
    COUNT(*) as total_count
FROM information_schema.columns c
CROSS JOIN raw_petitions p
WHERE table_name = 'raw_petitions'
GROUP BY column_name, data_type;
```

### Data Contract Validation

```sql
-- Check for contract violations

-- 1. Petition IDs must be unique
SELECT
    'Unique Petition IDs' as check_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT petition_id) as unique_ids,
    CASE WHEN COUNT(*) = COUNT(DISTINCT petition_id) THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM raw_petitions;

-- 2. Signature count must be positive
SELECT
    'Positive Signatures' as check_name,
    COUNT(*) as total_rows,
    SUM(CASE WHEN signature_count < 0 THEN 1 ELSE 0 END) as negative_count,
    CASE WHEN SUM(CASE WHEN signature_count < 0 THEN 1 ELSE 0 END) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM raw_petitions;

-- 3. Status must be valid
SELECT
    'Valid Status' as check_name,
    COUNT(*) as total_rows,
    SUM(CASE WHEN status NOT IN ('open', 'closed', 'rejected') THEN 1 ELSE 0 END) as invalid_count,
    CASE WHEN SUM(CASE WHEN status NOT IN ('open', 'closed', 'rejected') THEN 1 ELSE 0 END) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM raw_petitions;

-- 4. Created date must exist
SELECT
    'Created Date Exists' as check_name,
    COUNT(*) as total_rows,
    SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) as null_count,
    CASE WHEN SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM raw_petitions;
```

---

## ✓ **4. GREAT EXPECTATIONS (Data Quality)**

### Run Data Quality Checks

```bash
# From project root
uv run python -m data.quality.run_validations
```

### Check Validation Results

```sql
-- If you created a validation results table
CREATE TABLE IF NOT EXISTS data_quality_results (
    id SERIAL PRIMARY KEY,
    checkpoint_name VARCHAR(100),
    suite_name VARCHAR(100),
    expectation_type VARCHAR(100),
    column_name VARCHAR(100),
    success BOOLEAN,
    observed_value TEXT,
    expected_value TEXT,
    run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- View quality check results
SELECT
    checkpoint_name,
    COUNT(*) as total_checks,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 1) as pass_rate_pct
FROM data_quality_results
GROUP BY checkpoint_name;
```

### Manual Data Quality Checks

```sql
-- Completeness: Check for null values in critical fields
SELECT
    'petition_id' as column_name,
    COUNT(*) FILTER (WHERE petition_id IS NULL) as null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE petition_id IS NOT NULL) / COUNT(*), 2) as completeness_pct
FROM raw_petitions
UNION ALL
SELECT
    'action' as column_name,
    COUNT(*) FILTER (WHERE action IS NULL) as null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE action IS NOT NULL) / COUNT(*), 2) as completeness_pct
FROM raw_petitions
UNION ALL
SELECT
    'signature_count' as column_name,
    COUNT(*) FILTER (WHERE signature_count IS NULL) as null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE signature_count IS NOT NULL) / COUNT(*), 2) as completeness_pct
FROM raw_petitions;

-- Validity: Check date ranges
SELECT
    'Date Validity' as check_name,
    MIN(created_at) as earliest_petition,
    MAX(created_at) as latest_petition,
    CASE
        WHEN MIN(created_at::timestamp) < NOW() - INTERVAL '10 years' THEN '⚠️  WARNING: Very old data'
        WHEN MAX(created_at::timestamp) > NOW() THEN '❌ ERROR: Future dates'
        ELSE '✅ PASS'
    END as status
FROM raw_petitions;

-- Consistency: Check signature thresholds
SELECT
    'Debate Threshold Logic' as check_name,
    COUNT(*) as total,
    SUM(CASE WHEN signature_count >= 100000 AND debate_threshold_reached_at IS NULL THEN 1 ELSE 0 END) as inconsistent,
    CASE
        WHEN SUM(CASE WHEN signature_count >= 100000 AND debate_threshold_reached_at IS NULL THEN 1 ELSE 0 END) > 0
        THEN '⚠️  ' || SUM(CASE WHEN signature_count >= 100000 AND debate_threshold_reached_at IS NULL THEN 1 ELSE 0 END)::text || ' petitions with 100K+ sigs but no debate threshold'
        ELSE '✅ PASS'
    END as status
FROM raw_petitions;
```

---

## 🔄 **5. TRANSFORMATIONS (dbt)**

### View dbt Models
```bash
# List models
ls data/dbt/models/

# bronze/ - Raw data models
# silver/ - Cleaned & enriched
# gold/ - Business metrics & aggregations
```

### Run dbt Transformations
```bash
# Run all models
uv run dbt run --project-dir data/dbt --profiles-dir data/dbt

# Run specific model
uv run dbt run --models stg_petitions --project-dir data/dbt --profiles-dir data/dbt

# Test models
uv run dbt test --project-dir data/dbt --profiles-dir data/dbt
```

### Check dbt Artifacts
```bash
# View compiled SQL
cat data/dbt/target/compiled/ngo_platform/models/silver/stg_petitions.sql

# View run results
cat data/dbt/target/run_results.json | jq '.results[] | {model: .unique_id, status: .status}'
```

---

## 📈 **6. GRAFANA DASHBOARDS**

### Step 1: Add Postgres Data Source

1. Open Grafana: http://localhost:3000 (admin/admin)
2. Go to **Connections** → **Data sources** → **Add data source**
3. Select **PostgreSQL**
4. Configure:
   ```
   Host: dev-postgres-1:5432
   Database: petitions
   User: postgres
   Password: postgres
   TLS/SSL Mode: disable
   ```
5. Click **Save & test**

### Step 2: Create Dashboard Panels

#### Panel 1: Total Signatures Over Time
```sql
SELECT
    DATE_TRUNC('day', created_at::timestamp) as time,
    SUM(SUM(signature_count)) OVER (ORDER BY DATE_TRUNC('day', created_at::timestamp)) as cumulative_signatures
FROM raw_petitions
WHERE created_at IS NOT NULL
GROUP BY DATE_TRUNC('day', created_at::timestamp)
ORDER BY time;
```
**Visualization**: Time series line chart

#### Panel 2: Petition Status Distribution
```sql
SELECT
    status,
    COUNT(*) as count,
    SUM(signature_count) as signatures
FROM raw_petitions
GROUP BY status;
```
**Visualization**: Pie chart or Bar gauge

#### Panel 3: Top 10 Petitions (Bar Chart)
```sql
SELECT
    LEFT(action, 50) || '...' as petition,
    signature_count
FROM raw_petitions
ORDER BY signature_count DESC
LIMIT 10;
```
**Visualization**: Bar chart

#### Panel 4: Daily Petition Activity
```sql
SELECT
    DATE(created_at::timestamp) as date,
    COUNT(*) as new_petitions,
    SUM(signature_count) as total_signatures
FROM raw_petitions
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at::timestamp)
ORDER BY date;
```
**Visualization**: Time series

#### Panel 5: Single Stat - Total Petitions
```sql
SELECT COUNT(*) FROM raw_petitions;
```
**Visualization**: Stat (big number)

#### Panel 6: Single Stat - Total Signatures
```sql
SELECT SUM(signature_count) FROM raw_petitions;
```
**Visualization**: Stat (big number)

---

## ⚡ **7. PROMETHEUS METRICS**

### Access Prometheus
```bash
open http://localhost:9090
```

### Sample Queries

```promql
# Check which services are up
up

# Container memory usage
container_memory_usage_bytes{name=~"dev-.*"}

# Container CPU usage
rate(container_cpu_usage_seconds_total{name=~"dev-.*"}[5m])

# Postgres connections
pg_stat_database_numbackends{datname="petitions"}
```

### Create Alerts
```yaml
# example: alerts.yml
groups:
  - name: petition_pipeline
    rules:
      - alert: NoRecentPetitions
        expr: count(raw_petitions) == 0
        for: 1h
        annotations:
          summary: "No petitions in database"
```

---

## 🔍 **8. QUICK CHECKS - ONE-LINERS**

```bash
# Check if services are running
docker compose -f dev/docker-compose.yaml ps

# Check Postgres has data
docker exec dev-postgres-1 psql -U postgres -d petitions -c "SELECT COUNT(*) FROM raw_petitions;"

# Check Airflow DAGs
docker exec dev-airflow-webserver-1 airflow dags list

# Check logs for errors
docker logs dev-airflow-scheduler-1 | grep -i error | tail -20

# Check disk usage
docker system df

# Check container resource usage
docker stats --no-stream
```

---

## 🎯 **SUMMARY: Where Everything Lives**

| **What** | **Where** | **How to Access** |
|----------|-----------|-------------------|
| **Raw Data (Bronze)** | `raw_petitions` table | `docker exec -it dev-postgres-1 psql -U postgres -d petitions` |
| **Silver/Gold Tables** | `silver_petitions`, `gold_petition_metrics` | Same as above, run CREATE TABLE statements first |
| **Unstructured Data** | `topics` JSONB column in `raw_petitions` | Query with `jsonb_*` functions |
| **Schema/Contracts** | Database schema + validation queries | `\d raw_petitions` or information_schema queries |
| **Great Expectations** | `data/quality/` directory | Run `uv run python -m data.quality.run_validations` |
| **dbt Models** | `data/dbt/models/` | Run `uv run dbt run` |
| **Airflow Pipelines** | http://localhost:8080 | Login: airflow/airflow |
| **Grafana Dashboards** | http://localhost:3000 | Login: admin/admin, then create panels with SQL above |
| **Prometheus Metrics** | http://localhost:9090 | No login required |
| **MLflow Experiments** | http://localhost:5000 | No login required |

---

**Now you have EVERYTHING you need to see your data!** 🚀
