import json

import pytest
from sqlalchemy import select

from app.evidence import EvidenceLedger, assert_metadata_only
from app.models import EvidenceEvent
from scripts.export_evidence import build_export


def test_evidence_rejects_sensitive_payload_keys_recursively():
    with pytest.raises(ValueError, match="forbidden in evidence"):
        assert_metadata_only({"nested": [{"transcript": "do not persist"}]})


@pytest.mark.asyncio
async def test_verified_export_contains_complete_signed_metadata_chain(db):
    event = await EvidenceLedger().append(
        db,
        tenant_id="tenant-export",
        event_type="egress.receipt",
        payload={"session_id": "ses-export", "decision": "allow"},
    )
    exported = await build_export(db, "tenant-export")
    rows = [json.loads(line) for line in exported.decode().splitlines()]
    assert rows[0]["chain_verified"] is True
    assert rows[0]["event_count"] == 1
    assert rows[1]["event_hash"] == event.event_hash
    assert rows[1]["signature"]
    assert "transcript" not in exported.decode().lower()


@pytest.mark.asyncio
async def test_signed_hash_chain_detects_payload_tampering(db):
    ledger = EvidenceLedger()
    first = await ledger.append(
        db,
        tenant_id="tenant-a",
        event_type="session.created",
        payload={"session_id": "ses-1", "status": "active"},
    )
    second = await ledger.append(
        db,
        tenant_id="tenant-a",
        event_type="egress.receipt",
        payload={"session_id": "ses-1", "decision": "allow"},
    )
    assert second.previous_hash == first.event_hash
    db.expire_all()  # force timestamps and signatures to be reloaded from storage
    assert await ledger.verify(db, "tenant-a") == (True, 2, None)
    event = await db.scalar(
        select(EvidenceEvent).where(EvidenceEvent.tenant_id == "tenant-a", EvidenceEvent.sequence == 1)
    )
    assert event is not None
    event.payload = {"session_id": "ses-1", "status": "tampered"}
    await db.flush()
    assert await ledger.verify(db, "tenant-a") == (False, 2, 1)
    event.payload = {"session_id": "ses-1", "status": "active"}
    await db.flush()
    assert await ledger.verify(db, "tenant-a") == (True, 2, None)
    await db.delete(second)
    await db.flush()
    assert await ledger.verify(db, "tenant-a") == (False, 1, 2)
