# 🚀 BUILD FROM SCRATCH - PHASE 1
> Production-ready data platform with comprehensive testing • FAANG patterns • 2025

---

## 📋 What You're Building

A **modern data platform** with:
- **Medallion Architecture** (Bronze/Silver/Gold + Fact/Dimension tables)
- **6-Layer Testing Strategy** (Unit → Integration → E2E → Performance)
- **dbt Semantic Layer** (single source of truth for metrics)
- **Unity Catalog patterns** (RBAC, lineage, data contracts)
- **Prometheus + Grafana** (infrastructure & business observability)
- **Streamlit dashboards** (interactive analytics)

**Data Flow**: UK Parliament API → MinIO (immutable) → Bronze → Silver → Gold → Dashboards

<details>
<summary><b>Why MinIO? (FAANG Pattern)</b></summary>

- 🔒 **Immutability**: Original API responses stored forever (audit trail)
- 🔄 **Replay capability**: If Postgres corrupted, replay from S3
- 📦 **Unstructured data**: JSON, PDFs, images (Postgres = structured only)
- 💰 **Cost**: Cheap storage for historical data (S3 < Postgres)
</details>

<details>
<summary><b>Why This Architecture?</b></summary>

| Problem | Without Platform | With Platform |
|---------|------------------|---------------|
| Manual data collection | 2-3 hrs/day, error-prone | Automated every 6 hours |
| No data history | Can't track trends | Historical data forever (MinIO) |
| Inconsistent metrics | "Which query is right?" | Single source of truth (dbt) |
| No monitoring | Pipelines fail silently | Alerts + dashboards |
| Breaking schema changes | Breaks all downstream | Data contracts enforce versioning |
| Untested code | Bugs in production | 6-layer testing strategy |
</details>

---

## 🧪 Testing Strategy (FAANG Standard)

**6 layers of testing at different pipeline stages:**

| Test Layer | What | When | Failure Action | Tool |
|------------|------|------|----------------|------|
| **1. Unit Tests** | Transformation logic | Pre-commit | Block commit | pytest |
| **2. Schema Tests** | Contract validation | Ingestion | Quarantine row | jsonschema |
| **3. Data Quality** | Null checks, ranges | Post-load | Alert + flag | Great Expectations |
| **4. dbt Tests** | Business rules | Post-transform | Fail pipeline | dbt test |
| **5. Integration** | End-to-end pipeline | Pre-deploy | Block deploy | pytest + Docker |
| **6. Performance** | Query latency | Nightly | Alert if >2s | Prometheus |

<details>
<summary><b>Detailed Testing Breakdown</b></summary>

### 1️⃣ Unit Tests (Pre-Commit)
**File**: `tests/unit/test_transformations.py`
```python
def test_classify_signature_tier():
    """Test signature tier classification logic."""
    assert classify_tier(500) == "Low"
    assert classify_tier(5000) == "Medium"
    assert classify_tier(50000) == "High"
    assert classify_tier(150000) == "Viral"

def test_calculate_quality_score():
    """Test data quality scoring."""
    row = {"action": "Ban X", "signature_count": 1000, "status": "open"}
    assert calculate_quality_score(row) == 100.0

    row_missing = {"action": None, "signature_count": -1}
    assert calculate_quality_score(row_missing) < 60.0
```

**Run**: `pytest tests/unit/ -v`
**Failure Action**: ❌ Block git commit via pre-commit hook

---

### 2️⃣ Schema Validation Tests (Ingestion)
**File**: `data/ingestion/validate_schema.py`
```python
from jsonschema import validate, ValidationError
from observability.prometheus_metrics import rows_quarantined_total

PETITION_SCHEMA_V1 = {
    "type": "object",
    "required": ["petition_id", "action", "signature_count"],
    "properties": {
        "petition_id": {"type": "integer"},
        "signature_count": {"type": "integer", "minimum": 0}
    }
}

def validate_and_load(records):
    valid = []
    quarantined = []

    for record in records:
        try:
            validate(instance=record, schema=PETITION_SCHEMA_V1)
            valid.append(record)
        except ValidationError as e:
            quarantined.append({"record": record, "error": str(e)})
            rows_quarantined_total.labels(
                pipeline_name='ingest_petitions',
                reason='schema_validation_failed'
            ).inc()

    # Load valid to bronze
    load_to_postgres(valid, table='bronze.petitions')

    # Load quarantined to separate table
    load_to_postgres(quarantined, table='bronze.quarantined_petitions')

    # Alert if >5% quarantined
    if len(quarantined) / len(records) > 0.05:
        send_alert_to_slack(f"⚠️ High quarantine rate: {len(quarantined)} rows")
```

**Run**: Automatically during ingestion
**Failure Action**:
- 📦 Quarantine bad rows to `bronze.quarantined_petitions`
- 📊 Increment Prometheus `rows_quarantined_total` metric
- 🚨 Alert if quarantine rate >5%

---

### 3️⃣ Data Quality Tests (Post-Load to Bronze)
**File**: `tests/data_quality/great_expectations/expectations.yml`
```yaml
expectations:
  - expectation_type: expect_column_values_to_not_be_null
    kwargs:
      column: petition_id

  - expectation_type: expect_column_values_to_be_between
    kwargs:
      column: signature_count
      min_value: 0
      max_value: 10000000

  - expectation_type: expect_column_values_to_be_in_set
    kwargs:
      column: status
      value_set: ["open", "closed", "rejected"]

  - expectation_type: expect_table_row_count_to_be_between
    kwargs:
      min_value: 100  # Expect at least 100 petitions
      max_value: 100000
```

