from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, exists, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionFactory
from .models import IdempotencyRecord, IdentityBinding, ReidentificationRequest, SessionRecord, TokenMapping

log = structlog.get_logger()


async def apply_retention(db: AsyncSession, now: datetime) -> dict[str, int]:
    mappings = (await db.execute(delete(TokenMapping).where(TokenMapping.expires_at <= now))).rowcount or 0
    bindings = (
        await db.execute(
            delete(IdentityBinding).where(
                exists().where(
                    SessionRecord.id == IdentityBinding.session_id,
                    SessionRecord.tenant_id == IdentityBinding.tenant_id,
                    SessionRecord.expires_at <= now,
                )
            )
        )
    ).rowcount or 0
    idempotency = (
        await db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at <= now))
    ).rowcount or 0
    requests = (
        await db.execute(
            delete(ReidentificationRequest).where(
                ReidentificationRequest.expires_at <= now,
                ReidentificationRequest.status.in_(["pending", "consumed"]),
            )
        )
    ).rowcount or 0
    sessions = (
        await db.execute(
            update(SessionRecord)
            .where(SessionRecord.expires_at <= now, SessionRecord.status == "active")
            .values(status="expired")
        )
    ).rowcount or 0
    return {
        "expired_token_mappings_deleted": mappings,
        "expired_identity_bindings_deleted": bindings,
        "idempotency_records_deleted": idempotency,
        "reidentification_records_deleted": requests,
        "sessions_expired": sessions,
    }


async def run_retention() -> dict[str, int]:
    async with SessionFactory() as db, db.begin():
        result = await apply_retention(db, datetime.now(UTC))
    log.info("retention_complete", **result)
    return result


if __name__ == "__main__":
    print(asyncio.run(run_retention()))
