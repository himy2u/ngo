"""Anonymize PII fields for dev/staging environments."""

import hashlib
import json
from pathlib import Path
from typing import Any

from faker import Faker
from pydantic import BaseModel

from contracts.schemas.petition_events import (
    UserSignatureEvent,
    get_pii_fields,
)

fake = Faker()
Faker.seed(42)  # Reproducible fakes


class Anonymizer:
    """Anonymize PII fields in records."""

    def __init__(self, seed: int = 42):
        self.fake = Faker()
        Faker.seed(seed)
        self._hash_cache: dict[str, str] = {}

    def _consistent_hash(self, value: str) -> str:
        """Same input always produces same output (preserves joins)."""
        if value not in self._hash_cache:
            self._hash_cache[value] = hashlib.sha256(value.encode()).hexdigest()[:16]
        return self._hash_cache[value]

    def _fake_field(self, field_name: str, original_value: Any) -> Any:
        """Generate appropriate fake value based on field name."""
        if original_value is None:
            return None

        field_lower = field_name.lower()

        if "email" in field_lower:
            return f"user_{self._consistent_hash(str(original_value))}@anonymized.test"
        elif "name" in field_lower:
            return f"User_{self._consistent_hash(str(original_value))}"
        elif "ip" in field_lower:
            return "0.0.0.0"
        elif "postcode" in field_lower or "zip" in field_lower:
            return "XXXXX"
        elif "user_id" in field_lower:
            return f"anon_{self._consistent_hash(str(original_value))}"
        else:
            return "[REDACTED]"

    def anonymize_record(self, record: dict[str, Any], model: type[BaseModel]) -> dict[str, Any]:
        """Anonymize PII fields in a single record."""
        pii_fields = get_pii_fields(model)
        anonymized = record.copy()

        for field in pii_fields:
            if field in anonymized:
                anonymized[field] = self._fake_field(field, anonymized[field])

        return anonymized

    def anonymize_file(
        self, input_path: str, output_path: str, model: type[BaseModel]
    ) -> dict[str, int]:
        """Anonymize all records in a JSON file."""
        input_data = json.loads(Path(input_path).read_text())
        anonymized = [self.anonymize_record(r, model) for r in input_data]
        Path(output_path).write_text(json.dumps(anonymized, indent=2, default=str))
        return {"input_count": len(input_data), "output_count": len(anonymized)}


if __name__ == "__main__":
    anonymizer = Anonymizer()

    # Example usage
    sample_record = {
        "event_id": "123",
        "petition_id": 1,
        "user_id": "user-abc-123",
        "user_email": "john.doe@gmail.com",
        "user_name": "John Doe",
        "user_ip": "192.168.1.100",
        "source": "web",
        "signed_at": "2024-01-01T10:00:00",
        "country": "GB",
        "postcode": "SW1A 1AA",
    }

    anonymized = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
    print(f"Original: {sample_record}")
    print(f"Anonymized: {anonymized}")
