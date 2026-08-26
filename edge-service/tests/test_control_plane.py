import httpx
import pytest

from app.config import Settings
from app.control_plane import ControlPlaneClient


@pytest.mark.asyncio
async def test_edge_uses_versioned_policy_and_only_approved_destinations():
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path == "/v1/sessions":
            return httpx.Response(201, json={"session_id": "ses_0123456789abcdef01234567"})
        if request.url.path.endswith("/bindings"):
            return httpx.Response(
                200,
                json={
                    "speaker_track": "SPEAKER_A",
                    "llm_speaker_token": "[SPEAKER_A1B2C3]",
                    "assurance": "sso_verified",
                    "status": "bound",
                },
            )
        return httpx.Response(
            200,
            json={
                "protected_text": "[EMAIL_ABCD1234]",
                "entities": [],
                "decision": "allow",
                "receipt": {"receipt_id": "evt_1", "signature": "signed"},
            },
        )

    settings = Settings(
        environment="test",
        control_plane_url="https://control.internal",
        control_plane_dev_token="development-only",  # noqa: S106 - test placeholder
    )
    client = ControlPlaneClient(settings)
    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url="https://control.internal", transport=httpx.MockTransport(handler)
    )
    session_id, policy = await client.create_session("Financial services · PCI")
    binding = await client.bind_identity(
        session_id=session_id,
        speaker_track="SPEAKER_A",
        subject_token="oidc-subject-123",  # noqa: S106 - opaque test subject
        assurance="sso_verified",
        source="sso",
    )
    await client.protect(
        session_id=session_id,
        policy=policy,
        text="alice@example.com",
        final_egress=False,
        speaker_token=binding["llm_speaker_token"],
    )
    await client.protect(
        session_id=session_id,
        policy=policy,
        text="alice@example.com",
        final_egress=True,
    )
    await client.close()

    assert calls[0][1]["policy"] == "finance-eu-us-v1"
    assert calls[1][1]["speaker_track"] == "SPEAKER_A"
    assert calls[2][1]["destination"] == "agent-assist-local"
    assert calls[2][1]["speaker_token"] == "[SPEAKER_A1B2C3]"  # noqa: S105
    assert calls[3][1]["destination"] == "approved-finance-llm"
    assert calls[2][1]["idempotency_key"] != calls[3][1]["idempotency_key"]
