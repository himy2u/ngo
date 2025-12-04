"""Fetch petitions from UK Parliament API with validation and quarantine."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from contracts.schemas.petition_events import (
    PetitionEvent,
    QuarantineRecord,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UK_PARLIAMENT_API = "https://petition.parliament.uk/petitions.json"


class PetitionIngester:
    """Fetches and validates petition data."""

    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.valid_records: list[PetitionEvent] = []
        self.quarantine_records: list[QuarantineRecord] = []

    def fetch_from_api(self, state: str = "all", page: int = 1) -> dict[str, Any]:
        """Fetch petitions from UK Parliament API."""
        params = {"state": state, "page": page}
        with httpx.Client(timeout=30) as client:
            response = client.get(UK_PARLIAMENT_API, params=params)
            response.raise_for_status()
            return response.json()

    def _parse_petition(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform API response to our schema."""
        attrs = raw.get("attributes", {})
        return {
            "petition_id": raw.get("id"),
            "action": attrs.get("action"),
            "background": attrs.get("background"),
            "additional_details": attrs.get("additional_details"),
            "status": attrs.get("state"),
            "signature_count": attrs.get("signature_count", 0),
            "created_at": attrs.get("created_at"),
            "updated_at": attrs.get("updated_at"),
            "open_at": attrs.get("open_at"),
            "closed_at": attrs.get("closed_at"),
            "government_response_at": attrs.get("government_response_at"),
            "debate_threshold_reached_at": attrs.get("debate_threshold_reached_at"),
            "response_threshold_reached_at": attrs.get("response_threshold_reached_at"),
            "creator_name": attrs.get("creator_name"),
            "topics": attrs.get("topics", []) or [],
        }

    def validate_and_partition(self, raw_data: list[dict[str, Any]]) -> None:
        """Validate records, partition into valid/quarantine."""
        for raw in raw_data:
            parsed = self._parse_petition(raw)
            try:
                validated = PetitionEvent(**parsed)
                self.valid_records.append(validated)
            except ValidationError as e:
                quarantine = QuarantineRecord(
                    raw_payload=parsed,
                    error_type="validation_error",
                    error_message=str(e),
                    source="uk_parliament_api",
                    schema_name="PetitionEvent",
                )
                self.quarantine_records.append(quarantine)
                logger.warning(f"Quarantined record: {parsed.get('petition_id')}")

    def save_to_bronze(self, run_id: str) -> dict[str, str]:
        """Save valid and quarantine records to bronze layer."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save valid records
        valid_path = self.output_dir / f"petitions_{timestamp}_{run_id}.json"
        valid_data = [r.model_dump(mode="json") for r in self.valid_records]
        valid_path.write_text(json.dumps(valid_data, indent=2, default=str))

        # Save quarantine records
        quarantine_path = self.output_dir / f"quarantine_{timestamp}_{run_id}.json"
        quarantine_data = [r.model_dump(mode="json") for r in self.quarantine_records]
        quarantine_path.write_text(json.dumps(quarantine_data, indent=2, default=str))

        logger.info(
            f"Valid: {len(self.valid_records)}, Quarantined: {len(self.quarantine_records)}"
        )

        return {
            "valid_path": str(valid_path),
            "quarantine_path": str(quarantine_path),
            "valid_count": len(self.valid_records),
            "quarantine_count": len(self.quarantine_records),
        }

    def run(self, pages: int = 1, run_id: str = "manual") -> dict[str, Any]:
        """Full ingestion run."""
        all_petitions = []
        for page in range(1, pages + 1):
            logger.info(f"Fetching page {page}")
            data = self.fetch_from_api(page=page)
            petitions = data.get("data", [])
            all_petitions.extend(petitions)
            if not petitions:
                break

        self.validate_and_partition(all_petitions)
        return self.save_to_bronze(run_id)


if __name__ == "__main__":
    ingester = PetitionIngester()
    result = ingester.run(pages=3)
    print(f"Ingestion complete: {result}")
