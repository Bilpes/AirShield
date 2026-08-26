from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import IdentityBinding, SessionRecord
from app.retention import apply_retention


@pytest.mark.asyncio
async def test_expired_session_removes_identity_binding_and_marks_session_expired(db):
    now = datetime.now(UTC)
    session = SessionRecord(
        id="ses_0123456789abcdef01234567",
        tenant_id="tenant-retention",
        policy_id="healthcare-us-eu-v1",
        policy_version="1.0.0",
        language="en",
        status="active",
        expires_at=now - timedelta(minutes=1),
    )
    binding = IdentityBinding(
        tenant_id=session.tenant_id,
        session_id=session.id,
        speaker_track="SPEAKER_A",
        subject_token="keyed-subject-digest",  # noqa: S106 - test digest
        llm_speaker_token="[SPEAKER_A1B2C3]",  # noqa: S106 - test token
        assurance="sso_verified",
        source="sso",
        bound_by="keyed-actor-digest",
    )
    db.add_all([session, binding])
    await db.flush()

    result = await apply_retention(db, now)

    assert result["expired_identity_bindings_deleted"] == 1
    assert result["sessions_expired"] == 1
    assert await db.scalar(select(IdentityBinding).where(IdentityBinding.session_id == session.id)) is None
    await db.refresh(session)
    assert session.status == "expired"
