from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionFactory, engine
from app.evidence import EvidenceLedger, iso_utc
from app.models import EvidenceEvent

SAFE_TENANT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


async def build_export(db: AsyncSession, tenant_id: str) -> bytes:
    valid, checked, invalid = await EvidenceLedger().verify(db, tenant_id)
    if not valid:
        raise RuntimeError(f"Evidence verification failed at sequence {invalid}")
    events = list(
        (
            await db.scalars(
                select(EvidenceEvent)
                .where(EvidenceEvent.tenant_id == tenant_id)
                .order_by(EvidenceEvent.sequence)
            )
        ).all()
    )
    if len(events) != checked:
        raise RuntimeError("Evidence count changed during export")
    header = {
        "record_type": "airshield.evidence.export",
        "format_version": "1.0",
        "tenant_id": tenant_id,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event_count": checked,
        "first_sequence": events[0].sequence if events else None,
        "last_sequence": events[-1].sequence if events else None,
        "last_event_hash": events[-1].event_hash if events else "0" * 64,
        "chain_verified": True,
    }
    rows = [json.dumps(header, sort_keys=True, separators=(",", ":"))]
    for event in events:
        rows.append(
            json.dumps(
                {
                    "record_type": "airshield.evidence.event",
                    "id": event.id,
                    "tenant_id": event.tenant_id,
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "previous_hash": event.previous_hash,
                    "event_hash": event.event_hash,
                    "signature": base64.b64encode(event.signature).decode(),
                    "signing_key_id": event.signing_key_id,
                    "signing_algorithm": event.signing_algorithm,
                    "created_at": iso_utc(event.created_at),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return ("\n".join(rows) + "\n").encode()


def atomic_private_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


async def run(tenant_id: str, output: Path) -> None:
    if not SAFE_TENANT.fullmatch(tenant_id):
        raise ValueError("Tenant identifier has an unsafe format")
    async with SessionFactory() as db:
        async with db.begin():
            content = await build_export(db, tenant_id)
    atomic_private_write(output, content)
    digest = hashlib.sha256(content).hexdigest()
    atomic_private_write(output.with_suffix(output.suffix + ".sha256"), f"{digest}  {output.name}\n".encode())
    print(json.dumps({"status": "exported", "events": content.count(b"\n") - 1, "sha256": digest}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and export one tenant's signed evidence chain")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        asyncio.run(run(arguments.tenant, arguments.output))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
