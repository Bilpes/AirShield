from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Principal, current_principal
from app.database import get_db
from app.main import app
from app.models import EvidenceEvent


def principal(tenant: str, *scopes: str) -> Principal:
    return Principal(
        subject=f"workload-{tenant}",
        tenant_id=tenant,
        scopes=frozenset(scopes),
        claims={"sub": f"workload-{tenant}", "tid": tenant},
    )


@pytest.mark.asyncio
async def test_routes_persist_idempotent_receipt_enforce_scopes_and_deny_cross_tenant(db):
    current = {"value": principal("tenant-a", "airshield.protect")}

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield db

    async def override_principal() -> Principal:
        return current["value"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_principal] = override_principal
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://control.test") as client:
            created = await client.post(
                "/v1/sessions",
                json={"policy": "finance-eu-us-v1", "language": "en", "ttl_minutes": 60},
            )
            assert created.status_code == 201
            session_id = created.json()["session_id"]
            request = {
                "session_id": session_id,
                "text": "Email alice@example.com",
                "policy": "finance-eu-us-v1",
                "destination": "agent-assist-local",
                "idempotency_key": "route-test-idempotency-0001",
            }
            first = await client.post("/v1/protect", json=request)
            replay = await client.post("/v1/protect", json=request)
            assert first.status_code == 200
            assert replay.status_code == 409
            receipt_id = first.json()["receipt"]["receipt_id"]
            assert receipt_id in replay.json()["detail"]
            assert "alice@example.com" not in first.text
            assert "alice@example.com" not in replay.text
            forbidden = await client.get(f"/v1/evidence/{receipt_id}")
            assert forbidden.status_code == 403

            current["value"] = principal("tenant-b", "airshield.protect")
            denied = await client.post(
                "/v1/protect",
                json={**request, "idempotency_key": "route-test-idempotency-0002"},
            )
            assert denied.status_code == 404

        receipt_count = await db.scalar(
            select(func.count())
            .select_from(EvidenceEvent)
            .where(
                EvidenceEvent.tenant_id == "tenant-a",
                EvidenceEvent.event_type == "egress.receipt",
            )
        )
        assert receipt_count == 1
    finally:
        app.dependency_overrides.clear()
