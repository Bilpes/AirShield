"""Initial encrypted vault and evidence ledger schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", "tenant_id"),
    )
    op.create_table(
        "token_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("lookup_hash", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("wrap_key_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["session_id", "tenant_id"], ["sessions.id", "sessions.tenant_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_token_mapping_id_tenant"),
        sa.UniqueConstraint("tenant_id", "session_id", "token", name="uq_token_mapping_session_token"),
        sa.UniqueConstraint("tenant_id", "session_id", "lookup_hash", name="uq_token_mapping_session_lookup"),
    )
    op.create_index("ix_token_expiry", "token_mappings", ["expires_at"])
    op.create_table(
        "identity_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("speaker_track", sa.String(64), nullable=False),
        sa.Column("subject_token", sa.String(256), nullable=False),
        sa.Column("llm_speaker_token", sa.String(64), nullable=False),
        sa.Column("assurance", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("consent_id", sa.String(128)),
        sa.Column("bound_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["session_id", "tenant_id"], ["sessions.id", "sessions.tenant_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "session_id", "speaker_track", name="uq_identity_binding_session_track"
        ),
    )
    op.create_table(
        "ledger_state",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("last_hash", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "evidence_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("signature", sa.LargeBinary(), nullable=False),
        sa.Column("signing_key_id", sa.Text(), nullable=False),
        sa.Column("signing_algorithm", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "sequence", name="uq_evidence_tenant_sequence"),
    )
    op.create_index("ix_evidence_created", "evidence_events", ["created_at"])
    op.create_table(
        "idempotency_records",
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("receipt_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "key"),
    )
    op.create_index("ix_idempotency_expiry", "idempotency_records", ["expires_at"])
    op.create_table(
        "reidentification_requests",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("mapping_id", sa.Uuid(), nullable=False),
        sa.Column("requester_subject", sa.String(256), nullable=False),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("ticket_reference", sa.String(128), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("approver_subject", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["mapping_id", "tenant_id"],
            ["token_mappings.id", "token_mappings.tenant_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_reid_status_expiry", "reidentification_requests", ["status", "expires_at"])


def downgrade():
    for name in [
        "reidentification_requests",
        "idempotency_records",
        "evidence_events",
        "ledger_state",
        "identity_bindings",
        "token_mappings",
        "sessions",
    ]:
        op.drop_table(name)
