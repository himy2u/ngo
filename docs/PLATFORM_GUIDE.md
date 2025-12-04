# NGO Data Platform - Complete User Guide

## 🚀 Quick Access

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Airflow** | http://localhost:8080 | `airflow` / `airflow` | Pipeline orchestration |
| **Grafana** | http://localhost:3000 | `admin` / `admin` | Metrics & dashboards |
| **MLflow** | http://localhost:5000 | None | ML experiment tracking |
| **MinIO Console** | http://localhost:9001 | `minioadmin` / `minioadmin` | Object storage UI |
| **Prometheus** | http://localhost:9090 | None | Metrics database |
| **Qdrant** | http://localhost:6333 | None | Vector database API |

## 📊 Part 1: Running the Data Pipeline

### Step 1: Access Airflow UI
```bash
open http://localhost:8080
# Login: airflow / airflow
```

### Step 2: View Available DAGs
1. Click on **DAGs** in the left sidebar
2. You should see: `ingest_petitions`
3. Click the toggle to **unpause** the DAG (if paused)

###  Step 3: Trigger a Pipeline Run
```bash
# Option A: From UI
# Click the "play" button next to the DAG name

# Option B: From CLI
docker exec dev-airflow-webserver-1 airflow dags trigger ingest_petitions
```

### Step 4: Monitor Execution
1. Click on the DAG name to see the Graph view
2. Watch tasks turn from **queued** → **running** → **success**
3. Click on any task to see logs

### Step 5: Check Logs
```bash
# View DAG run logs
docker exec dev-airflow-webserver-1 airflow dags list-runs -d ingest_petitions

# View task logs
docker exec dev-airflow-webserver-1 airflow tasks logs ingest_petitions fetch_petitions <date>
```

## 🗄️ Part 2: Querying the Data

### Connect to Postgres
```bash
# From your machine
docker exec -it dev-postgres-1 psql -U postgres -d petitions

# Or use a SQL client:
# Host: localhost
# Port: 5432
# Database: petitions
# User: postgres
# Password: postgres
```

### Sample Queries
```sql
-- See total petitions loaded
SELECT COUNT(*), SUM(signature_count) as total_signatures
FROM raw_petitions;

-- Top 10 petitions by signatures
SELECT
    petition_id,
    action,
    signature_count,
    status,
    created_at
FROM raw_petitions
ORDER BY signature_count DESC
LIMIT 10;

-- Petitions by status
SELECT
    status,
    COUNT(*) as count,
    SUM(signature_count) as total_signatures
FROM raw_petitions
GROUP BY status
ORDER BY count DESC;

-- Recent petitions (last 30 days)
SELECT
    action,
    signature_count,
    created_at
FROM raw_petitions
WHERE created_at > NOW() - INTERVAL '30 days'
ORDER BY signature_count DESC
LIMIT 20;
```

## 📈 Part 3: Setting Up Grafana Dashboards

### Step 1: Add Postgres Data Source
```bash
open http://localhost:3000
# Login: admin / admin
```

1. Go to **Connections** → **Data Sources**
2. Click **Add data source**
3. Select **PostgreSQL**
4. Configure:
   - **Host**: `dev-postgres-1:5432`
   - **Database**: `petitions`
   - **User**: `postgres`
   - **Password**: `postgres`
   - **TLS/SSL Mode**: `disable`
5. Click **Save & Test**

### Step 2: Create Your First Dashboard
1. Go to **Dashboards** → **New** → **New Dashboard**
2. Click **Add visualization**
3. Select your Postgres data source
4. Use SQL query:
   ```sql
   SELECT
     status,
     COUNT(*) as count
   FROM raw_petitions
   GROUP BY status
   ```
5. Choose visualization type (Pie chart, Bar chart, etc.)
6. Click **Apply**

### Example Dashboard Panels

#### Panel 1: Total Signatures Over Time
```sql
SELECT
    DATE_TRUNC('day', created_at) as time,
    SUM(signature_count) as signatures
FROM raw_petitions
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY time
ORDER BY time
```
**Visualization**: Time series

#### Panel 2: Petition Status Distribution
```sql
SELECT
    status,
    COUNT(*) as count
FROM raw_petitions
GROUP BY status
```
**Visualization**: Pie chart

#### Panel 3: Top Petitions
```sql
SELECT
    action as petition,
    signature_count
FROM raw_petitions
ORDER BY signature_count DESC
LIMIT 10
```
**Visualization**: Bar gauge

## 🔍 Part 4: Monitoring Pipeline Health

### View Prometheus Metrics
```bash
open http://localhost:9090
```

1. Go to **Graph**
2. Try these queries:
   - `up` - Show which services are running
   - `process_cpu_seconds_total` - CPU usage
   - `process_resident_memory_bytes` - Memory usage

