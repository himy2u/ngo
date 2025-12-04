# Machine Learning

## Structure

- `training/` - Training scripts and notebooks
- `pipelines/` - ML pipelines (feature engineering, training, evaluation)
- `models/` - Model code and configs
- `registry/` - MLflow model registry integration

## Model Lifecycle

1. Experiment in `training/`
2. Productionize in `pipelines/`
3. Register in MLflow → Staging → Production → Archived
