import pytest
from pydantic import ValidationError

from app.logging import scrub_value
from app.schemas import DeletionRequest, ProtectRequest, ReidentificationCreate


def test_nested_sensitive_log_fields_are_redacted():
    value = scrub_value(
        {
            "nested": {"text": "alice@example.com"},
            "items": [{"authorization": "Bearer secret"}],
            "message": "issued [EMAIL_ABC12345]",
        }
    )
    assert value["nested"]["text"] == "[REDACTED]"
    assert value["items"][0]["authorization"] == "[REDACTED]"
    assert value["message"] == "issued [PROTECTED_TOKEN]"


def test_speaker_token_cannot_put_a_name_in_evidence():
    with pytest.raises(ValidationError):
        ProtectRequest(
            session_id="ses_0123456789abcdef01234567",
            text="hello",
            policy="finance-eu-us-v1",
            destination="fraud-review",
            speaker_token="[SPEAKER_ALICE]",  # noqa: S106 - deliberately invalid privacy token
            idempotency_key="1234567890abcdef",
        )


def test_purpose_and_ticket_are_controlled_metadata():
    request = ReidentificationCreate(
        session_id="ses_0123456789abcdef01234567",
        token="[EMAIL_ABCD1234]",  # noqa: S106 - opaque application token
        purpose="fraud_investigation",
        ticket_reference="SEC-1042",
    )
    assert request.purpose == "fraud_investigation"
    with pytest.raises(ValidationError):
        ReidentificationCreate(
            session_id="ses_0123456789abcdef01234567",
            token="[EMAIL_ABCD1234]",  # noqa: S106 - opaque application token
            purpose="Alice asked for this",  # type: ignore[arg-type]
            ticket_reference="contains customer name",
        )
    assert DeletionRequest(purpose="privacy_erasure", ticket_reference="PRIV-9")
