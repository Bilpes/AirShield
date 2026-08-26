import pytest
from fastapi import HTTPException

from app.auth import Principal
from app.detection import Detection
from app.schemas import DeletionRequest, IdentityBindingRequest, ProtectRequest, ReidentificationCreate
from app.service import (
    approve_reidentification,
    bind_identity,
    consume_reidentification,
    create_session,
    delete_session_data,
    protect,
    request_reidentification,
)


class EmailDetector:
    def detect(self, text: str, allowed: set[str]):
        raw = "alice@example.com"
        start = text.index(raw)
        return [Detection("EMAIL", raw, start, start + len(raw), 0.99)]


class MixedConfidenceDetector:
    def detect(self, text: str, allowed: set[str]):
        return [
            Detection("MRN", "AB-123456", 0, 9, 0.50),
            Detection("LOCATION", "Oslo", 10, 14, 0.50),
        ]


class FailingDetector:
    def detect(self, text: str, allowed: set[str]):
        raise RuntimeError("model unavailable")


def principal(tenant: str, subject: str) -> Principal:
    return Principal(subject=subject, tenant_id=tenant, scopes=frozenset({"airshield.admin"}), claims={})


@pytest.mark.asyncio
async def test_tenant_isolation_idempotency_and_four_eyes_reidentification(db, monkeypatch):
    import app.service as service

    monkeypatch.setattr(service, "get_detector", lambda: EmailDetector())
    requester = principal("tenant-a", "requester@example.com")
    approver = principal("tenant-a", "approver@example.com")
    intruder = principal("tenant-b", "intruder@example.com")
    session = await create_session(db, requester, "finance-eu-us-v1", 60)
    request = ProtectRequest(
        session_id=session.id,
        text="Contact alice@example.com now",
        policy="finance-eu-us-v1",
        destination="fraud-review",
        idempotency_key="idem-1234567890123456",
    )
    protected, entities, decision, receipt = await protect(db, requester, request)
    assert "alice@example.com" not in protected
    assert entities[0]["type"] == "EMAIL"
    assert decision == "allow"
    assert receipt["signature"]

    with pytest.raises(HTTPException) as duplicate:
        await protect(db, requester, request)
    assert duplicate.value.status_code == 409

    tenant_b_request = request.model_copy(update={"idempotency_key": "tenant-b-1234567890"})
    with pytest.raises(HTTPException) as isolated:
        await protect(db, intruder, tenant_b_request)
    assert isolated.value.status_code == 404

    reid = await request_reidentification(
        db,
        requester,
        ReidentificationCreate(
            session_id=session.id,
            token=entities[0]["token"],
            purpose="fraud_investigation",
            ticket_reference="SEC-1042",
        ),
    )
    with pytest.raises(HTTPException) as same_person:
        await approve_reidentification(db, requester, reid.id)
    assert same_person.value.status_code == 403
    await approve_reidentification(db, approver, reid.id)
    consumed, token, value = await consume_reidentification(db, requester, reid.id)
    assert consumed.status == "consumed"
    assert token == entities[0]["token"]
    assert value == "alice@example.com"
    with pytest.raises(HTTPException) as replay:
        await consume_reidentification(db, requester, reid.id)
    assert replay.value.status_code == 409

    deleted, mapping_count, _binding_count, deletion_event = await delete_session_data(
        db,
        requester,
        session.id,
        DeletionRequest(
            purpose="privacy_erasure",
            ticket_reference="PRIV-2048",
        ),
    )
    assert deleted.status == "deleted"
    assert mapping_count == 1
    assert deletion_event.startswith("evt_")
    with pytest.raises(HTTPException) as no_longer_available:
        await request_reidentification(
            db,
            requester,
            ReidentificationCreate(
                session_id=session.id,
                token=token,
                purpose="fraud_investigation",
                ticket_reference="SEC-1043",
            ),
        )
    assert no_longer_available.value.status_code == 409


