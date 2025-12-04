"""Slack alerting for pipeline events."""

import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SlackAlerter:
    """Send alerts to Slack."""

    COLORS = {
        AlertSeverity.INFO: "#36a64f",  # green
        AlertSeverity.WARNING: "#ff9800",  # orange
        AlertSeverity.CRITICAL: "#dc3545",  # red
    }

    ICONS = {
        AlertSeverity.INFO: "✅",
        AlertSeverity.WARNING: "⚠️",
        AlertSeverity.CRITICAL: "🚨",
    }

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)

    def send(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        fields: dict[str, Any] | None = None,
    ) -> bool:
        """Send alert to Slack."""
        if not self.enabled:
            logger.warning(f"Slack not configured. Alert: {title} - {message}")
            return False

        icon = self.ICONS[severity]
        color = self.COLORS[severity]

        attachment_fields = [
            {"title": "Severity", "value": severity.value.upper(), "short": True},
            {"title": "Time", "value": datetime.utcnow().isoformat(), "short": True},
        ]

        if fields:
            for key, value in fields.items():
                attachment_fields.append({"title": key, "value": str(value), "short": True})

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{icon} {title}",
                    "text": message,
                    "fields": attachment_fields,
                    "footer": "NGO Data Platform",
                }
            ]
        }

        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def pipeline_success(self, pipeline: str, duration: float, records: int):
        """Alert on successful pipeline run."""
        self.send(
            title=f"Pipeline {pipeline} completed",
            message=f"Processed {records} records in {duration:.1f}s",
            severity=AlertSeverity.INFO,
            fields={"Pipeline": pipeline, "Records": records, "Duration": f"{duration:.1f}s"},
        )

    def pipeline_failure(self, pipeline: str, error: str):
        """Alert on pipeline failure."""
        self.send(
            title=f"Pipeline {pipeline} FAILED",
            message=f"Error: {error}",
            severity=AlertSeverity.CRITICAL,
            fields={"Pipeline": pipeline},
        )

    def high_quarantine_rate(self, pipeline: str, rate: float, threshold: float):
        """Alert when quarantine rate exceeds threshold."""
        self.send(
            title=f"High quarantine rate in {pipeline}",
            message=f"Quarantine rate {rate:.1%} exceeds threshold {threshold:.1%}",
            severity=AlertSeverity.WARNING,
            fields={"Pipeline": pipeline, "Rate": f"{rate:.1%}", "Threshold": f"{threshold:.1%}"},
        )

    def data_quality_failure(self, checkpoint: str, failed_expectations: list[str]):
        """Alert on data quality check failure."""
        self.send(
            title=f"Data quality check failed: {checkpoint}",
            message=f"Failed expectations: {', '.join(failed_expectations[:5])}",
            severity=AlertSeverity.CRITICAL,
            fields={"Checkpoint": checkpoint, "Failed": len(failed_expectations)},
        )

    def freshness_sla_breach(self, table: str, delay_minutes: int, sla_minutes: int):
        """Alert on data freshness SLA breach."""
        self.send(
            title=f"Freshness SLA breach: {table}",
            message=f"Data is {delay_minutes}min old (SLA: {sla_minutes}min)",
            severity=AlertSeverity.WARNING,
            fields={"Table": table, "Delay": f"{delay_minutes}min", "SLA": f"{sla_minutes}min"},
        )


# Singleton instance
alerter = SlackAlerter()
