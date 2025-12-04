"""Airflow DAG: Ingest petitions from UK Parliament API."""

import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "ngo-platform",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


def fetch_petitions(**context):
    """Fetch petitions from API with metrics and alerts."""
    from data.ingestion.fetch_petitions import PetitionIngester
    from data.monitoring.alerts import alerter
    from data.monitoring.metrics import record_ingestion

    run_id = context["run_id"]
    start_time = time.time()

    try:
        ingester = PetitionIngester()
        result = ingester.run(pages=5, run_id=run_id)

        # Record metrics
        record_ingestion(
            pipeline="ingest_petitions",
            source="uk_parliament_api",
            valid=result["valid_count"],
            quarantined=result["quarantine_count"],
        )

        # Check quarantine rate
        total = result["valid_count"] + result["quarantine_count"]
        if total > 0:
            quarantine_rate = result["quarantine_count"] / total
            if quarantine_rate > 0.05:
                alerter.high_quarantine_rate("ingest_petitions", quarantine_rate, 0.05)
                raise ValueError(f"High quarantine rate: {quarantine_rate:.1%}")

        # Success alert
        duration = time.time() - start_time
        alerter.pipeline_success("ingest_petitions", duration, result["valid_count"])

        context["ti"].xcom_push(key="ingestion_result", value=result)
        return result

    except Exception as e:
        alerter.pipeline_failure("ingest_petitions", str(e))
        raise


def generate_user_events(**context):
    """Generate synthetic user events."""
    from data.ingestion.generate_events import EventGenerator
    from data.monitoring.metrics import record_ingestion

    run_id = context["run_id"]
    petition_ids = list(range(1, 101))

    generator = EventGenerator()
    result = generator.run(petition_ids=petition_ids, events_per_petition=20, run_id=run_id)

    record_ingestion(
        pipeline="generate_events",
        source="synthetic",
        valid=result["event_count"],
        quarantined=0,
    )

    return result


def run_quality_checks(**context):
    """Run Great Expectations validations."""
    from data.monitoring.alerts import alerter

    # Placeholder - in production, run GE checkpoints
    # from data.quality.run_validations import run_checkpoint
    # result = run_checkpoint("bronze_checkpoint")

    result = {"status": "passed", "failed_expectations": []}

    if result.get("failed_expectations"):
        alerter.data_quality_failure("bronze_checkpoint", result["failed_expectations"])
        raise ValueError("Quality checks failed")

    return result


with DAG(
    dag_id="ingest_petitions",
    default_args=default_args,
    description="Ingest petitions from UK Parliament API",
    schedule_interval="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ingestion", "petitions", "bronze"],
) as dag:
    t_fetch = PythonOperator(
        task_id="fetch_petitions",
        python_callable=fetch_petitions,
    )

    t_generate = PythonOperator(
        task_id="generate_user_events",
        python_callable=generate_user_events,
    )

    t_quality = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks,
    )

    t_fetch >> t_generate >> t_quality
