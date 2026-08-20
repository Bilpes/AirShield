import pytest

from app.main import AuthenticationError, MessageRate, authenticate, normalize_edge_event


@pytest.mark.asyncio
async def test_development_session_is_explicit_not_anonymous(monkeypatch):
    from app import main

    monkeypatch.setattr(main.settings, "dev_session_token", "development-browser-session")
    claims = await authenticate("development-browser-session")
    assert claims["sub"] == "development-user"
    with pytest.raises(AuthenticationError):
        await authenticate(None)


def test_unsigned_edge_allow_is_never_forwarded_as_egress_safe():
    event = normalize_edge_event(
        {
            "type": "transcript.final",
            "decision": "allow",
            "protected": "[EMAIL_ABCD1234]",
            "safe_for_egress": True,
            "receipt": {"receipt_id": "evt_1", "signature": "demo_unsigned"},
        }
    )
    assert event["decision"] == "block"
    assert event["safe_for_egress"] is False
    assert event["protected"] == ""


def test_message_rate_fails_closed(monkeypatch):
    from app import main

    monkeypatch.setattr(main.settings, "max_messages_per_second", 2)
    rate = MessageRate()
    assert rate.accept() is True
    assert rate.accept() is True
    assert rate.accept() is False
