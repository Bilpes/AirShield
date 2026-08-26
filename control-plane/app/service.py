from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections import Counter
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import Principal
from .config import get_settings
from .detection import get_detector
from .evidence import EvidenceLedger, receipt_dict
from .metrics import ENTITY_COUNTS, PROTECTION_REQUESTS, REIDENTIFICATION
from .models import IdempotencyRecord, IdentityBinding, ReidentificationRequest, SessionRecord, TokenMapping
from .policies import get_policy_registry
from .schemas import DeletionRequest, IdentityBindingRequest, ProtectRequest, ReidentificationCreate
from .vault import TokenVault

settings = get_settings()


@lru_cache(maxsize=1)
def get_vault() -> TokenVault:
    return TokenVault()


@lru_cache(maxsize=1)
def get_ledger() -> EvidenceLedger:
    return EvidenceLedger()


def _expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)


def keyed_digest(value: str) -> str:
    encoded_key = settings.token_index_key_b64
    if not encoded_key:
        raise RuntimeError("TOKEN_INDEX_KEY_B64 is required")
    key = base64.b64decode(encoded_key)
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


async def create_session(
    db: AsyncSession, principal: Principal, policy_id: str, ttl_minutes: int
) -> SessionRecord:
    try:
        policy = get_policy_registry().get(policy_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown policy") from exc
    record = SessionRecord(
        id="ses_" + secrets.token_hex(12),
        tenant_id=principal.tenant_id,
        policy_id=policy.id,
        policy_version=policy.version,
        language="en",
        status="active",
        expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
    )
    db.add(record)
    await db.flush()
    await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="session.created",
        payload={
            "session_id": record.id,
            "policy": policy.id,
            "policy_version": policy.version,
            "language": "en",
            "actor_digest": keyed_digest(principal.subject),
        },
    )
    return record


async def _session(db: AsyncSession, tenant_id: str, session_id: str) -> SessionRecord:
    record = await db.scalar(
        select(SessionRecord).where(SessionRecord.id == session_id, SessionRecord.tenant_id == tenant_id)
    )
    if not record:
        raise HTTPException(404, "Session not found")
    if record.status != "active" or _expired(record.expires_at):
        raise HTTPException(409, "Session is not active")
    return record


