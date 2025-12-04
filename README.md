# NGO Data & AI Platform

Production-grade data platform for Change.org portfolio project.

## Structure

| Folder | Purpose |
|--------|---------|
| `docs/` | Architecture decisions, stakeholder maps, runbooks |
| `infra/` | Terraform + Kubernetes configs |
| `data/` | dbt models, Airflow DAGs, data quality |
| `feature_store/` | ML feature definitions |
| `ml/` | Training pipelines, model code, MLflow registry |
| `serving/` | Model serving (FastAPI, KServe, BentoML) |
| `vectorstore/` | Vector DB configs (Qdrant) |
| `flows/` | Temporal workflows |
| `orchestration/` | Ray distributed compute |
| `monitoring/` | Grafana, Prometheus, OpenSearch, WhyLabs |
| `contracts/` | Data contracts and schemas |
| `tests/` | Unit, integration, performance, chaos tests |
| `dev/` | Local development (docker-compose) |

## Quick Start

```bash
task bootstrap  # Install dependencies
task up         # Start local stack
task test       # Run all tests
```
