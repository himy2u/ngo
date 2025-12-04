#!/usr/bin/env python3
"""
Load petition data from JSON into Postgres with Prometheus instrumentation.
"""

import json
import sys
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

# Import Prometheus metrics
sys.path.insert(0, str(Path(__file__).parent.parent))
from observability.prometheus_metrics import (
    track_pipeline_execution,
    track_db_operation,
    rows_processed_total,
    update_business_metrics,
    start_metrics_server,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_petitions(json_path: str, db_conn_str: str):
    """Load petitions from JSON file into Postgres."""
    with track_pipeline_execution("load_petitions"):
        # Read JSON data
        logger.info(f"Reading data from {json_path}")
        with open(json_path) as f:
            petitions = json.load(f)

        logger.info(f"📊 Loading {len(petitions)} petitions...")

        # Track rows being processed
        rows_processed_total.labels(pipeline_name="load_petitions", layer="bronze").inc(
            len(petitions)
        )

        # Connect to database
        conn = psycopg2.connect(db_conn_str)
        cur = conn.cursor()

        try:
            # Prepare data for insert
            insert_query = """
                INSERT INTO raw_petitions (
                    petition_id, action, background, additional_details, status,
                    signature_count, created_at, updated_at, open_at, closed_at,
                    government_response_at, debate_threshold_reached_at,
                    response_threshold_reached_at, creator_name, topics
                ) VALUES (
                    %(petition_id)s, %(action)s, %(background)s, %(additional_details)s,
                    %(status)s, %(signature_count)s, %(created_at)s, %(updated_at)s,
                    %(open_at)s, %(closed_at)s, %(government_response_at)s,
                    %(debate_threshold_reached_at)s, %(response_threshold_reached_at)s,
                    %(creator_name)s, %(topics)s
                )
                ON CONFLICT (petition_id) DO UPDATE SET
                    signature_count = EXCLUDED.signature_count,
                    updated_at = EXCLUDED.updated_at,
                    status = EXCLUDED.status;
            """

            # Convert topics to JSON string
            for p in petitions:
                if "topics" in p and isinstance(p["topics"], list):
                    p["topics"] = json.dumps(p["topics"])
                else:
                    p["topics"] = "[]"

            # Batch insert with tracking
            with track_db_operation("insert"):
                execute_batch(cur, insert_query, petitions, page_size=100)
                logger.info(f"Inserted {len(petitions)} petitions")

            # Insert pipeline metric
            with track_db_operation("insert"):
                cur.execute(
                    """
                    INSERT INTO pipeline_metrics (
                        pipeline_name, source, records_processed,
                        records_valid, records_quarantined, status
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        "ingest_petitions",
                        "uk_parliament_api",
                        len(petitions),
                        len(petitions),
                        0,
                        "success",
                    ),
                )

            conn.commit()

            # Verify and update business metrics
            with track_db_operation("select"):
                cur.execute("""
                    SELECT
                        COUNT(*) as total_count,
                        SUM(signature_count) as total_sigs,
                        COUNT(CASE WHEN signature_count >= 100000 THEN 1 END) as viral_count,
                        COUNT(CASE WHEN government_response_at IS NOT NULL THEN 1 END) as response_count
                    FROM raw_petitions
                """)
                count, total_sigs, viral_count, response_count = cur.fetchone()

            # Update Prometheus business metrics
            update_business_metrics(
                petition_count=count,
                signature_count=total_sigs,
                viral_count=viral_count,
                response_count=response_count,
            )

            logger.info(f"✅ Loaded {count} petitions with {total_sigs:,} total signatures")
            logger.info(
                f"   Viral petitions: {viral_count}, Government responses: {response_count}"
            )

        finally:
            cur.close()
            conn.close()


if __name__ == "__main__":
    # Start Prometheus metrics server (optional - for standalone runs)
    import os

    if os.getenv("ENABLE_METRICS_SERVER", "false").lower() == "true":
        start_metrics_server(port=8000)
        logger.info("Metrics available at http://localhost:8000/metrics")

    # Load data
    json_file = "data/raw/petitions_20251204_012415_manual.json"
    db_string = "host=localhost port=5432 dbname=petitions user=postgres password=postgres"

    load_petitions(json_file, db_string)

    logger.info("Data load complete! Check metrics at http://localhost:8000/metrics")
