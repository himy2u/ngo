"""Prometheus metrics for data pipelines."""

import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Counters
records_ingested = Counter(
    "pipeline_records_ingested_total",
    "Total records ingested",
    ["pipeline", "source", "status"],  # status: valid, quarantined
)

pipeline_runs = Counter(
    "pipeline_runs_total",
    "Total pipeline runs",
    ["pipeline", "status"],  # status: success, failure
)

# Gauges
quarantine_depth = Gauge("pipeline_quarantine_depth", "Current quarantine table size", ["pipeline"])

data_freshness_seconds = Gauge(
    "pipeline_data_freshness_seconds", "Seconds since last data update", ["table"]
)

# Histograms
pipeline_duration = Histogram(
    "pipeline_duration_seconds",
    "Pipeline execution duration",
    ["pipeline"],
    buckets=[10, 30, 60, 120, 300, 600, 1800],
)

validation_duration = Histogram(
    "validation_duration_seconds",
    "Data validation duration",
    ["checkpoint"],
    buckets=[1, 5, 10, 30, 60, 120],
)


def track_pipeline(pipeline_name: str):
    """Decorator to track pipeline metrics."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                pipeline_runs.labels(pipeline=pipeline_name, status="success").inc()
                return result
            except Exception:
                pipeline_runs.labels(pipeline=pipeline_name, status="failure").inc()
                raise
            finally:
                duration = time.time() - start_time
                pipeline_duration.labels(pipeline=pipeline_name).observe(duration)

        return wrapper

    return decorator


def record_ingestion(pipeline: str, source: str, valid: int, quarantined: int):
    """Record ingestion metrics."""
    records_ingested.labels(pipeline=pipeline, source=source, status="valid").inc(valid)
    records_ingested.labels(pipeline=pipeline, source=source, status="quarantined").inc(quarantined)


def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")
