"""Unit tests for data contracts."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from contracts.schemas.petition_events import (
    PetitionEvent,
    PetitionStatus,
    SignatureSource,
    UserSignatureEvent,
    get_pii_fields,
)


class TestPetitionEvent:
    """Tests for PetitionEvent schema."""

    def test_valid_petition(self):
        """Valid petition passes validation."""
        petition = PetitionEvent(
            petition_id=123,
            action="Test petition",
            status=PetitionStatus.OPEN,
            signature_count=100,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert petition.petition_id == 123
        assert petition.action == "Test petition"

    def test_missing_required_field(self):
        """Missing required field raises error."""
        with pytest.raises(ValidationError):
            PetitionEvent(
                petition_id=123,
                # action is missing
                status=PetitionStatus.OPEN,
                signature_count=100,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_negative_signature_count(self):
        """Negative signature count raises error."""
        with pytest.raises(ValidationError):
            PetitionEvent(
                petition_id=123,
                action="Test",
                status=PetitionStatus.OPEN,
                signature_count=-1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_invalid_status(self):
        """Invalid status raises error."""
        with pytest.raises(ValidationError):
            PetitionEvent(
                petition_id=123,
                action="Test",
                status="invalid_status",
                signature_count=100,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )


class TestUserSignatureEvent:
    """Tests for UserSignatureEvent schema."""

    def test_valid_event(self):
        """Valid event passes validation."""
        event = UserSignatureEvent(
            event_id="abc-123",
            petition_id=1,
            user_id="user-456",
            user_email="test@example.com",
            source=SignatureSource.WEB,
            signed_at=datetime.now(),
        )
        assert event.event_id == "abc-123"

    def test_pii_fields_tagged(self):
        """PII fields are properly tagged."""
        pii_fields = get_pii_fields(UserSignatureEvent)
        assert "user_email" in pii_fields
        assert "user_id" in pii_fields
        assert "user_name" in pii_fields
        assert "user_ip" in pii_fields
        assert "postcode" in pii_fields
        # Non-PII fields should not be in list
        assert "petition_id" not in pii_fields
        assert "source" not in pii_fields


class TestPetitionEventPII:
    """Tests for PII tagging in PetitionEvent."""

    def test_creator_name_is_pii(self):
        """Creator name should be tagged as PII."""
        pii_fields = get_pii_fields(PetitionEvent)
        assert "creator_name" in pii_fields