**Run**:
```python
# data/scripts/run_quality_checks.py
import great_expectations as ge

df = ge.read_csv("bronze.petitions")
results = df.validate(expectation_suite="petition_suite")

if not results["success"]:
    # Log failures to governance table
    log_quality_failures(results, table="governance.data_quality_checks")

    # Update Prometheus metric
    data_quality_score.labels(
        table_name='bronze.petitions',
        check_type='completeness'
    ).set(results["statistics"]["success_percent"])

    # Alert if <90% pass
    if results["statistics"]["success_percent"] < 90:
        send_alert("🚨 Data quality below 90%")
```

**Failure Action**:
- 📝 Log failures to `governance.data_quality_checks` table
- 📊 Update `data_quality_score` Prometheus metric
- 🚨 Alert if success rate <90%
- ⏸️ Pause downstream pipelines until fixed

---

### 4️⃣ dbt Tests (Post-Transformation)
**File**: `data/dbt/models/silver/silver_petitions.yml`
```yaml
models:
  - name: silver_petitions
    columns:
      - name: petition_id
        tests:
          - unique
          - not_null

      - name: signature_count
        tests:
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: signature_tier
        tests:
          - accepted_values:
              values: ['Low', 'Medium', 'High', 'Viral']

      - name: _data_quality_score
        tests:
          - dbt_utils.expression_is_true:
              expression: "BETWEEN 0 AND 100"

    # Table-level tests
    tests:
      - dbt_utils.recency:
          datepart: day
          field: _ingested_at
          interval: 1  # Must have data from last 24 hours
```

**Run**: `uv run dbt test --project-dir data/dbt`

**Failure Action**:
- ❌ Fail pipeline (exit code 1)
- 📧 Send email alert to data team
- 🔄 Rollback gold layer update (keep previous materialization)
- 📊 Increment `quality_checks_failed_total` metric
- 📝 Log to `governance.data_quality_checks`

---

### 5️⃣ Integration Tests (End-to-End)
**File**: `tests/integration/test_full_pipeline.py`
```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer

@pytest.fixture(scope="session")
def test_infrastructure():
    """Spin up test containers."""
    with PostgresContainer("postgres:15") as pg, \
         MinioContainer("minio/minio:latest") as s3:
        yield {"postgres": pg, "minio": s3}

def test_end_to_end_pipeline(test_infrastructure):
    """Test: API → MinIO → Bronze → Silver → Gold."""

    # 1. Mock API data
    sample_petitions = [
        {"petition_id": 1, "action": "Test", "signature_count": 1000},
        {"petition_id": 2, "action": "Test2", "signature_count": 50000}
    ]

    # 2. Save to MinIO
    save_to_minio(sample_petitions, bucket="bronze")

    # 3. Load to Bronze
    load_to_postgres(sample_petitions, table="bronze.petitions")
    assert row_count("bronze.petitions") == 2

    # 4. Run dbt transformations
    run_dbt_command("run --select silver_petitions")
    assert row_count("silver.petitions") == 2

    # 5. Check Silver has derived columns
    result = query_db("SELECT signature_tier FROM silver.petitions WHERE petition_id=2")
    assert result[0]["signature_tier"] == "High"

    # 6. Run Gold aggregations
    run_dbt_command("run --select fact_petition_metrics")
    assert row_count("gold.fact_petition_metrics") > 0

def test_pipeline_idempotency():
    """Test: Running pipeline twice produces same result."""
    run_pipeline()
    result1 = query_db("SELECT COUNT(*) FROM gold.fact_petition_metrics")

    run_pipeline()  # Run again
    result2 = query_db("SELECT COUNT(*) FROM gold.fact_petition_metrics")

    assert result1 == result2  # Should be idempotent
```

**Run**: `pytest tests/integration/ -v --tb=short`

**Failure Action**:
- ❌ Block deployment to production
- 📧 Send alert to Slack #data-eng channel
- 🔄 Rollback to last known good commit
- 📝 Create incident ticket

---

### 6️⃣ Performance Tests (Nightly)
**File**: `tests/performance/test_query_performance.py`
```python
import time
from observability.prometheus_metrics import db_query_duration_seconds

def test_dashboard_query_performance():
    """Ensure dashboard queries complete in <2s."""

    query = """
        SELECT status, signature_tier,
               SUM(petition_count) as total
        FROM gold.fact_petition_metrics
        GROUP BY status, signature_tier
    """

    start = time.time()
    result = execute_query(query)
    duration = time.time() - start

    # Record to Prometheus
    db_query_duration_seconds.labels(operation='dashboard_query').observe(duration)

    # Alert if slow
    assert duration < 2.0, f"Query took {duration:.2f}s (expected <2s)"

def test_aggregation_performance():
    """Test dbt Gold layer builds in <60s."""

    start = time.time()
    run_dbt_command("run --select gold.*")
    duration = time.time() - start

    assert duration < 60, f"Gold layer took {duration:.2f}s (expected <60s)"
```

