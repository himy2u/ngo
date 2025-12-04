# Data Platform

## Structure

- `dbt/` - Transformation models (Bronze → Silver → Gold)
- `airflow_dags/` - Orchestration DAGs
- `quality/` - Great Expectations suites

## Domains

Each domain owns their pipelines end-to-end:
- `petitions/` - Petition lifecycle data (Phase 1)
- `users/` - User profiles and activity (Phase 3)
