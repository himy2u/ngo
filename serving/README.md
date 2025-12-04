# Model Serving

## Options

| Tool | Use Case |
|------|----------|
| FastAPI | Simple REST endpoints, low latency |
| KServe | Kubernetes-native, autoscaling |
| BentoML | Packaging + serving + versioning |

## Rollback

Models registered in MLflow with stages:
- Staging → Production → Archived
- Version pinning in deployment configs
