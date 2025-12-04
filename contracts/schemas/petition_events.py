"""Petition domain data contracts with PII tagging."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SignatureSource(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    EMAIL = "email"
    API = "api"


class PetitionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    REJECTED = "rejected"
    AWAITING_RESPONSE = "awaiting_response"
    RESPONDED = "responded"


class PetitionEvent(BaseModel):
    """Raw petition data from UK Parliament API."""

    petition_id: int = Field(..., description="Unique petition identifier")
    action: str = Field(
        ..., description="Petition title/action text", json_schema_extra={"pii": False}
    )
    background: str | None = Field(None, description="Detailed background text")
    additional_details: str | None = Field(None, description="Extra context")
    status: PetitionStatus
    signature_count: int = Field(..., ge=0)
    created_at: datetime
    updated_at: datetime
    open_at: datetime | None = None
    closed_at: datetime | None = None
    government_response_at: datetime | None = None
    debate_threshold_reached_at: datetime | None = None
    response_threshold_reached_at: datetime | None = None
    creator_name: str | None = Field(None, json_schema_extra={"pii": True})
    topics: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class UserSignatureEvent(BaseModel):
    """User signing a petition (streaming event)."""

    event_id: str = Field(..., description="Unique event ID")
    petition_id: int
    user_id: str = Field(..., json_schema_extra={"pii": True})
    user_email: str = Field(..., json_schema_extra={"pii": True})
    user_name: str | None = Field(None, json_schema_extra={"pii": True})
    user_ip: str | None = Field(None, json_schema_extra={"pii": True})
    source: SignatureSource
    signed_at: datetime
    country: str | None = None
    postcode: str | None = Field(None, json_schema_extra={"pii": True})

    model_config = {"extra": "ignore"}


class QuarantineRecord(BaseModel):
    """Failed record stored for review."""

    raw_payload: dict[str, Any]
    error_type: str
    error_message: str
    source: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    schema_name: str
    retried: bool = False
    retry_count: int = 0


# Helper to get PII fields
def get_pii_fields(model: type[BaseModel]) -> list[str]:
    """Return list of field names marked as PII."""
    pii_fields = []
    for name, field_info in model.model_fields.items():
        extra = field_info.json_schema_extra or {}
        if extra.get("pii"):
            pii_fields.append(name)
    return pii_fields