async def protect(db: AsyncSession, principal: Principal, request: ProtectRequest):
    if len(request.text.encode()) > settings.max_text_bytes:
        raise HTTPException(413, "Text exceeds configured limit")
    session = await _session(db, principal.tenant_id, request.session_id)
    if session.policy_id != request.policy:
        raise HTTPException(409, "Session policy mismatch")
    policy = get_policy_registry().get(request.policy)
    if request.speaker_token:
        binding = await db.scalar(
            select(IdentityBinding).where(
                IdentityBinding.tenant_id == principal.tenant_id,
                IdentityBinding.session_id == session.id,
                IdentityBinding.llm_speaker_token == request.speaker_token,
            )
        )
        if not binding:
            raise HTTPException(409, "Speaker token is not bound to this session")
    request_digest = keyed_digest(
        f"{request.session_id}\0{request.policy}\0{request.destination}\0"
        f"{request.speaker_token or ''}\0{request.text}"
    )
    connection = await db.connection()
    if connection.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"{principal.tenant_id}\0{request.idempotency_key}"},
        )
    existing = await db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == principal.tenant_id,
            IdempotencyRecord.key == request.idempotency_key,
            IdempotencyRecord.expires_at > datetime.now(UTC),
        )
    )
    if existing:
        if not hmac.compare_digest(existing.request_digest, request_digest):
            raise HTTPException(409, "Idempotency key reused for different content")
        raise HTTPException(409, f"Request already processed; receipt={existing.receipt_id}")
    idem = IdempotencyRecord(
        tenant_id=principal.tenant_id,
        key=request.idempotency_key,
        request_digest=request_digest,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(idem)
    await db.flush()
    if not policy.destination_allowed(request.destination):
        event = await get_ledger().append(
            db,
            tenant_id=principal.tenant_id,
            event_type="egress.receipt",
            payload={
                "session_id": session.id,
                "protected_content_sha256": hashlib.sha256(b"").hexdigest(),
                "policy": policy.id,
                "policy_version": policy.version,
                "entity_counts": {},
                "destination": request.destination,
                "decision": "block",
                "reason_codes": ["destination_not_allowed"],
                "speaker_token": request.speaker_token or "none",
                "idempotency_digest": keyed_digest(request.idempotency_key),
                "actor_digest": keyed_digest(principal.subject),
            },
        )
        idem.receipt_id = event.id
        PROTECTION_REQUESTS.labels("block", policy.id).inc()
        return "", [], "block", receipt_dict(event)
    detector = get_detector()
    try:
        detections = detector.detect(request.text, set(policy.entities))
    except Exception:
        event = await get_ledger().append(
            db,
            tenant_id=principal.tenant_id,
            event_type="egress.receipt",
            payload={
                "session_id": session.id,
                "protected_content_sha256": hashlib.sha256(b"").hexdigest(),
                "policy": policy.id,
                "policy_version": policy.version,
                "entity_counts": {},
                "destination": request.destination,
                "decision": "block",
                "reason_codes": ["detector_unavailable"],
                "speaker_token": request.speaker_token or "none",
                "idempotency_digest": keyed_digest(request.idempotency_key),
                "actor_digest": keyed_digest(principal.subject),
            },
        )
        idem.receipt_id = event.id
        PROTECTION_REQUESTS.labels("block", policy.id).inc()
        return "", [], "block", receipt_dict(event)
    output: list[str] = []
    cursor = 0
    public: list[dict[str, object]] = []
    decision = "allow"
    reason_codes: set[str] = set()
    for detection in detections:
        rule = policy.entities[detection.entity_type]
        if detection.confidence < rule.threshold:
            candidate_decision = "block" if rule.critical or not policy.review_below_threshold else "review"
            if candidate_decision == "block" or decision == "allow":
                decision = candidate_decision
            reason_codes.add(f"below_threshold:{detection.entity_type}")
        if rule.action in {"redact", "generalize"}:
            token = f"[{detection.entity_type}_{rule.action.upper()}]"
        elif rule.action in {"tokenize", "mask"}:
            mapping = await get_vault().get_or_create(
                db,
                tenant_id=principal.tenant_id,
                session_id=session.id,
                entity_type=detection.entity_type,
                raw=detection.raw,
                ttl_minutes=policy.mapping_ttl_minutes,
            )
            token = mapping.token
        else:
            raise HTTPException(503, f"Unsupported policy action: {rule.action}")
        output.extend((request.text[cursor : detection.start], token))
        cursor = detection.end
        public.append(
            {
                "type": detection.entity_type,
                "token": token,
                "start": detection.start,
                "end": detection.end,
                "confidence": detection.confidence,
            }
        )
        ENTITY_COUNTS.labels(detection.entity_type, policy.id).inc()
    output.append(request.text[cursor:])
    protected = "".join(output)
    protected_hash = hashlib.sha256(protected.encode()).hexdigest()
    counts = dict(Counter(item["type"] for item in public))
    event = await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="egress.receipt",
        payload={
            "session_id": session.id,
            "protected_content_sha256": protected_hash,
            "policy": policy.id,
            "policy_version": policy.version,
            "entity_counts": counts,
            "destination": request.destination,
            "decision": decision,
            "reason_codes": sorted(reason_codes),
            "speaker_token": request.speaker_token or "none",
            "idempotency_digest": keyed_digest(request.idempotency_key),
            "actor_digest": keyed_digest(principal.subject),
        },
    )
    idem.receipt_id = event.id
    PROTECTION_REQUESTS.labels(decision, policy.id).inc()
    return protected, public, decision, receipt_dict(event)


async def bind_identity(
    db: AsyncSession, principal: Principal, session_id: str, request: IdentityBindingRequest
):
    await _session(db, principal.tenant_id, session_id)
    existing = await db.scalar(
        select(IdentityBinding).where(
            IdentityBinding.tenant_id == principal.tenant_id,
            IdentityBinding.session_id == session_id,
            IdentityBinding.speaker_track == request.speaker_track,
        )
    )
    if existing:
        raise HTTPException(409, "Speaker track already bound")
    llm_token = f"[SPEAKER_{secrets.token_hex(3).upper()}]"
    record = IdentityBinding(
        tenant_id=principal.tenant_id,
        session_id=session_id,
        speaker_track=request.speaker_track,
        subject_token=keyed_digest(request.subject_token),
        llm_speaker_token=llm_token,
        assurance=request.assurance,
        source=request.source,
        consent_id=keyed_digest(request.consent_id) if request.consent_id else None,
        bound_by=keyed_digest(principal.subject),
    )
    db.add(record)
    await db.flush()
    await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="identity.bound",
        payload={
            "session_id": session_id,
            "speaker_track": request.speaker_track,
            "llm_speaker_token": llm_token,
            "assurance": request.assurance,
            "source": request.source,
            "consent_present": bool(request.consent_id),
            "actor_digest": keyed_digest(principal.subject),
        },
    )
    return record