**Run**: Nightly via cron/Airflow
```python
# data/airflow_dags/nightly_tests_dag.py
from airflow import DAG
from airflow.operators.bash_operator import BashOperator

with DAG('nightly_performance_tests', schedule_interval='0 2 * * *') as dag:
    run_tests = BashOperator(
        task_id='run_performance_tests',
        bash_command='pytest tests/performance/ --html=report.html'
    )
```

**Failure Action**:
- 📊 Record to Prometheus (track degradation over time)
- 🚨 Alert if query >2s for 3 consecutive nights
- 🔍 Trigger EXPLAIN ANALYZE for slow queries
- 📝 Create performance investigation ticket

</details>

<details>
<summary><b>Test Orchestration (Airflow)</b></summary>

### Full Testing DAG
**File**: `data/airflow_dags/test_orchestration_dag.py`
```python
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

default_args = {
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': send_slack_alert
}

with DAG('data_pipeline_with_tests',
         schedule_interval='0 */6 * * *',  # Every 6 hours
         default_args=default_args) as dag:

    # Stage 1: Ingestion with schema validation
    ingest = PythonOperator(
        task_id='ingest_petitions',
        python_callable=validate_and_load  # Includes schema tests
    )

    # Stage 2: Data quality checks on Bronze
    quality_checks = PythonOperator(
        task_id='run_quality_checks',
        python_callable=run_great_expectations
    )

    # Stage 3: dbt transformations
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='uv run dbt run --project-dir data/dbt'
    )

    # Stage 4: dbt tests (business rules)
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='uv run dbt test --project-dir data/dbt',
        # If tests fail, don't update gold layer
        trigger_rule='all_success'
    )

    # Stage 5: Update metrics
    update_metrics = PythonOperator(
        task_id='update_prometheus_metrics',
        python_callable=update_business_metrics
    )

    # Pipeline flow with test gates
    ingest >> quality_checks >> dbt_run >> dbt_test >> update_metrics
```

**Failure Handling**:
```python
def send_slack_alert(context):
    """Called on any task failure."""
    task = context['task_instance']

    message = f"""
    🚨 Pipeline Failed

    Task: {task.task_id}
    DAG: {task.dag_id}
    Execution: {task.execution_date}

    Log: {task.log_url}
    """

    requests.post(SLACK_WEBHOOK, json={"text": message})

    # Also log to governance
    log_pipeline_failure(
        pipeline_name=task.dag_id,
        task_name=task.task_id,
        error=context['exception']
    )
```

</details>

---

## 🏗️ Architecture Clarifications (Important!)

<details>
<summary><b>Q1: What is `calculate_quality_score`? The example isn't clear.</b></summary>

**Answer**: It's a function that scores data quality (0-100) based on completeness and validity.

**Implementation** (`data/scripts/quality_score.py`):
```python
def calculate_quality_score(row: dict) -> float:
    """
    Calculate data quality score (0-100) based on completeness and validity.

    Scoring logic:
    - Start with 100 points
    - Deduct 20 points for each NULL required field
    - Deduct 10 points for each invalid value
    - Deduct 5 points for each missing optional field
    """
    score = 100.0

    # Required fields (20 points each)
    required_fields = ['petition_id', 'action', 'signature_count', 'status']
    for field in required_fields:
        if row.get(field) is None:
            score -= 20

    # Invalid values (10 points each)
    if row.get('signature_count', 0) < 0:
        score -= 10  # Signatures can't be negative

    if row.get('status') not in ['open', 'closed', 'rejected']:
        score -= 10  # Invalid status

    # Optional fields (5 points each)
    optional_fields = ['created_at', 'updated_at', 'topics']
    for field in optional_fields:
        if row.get(field) is None:
            score -= 5

    return max(0.0, score)  # Never below 0
```

**Examples**:

| Row Data | Quality Score | Reason |
|----------|--------------|--------|
| `{"petition_id": 1, "action": "Ban X", "signature_count": 1000, "status": "open", "created_at": "2024-01-01", "topics": ["health"]}` | **100.0** | All fields present and valid |
| `{"petition_id": 1, "action": "Ban X", "signature_count": 1000, "status": "open"}` | **85.0** | Missing 3 optional fields (-15) |
| `{"petition_id": 1, "action": None, "signature_count": 1000, "status": "open"}` | **80.0** | NULL in required field action (-20) |
| `{"petition_id": 1, "action": "Ban X", "signature_count": -5, "status": "invalid"}` | **70.0** | Negative signatures (-10) + invalid status (-10) + missing fields (-10) |
| `{"petition_id": 1, "action": None, "signature_count": -1, "status": None}` | **40.0** | Missing 3 required fields (-60) |

**Usage in Pipeline**:
```python
# During bronze → silver transformation
for row in bronze_petitions:
    quality_score = calculate_quality_score(row)

    if quality_score >= 80:
        # Load to silver (high quality)
        load_to_silver(row, quality_score=quality_score)
    elif quality_score >= 60:
        # Load to silver but flag for review
        load_to_silver(row, quality_score=quality_score, flag='needs_review')
    else:
        # Quarantine (too low quality)
        load_to_quarantine(row, quality_score=quality_score, reason='low_quality')
```

**Why This Matters**:
- **Data observability**: Track quality degradation over time
- **Downstream protection**: Don't pollute silver/gold with bad data
- **Alerting**: Alert if average quality drops below 90%
- **Business metrics**: "95% of our data has quality score >90"

