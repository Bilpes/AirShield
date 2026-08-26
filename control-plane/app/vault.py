from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .keys import get_key_provider
from .models import TokenMapping


class TokenVault:
    def __init__(self):
        self.settings = get_settings()
        self.provider = get_key_provider()
        self.index_key = base64.b64decode(self.settings.token_index_key_b64)

    def _lookup(self, tenant_id: str, session_id: str, entity_type: str, raw: str) -> str:
        message = f"{tenant_id}\0{session_id}\0{entity_type}\0{raw}".encode()
        return hmac.new(self.index_key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def _aad(tenant_id: str, session_id: str, token: str, entity_type: str) -> bytes:
        return f"airshield:v1:{tenant_id}:{session_id}:{token}:{entity_type}".encode()

    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        session_id: str,
        entity_type: str,
        raw: str,
        ttl_minutes: int,
    ) -> TokenMapping:
        lookup = self._lookup(tenant_id, session_id, entity_type, raw)
        connection = await db.connection()
        if connection.dialect.name == "postgresql":
            lock_key = f"{tenant_id}\0{session_id}\0{lookup}"
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )
        existing = await db.scalar(
            select(TokenMapping).where(
                TokenMapping.tenant_id == tenant_id,
                TokenMapping.session_id == session_id,
                TokenMapping.lookup_hash == lookup,
                TokenMapping.expires_at > datetime.now(UTC),
            )
        )
        if existing:
            return existing
        token = f"[{entity_type}_{secrets.token_hex(4).upper()}]"
        dek = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        aad = self._aad(tenant_id, session_id, token, entity_type)
        ciphertext = AESGCM(dek).encrypt(nonce, raw.encode(), aad)
        wrapped_dek, key_id = await asyncio.to_thread(self.provider.wrap_key, dek)
        mapping = TokenMapping(
            tenant_id=tenant_id,
            session_id=session_id,
            token=token,
            entity_type=entity_type,
            lookup_hash=lookup,
            ciphertext=ciphertext,
            nonce=nonce,
            wrapped_dek=wrapped_dek,
            wrap_key_id=key_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        db.add(mapping)
        await db.flush()
        return mapping

    async def reveal(self, db: AsyncSession, mapping: TokenMapping) -> str:
        dek = await asyncio.to_thread(self.provider.unwrap_key, mapping.wrapped_dek, mapping.wrap_key_id)
        aad = self._aad(mapping.tenant_id, mapping.session_id, mapping.token, mapping.entity_type)
        value = AESGCM(dek).decrypt(mapping.nonce, mapping.ciphertext, aad).decode()
        mapping.last_accessed_at = datetime.now(UTC)
        await db.flush()
        return value
