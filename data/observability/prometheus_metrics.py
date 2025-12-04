#!/usr/bin/env python3
"""
Prometheus metrics for NGO data platform.
Instruments data pipelines with custom business and operational metrics.
"""

import time
import logging
from typing import Optional, Callable, Any
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    start_http_server,
    CollectorRegistry,
    push_to_gateway,
    REGISTRY,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===================================================================
# PIPELINE EXECUTION METRICS
# ===================================================================

# Counter: Total pipeline executions
pipeline_executions_total = Counter(
    "pipeline_executions_total",
    "Total number of pipeline executions",
    ["pipeline_name", "status"],  # status: success, failed, running
)

# Histogram: Pipeline execution duration
pipeline_duration_seconds = Histogram(
    "pipeline_duration_seconds",
    "Time taken to execute pipeline",
    ["pipeline_name"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],  # 10s to 1hr
)

# Gauge: Currently running pipelines
pipelines_running = Gauge(
    "pipelines_running", "Number of pipelines currently executing", ["pipeline_name"]
)

# ===================================================================
# DATA VOLUME METRICS
# ===================================================================

# Counter: Total rows processed
rows_processed_total = Counter(
    "rows_processed_total",
    "Total number of rows processed",
    ["pipeline_name", "layer"],  # layer: bronze, silver, gold
)

# Gauge: Current row count in tables
table_row_count = Gauge(
    "table_row_count", "Current number of rows in table", ["table_name", "schema"]
)

# Counter: Rows quarantined (failed quality checks)
rows_quarantined_total = Counter(
    "rows_quarantined_total",
    "Total number of rows that failed quality checks",
    ["pipeline_name", "reason"],
)

# ===================================================================
# DATA QUALITY METRICS
# ===================================================================

# Gauge: Data quality score (0-100)
data_quality_score = Gauge(
    "data_quality_score",
    "Data quality score for dataset (0-100)",
    ["table_name", "check_type"],  # check_type: completeness, validity, uniqueness
)

# Counter: Quality check failures
quality_checks_failed_total = Counter(
    "quality_checks_failed_total",
    "Total number of failed quality checks",
    ["table_name", "check_name"],
)

# ===================================================================
# API / DATA SOURCE METRICS
# ===================================================================

# Counter: API calls made
api_calls_total = Counter(
    "api_calls_total", "Total number of API calls", ["api_name", "status_code"]
)