</details>

<details>
<summary><b>Q2: Where is Bronze layer stored? MinIO or Postgres?</b></summary>

**Answer**: **BOTH** - this is a key FAANG pattern!

### Data Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UK PARLIAMENT API                         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ↓
    ┌───────────────────────────────────────────────────┐
    │  STEP 1: Save Raw JSON to MinIO (S3)              │
    │  ─────────────────────────────────────────────    │
    │  Location: s3://bronze/petitions_20241204.json    │
    │  Format: JSON (exactly as API returned it)        │
    │  Purpose: Immutable audit trail, replay source    │
    └───────────────┬───────────────────────────────────┘
                    │
                    ↓
    ┌───────────────────────────────────────────────────┐
    │  STEP 2: Parse + Load to Postgres Bronze          │
    │  ─────────────────────────────────────────────    │
    │  Location: postgres://petitions/bronze.petitions  │
    │  Format: Structured table with columns            │
    │  Purpose: Fast SQL queries, dbt transformations   │
    └───────────────┬───────────────────────────────────┘
                    │
                    ↓
    ┌───────────────────────────────────────────────────┐
    │  dbt: Bronze → Silver → Gold                      │
    │  ───────────────────────────────────────          │
    │  All in Postgres (silver.*, gold.*)               │
    └───────────────────────────────────────────────────┘
```

### Why Dual Storage?

| Storage Layer | MinIO (S3) | Postgres Bronze |
|---------------|------------|-----------------|
| **Purpose** | Immutable archive | Queryable structured data |
| **Format** | Raw JSON | Relational table |
| **Query Speed** | Slow (scan files) | Fast (indexed) |
| **Cost** | Cheap ($0.023/GB) | Expensive ($0.10/GB) |
| **Retention** | Forever (compliance) | 6-12 months (then archive) |
| **Use Case** | Audit trail, replay, ML training | dbt transforms, dashboards |
| **Example** | `{"petition_id": 1, "action": "Ban X", ...}` | `SELECT * FROM bronze.petitions WHERE id=1` |

### Real-World Scenario: Why This Matters

**Incident**: Someone accidentally runs `DELETE FROM bronze.petitions WHERE 1=1` 😱

**Recovery with dual storage**:
```bash
# 1. Bronze is gone from Postgres
SELECT COUNT(*) FROM bronze.petitions;
# Result: 0 rows

# 2. But raw data still in MinIO!
aws s3 ls s3://bronze/petitions/
# Result: 365 JSON files (one per day)

# 3. Replay from MinIO to rebuild Postgres bronze
python data/scripts/replay_from_s3.py --start-date 2024-01-01

# 4. Bronze restored in 10 minutes
SELECT COUNT(*) FROM bronze.petitions;
# Result: 150 rows ✅
```

**Without MinIO**: You lost all data. Game over. 🚨

</details>

<details>
<summary><b>Q3: In Databricks, does data stay in Parquet/Lakehouse or database tables?</b></summary>

**Answer**: **Data stays in Parquet files (Delta Lake format) on cloud storage (S3/ADLS)**

### Databricks Storage Pattern (Industry Standard 2025)

```
┌────────────────────────────────────────────────────────────┐
│         AZURE BLOB STORAGE / AWS S3 / GCS                  │
│                                                            │
│  abfss://data@mystorageaccount.dfs.core.windows.net/      │
│                                                            │
│  ├── bronze/                                               │
│  │   └── petitions/                                        │
│  │       ├── part-00000.parquet (1M rows)                  │
│  │       ├── part-00001.parquet (1M rows)                  │
│  │       └── _delta_log/                                   │
│  │           ├── 00000.json (transaction log)              │
│  │           └── 00001.json                                │
│  │                                                         │
│  ├── silver/                                               │
│  │   └── dim_petitions/                                    │
│  │       ├── part-00000.parquet                            │
│  │       └── _delta_log/                                   │
│  │                                                         │
│  └── gold/                                                 │
│      └── fact_petition_metrics/                            │
│          ├── date=2024-01-01/part-00000.parquet            │
│          ├── date=2024-01-02/part-00000.parquet            │
│          └── _delta_log/                                   │
└────────────────────────────────────────────────────────────┘
                        ↑
                        │
            ┌───────────┴──────────┐
            │   DATABRICKS         │
            │   ────────────       │
            │   • Reads Parquet    │
            │   • SQL queries work │
            │   • No data copy!    │
            └──────────────────────┘
```

### Key Insights

**1. Data is NOT in a traditional database**
```sql
-- This query in Databricks SQL...
SELECT * FROM bronze.petitions;

-- ...actually reads from:
abfss://data@myaccount.dfs.core.windows.net/bronze/petitions/*.parquet
```

**2. Why Parquet instead of Postgres?**

| Aspect | Parquet (Databricks) | Postgres |
|--------|---------------------|----------|
| **Scale** | Petabyte-scale | ~10TB max practical |
| **Cost** | $0.023/GB storage | $0.10/GB storage |
| **Query** | Spark (distributed) | Single-node SQL |
| **Compute** | Elastic (scale to 1000s nodes) | Fixed (scale up only) |
| **Schema evolution** | Easy (add columns) | ALTER TABLE locks |
| **ML integration** | Native (PySpark, MLflow) | Export to files first |

**3. Delta Lake = Parquet + ACID + Time Travel**

```python
# Delta Lake gives you ACID on Parquet files!
spark.sql("""
    DELETE FROM bronze.petitions
    WHERE signature_count < 0
""")
# This creates a new parquet file + transaction log entry
# Old parquet files kept for time travel

