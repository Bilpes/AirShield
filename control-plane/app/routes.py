from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import Principal, require
from .config import get_settings
from .database import get_db
from .detection import get_detector
from .evidence import EvidenceLedger, receipt_dict
from .metrics import PROTECTION_LATENCY
from .models import EvidenceEvent
from .schemas import (
    CreateSessionRequest,
    DeletionRequest,
    DeletionResponse,
    EvidenceVerifyResponse,
    HealthResponse,
    IdentityBindingRequest,
    IdentityBindingResponse,
    ProtectedEntity,
    ProtectRequest,
    ProtectResponse,
    ReceiptResponse,
    ReidentificationCreate,
    ReidentificationResponse,
    ReidentificationResult,
    SessionResponse,
)
from .service import (
    approve_reidentification,
    bind_identity,
    consume_reidentification,
    create_session,
    delete_session_data,
    protect,
    request_reidentification,
)

router = APIRouter(prefix="/v1")
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health/live")
async def live():
    return {"status": "alive"}


@router.get("/health/ready", response_model=HealthResponse)
async def ready(db: DB):
    settings = get_settings()
    try:
        await db.execute(text("SELECT 1"))
        database = "ready"
    except Exception:
        database = "unavailable"
    detector = "ready" if get_detector().healthy else "unavailable"
    status = "ready" if database == "ready" and detector == "ready" else "not_ready"
    if status != "ready" and settings.fail_closed:
        raise HTTPException(503, {"status": status, "database": database, "detector": detector})
    return HealthResponse(
        status=status,
        database=database,
        key_provider=settings.key_provider,
        detector=detector,
        fail_closed=settings.fail_closed,
        environment=settings.environment,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def sessions(
    request: CreateSessionRequest,
    db: DB,
    principal: Annotated[Principal, Depends(require("airshield.protect"))],
):
    record = await create_session(db, principal, request.policy, request.ttl_minutes)
    return SessionResponse(
        session_id=record.id,
        policy=record.policy_id,
        policy_version=record.policy_version,
        language=record.language,
        expires_at=record.expires_at,
    )


@router.post("/protect", response_model=ProtectResponse)
async def protect_route(
    request: ProtectRequest, db: DB, principal: Annotated[Principal, Depends(require("airshield.protect"))]
):
    started = time.perf_counter()
    try:
        protected, entities, decision, receipt = await protect(db, principal, request)
    finally:
        PROTECTION_LATENCY.observe(time.perf_counter() - started)
    return ProtectResponse(
        protected_text=protected,
        entities=[ProtectedEntity(**e) for e in entities],
        decision=decision,
        receipt=ReceiptResponse(**receipt),
    )


@router.post("/sessions/{session_id}/bindings", response_model=IdentityBindingResponse)
async def binding(
    session_id: str,
    request: IdentityBindingRequest,
    db: DB,
    principal: Annotated[Principal, Depends(require("airshield.bind"))],
):
    record = await bind_identity(db, principal, session_id, request)
    return IdentityBindingResponse(
        speaker_track=record.speaker_track,
        llm_speaker_token=record.llm_speaker_token,
        assurance=record.assurance,
        status="bound",
    )


@router.delete("/sessions/{session_id}/data", response_model=DeletionResponse)
async def delete_data(
    session_id: str,
    request: DeletionRequest,
    db: DB,
    principal: Annotated[Principal, Depends(require("airshield.delete"))],
):
    session, mappings, bindings, event_id = await delete_session_data(db, principal, session_id, request)
    return DeletionResponse(
        session_id=session.id,
        status="deleted",
        token_mappings_deleted=mappings,
        identity_bindings_deleted=bindings,
        deletion_event_id=event_id,
    )


@router.post("/reidentification-requests", response_model=ReidentificationResponse, status_code=202)
async def reid_request(
    request: ReidentificationCreate,
    db: DB,
    principal: Annotated[Principal, Depends(require("airshield.reidentify.request"))],
):
    record = await request_reidentification(db, principal, request)
    return ReidentificationResponse(request_id=record.id, status=record.status, expires_at=record.expires_at)


@router.post("/reidentification-requests/{request_id}/approve", response_model=ReidentificationResponse)
async def reid_approve(
    request_id: str, db: DB, principal: Annotated[Principal, Depends(require("airshield.reidentify.approve"))]
):
    record = await approve_reidentification(db, principal, request_id)
    return ReidentificationResponse(request_id=record.id, status=record.status, expires_at=record.expires_at)


@router.get("/reidentification-requests/{request_id}/result", response_model=ReidentificationResult)
async def reid_result(
    request_id: str, db: DB, principal: Annotated[Principal, Depends(require("airshield.reidentify.request"))]
):
    record, token, value = await consume_reidentification(db, principal, request_id)
    return ReidentificationResult(
        request_id=record.id, token=token, value=value, consumed_at=record.consumed_at
    )


@router.get("/evidence/{event_id}", response_model=ReceiptResponse)
async def evidence(
    event_id: str, db: DB, principal: Annotated[Principal, Depends(require("airshield.evidence.read"))]
):
    event = await db.scalar(
        select(EvidenceEvent).where(
            EvidenceEvent.id == event_id,
            EvidenceEvent.tenant_id == principal.tenant_id,
            EvidenceEvent.event_type == "egress.receipt",
        )
    )
    if not event:
        raise HTTPException(404, "Receipt not found")
    return ReceiptResponse(**receipt_dict(event))


@router.post("/evidence/verify", response_model=EvidenceVerifyResponse)
async def verify_evidence(db: DB, principal: Annotated[Principal, Depends(require("airshield.admin"))]):
    valid, count, invalid = await EvidenceLedger().verify(db, principal.tenant_id)
    return EvidenceVerifyResponse(valid=valid, checked_events=count, first_invalid_sequence=invalid)