### Create Alerts in Grafana
1. In Grafana, go to **Alerting** → **Alert rules**
2. Click **New alert rule**
3. Example: Alert when no petitions ingested in last hour
   ```sql
   SELECT COUNT(*)
   FROM raw_petitions
   WHERE ingested_at > NOW() - INTERVAL '1 hour'
   ```
4. Set threshold: `< 1`
5. Configure notification channel (Slack, Email, etc.)

## 🤖 Part 5: ML Experiment Tracking

### Access MLflow
```bash
open http://localhost:5000
```

### Log an Experiment (Example)
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("petition_classification")

with mlflow.start_run():
    # Your ML code here
    mlflow.log_param("model_type", "random_forest")
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_artifact("model.pkl")
```

## 📦 Part 6: Object Storage (MinIO)

### Access MinIO Console
```bash
open http://localhost:9001
# Login: minioadmin / minioadmin
```

### Create Buckets
1. Click **Buckets** → **Create Bucket**
2. Create these buckets:
   - `raw-data` - For ingested petition JSONs
   - `processed-data` - For transformed data
   - `ml-artifacts` - For ML models
   - `mlflow` - For MLflow artifacts

### Upload/Download Files
```bash
# Install MinIO client
brew install minio/stable/mc

# Configure
mc alias set local http://localhost:9000 minioadmin minioadmin

# Upload file
mc cp data/raw/petitions_*.json local/raw-data/

# List files
mc ls local/raw-data
```

## 🔄 Part 7: Running dbt Transformations

### Run dbt Models
```bash
# From your machine
uv run dbt run --project-dir data/dbt --profiles-dir data/dbt

# Or from Airflow
# Add a dbt task to your DAG (already configured)
```

### View dbt Documentation
```bash
uv run dbt docs generate --project-dir data/dbt --profiles-dir data/dbt
uv run dbt docs serve --project-dir data/dbt --profiles-dir data/dbt
# Opens at http://localhost:8080
```

## 🛠️ Part 8: Development Workflow

### Making Changes
```bash
# 1. Create feature branch
git checkout -b feat/your-feature

# 2. Make changes to code

# 3. Test locally
task test

# 4. Run linters
task lint

# 5. Commit with conventional commits
git commit -m "feat: add new feature"

# 6. Push and create PR
git push -u origin feat/your-feature
```

### Adding a New DAG
1. Create file in `data/airflow_dags/your_dag.py`
2. Wait ~30 seconds for Airflow to pick it up
3. Refresh Airflow UI
4. Your DAG should appear

### Adding a New dbt Model
1. Create SQL file in `data/dbt/models/`
2. Add tests in `.yml` file
3. Run: `uv run dbt run --models your_model`
4. Test: `uv run dbt test --models your_model`

## 🔒 Part 9: Secrets Management (Vault)

### Access Vault
```bash
# Vault is running at http://localhost:8200
# Dev Root Token: root

# Set token
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root'

# Store a secret
vault kv put secret/data/api-keys change_org_api_key=your-key-here

# Read a secret
vault kv get secret/data/api-keys
```

## 📊 Part 10: Common Tasks

### Restart All Services
```bash
task down && task up
```

### View All Container Logs
```bash
task logs
```

### Check Service Health
```bash
docker compose -f dev/docker-compose.yaml ps
```

### Clean Everything
```bash
task down:clean  # Removes volumes too
```

### Run Tests
```bash
task test:unit          # Fast unit tests
task test:integration   # Integration tests (requires docker)
task test               # All tests
```

## 🐛 Troubleshooting

### DAG Not Appearing?
```bash
# Check logs
docker logs dev-airflow-webserver-1 | grep -i error

# Restart Airflow
docker compose -f dev/docker-compose.yaml restart airflow-webserver
```

### Can't Connect to Postgres?
```bash
# Check it's running
docker ps | grep postgres

# Test connection
docker exec dev-postgres-1 pg_isready -U postgres
```

### Grafana Dashboard Not Loading Data?
1. Check data source connection (Save & Test)
2. Verify database has data: `SELECT COUNT(*) FROM raw_petitions;`
3. Check query syntax in panel

### Out of Memory?
```bash
# Check resources
docker stats

# Increase Colima resources
colima stop
colima start --cpu 6 --memory 12
```

## 🎯 Next Steps

1. **Set up scheduled DAG runs** - Edit DAG `schedule_interval`
2. **Add more data sources** - Create new ingestion DAGs
3. **Build ML models** - Use MLflow for tracking
4. **Create production dashboards** - Share Grafana dashboards
5. **Set up alerts** - Configure alerting for failures
6. **Deploy to production** - Use Terraform configs in `infra/`

---

**Questions?** Check the main README or create an issue!
