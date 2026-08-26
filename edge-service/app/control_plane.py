from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from .config import Settings

POLICY_ALIASES = {
    "Healthcare · HIPAA": "healthcare-us-eu-v1",
    "Financial services · PCI": "finance-eu-us-v1",
    "Insurance claims": "insurance-eu-us-v1",
    "Contact center privacy": "contact-center-eu-us-v1",
    "Internal copilot DLP": "saas-copilot-eu-us-v1",
}
LOCAL_DESTINATIONS = {
    "healthcare-us-eu-v1": "clinical-note-local",
    "finance-eu-us-v1": "agent-assist-local",
    "insurance-eu-us-v1": "claims-local",
    "contact-center-eu-us-v1": "qa-local",
    "saas-copilot-eu-us-v1": "ollama-local",
}
EGRESS_DESTINATIONS = {
    "healthcare-us-eu-v1": "approved-health-llm",
    "finance-eu-us-v1": "approved-finance-llm",
    "insurance-eu-us-v1": "approved-insurance-llm",
    "contact-center-eu-us-v1": "approved-contact-center-llm",
    "saas-copilot-eu-us-v1": "enterprise-copilot",
}


class ControlPlaneClient:
    def __init__(self, settings: Settings):
        if not settings.control_plane_url:
            raise ValueError("CONTROL_PLANE_URL is required")
        self.settings = settings
        verify: bool | str = str(settings.control_plane_ca_file) if settings.control_plane_ca_file else True
        self.client = httpx.AsyncClient(
            base_url=settings.control_plane_url.rstrip("/"), timeout=20, verify=verify
        )
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    async def _read_token(path: Path) -> str:
        return (await asyncio.to_thread(path.read_text)).strip()

    async def _token(self) -> str:
        if self._access_token and self._expires_at > time.time() + 60:
            return self._access_token
        async with self._token_lock:
            if self._access_token and self._expires_at > time.time() + 60:
                return self._access_token
            if self.settings.azure_federated_token_file:
                assertion = await self._read_token(self.settings.azure_federated_token_file)
                tenant = self.settings.azure_tenant_id
                client_id = self.settings.azure_client_id
                scope = self.settings.control_plane_scope
                if not tenant or not client_id or not scope:
                    raise RuntimeError("Azure workload identity configuration is incomplete")
                async with httpx.AsyncClient(timeout=10) as exchange:
                    response = await exchange.post(
                        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                        data={
                            "client_id": client_id,
                            "scope": scope,
                            "grant_type": "client_credentials",
                            "client_assertion_type": (
                                "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                            ),
                            "client_assertion": assertion,
                        },
                    )
                response.raise_for_status()
                payload = response.json()
                self._access_token = str(payload["access_token"])
                self._expires_at = time.time() + int(payload.get("expires_in", 300))
                return self._access_token
            if self.settings.control_plane_token_file:
                return await self._read_token(self.settings.control_plane_token_file)
            if self.settings.environment != "production":
                return self.settings.control_plane_dev_token or "development-only"
            raise RuntimeError("No control-plane workload identity is configured")

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        token = await self._token()
        response = await self.client.post(path, json=body, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()

    async def ready(self) -> bool:
        try:
            token = await self._token()
            response = await self.client.get("/v1/health/ready", headers={"Authorization": f"Bearer {token}"})
            return response.status_code == 200
        except Exception:
            return False

    async def create_session(self, policy: str) -> tuple[str, str]:
        policy_id = POLICY_ALIASES.get(policy, policy)
        result = await self._post(
            "/v1/sessions",
            {"policy": policy_id, "language": "en", "ttl_minutes": 60},
        )
        return str(result["session_id"]), policy_id

    async def bind_identity(
        self,
        *,
        session_id: str,
        speaker_track: str,
        subject_token: str,
        assurance: str,
        source: str,
    ) -> dict[str, Any]:
        return await self._post(
            f"/v1/sessions/{session_id}/bindings",
            {
                "speaker_track": speaker_track,
                "subject_token": subject_token,
                "assurance": assurance,
                "source": source,
            },
        )

    async def protect(
        self,
        *,
        session_id: str,
        policy: str,
        text: str,
        final_egress: bool,
        speaker_token: str | None = None,
    ) -> dict[str, Any]:
        destinations = EGRESS_DESTINATIONS if final_egress else LOCAL_DESTINATIONS
        destination = destinations.get(policy)
        if not destination:
            raise ValueError("No approved destination exists for policy")
        payload = {
            "session_id": session_id,
            "text": text,
            "policy": policy,
            "destination": destination,
            "idempotency_key": str(uuid.uuid4()),
        }
        if speaker_token:
            payload["speaker_token"] = speaker_token
        return await self._post("/v1/protect", payload)
