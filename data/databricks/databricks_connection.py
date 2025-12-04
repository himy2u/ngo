#!/usr/bin/env python3
"""
Azure Databricks connection utilities.
Provides helper functions for connecting to Databricks and executing queries.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_databricks_config() -> Dict[str, str]:
    """
    Load Databricks configuration from environment variables or .env file.

    Returns:
        Dict containing Databricks configuration
    """
    config = {
        "host": os.getenv("DATABRICKS_HOST", ""),
        "token": os.getenv("DATABRICKS_TOKEN", ""),
        "workspace_id": os.getenv("DATABRICKS_WORKSPACE_ID", ""),
        "sql_warehouse_path": os.getenv("DATABRICKS_SQL_WAREHOUSE_PATH", ""),
        "cluster_id": os.getenv("DATABRICKS_CLUSTER_ID", ""),
        "catalog": os.getenv("DATABRICKS_CATALOG", "ngo_platform_dev"),
        "schema_bronze": os.getenv("DATABRICKS_SCHEMA_BRONZE", "bronze"),
        "schema_silver": os.getenv("DATABRICKS_SCHEMA_SILVER", "silver"),
        "schema_gold": os.getenv("DATABRICKS_SCHEMA_GOLD", "gold"),
    }

    # Try to load from .env.databricks file if environment variables not set
    if not config["host"]:
        env_file = Path(__file__).parent.parent.parent / ".env.databricks"
        if env_file.exists():
            logger.info(f"Loading config from {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_key = key.strip()
                        env_value = value.strip()
                        # Map to config keys
                        if env_key == "DATABRICKS_HOST":
                            config["host"] = env_value
                        elif env_key == "DATABRICKS_TOKEN":
                            config["token"] = env_value
                        # Add more mappings as needed

    return config


def test_databricks_connection() -> bool:
    """
    Test connection to Azure Databricks.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        from databricks import sql

        config = load_databricks_config()

        if not config["host"] or not config["token"]:
            logger.error("Databricks host and token must be configured")
            logger.info("Copy .env.databricks.example to .env.databricks and fill in values")
            return False

        logger.info(f"Testing connection to {config['host']}")

        # Test connection
        with sql.connect(
            server_hostname=config["host"].replace("https://", ""),
            http_path=config["sql_warehouse_path"],
            access_token=config["token"],
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'Connection successful!' as message")
                result = cursor.fetchone()
                logger.info(f"✅ {result[0]}")
                return True

    except ImportError:
        logger.error("databricks-sql-connector not installed")
        logger.info("Install with: pip install databricks-sql-connector")
        return False
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


def execute_sql(sql_query: str, fetch_results: bool = True) -> Optional[List[tuple]]:
    """
    Execute SQL query on Databricks SQL Warehouse.

    Args:
        sql_query: SQL query to execute
        fetch_results: Whether to fetch and return results

    Returns:
        Query results if fetch_results=True, None otherwise
    """
    try:
        from databricks import sql

        config = load_databricks_config()

        with sql.connect(
            server_hostname=config["host"].replace("https://", ""),
            http_path=config["sql_warehouse_path"],
            access_token=config["token"],
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                if fetch_results:
                    return cursor.fetchall()
                return None

    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        raise


def create_unity_catalog_schema():
    """
    Create Unity Catalog schemas for medallion architecture.
    """
    try:
        config = load_databricks_config()
        catalog = config["catalog"]

        # SQL to create catalog and schemas
        sql_commands = [
            f"CREATE CATALOG IF NOT EXISTS {catalog}",
            f"USE CATALOG {catalog}",
            f"CREATE SCHEMA IF NOT EXISTS {config['schema_bronze']}",
            f"CREATE SCHEMA IF NOT EXISTS {config['schema_silver']}",
            f"CREATE SCHEMA IF NOT EXISTS {config['schema_gold']}",
            f"COMMENT ON SCHEMA {config['schema_bronze']} IS 'Raw data layer'",
            f"COMMENT ON SCHEMA {config['schema_silver']} IS 'Cleaned and enriched data'",
            f"COMMENT ON SCHEMA {config['schema_gold']} IS 'Business metrics and aggregations'",
        ]

        logger.info("Creating Unity Catalog schemas...")
        for cmd in sql_commands:
            logger.info(f"Executing: {cmd}")
            execute_sql(cmd, fetch_results=False)

        logger.info("✅ Unity Catalog schemas created successfully")

    except Exception as e:
        logger.error(f"Failed to create schemas: {e}")
        raise


def main():
    """Test Databricks connection and setup."""
    logger.info("Azure Databricks Connection Test")
    logger.info("=" * 50)

    # Test connection
    if test_databricks_connection():
        logger.info("\n✅ Connection successful!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python data/databricks/create_delta_tables.py")
        logger.info("2. Migrate data from Postgres to Databricks")
    else:
        logger.error("\n❌ Connection failed")
        logger.info("\nTroubleshooting:")
        logger.info("1. Copy .env.databricks.example to .env.databricks")
        logger.info("2. Fill in DATABRICKS_HOST and DATABRICKS_TOKEN")
        logger.info("3. Install: pip install databricks-sql-connector")


if __name__ == "__main__":
    main()