@pytest.mark.asyncio
async def test_identity_binding_is_hashed_and_speaker_token_must_be_bound(db, monkeypatch):
    import app.service as service

    monkeypatch.setattr(service, "get_detector", lambda: EmailDetector())
    actor = principal("tenant-a", "actor@example.com")
    session = await create_session(db, actor, "finance-eu-us-v1", 60)
    unbound_request = ProtectRequest(
        session_id=session.id,
        text="Contact alice@example.com now",
        policy="finance-eu-us-v1",
        destination="fraud-review",
        speaker_token="[SPEAKER_A1B2C3]",  # noqa: S106 - deliberately unbound token
        idempotency_key="unbound-speaker-1234",
    )
    with pytest.raises(HTTPException) as unbound:
        await protect(db, actor, unbound_request)
    assert unbound.value.status_code == 409

    binding = await bind_identity(
        db,
        actor,
        session.id,
        IdentityBindingRequest(
            speaker_track="SPEAKER_A",
            subject_token="crm-customer-1042",  # noqa: S106 - opaque host subject reference
            assurance="sso_verified",
            source="crm",
            consent_id="consent-case-2048",
        ),
    )
    assert binding.subject_token != "crm-customer-1042"  # noqa: S105
    assert binding.consent_id != "consent-case-2048"
    allowed_request = unbound_request.model_copy(
        update={
            "speaker_token": binding.llm_speaker_token,
            "idempotency_key": "bound-speaker-123456",
        }
    )
    _protected, _entities, decision, receipt = await protect(db, actor, allowed_request)
    assert decision == "allow"
    assert receipt["signature"]


@pytest.mark.asyncio
async def test_critical_block_decision_cannot_be_downgraded_to_review(db, monkeypatch):
    import app.service as service

    monkeypatch.setattr(service, "get_detector", lambda: MixedConfidenceDetector())
    actor = principal("tenant-a", "actor@example.com")
    session = await create_session(db, actor, "healthcare-us-eu-v1", 60)
    protected, _entities, decision, receipt = await protect(
        db,
        actor,
        ProtectRequest(
            session_id=session.id,
            text="AB-123456 Oslo",
            policy="healthcare-us-eu-v1",
            destination="approved-health-llm",
            idempotency_key="critical-block-1234",
        ),
    )
    assert "AB-123456" not in protected
    assert decision == "block"
    assert receipt["decision"] == "block"


@pytest.mark.asyncio
async def test_destination_policy_blocks_before_detection(db, monkeypatch):
    import app.service as service

    monkeypatch.setattr(service, "get_detector", lambda: EmailDetector())
    actor = principal("tenant-a", "actor@example.com")
    session = await create_session(db, actor, "finance-eu-us-v1", 60)
    request = ProtectRequest(
        session_id=session.id,
        text="Contact alice@example.com now",
        policy="finance-eu-us-v1",
        destination="public-unapproved-llm",
        idempotency_key="blocked-123456789012",
    )
    protected, entities, decision, receipt = await protect(db, actor, request)
    assert protected == ""
    assert entities == []
    assert decision == "block"
    assert receipt["reason_codes"] == ["destination_not_allowed"]
    assert receipt["signature"]


@pytest.mark.asyncio
async def test_detector_failure_returns_a_signed_block_receipt(db, monkeypatch):
    import app.service as service

    monkeypatch.setattr(service, "get_detector", lambda: FailingDetector())
    actor = principal("tenant-a", "actor@example.com")
    session = await create_session(db, actor, "finance-eu-us-v1", 60)
    protected, entities, decision, receipt = await protect(
        db,
        actor,
        ProtectRequest(
            session_id=session.id,
            text="Contact alice@example.com now",
            policy="finance-eu-us-v1",
            destination="fraud-review",
            idempotency_key="detector-fail-12345",
        ),
    )
    assert protected == ""
    assert entities == []
    assert decision == "block"
    assert receipt["reason_codes"] == ["detector_unavailable"]
    assert receipt["signature"]