# Time travel (30 days default)
spark.sql("""
    SELECT * FROM bronze.petitions
    VERSION AS OF 10  -- Read version from 10 commits ago
""")
```

</details>

<details>
<summary><b>Q4: What's the use of ACID and Unity Catalog if data is in files?</b></summary>

**Answer**: **ACID and Unity Catalog work on files through Delta Lake's transaction log**

### How ACID Works on Files (Delta Lake Magic)

**Traditional Files (No ACID)** ❌:
```bash
# Two writers try to update same file
Writer A: Write part-00000.parquet (10 seconds)
Writer B: Write part-00000.parquet (10 seconds)
# Result: File corrupted or one write lost!
```

**Delta Lake (ACID on Files)** ✅:
```bash
# Each write creates new file + transaction log entry
Writer A:
  1. Writes: part-00001.parquet
  2. Commits to _delta_log/00001.json:
     {
       "add": {"path": "part-00001.parquet"},
       "timestamp": "2024-01-01T10:00:00Z",
       "operation": "WRITE"
     }

Writer B (happens simultaneously):
  1. Writes: part-00002.parquet
  2. Commits to _delta_log/00002.json:
     {
       "add": {"path": "part-00002.parquet"},
       "timestamp": "2024-01-01T10:00:01Z",
       "operation": "WRITE"
     }

# Result: Both writes succeed! No corruption.
```

### Unity Catalog on Files

**Unity Catalog = Metadata Layer on Top of Storage**

```
┌──────────────────────────────────────────────────────────┐
│                   UNITY CATALOG                          │
│                   (Metadata Store)                       │
│                                                          │
│  Catalog: ngo_platform_dev                               │
│  ├── Schema: bronze                                      │
│  │   └── Table: petitions                                │
│  │       • Owner: data_engineer@company.com              │
│  │       • PII Columns: [creator_name]  ← Tagged!        │
│  │       • Grants: READ → data_analyst role              │
│  │       • Location: abfss://.../bronze/petitions/       │
│  │       • Format: DELTA                                 │
│  │       • Schema: {petition_id: BIGINT, ...}            │
│  │       • Lineage: [uk_parliament_api] ← Source         │
│  │       • Created: 2024-01-01                           │
│  │       • Last Updated: 2024-12-04                      │
└──┬───────────────────────────────────────────────────────┘
   │
   │ Points to ↓
   │
┌──┴───────────────────────────────────────────────────────┐
│         AZURE STORAGE (Actual Data)                      │
│         abfss://.../bronze/petitions/                    │
│         ├── part-00000.parquet                           │
│         ├── part-00001.parquet                           │
│         └── _delta_log/                                  │
└──────────────────────────────────────────────────────────┘
```

### Unity Catalog Powers (Even on Files!)

**1. RBAC on Files**:
```sql
-- Grant permissions (Unity Catalog enforces)
GRANT SELECT ON TABLE bronze.petitions TO data_analyst;

-- When data_analyst runs this query:
SELECT * FROM bronze.petitions;

-- Unity Catalog:
-- 1. Checks: Does data_analyst have SELECT permission? ✅
-- 2. Checks: Any row-level security policies? Apply filters
-- 3. Redacts: PII columns (creator_name) → NULL
-- 4. Allows: Read from abfss://.../bronze/petitions/*.parquet
```

**2. Data Lineage (Across Files)**:
```sql
-- Lineage graph automatically tracked
uk_parliament_api
  → bronze.petitions (parquet)
    → silver.dim_petitions (parquet)
      → gold.fact_petition_metrics (parquet)
        → streamlit_dashboard.py
```

**3. PII Tagging (On Parquet Columns)**:
```sql
-- Tag PII in Unity Catalog
ALTER TABLE bronze.petitions
SET TAGS ('PII' = 'creator_name,email');

-- Now all queries automatically:
-- - Audit PII access
-- - Redact for non-privileged users
-- - Track compliance (GDPR, CCPA)
```

### Why This is Powerful

| Without Unity Catalog | With Unity Catalog |
|---------------------|-------------------|
| Files scattered across S3 | Centralized metadata catalog |
| No permission controls | RBAC on every table |
| Unknown data lineage | Automatic lineage tracking |
| Manual PII discovery | Automated PII tagging |
| No audit trail | Complete access logs |
| Schema in your head | Searchable data discovery |

</details>

<details>
<summary><b>Q5: If there was no structured data, would there be no dbt?</b></summary>

**Answer**: **Correct! dbt requires structured/semi-structured data (tables or Parquet)**

### dbt Requirements

**dbt works on** ✅:
- Relational databases (Postgres, MySQL, SQL Server)
- Data warehouses (Snowflake, BigQuery, Redshift)
- Lakehouse formats (Delta Lake, Iceberg) via Spark SQL
- Semi-structured (JSON columns, nested Parquet)

**dbt does NOT work on** ❌:
- Raw text files (CSV without schema)
- Unstructured documents (PDFs, Word docs)
- Images, videos, audio
- Raw logs (before parsing)
- Binary blobs

### What Happens Without Structured Data?

**Scenario 1: Only raw JSON files (no schema)**
```
data/
├── petition_001.json
├── petition_002.json
└── petition_003.json
```

**Problem**:
- dbt can't read arbitrary JSON files
- No SQL table to query
- No consistent schema

**Solution**:
```python
# FIRST: Create structure with ingestion pipeline
# data/ingestion/load_json_to_bronze.py

