# Local Development

## Quick Start

```bash
task bootstrap  # One-time setup
task up         # Start all services
task down       # Stop all services
```

## Services

docker-compose starts:
- Postgres (source DB simulation)
- Kafka (streaming)
- MinIO (S3-compatible storage)
- Airflow (orchestration)
- MLflow (experiment tracking)
- Qdrant (vector DB)
- Prometheus + Grafana (monitoring)

## Profiles

```bash
task up              # Full stack
task up:minimal      # Postgres + MinIO only
task up:ml           # Add MLflow + Ray
```
