#!/usr/bin/env python3
"""
Create Delta Lake tables in Azure Databricks.
Implements medallion architecture with Unity Catalog.
"""

import logging
from databricks_connection import load_databricks_config, execute_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_bronze_tables():
    """Create bronze layer Delta tables."""
    config = load_databricks_config()
    catalog = config["catalog"]
    schema = config["schema_bronze"]

    logger.info(f"Creating bronze tables in {catalog}.{schema}")

    # Bronze petitions table
    sql = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.petitions (
        petition_id BIGINT NOT NULL,
        action STRING NOT NULL,
        background STRING,
        additional_details STRING,
        status STRING,
        signature_count BIGINT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        open_at TIMESTAMP,
        closed_at TIMESTAMP,
        government_response_at TIMESTAMP,
        debate_threshold_reached_at TIMESTAMP,
        response_threshold_reached_at TIMESTAMP,
        creator_name STRING,
        topics STRING,
        _ingested_at TIMESTAMP,
        _source STRING,
        _ingestion_id STRING
    )
    USING DELTA
    COMMENT 'Raw petition data from UK Parliament API'
    TBLPROPERTIES (
        'delta.autoOptimize.optimizeWrite' = 'true',
        'delta.autoOptimize.autoCompact' = 'true'
    )
    """

    execute_sql(sql, fetch_results=False)
    logger.info("✅ Bronze petitions table created")


def create_silver_tables():
    """Create silver layer Delta tables."""
    config = load_databricks_config()
    catalog = config["catalog"]
    schema = config["schema_silver"]

    logger.info(f"Creating silver tables in {catalog}.{schema}")

    # Silver petitions table
    sql = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.petitions (
        petition_id BIGINT NOT NULL,
        petition_title STRING NOT NULL,
        petition_background STRING,
        status STRING,
        signature_count BIGINT,
        created_date TIMESTAMP,
        updated_date TIMESTAMP,
        closed_date TIMESTAMP,
        response_date TIMESTAMP,
        debate_reached_date TIMESTAMP,
        signature_tier STRING,
        has_government_response BOOLEAN,
        reached_debate_threshold BOOLEAN,
        created_year INT,
        created_month INT,
        created_day DATE,
        _loaded_at TIMESTAMP,
        _source_table STRING,
        _data_quality_score DECIMAL(5,2)
    )
    USING DELTA
    COMMENT 'Cleaned and enriched petition data'
    PARTITIONED BY (created_year, created_month)
    TBLPROPERTIES (
        'delta.autoOptimize.optimizeWrite' = 'true',
        'delta.autoOptimize.autoCompact' = 'true'
    )
    """

    execute_sql(sql, fetch_results=False)
    logger.info("✅ Silver petitions table created")


def create_gold_tables():
    """Create gold layer Delta tables."""
    config = load_databricks_config()
    catalog = config["catalog"]
    schema = config["schema_gold"]

    logger.info(f"Creating gold tables in {catalog}.{schema}")

    # Gold petition metrics table
    sql_metrics = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.petition_metrics (
        id BIGINT GENERATED ALWAYS AS IDENTITY,
        status STRING,
        signature_tier STRING,
        petition_count INT,
        total_signatures BIGINT,
        avg_signatures DECIMAL(10,2),
        min_signatures BIGINT,
        max_signatures BIGINT,
        govt_responses INT,
        debates_reached INT,
        response_rate_pct DECIMAL(5,2),
        _calculated_at TIMESTAMP,
        _metric_date DATE
    )
    USING DELTA
    COMMENT 'Aggregated petition performance metrics'
    """

    execute_sql(sql_metrics, fetch_results=False)
    logger.info("✅ Gold petition_metrics table created")

    # Gold daily summary table
    sql_daily = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.daily_petition_summary (
        summary_date DATE NOT NULL,
        new_petitions_count INT,
        total_signatures_added BIGINT,
        avg_signatures_per_petition DECIMAL(10,2),
        viral_petitions_count INT,
        government_responses_count INT,
        _calculated_at TIMESTAMP
    )
    USING DELTA
    COMMENT 'Daily petition activity summary'
    PARTITIONED BY (summary_date)
    """

    execute_sql(sql_daily, fetch_results=False)
    logger.info("✅ Gold daily_petition_summary table created")


def setup_table_access_control():
    """Setup role-based access control for tables."""
    config = load_databricks_config()
    catalog = config["catalog"]

    logger.info("Setting up access controls...")

    # Grant permissions (requires admin privileges)
    # These are examples - adjust based on your actual roles
    try:
        grants = [
            # Analysts can read silver and gold
            f"GRANT SELECT ON SCHEMA {catalog}.silver TO `analysts`",
            f"GRANT SELECT ON SCHEMA {catalog}.gold TO `analysts`",
            # Engineers can write to bronze and silver
            f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.bronze TO `engineers`",
            f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.silver TO `engineers`",
        ]

        for grant in grants:
            try:
                execute_sql(grant, fetch_results=False)
                logger.info(f"✅ {grant}")
            except Exception as e:
                logger.warning(f"Could not grant permission (may require admin): {e}")

    except Exception as e:
        logger.warning(f"Access control setup requires admin privileges: {e}")


def main():
    """Create all Delta Lake tables."""
    logger.info("Creating Delta Lake Tables in Azure Databricks")
    logger.info("=" * 60)

    try:
        # Create tables in each layer
        create_bronze_tables()
        create_silver_tables()
        create_gold_tables()

        # Setup access control
        setup_table_access_control()

        logger.info("\n" + "=" * 60)
        logger.info("✅ All Delta Lake tables created successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Migrate data: python data/databricks/migrate_to_databricks.py")
        logger.info("2. Query tables using Databricks SQL or notebooks")
        logger.info("3. Set up scheduled jobs for data refresh")

    except Exception as e:
        logger.error(f"\n❌ Failed to create tables: {e}")
        raise


if __name__ == "__main__":
    main()
