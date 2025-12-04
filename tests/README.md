# Tests

## Structure

| Folder | What | When |
|--------|------|------|
| `unit/` | Pure functions, no I/O | Every PR |
| `integration/` | DB, API, cross-service | Every PR |
| `performance/` | Latency, throughput benchmarks | Nightly |
| `chaos/` | Failure injection, resilience | Weekly |

## Running

```bash
task test:unit         # Fast, local
task test:integration  # Requires docker-compose
task test:performance  # Benchmark against baseline
task test:chaos        # Inject failures
task test              # All of the above
```

## Tools

- pytest + pytest-cov
- testcontainers (integration)
- pytest-benchmark (performance)
- Custom chaos fixtures
