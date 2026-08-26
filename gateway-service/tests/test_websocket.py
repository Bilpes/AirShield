import json

from fastapi.testclient import TestClient

from app import main


class FakeEdge:
    def __init__(self) -> None:
        self.queue: __import__("asyncio").Queue[str] = __import__("asyncio").Queue()
        self.sent: list[str | bytes] = []

    async def send(self, message: str | bytes) -> None:
        self.sent.append(message)
        if isinstance(message, bytes):
            await self.queue.put(
                json.dumps(
                    {
                        "type": "transcript.pair",
                        "raw": "alice@example.com",
                        "protected": "[EMAIL_ABCD1234]",
                        "safe_for_egress": False,
                    }
                )
            )
            return
        event = json.loads(message)
        if event["type"] == "session.start":
            await self.queue.put(json.dumps({"type": "session.ready", "language": "en"}))
        elif event["type"] == "session.end":
            await self.queue.put(
                json.dumps(
                    {
                        "type": "transcript.final",
                        "decision": "allow",
                        "protected": "[EMAIL_ABCD1234]",
                        "safe_for_egress": True,
                        "receipt": {"receipt_id": "evt_1", "signature": "s" * 88},
                    }
                )
            )

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        return await self.queue.get()


class FakeConnection:
    def __init__(self, edge: FakeEdge) -> None:
        self.edge = edge

    async def __aenter__(self) -> FakeEdge:
        return self.edge

    async def __aexit__(self, *_args) -> None:
        return None


def test_gateway_authenticates_rebuilds_protocol_and_injects_private_secret(monkeypatch):
    edge = FakeEdge()
    connection_headers: dict[str, str] = {}

    def connect(_url: str, **kwargs):
        connection_headers.update(kwargs["additional_headers"])
        return FakeConnection(edge)

    async def authenticated_claims(_token: str | None):
        return {"sub": "signed-host-subject", "airshield_speaker_track": "SPEAKER_A"}

    monkeypatch.setattr(main.websockets, "connect", connect)
    monkeypatch.setattr(main, "authenticate", authenticated_claims)
    monkeypatch.setattr(main.settings, "edge_gateway_secret", "private-edge-secret")
    client = TestClient(main.app)
    headers = {
        "origin": "http://localhost:4174",
        "cookie": "airshield_session=development-browser-session",
        "x-airshield-edge-auth": "client-forgery",
    }
    with client.websocket_connect("/ws/voice", headers=headers) as websocket:
        websocket.send_json(
            {
                "type": "session.start",
                "language": "en",
                "policy": "Healthcare · HIPAA",
                "audio_format": "audio/mp4",
                "x-airshield-edge-auth": "client-forgery",
            }
        )
        assert websocket.receive_json()["type"] == "session.ready"
        websocket.send_bytes(b"audio")
        pair = websocket.receive_json()
        assert pair["type"] == "transcript.pair"
        assert pair["safe_for_egress"] is False
        websocket.send_json({"type": "session.end", "unsafe": "ignored"})
        final = websocket.receive_json()
        assert final["type"] == "transcript.final"
        assert final["safe_for_egress"] is True

    assert connection_headers == {"x-airshield-edge-auth": "private-edge-secret"}
    start = json.loads(edge.sent[0])
    assert start == {
        "type": "session.start",
        "language": "en",
        "policy": "Healthcare · HIPAA",
        "audio_format": "audio/mp4",
        "host_identity": {
            "speaker_track": "SPEAKER_A",
            "subject_token": "signed-host-subject",
            "assurance": "sso_verified",
            "source": "sso",
        },
    }
    assert json.loads(edge.sent[-1]) == {"type": "session.end"}