async def delete_session_data(
    db: AsyncSession,
    principal: Principal,
    session_id: str,
    request: DeletionRequest,
) -> tuple[SessionRecord, int, int, str]:
    session = await db.scalar(
        select(SessionRecord)
        .where(SessionRecord.id == session_id, SessionRecord.tenant_id == principal.tenant_id)
        .with_for_update()
    )
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status == "deleted":
        raise HTTPException(409, "Session data was already deleted")
    mapping_result = await db.execute(
        delete(TokenMapping).where(
            TokenMapping.tenant_id == principal.tenant_id,
            TokenMapping.session_id == session_id,
        )
    )
    binding_result = await db.execute(
        delete(IdentityBinding).where(
            IdentityBinding.tenant_id == principal.tenant_id,
            IdentityBinding.session_id == session_id,
        )
    )
    mapping_count = mapping_result.rowcount or 0  # type: ignore[attr-defined]
    binding_count = binding_result.rowcount or 0  # type: ignore[attr-defined]
    session.status = "deleted"
    event = await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="data.deleted",
        payload={
            "session_id": session_id,
            "purpose": request.purpose,
            "ticket_reference": request.ticket_reference,
            "token_mappings_deleted": mapping_count,
            "identity_bindings_deleted": binding_count,
            "actor_digest": keyed_digest(principal.subject),
            "status": "deleted",
        },
    )
    return session, mapping_count, binding_count, event.id


async def request_reidentification(db: AsyncSession, principal: Principal, request: ReidentificationCreate):
    await _session(db, principal.tenant_id, request.session_id)
    mapping = await db.scalar(
        select(TokenMapping).where(
            TokenMapping.tenant_id == principal.tenant_id,
            TokenMapping.session_id == request.session_id,
            TokenMapping.token == request.token,
            TokenMapping.expires_at > datetime.now(UTC),
        )
    )
    if not mapping:
        raise HTTPException(404, "Active token mapping not found")
    record = ReidentificationRequest(
        id="rid_" + secrets.token_hex(12),
        tenant_id=principal.tenant_id,
        mapping_id=mapping.id,
        requester_subject=keyed_digest(principal.subject),
        purpose=request.purpose,
        ticket_reference=request.ticket_reference,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(record)
    await db.flush()
    REIDENTIFICATION.labels("request", "pending").inc()
    await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="reidentification.requested",
        payload={
            "request_id": record.id,
            "session_id": request.session_id,
            "token_digest": keyed_digest(request.token),
            "purpose": request.purpose,
            "ticket_reference": request.ticket_reference,
            "requester_digest": record.requester_subject,
            "status": "pending",
        },
    )
    return record


async def approve_reidentification(db: AsyncSession, principal: Principal, request_id: str):
    record = await db.scalar(
        select(ReidentificationRequest)
        .where(
            ReidentificationRequest.id == request_id, ReidentificationRequest.tenant_id == principal.tenant_id
        )
        .with_for_update()
    )
    if not record:
        raise HTTPException(404, "Request not found")
    if record.status != "pending" or _expired(record.expires_at):
        raise HTTPException(409, "Request is not pending or has expired")
    approver = keyed_digest(principal.subject)
    if hmac.compare_digest(record.requester_subject, approver):
        raise HTTPException(403, "Four-eyes control requires a different approver")
    record.status = "approved"
    record.approver_subject = approver
    record.approved_at = datetime.now(UTC)
    await db.flush()
    REIDENTIFICATION.labels("approve", "approved").inc()
    await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="reidentification.approved",
        payload={
            "request_id": record.id,
            "purpose": record.purpose,
            "ticket_reference": record.ticket_reference,
            "approver_digest": approver,
            "status": "approved",
        },
    )
    return record


async def consume_reidentification(db: AsyncSession, principal: Principal, request_id: str):
    record = await db.scalar(
        select(ReidentificationRequest)
        .where(
            ReidentificationRequest.id == request_id, ReidentificationRequest.tenant_id == principal.tenant_id
        )
        .with_for_update()
    )
    if not record:
        raise HTTPException(404, "Request not found")
    if record.status != "approved" or _expired(record.expires_at) or record.consumed_at:
        raise HTTPException(409, "Approved result unavailable")
    if not hmac.compare_digest(record.requester_subject, keyed_digest(principal.subject)):
        raise HTTPException(403, "Only the requester may consume the result")
    mapping = await db.scalar(
        select(TokenMapping).where(
            TokenMapping.id == record.mapping_id,
            TokenMapping.tenant_id == principal.tenant_id,
        )
    )
    if not mapping or _expired(mapping.expires_at):
        raise HTTPException(410, "Token mapping expired")
    value = await get_vault().reveal(db, mapping)
    record.consumed_at = datetime.now(UTC)
    record.status = "consumed"
    await db.flush()
    REIDENTIFICATION.labels("consume", "success").inc()
    await get_ledger().append(
        db,
        tenant_id=principal.tenant_id,
        event_type="reidentification.consumed",
        payload={
            "request_id": record.id,
            "purpose": record.purpose,
            "ticket_reference": record.ticket_reference,
            "requester_digest": record.requester_subject,
            "status": "consumed",
        },
    )
    return record, mapping.token, value
