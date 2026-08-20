from datetime import UTC, datetime, timedelta

import pytest
from cryptography.exceptions import InvalidTag

from app.config import get_settings
from app.keys import LocalKeyProvider
from app.models import SessionRecord
from app.vault import TokenVault


def test_local_key_provider_wrap_sign_and_tamper_detection():
    provider = LocalKeyProvider(get_settings())
    dek = b"d" * 32
    wrapped, key_id = provider.wrap_key(dek)
    assert provider.unwrap_key(wrapped, key_id) == dek
    with pytest.raises(InvalidTag):
        provider.unwrap_key(wrapped[:-1] + bytes([wrapped[-1] ^ 1]), key_id)
    digest = b"h" * 32
    signature, signing_key_id, algorithm = provider.sign_digest(digest)
    assert provider.verify_digest(digest, signature, signing_key_id, algorithm)
    assert not provider.verify_digest(b"x" * 32, signature, signing_key_id, algorithm)


@pytest.mark.asyncio
async def test_vault_round_trip_and_aad_tenant_integrity(db):
    db.add(
        SessionRecord(
            id="ses-vault",
            tenant_id="tenant-a",
            policy_id="finance-eu-us-v1",
            policy_version="1.0.0",
            language="en",
            status="active",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await db.flush()
    vault = TokenVault()
    mapping = await vault.get_or_create(
        db,
        tenant_id="tenant-a",
        session_id="ses-vault",
        entity_type="EMAIL",
        raw="alice@example.com",
        ttl_minutes=30,
    )
    assert mapping.ciphertext != b"alice@example.com"
    assert await vault.reveal(db, mapping) == "alice@example.com"
    mapping.tenant_id = "tenant-b"
    with pytest.raises(InvalidTag):
        await vault.reveal(db, mapping)
