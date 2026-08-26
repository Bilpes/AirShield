from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    policy: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,127}$")
    language: Literal["en"] = "en"
    ttl_minutes: int = Field(default=60, ge=5, le=1440)


class SessionResponse(BaseModel):
    session_id: str
    policy: str
    policy_version: str
    language: str
    expires_at: datetime


class ProtectRequest(BaseModel):
    session_id: str = Field(pattern=r"^ses_[a-f0-9]{24}$")
    text: str = Field(min_length=1)
    policy: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,127}$")
    destination: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    speaker_token: str | None = Field(default=None, pattern=r"^\[SPEAKER_[A-F0-9]{6}\]$")
    idempotency_key: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$")


class ProtectedEntity(BaseModel):
    type: str
    token: str
    start: int
    end: int
    confidence: float


class ReceiptResponse(BaseModel):
    receipt_id: str
    sequence: int
    content_sha256: str
    policy: str
    policy_version: str
    entity_counts: dict[str, int]
    destination: str
    decision: str
    reason_codes: list[str] = Field(default_factory=list)
    previous_hash: str
    event_hash: str
    signature: str
    signing_key_id: str
    signing_algorithm: str
    created_at: datetime


class ProtectResponse(BaseModel):
    protected_text: str
    entities: list[ProtectedEntity]
    decision: Literal["allow", "block", "review"]
    receipt: ReceiptResponse


class IdentityBindingRequest(BaseModel):
    speaker_track: str = Field(pattern=r"^SPEAKER_[A-Z0-9]{1,8}$")
    subject_token: str = Field(min_length=3, max_length=256)
    assurance: Literal["unverified", "claimed", "otp_verified", "sso_verified", "biometric_verified"]
    source: Literal["host_app", "sso", "otp", "ivr", "crm", "ehr", "voice_biometric"]
    consent_id: str | None = None


class IdentityBindingResponse(BaseModel):
    speaker_track: str
    llm_speaker_token: str
    assurance: str
    status: str


class ReidentificationCreate(BaseModel):
    session_id: str = Field(pattern=r"^ses_[a-f0-9]{24}$")
    token: str = Field(pattern=r"^\[[A-Z0-9_]+\]$")
    purpose: Literal[
        "security_incident",
        "privacy_request",
        "clinical_safety",
        "fraud_investigation",
        "legal_hold",
        "customer_support_escalation",
    ]
    ticket_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


class ReidentificationResponse(BaseModel):
    request_id: str
    status: str
    expires_at: datetime


class ReidentificationResult(BaseModel):
    request_id: str
    token: str
    value: str
    consumed_at: datetime


class EvidenceVerifyResponse(BaseModel):
    valid: bool
    checked_events: int
    first_invalid_sequence: int | None = None


class DeletionRequest(BaseModel):
    purpose: Literal[
        "privacy_erasure",
        "retention_expiry",
        "contract_termination",
        "security_containment",
    ]
    ticket_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


class DeletionResponse(BaseModel):
    session_id: str
    status: Literal["deleted"]
    token_mappings_deleted: int
    identity_bindings_deleted: int
    deletion_event_id: str


class HealthResponse(BaseModel):
    status: str
    database: str
    key_provider: str
    detector: str
    fail_closed: bool
    environment: str
