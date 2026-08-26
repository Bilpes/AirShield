from fastapi.testclient import TestClient

from app import main


class FakeControlPlane:
    def __init__(self) -> None:
        self.protect_calls: list[bool] = []
        self.protect_payloads: list[dict] = []
        self.binding_calls: list[dict] = []

    async def create_session(self, policy_label: str):
        assert policy_label == "Healthcare · HIPAA"
        return "ses_0123456789abcdef01234567", "healthcare-us-eu-v1"

    async def bind_identity(self, **kwargs):
        self.binding_calls.append(kwargs)
        return {"llm_speaker_token": "[SPEAKER_A1B2C3]"}

    async def protect(self, **kwargs):
        final = bool(kwargs["final_egress"])
        self.protect_calls.append(final)
        self.protect_payloads.append(kwargs)
        if final:
            return {
                "decision": "block",
                "protected_text": "",
                "entities": [],
                "receipt": {"receipt_id": "evt_final", "signature": "s" * 88},
            }
        return {
            "decision": "allow",
            "protected_text": "Call [EMAIL_ABCD1234] now",
            "entities": [],
            "receipt": {"receipt_id": "evt_provisional", "signature": "s" * 88},
        }

    async def close(self) -> None:
        return None


def test_unsigned_final_allow_is_converted_to_block():
    result = main.enforce_signed_final(
        {
            "decision": "allow",
            "protected_text": "[EMAIL_ABCD1234]",
            "entities": [],
            "receipt": {"receipt_id": "evt_unsigned", "signature": "demo_unsigned"},
        }
    )
    assert result["decision"] == "block"
    assert result["protected_text"] == ""
    assert result["reason_codes"] == ["signed_final_receipt_required"]


def test_websocket_marks_chunks_provisional_and_requires_signed_final(monkeypatch):
    fake = FakeControlPlane()
    monkeypatch.setattr(main, "control", fake)
    monkeypatch.setattr(main.settings, "environment", "production")
    monkeypatch.setattr(main.settings, "gateway_shared_secret", "g" * 32)
    monkeypatch.setattr(main.settings, "allow_origins", "https://app.example.com")
    monkeypatch.setattr(
        main,
        "transcribe",
        lambda _: (
            "Call alice@example.com now",
            [{"start": 0.0, "end": 1.0, "text": "Call alice@example.com now"}],
        ),
    )
    monkeypatch.setattr(main, "diarize", lambda _: [])

    headers = {
        "origin": "https://app.example.com",
        "x-airshield-edge-auth": "g" * 32,
    }
    # Do not enter TestClient as a context: the production lifespan intentionally
    # rejects an unconfigured real control plane. This test injects the bounded fake.
    client = TestClient(main.app)
    with client.websocket_connect("/ws/voice", headers=headers) as websocket:
        websocket.send_json(
            {
                "type": "session.start",
                "language": "en",
                "policy": "Healthcare · HIPAA",
                "host_identity": {
                    "speaker_track": "SPEAKER_A",
                    "subject_token": "signed-host-subject",
                    "assurance": "sso_verified",
                    "source": "sso",
                },
            }
        )
        ready = websocket.receive_json()
        assert ready["type"] == "session.ready"
        websocket.send_bytes(b"0" * main.settings.min_process_bytes)
        pair = websocket.receive_json()
        assert pair["type"] == "transcript.pair"
        assert pair["safe_for_egress"] is False
        assert pair["provisional"] is True
        assert pair["speaker_token"] == "[SPEAKER_A1B2C3]"  # noqa: S105
        websocket.send_json({"type": "session.end"})
        final = websocket.receive_json()
        assert final["type"] == "transcript.final"
        assert final["decision"] == "block"
        assert final["safe_for_egress"] is False
        assert final["protected"] == ""
        assert len(final["receipt"]["signature"]) == 88

    assert fake.binding_calls[0]["subject_token"] == "signed-host-subject"  # noqa: S105
    assert fake.protect_calls == [False, True]
    assert fake.protect_payloads[0]["speaker_token"] == "[SPEAKER_A1B2C3]"  # noqa: S105
    assert fake.protect_payloads[1].get("speaker_token") is None


def test_session_end_flushes_short_final_audio_chunk(monkeypatch):
    fake = FakeControlPlane()
    monkeypatch.setattr(main, "control", fake)
    monkeypatch.setattr(main.settings, "environment", "production")
    monkeypatch.setattr(main.settings, "gateway_shared_secret", "g" * 32)
    monkeypatch.setattr(
        main,
        "transcribe",
        lambda path: (
            "Email alice@example.com",
            [{"start": 0.0, "end": 0.7, "text": "Email alice@example.com"}],
        ),
    )
    monkeypatch.setattr(main, "diarize", lambda _: [])

    client = TestClient(main.app)
    with client.websocket_connect("/ws/voice", headers={"x-airshield-edge-auth": "g" * 32}) as websocket:
        websocket.send_json(
            {
                "type": "session.start",
                "language": "en",
                "policy": "Healthcare · HIPAA",
                "audio_format": "audio/webm;codecs=opus",
            }
        )
        assert websocket.receive_json()["type"] == "session.ready"
        websocket.send_bytes(b"short-audio")
        websocket.send_json({"type": "session.end"})

        pair = websocket.receive_json()
        assert pair["type"] == "transcript.pair"
        assert pair["raw"] == "Email alice@example.com"
        final = websocket.receive_json()
        assert final["type"] == "transcript.final"
        assert final["safe_for_egress"] is False

    assert fake.protect_calls == [False, True]
