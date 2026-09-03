"""Local (no-Docker, no-control-plane) development-mode tests.

These cover the run_local.sh / run_dev_edge.sh path: the edge runs standalone
with the in-memory PrivacyEngine and must still hand the browser a *signed*
final receipt so live voice demos complete end-to-end on a laptop. Production
never reaches this path (config.py production guards require a control plane).
"""

from fastapi.testclient import TestClient

from app import main


def _standalone_dev_client(monkeypatch):
    # No control plane -> local PrivacyEngine path (created when control is None).
    monkeypatch.setattr(main, "control", None)
    monkeypatch.setattr(main, "privacy", main.PrivacyEngine())
    monkeypatch.setattr(main.settings, "environment", "development")
    monkeypatch.setattr(main.settings, "allow_origins", "http://localhost:4174")
    monkeypatch.setattr(
        main,
        "transcribe",
        lambda _path: (
            "Patient is Jack with email jack@example.com call 5551234567",
            [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Patient is Jack with email jack@example.com call 5551234567",
                }
            ],
        ),
    )
    monkeypatch.setattr(main, "diarize", lambda _path: [])
    return TestClient(main.app)


def test_interim_local_turns_remain_provisional_and_unsigned(monkeypatch):
    client = _standalone_dev_client(monkeypatch)
    with client.websocket_connect("/ws/voice") as ws:
        ws.send_json(
            {
                "type": "session.start",
                "language": "en",
                "policy": "Healthcare · HIPAA",
                "audio_format": "audio/webm",
            }
        )
        assert ws.receive_json()["type"] == "session.ready"
        # Enough bytes to cross min_process_bytes; session.end forces the flush,
        # then we drain the interim pair before the final message.
        ws.send_bytes(b"x" * main.settings.min_process_bytes)
        ws.send_json({"type": "session.end"})
        messages = []
        for _ in range(3):
            messages.append(ws.receive_json())
            if messages[-1]["type"] == "transcript.final":
                break
        pair = next(m for m in messages if m["type"] == "transcript.pair")
        assert pair["safe_for_egress"] is False
        assert pair["provisional"] is True
        assert pair["decision"] == "review"


def test_local_final_receipt_is_signed_and_allow(monkeypatch):
    client = _standalone_dev_client(monkeypatch)
    with client.websocket_connect("/ws/voice") as ws:
        ws.send_json(
            {
                "type": "session.start",
                "language": "en",
                "policy": "Healthcare · HIPAA",
                "audio_format": "audio/webm",
            }
        )
        ws.receive_json()  # session.ready
        ws.send_bytes(b"x" * main.settings.min_process_bytes)
        ws.receive_json()  # interim transcript.pair
        ws.send_json({"type": "session.end"})
        final = ws.receive_json()
        assert final["type"] == "transcript.final"
        assert final["decision"] == "allow"
        assert final["safe_for_egress"] is True
        receipt = final["receipt"]
        signature = receipt["signature"]
        # Frontend egress gate: real signature, at least 40 chars, not the
        # unsigned placeholder.
        assert signature != "demo_unsigned"
        assert len(signature) >= 40
        assert receipt["environment"] == "development"
        assert receipt["receipt_id"].startswith("devrcpt_")
        # Masking must have happened before signing.
        assert "jack@example.com" not in final["protected"]
        assert "[EMAIL_" in final["protected"]


def test_local_protect_http_route_signs_final(monkeypatch):
    _standalone_dev_client(monkeypatch)
    result = main.local_protect("email jack@example.com", {}, final_egress=True, policy="healthcare-us-eu-v1")
    assert result["decision"] == "allow"
    assert result["receipt"]["signature"] != "demo_unsigned"
    assert len(result["receipt"]["signature"]) >= 40


def test_local_protect_interim_stays_unsigned(monkeypatch):
    _standalone_dev_client(monkeypatch)
    result = main.local_protect("email jack@example.com", {})
    assert result["decision"] == "review"
    assert result["receipt"]["signature"] == "demo_unsigned"


def test_development_receipt_signature_binds_content():
    import base64
    import hashlib
    import hmac

    def expected_signature(receipt_id, protected, policy, decision, created_at):
        content_sha256 = hashlib.sha256(protected.encode()).hexdigest()
        signing_input = "|".join(
            ["airshield-development-receipt-v1", receipt_id, decision, policy, content_sha256, created_at]
        )
        return (
            base64.urlsafe_b64encode(
                hmac.new(main.DEVELOPMENT_RECEIPT_KEY, signing_input.encode(), hashlib.sha256).digest()
            )
            .decode()
            .rstrip("=")
        )

    receipt = main.development_signed_receipt(
        protected="Patient [PERSON_1]",
        entities=[{"type": "PERSON"}],
        policy="healthcare-us-eu-v1",
        decision="allow",
    )
    # The issued signature verifies under the pinned development key.
    assert hmac.compare_digest(
        receipt["signature"],
        expected_signature(
            receipt["receipt_id"], "Patient [PERSON_1]", "healthcare-us-eu-v1", "allow", receipt["created_at"]
        ),
    )
    # Tampering with the protected content invalidates the signature.
    assert not hmac.compare_digest(
        receipt["signature"],
        expected_signature(
            receipt["receipt_id"], "Patient Jack", "healthcare-us-eu-v1", "allow", receipt["created_at"]
        ),
    )