# Histogram: API response time
api_response_duration_seconds = Histogram(
    "api_response_duration_seconds",
    "API response time",
    ["api_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

# Counter: API errors
api_errors_total = Counter(
    "api_errors_total", "Total number of API errors", ["api_name", "error_type"]
)

# ===================================================================
# DATABASE METRICS
# ===================================================================

# Summary: Database query execution time
db_query_duration_seconds = Summary(
    "db_query_duration_seconds",
    "Database query execution time",
    ["operation"],  # operation: select, insert, update, delete
)

# Counter: Database operations
db_operations_total = Counter(
    "db_operations_total", "Total number of database operations", ["operation", "status"]
)

# ===================================================================
# BUSINESS METRICS
# ===================================================================

# Gauge: Total petitions
total_petitions = Gauge("total_petitions", "Total number of petitions in system")

# Gauge: Total signatures
total_signatures = Gauge("total_signatures", "Total number of signatures across all petitions")

# Gauge: Viral petition rate (petitions with >100K signatures)
viral_petition_rate = Gauge(
    "viral_petition_rate", "Percentage of petitions that went viral (100K+ signatures)"
)

# Gauge: Government response rate
government_response_rate = Gauge(
    "government_response_rate", "Percentage of petitions with government response"
)

# ===================================================================
# SYSTEM INFO
# ===================================================================

platform_info = Info("ngo_platform", "NGO data platform version and environment info")

# Set platform info
platform_info.info({"version": "1.0.0", "environment": "dev", "python_version": "3.11"})

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================


@contextmanager
def track_pipeline_execution(pipeline_name: str):
    """
    Context manager to track pipeline execution.

    Usage:
        with track_pipeline_execution('ingest_petitions'):
            # Your pipeline code here
            pass
    """
    pipelines_running.labels(pipeline_name=pipeline_name).inc()
    start_time = time.time()

    try:
        yield
        duration = time.time() - start_time
        pipeline_duration_seconds.labels(pipeline_name=pipeline_name).observe(duration)
        pipeline_executions_total.labels(pipeline_name=pipeline_name, status="success").inc()
        logger.info(f"Pipeline '{pipeline_name}' completed successfully in {duration:.2f}s")

    except Exception as e:
        duration = time.time() - start_time
        pipeline_duration_seconds.labels(pipeline_name=pipeline_name).observe(duration)
        pipeline_executions_total.labels(pipeline_name=pipeline_name, status="failed").inc()
        logger.error(f"Pipeline '{pipeline_name}' failed after {duration:.2f}s: {e}")
        raise

    finally:
        pipelines_running.labels(pipeline_name=pipeline_name).dec()


def track_api_call(api_name: str):
    """
    Decorator to track API calls.

    Usage:
        @track_api_call('uk_parliament_api')
        def fetch_petitions():
            # API call code
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                api_response_duration_seconds.labels(api_name=api_name).observe(duration)
                api_calls_total.labels(api_name=api_name, status_code="200").inc()

                logger.info(f"API call to '{api_name}' succeeded in {duration:.2f}s")
                return result

            except Exception as e:
                duration = time.time() - start_time

                api_response_duration_seconds.labels(api_name=api_name).observe(duration)
                api_errors_total.labels(api_name=api_name, error_type=type(e).__name__).inc()

                logger.error(f"API call to '{api_name}' failed after {duration:.2f}s: {e}")
                raise

        return wrapper

    return decorator


@contextmanager
def track_db_operation(operation: str):
    """
    Context manager to track database operations.

    Usage:
        with track_db_operation('insert'):
            cursor.execute("INSERT INTO ...")
    """
    start_time = time.time()

    try:
        yield
        duration = time.time() - start_time
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        db_operations_total.labels(operation=operation, status="success").inc()

    except Exception as e:
        duration = time.time() - start_time
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        db_operations_total.labels(operation=operation, status="failed").inc()
        logger.error(f"Database {operation} operation failed: {e}")
        raise


def update_business_metrics(
    petition_count: int, signature_count: int, viral_count: int, response_count: int
):
    """Update business-level metrics."""
    total_petitions.set(petition_count)
    total_signatures.set(signature_count)

    if petition_count > 0:
        viral_rate = (viral_count / petition_count) * 100
        response_rate = (response_count / petition_count) * 100

        viral_petition_rate.set(viral_rate)
        government_response_rate.set(response_rate)

        logger.info(
            f"Business metrics updated: {petition_count} petitions, {signature_count:,} signatures"
        )


def start_metrics_server(port: int = 8000):
    """
    Start Prometheus metrics HTTP server.

    Args:
        port: Port to listen on (default: 8000)
    """
    try:
        start_http_server(port)
        logger.info(f"✅ Prometheus metrics server started on port {port}")
        logger.info(f"   Metrics available at: http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise


def push_metrics_to_gateway(gateway_url: str, job_name: str):
    """
    Push metrics to Prometheus Pushgateway.
    Useful for short-lived jobs.

    Args:
        gateway_url: Pushgateway URL (e.g., 'localhost:9091')
        job_name: Job identifier
    """
    try:
        push_to_gateway(gateway_url, job=job_name, registry=REGISTRY)
        logger.info(f"✅ Metrics pushed to {gateway_url} for job '{job_name}'")
    except Exception as e:
        logger.error(f"Failed to push metrics: {e}")


# ===================================================================
# EXAMPLE USAGE
# ===================================================================

if __name__ == "__main__":
    # Start metrics server
    start_metrics_server(port=8000)

    # Simulate pipeline execution
    with track_pipeline_execution("example_pipeline"):
        rows_processed_total.labels(pipeline_name="example_pipeline", layer="bronze").inc(150)

        data_quality_score.labels(table_name="petitions", check_type="completeness").set(98.5)

        update_business_metrics(
            petition_count=150, signature_count=18272337, viral_count=12, response_count=45
        )

        time.sleep(2)  # Simulate work

    logger.info("Example metrics generated successfully")
    logger.info("Visit http://localhost:8000/metrics to see metrics")

    # Keep server running
    try:
        import signal

        signal.pause()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")
