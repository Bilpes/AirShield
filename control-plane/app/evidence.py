from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .keys import get_key_provider
from .models import EvidenceEvent, LedgerState

FORBIDDEN_PAYLOAD_KEYS = {
    "raw",
    "value",
    "plaintext",
    "original",
    "text",
    "transcript",
    "audio",
    "ciphertext",
    "authorization",
}


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def assert_metadata_only(value: Any, path: str = "payload"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_PAYLOAD_KEYS:
                raise ValueError(f"Raw/sensitive field forbidden in evidence: {path}.{key}")
            assert_metadata_only(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_metadata_only(child, f"{path}[{index}]")


class EvidenceLedger:
    def __init__(self):
        self.provider = get_key_provider()

    async def append(
        self, db: AsyncSession, *, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> EvidenceEvent:
        assert_metadata_only(payload)
        connection = await db.connection()
        if connection.dialect.name == "postgresql":
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant_id, 0))"),
                {"tenant_id": tenant_id},
            )
        elif connection.dialect.name == "sqlite":
            await db.execute(
                text(
                    "INSERT OR IGNORE INTO ledger_state "
                    "(tenant_id, sequence, last_hash) VALUES (:tenant_id, 0, :last_hash)"
                ),
                {"tenant_id": tenant_id, "last_hash": "0" * 64},
            )
        state = await db.scalar(
            select(LedgerState).where(LedgerState.tenant_id == tenant_id).with_for_update()
        )
        if not state:
            state = LedgerState(tenant_id=tenant_id, sequence=0, last_hash="0" * 64)
            db.add(state)
            await db.flush()
        sequence = state.sequence + 1
        created = datetime.now(UTC)
        envelope = {
            "tenant_id": tenant_id,
            "sequence": sequence,
            "event_type": event_type,
            "created_at": iso_utc(created),
            "previous_hash": state.last_hash,
            "payload": payload,
        }
        event_hash = hashlib.sha256(bytes.fromhex(state.last_hash) + canonical(envelope)).hexdigest()
        signature, key_id, algorithm = await asyncio.to_thread(
            self.provider.sign_digest, bytes.fromhex(event_hash)
        )
        event = EvidenceEvent(
            id="evt_" + secrets.token_hex(12),
            tenant_id=tenant_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            previous_hash=state.last_hash,
            event_hash=event_hash,
            signature=signature,
            signing_key_id=key_id,
            signing_algorithm=algorithm,
            created_at=created,
        )
        db.add(event)
        state.sequence = sequence
        state.last_hash = event_hash
        await db.flush()
        return event

    async def verify(self, db: AsyncSession, tenant_id: str) -> tuple[bool, int, int | None]:
        events = (
            await db.scalars(
                select(EvidenceEvent)
                .where(EvidenceEvent.tenant_id == tenant_id)
                .order_by(EvidenceEvent.sequence)
            )
        ).all()
        state = await db.get(LedgerState, tenant_id)
        previous = "0" * 64
        for expected_sequence, event in enumerate(events, start=1):
            if event.sequence != expected_sequence:
                return False, len(events), expected_sequence
            envelope = {
                "tenant_id": tenant_id,
                "sequence": event.sequence,
                "event_type": event.event_type,
                "created_at": iso_utc(event.created_at),
                "previous_hash": previous,
                "payload": event.payload,
            }
            expected = hashlib.sha256(bytes.fromhex(previous) + canonical(envelope)).hexdigest()
            valid_hash = event.previous_hash == previous and hmac_equal(event.event_hash, expected)
            valid_signature = await asyncio.to_thread(
                self.provider.verify_digest,
                bytes.fromhex(event.event_hash),
                event.signature,
                event.signing_key_id,
                event.signing_algorithm,
            )
            if not valid_hash or not valid_signature:
                return False, len(events), event.sequence
            previous = event.event_hash
        if state is None:
            return (True, 0, None) if not events else (False, len(events), 1)
        if state.sequence != len(events) or not hmac_equal(state.last_hash, previous):
            return False, len(events), min(state.sequence, len(events)) + 1
        return True, len(events), None


def hmac_equal(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)


def receipt_dict(event: EvidenceEvent) -> dict[str, Any]:
    payload = event.payload
    return {
        "receipt_id": event.id,
        "sequence": event.sequence,
        "content_sha256": payload["protected_content_sha256"],
        "policy": payload["policy"],
        "policy_version": payload["policy_version"],
        "entity_counts": payload["entity_counts"],
        "destination": payload["destination"],
        "decision": payload["decision"],
        "reason_codes": payload.get("reason_codes", []),
        "previous_hash": event.previous_hash,
        "event_hash": event.event_hash,
        "signature": base64.b64encode(event.signature).decode(),
        "signing_key_id": event.signing_key_id,
        "signing_algorithm": event.signing_algorithm,
        "created_at": event.created_at,
    }
