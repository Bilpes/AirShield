from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TokenMapping(Base):
    __tablename__ = "token_mappings"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    lookup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrap_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "tenant_id"], ["sessions.id", "sessions.tenant_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("id", "tenant_id", name="uq_token_mapping_id_tenant"),
        UniqueConstraint("tenant_id", "session_id", "token", name="uq_token_mapping_session_token"),
        UniqueConstraint("tenant_id", "session_id", "lookup_hash", name="uq_token_mapping_session_lookup"),
        Index("ix_token_expiry", "expires_at"),
    )


class IdentityBinding(Base):
    __tablename__ = "identity_bindings"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    speaker_track: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_token: Mapped[str] = mapped_column(
        String(256), nullable=False
    )  # keyed digest, never raw identity
    llm_speaker_token: Mapped[str] = mapped_column(String(64), nullable=False)
    assurance: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_id: Mapped[str | None] = mapped_column(String(128))
    bound_by: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "tenant_id"], ["sessions.id", "sessions.tenant_id"], ondelete="CASCADE"
        ),
        UniqueConstraint(
            "tenant_id", "session_id", "speaker_track", name="uq_identity_binding_session_track"
        ),
    )


class LedgerState(Base):
    __tablename__ = "ledger_state"
    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    sequence: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_hash: Mapped[str] = mapped_column(String(64), default="0" * 64, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvidenceEvent(Base):
    __tablename__ = "evidence_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    signing_algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("tenant_id", "sequence", name="uq_evidence_tenant_sequence"),
        Index("ix_evidence_created", "created_at"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_idempotency_expiry", "expires_at"),)


class ReidentificationRequest(Base):
    __tablename__ = "reidentification_requests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mapping_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requester_subject: Mapped[str] = mapped_column(String(256), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    ticket_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    approver_subject: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["mapping_id", "tenant_id"],
            ["token_mappings.id", "token_mappings.tenant_id"],
            ondelete="CASCADE",
        ),
        Index("ix_reid_status_expiry", "status", "expires_at"),
    )
