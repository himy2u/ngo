"""Unit tests for anonymization."""

import pytest

from contracts.schemas.petition_events import UserSignatureEvent
from data.anonymization.anonymize import Anonymizer


class TestAnonymizer:
    """Tests for PII anonymization."""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer(seed=42)

    @pytest.fixture
    def sample_record(self):
        return {
            "event_id": "abc-123",
            "petition_id": 1,
            "user_id": "user-real-id",
            "user_email": "john.doe@gmail.com",
            "user_name": "John Doe",
            "user_ip": "192.168.1.100",
            "source": "web",
            "signed_at": "2024-01-01T10:00:00",
            "country": "GB",
            "postcode": "SW1A 1AA",
        }

    def test_email_anonymized(self, anonymizer, sample_record):
        """Email should be anonymized."""
        result = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        assert result["user_email"] != "john.doe@gmail.com"
        assert "@anonymized.test" in result["user_email"]

    def test_name_anonymized(self, anonymizer, sample_record):
        """Name should be anonymized."""
        result = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        assert result["user_name"] != "John Doe"
        assert result["user_name"].startswith("User_")

    def test_ip_anonymized(self, anonymizer, sample_record):
        """IP should be anonymized."""
        result = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        assert result["user_ip"] == "0.0.0.0"

    def test_non_pii_unchanged(self, anonymizer, sample_record):
        """Non-PII fields should remain unchanged."""
        result = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        assert result["petition_id"] == 1
        assert result["source"] == "web"
        assert result["country"] == "GB"

    def test_consistent_hash(self, anonymizer, sample_record):
        """Same input should produce same anonymized output."""
        result1 = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        result2 = anonymizer.anonymize_record(sample_record, UserSignatureEvent)
        assert result1["user_email"] == result2["user_email"]
        assert result1["user_id"] == result2["user_id"]

    def test_null_values_preserved(self, anonymizer):
        """Null values should remain null."""
        record = {
            "event_id": "abc-123",
            "petition_id": 1,
            "user_id": "user-123",
            "user_email": "test@test.com",
            "user_name": None,
            "user_ip": None,
            "source": "web",
            "signed_at": "2024-01-01T10:00:00",
            "country": "GB",
            "postcode": None,
        }
        result = anonymizer.anonymize_record(record, UserSignatureEvent)
        assert result["user_name"] is None
        assert result["user_ip"] is None
        assert result["postcode"] is None