import json
import psycopg2

def load_json_files_to_bronze():
    """Convert raw JSON to structured Bronze table"""

    conn = psycopg2.connect("postgresql://...")
    cursor = conn.cursor()

    # Load all JSON files
    for json_file in Path("data/raw").glob("*.json"):
        with open(json_file) as f:
            data = json.load(f)

        # Insert into Bronze table (now structured!)
        cursor.execute("""
            INSERT INTO bronze.petitions
            (petition_id, action, signature_count, status, raw_json)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['id'],
            data['attributes']['action'],
            data['attributes']['signature_count'],
            data['attributes']['state'],
            json.dumps(data)  # Keep raw for audit
        ))

    conn.commit()

# NOW dbt can work!
# data/dbt/models/silver/stg_petitions.sql
SELECT
    petition_id,
    action,
    signature_count,
    CASE
        WHEN signature_count < 1000 THEN 'Low'
        WHEN signature_count < 10000 THEN 'Medium'
        ELSE 'High'
    END as signature_tier
FROM {{ source('bronze', 'petitions') }}
```

### Real-World Example: When dbt Doesn't Help

**Use Case**: Analyzing customer support emails

**Data**:
```
emails/
├── email_001.txt
├── email_002.txt
└── email_003.txt
```

**Step 1: Python/Spark for unstructured → structured**
```python
# BEFORE dbt: Parse emails into structure
import spacy

nlp = spacy.load("en_core_web_sm")

def parse_email(email_text):
    """Extract structure from unstructured email"""
    doc = nlp(email_text)

    return {
        "email_id": generate_id(),
        "sender": extract_sender(email_text),
        "sentiment": doc.sentiment,  # Negative/Neutral/Positive
        "entities": [ent.text for ent in doc.ents],  # Organizations, people
        "word_count": len(doc),
        "topics": classify_topics(doc),  # Billing, Technical, etc
        "raw_text": email_text
    }

# Load to Bronze table
for email_file in emails:
    parsed = parse_email(email_file.read_text())
    insert_into_bronze(parsed)
```

**Step 2: NOW dbt can transform**
```sql
-- data/dbt/models/silver/stg_email_metrics.sql
SELECT
    DATE(created_at) as date,
    topic,
    sentiment,
    COUNT(*) as email_count,
    AVG(word_count) as avg_length
FROM {{ source('bronze', 'emails') }}
GROUP BY 1, 2, 3
```

### The Pattern

```
Unstructured Data
  ↓
[Python/Spark/Custom Code]  ← Extract structure
  ↓
Bronze (Structured Tables)
  ↓
[dbt]  ← Clean, transform, aggregate
  ↓
Silver → Gold
```

**Key Insight**: dbt is a transformation tool, not an extraction tool.

</details>

---

## 🛠️ Setup Steps

**Total Time**: ~20 minutes

### Prerequisites

<details>
<summary>Install software (macOS)</summary>

```bash
# Install tools
brew install git docker colima task python@3.11

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Start Docker
colima start --cpu 4 --memory 8
```

**Verify**:
```bash
docker --version && task --version && uv --version && python3 --version
```
</details>

---

### STEP 1: Project Setup (5 min)

<details>
<summary>Initialize project structure</summary>

```bash
# Create project
mkdir -p ~/projects/ngo-platform && cd ~/projects/ngo-platform
git init

# Create FAANG structure
mkdir -p {data/{airflow_dags,dbt,scripts,ingestion,observability},dev,docs,contracts,monitoring/{prometheus,grafana},tests/{unit,integration,performance},dashboards}

# Create Taskfile.yml
cat > Taskfile.yml << 'EOF'
version: '3'
tasks:
  up:
    desc: Start all services
    cmds:
      - docker compose -f dev/docker-compose.yaml up -d
  down:
    desc: Stop services
    cmds:
      - docker compose -f dev/docker-compose.yaml down
  status:
    desc: Check status
    cmds:
      - docker compose -f dev/docker-compose.yaml ps
  test:
    desc: Run all tests
    cmds:
      - pytest tests/ -v
EOF

# Initialize Python
cat > pyproject.toml << 'EOF'
[project]
name = "ngo-platform"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "psycopg2-binary>=2.9.9",
    "requests>=2.31.0",
    "prometheus-client>=0.19.0",
    "databricks-sql-connector>=3.0.0",
    "boto3>=1.34.0",
    "streamlit>=1.31.0",
    "plotly>=5.18.0",
    "great-expectations>=0.18.0",
    "pytest>=7.4.0",
    "jsonschema>=4.20.0",
]
EOF

uv sync
```
</details>

---

### STEP 2: Database Schema + RBAC (3 min)

<details>
<summary>Naming conventions & schema</summary>

**FAANG Naming Standards**:
| Pattern | Example | Purpose |
|---------|---------|---------|
| `bronze.*` | `bronze.petitions` | Raw data layer |
| `silver.dim_*` | `silver.dim_petitions` | Cleaned dimensions |
| `gold.fact_*` | `gold.fact_petition_metrics` | Business facts |
| `_column` | `_ingested_at`, `_quality_score` | System metadata |

**File**: `data/scripts/unity_catalog_setup.sql` (already exists!)

**What it does**:
- Creates schemas: `bronze`, `silver`, `gold`, `governance`
- Creates 5 roles with RBAC
- Enables row-level security
- Creates governance tables (lineage, access log, PII tags)
</details>

<details>
<summary>Data contracts</summary>

**Create**: `contracts/schemas/petitions_v1.yaml`
```yaml
version: 1
table: bronze.petitions
schema:
  fields:
    - name: petition_id
      type: BIGINT
      nullable: false
    - name: signature_count
      type: BIGINT
      constraints:
        - check: "signature_count >= 0"
breaking_changes:
  - Removing columns
  - Changing column types
  - Adding NOT NULL to existing columns
```

**Breaking Change Workflow**:
1. Increment `_schema_version` column
2. Dual-write for 1 sprint
3. Update dbt to handle both versions
4. Deprecate old schema
</details>

---

### STEP 3: Docker Services (3 min)

**File**: `dev/docker-compose.yaml` ✅ (already configured)

**Services** (6 total):
```
postgres, postgres-exporter, minio, airflow (x2), prometheus, grafana
```

```bash
# Start
task up

# Wait 2 minutes, then verify
task status
# Expected: All services "Up (healthy)"
```

---

### STEP 4: Initialize Database (3 min)

```bash
# Create database
docker exec dev-postgres-1 psql -U postgres -c "CREATE DATABASE petitions;"

# Run Unity Catalog setup (schemas + RBAC + governance)
docker cp data/scripts/unity_catalog_setup.sql dev-postgres-1:/tmp/
docker exec dev-postgres-1 psql -U postgres -d petitions -f /tmp/unity_catalog_setup.sql

# Verify
docker exec dev-postgres-1 psql -U postgres -d petitions -c "\dn"
# Expected: bronze, silver, gold, governance
```

<details>
<summary>RBAC verification</summary>

```bash
docker exec dev-postgres-1 psql -U postgres -d petitions -c "
SELECT rolname FROM pg_roles
WHERE rolname IN ('data_engineer', 'data_analyst', 'read_only_user');"
```

**Permissions**:
- `data_engineer`: Write bronze/silver
- `data_analyst`: Read silver/gold only
- `read_only_user`: Read gold (dashboards)
</details>

---

### STEP 5: Load Data + Tests (2 min)

```bash
# Load with schema validation + quality checks
ENABLE_METRICS_SERVER=true python data/scripts/load_data.py
```

**What happens**:
1. ✅ Schema validation (quarantine bad rows)
2. ✅ Load to `bronze.petitions`
3. ✅ Run Great Expectations quality checks
4. ✅ Update Prometheus metrics

<details>
<summary>Verify data in all layers</summary>

```bash
docker exec dev-postgres-1 psql -U postgres -d petitions -c "
SELECT 'Bronze' as layer, COUNT(*) FROM bronze.petitions
UNION ALL SELECT 'Silver', COUNT(*) FROM silver.petitions
UNION ALL SELECT 'Gold', COUNT(*) FROM gold.petition_metrics;"

# Expected: Bronze=150, Silver=150, Gold=4
```
</details>

---

### STEP 6: dbt Transformations + Tests (3 min)

<details>
<summary>What dbt does (layer-by-layer)</summary>

```
bronze.petitions (raw)
    ↓
silver.dim_petitions (cleaned)
    - Null handling: COALESCE(action, 'Unknown')
    - Derived: signature_tier, _quality_score
    - Deduplication: ROW_NUMBER()
    ↓
gold.fact_petition_metrics (aggregated)
    - Grain: status × signature_tier
    - Metrics: COUNT, SUM, AVG
```
</details>

**Run transformations + tests**:
```bash
# Transform
uv run dbt run --project-dir data/dbt --profiles-dir data/dbt

# Run dbt tests (unique, not_null, accepted_values)
uv run dbt test --project-dir data/dbt --profiles-dir data/dbt

# Expected: All tests pass
```

**If tests fail**:
- ❌ Pipeline fails (exit code 1)
- 🚨 Alert sent to Slack
- 📝 Logged to `governance.data_quality_checks`

---

### STEP 7: Verify Tests Ran (1 min)

```bash
# Check governance table for test results
docker exec dev-postgres-1 psql -U postgres -d petitions -c "
SELECT check_name, status, error_message, checked_at
FROM governance.data_quality_checks
ORDER BY checked_at DESC
LIMIT 5;"

# Check Prometheus metrics
curl http://localhost:8000/metrics | grep quality_checks_failed_total
```

---

### STEP 8: Access Dashboards (1 min)

**Grafana** (auto-provisioned):
```bash
open http://localhost:3000  # admin/admin
```
Dashboards: Petition Analytics, Infrastructure Monitoring

**Streamlit**:
```bash
streamlit run dashboards/petition_analytics.py
```

**Prometheus**:
```bash
open http://localhost:9090
# Query: pipeline_duration_seconds
# Alerts: http://localhost:9090/alerts
```

---

## 🎓 Understanding What You Built

<details>
<summary><b>Medallion Architecture</b></summary>

| Layer | Purpose | Grain | Mutability |
|-------|---------|-------|------------|
| **Bronze** | Raw from API | 1 row = 1 API response | Immutable (append-only) |
| **Silver** | Cleaned dimensions | 1 row = 1 petition (current) | SCD Type 2 |
| **Gold** | Pre-aggregated facts | status × tier × date | Rebuilt daily |

**Silver Transformations**:
- Remove duplicates
- Handle nulls: `COALESCE(title, 'Unknown')`
- Derive: `signature_tier`, `_quality_score`
- Filter invalid: `WHERE signature_count >= 0`

**Gold Aggregations**:
- Grain: Daily × Status × Signature Tier
- Metrics: COUNT, SUM, AVG
- Pre-calculated for dashboards
</details>

<details>
<summary><b>Why `_underscore` Prefix?</b></summary>

Columns with `_` = **system metadata** (Airbnb/Uber pattern):
- `_ingested_at` - Load timestamp
- `_quality_score` - 0-100 quality score
- `_schema_version` - Contract version
- `_valid_from`, `_valid_to` - SCD Type 2

**Benefit**: `SELECT * EXCEPT (_*)` excludes metadata
</details>

<details>
<summary><b>dbt Semantic Layer</b></summary>

**Problem**: 5 people write 5 different "viral_rate" queries

**Solution**: Define metrics once
```yaml
metrics:
  - name: viral_petition_rate
    type: ratio
    numerator: petitions_100k_plus
    denominator: total_petitions
```

**Used by**: Grafana, Streamlit, Power BI, Tableau (all get same answer)
</details>

<details>
<summary><b>Testing Pyramid</b></summary>

```
        /\
       /E2E\      ← 5 tests (full pipeline, slow)
      /------\
     /Integra\   ← 20 tests (dbt models, medium)
    /----------\
   /   Unit     \ ← 100 tests (functions, fast)
  /--------------\
```

**Run order**:
1. Unit (pre-commit) - fast feedback
2. Schema (ingestion) - catch bad data early
3. Quality (post-load) - validate bronze
4. dbt tests (post-transform) - business rules
5. Integration (pre-deploy) - end-to-end verification
6. Performance (nightly) - track degradation
</details>

---

## 🆕 How to Extend

<details>
<summary><b>Add New Data Source</b></summary>

**Example**: Twitter API

1. **Define Contract**: `contracts/schemas/tweets_v1.yaml`
2. **Create Table**: `bronze.tweets`
3. **Write Ingestion**: `data/ingestion/fetch_tweets.py` (with schema validation)
4. **Create dbt Model**: `data/dbt/models/silver/stg_tweets.sql`
5. **Add Tests**: Unit + dbt tests
6. **Add to Airflow**: `data/airflow_dags/ingest_tweets_dag.py`
</details>

<details>
<summary><b>Add New dbt Model</b></summary>

**Example**: `gold.fact_daily_summary`

1. **Create Model**: `data/dbt/models/gold/fact_daily_summary.sql`
2. **Add Tests**: `fact_daily_summary.yml` (unique, not_null, range checks)
3. **Run**: `uv run dbt run --select fact_daily_summary`
4. **Test**: `uv run dbt test --select fact_daily_summary`
</details>

<details>
<summary><b>Add New Test</b></summary>

**Unit Test**:
```python
# tests/unit/test_transforms.py
def test_signature_tier():
    assert classify_tier(500) == "Low"
```

**Integration Test**:
```python
# tests/integration/test_pipeline.py
def test_end_to_end():
    load_data() >> run_dbt() >> verify_gold()
```

**Performance Test**:
```python
# tests/performance/test_queries.py
def test_dashboard_query_under_2s():
    duration = time_query("SELECT * FROM gold.metrics")
    assert duration < 2.0
```
</details>

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 5432 allocated | `lsof -i :5432 && kill -9 <PID>` |
| Tests failing | Check `governance.data_quality_checks` table |
| Grafana no data | Wait 5 min for load, check `task status` |
| dbt test fails | See dbt docs: `uv run dbt docs generate && dbt docs serve` |
| Services crash | `docker compose down -v && task up` |

---

## ✅ Success Checklist

- [ ] All 6 Docker containers healthy
- [ ] Data: Bronze (150), Silver (150), Gold (4)
- [ ] Unit tests pass: `pytest tests/unit/`
- [ ] dbt tests pass: `uv run dbt test`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] RBAC verified (5 roles)
- [ ] Grafana shows 2 dashboards
- [ ] Prometheus metrics exposed
- [ ] Data contracts defined
- [ ] Quality checks logged to governance table

**All checked?** 🎉 **Production-ready with comprehensive testing!**

---

## 🚀 Next Steps (Phase 2)

1. **Real-time**: Kafka + Flink streaming
2. **ML**: Predict viral petitions
3. **Cloud**: Deploy to Azure Databricks
4. **Scale**: 10M+ rows, multiple teams
5. **Advanced Testing**: Chaos engineering, load testing

---

**Total Time**: ~20 minutes
**FAANG Patterns**: Medallion, Semantic Layer, Unity Catalog, Observability-first, 6-Layer Testing
**Ready for**: 1-10M rows, production workloads

🚀 **Go build something amazing!**
