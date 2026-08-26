import pytest

from app.detection import Detector
from app.policies import PolicyRegistry


def test_all_sector_policies_load_and_are_english_only():
    registry = PolicyRegistry()
    expected = {
        "healthcare-us-eu-v1",
        "finance-eu-us-v1",
        "insurance-eu-us-v1",
        "contact-center-eu-us-v1",
        "saas-copilot-eu-us-v1",
    }
    assert set(registry.all()) == expected
    assert all(registry.get(policy_id).language == "en" for policy_id in expected)


def test_deterministic_detection_for_pii_pci_and_secrets():
    detector = Detector()
    text = "Email alice@example.com, card 4111 1111 1111 1111, key sk_live_1234567890ABCD."
    found = detector.detect(text, {"EMAIL", "CARD_OR_ACCOUNT", "SECRET"})
    assert {item.entity_type for item in found} == {"EMAIL", "CARD_OR_ACCOUNT", "SECRET"}
    assert all(text[item.start : item.end] == item.raw for item in found)


def test_context_labels_detect_short_account_and_phone_values():
    detector = Detector()
    text = "Customer jack, account 123456789, called from +91 123456789 and email jack@example.com."
    found = detector.detect(text, {"CARD_OR_ACCOUNT", "PHONE", "EMAIL"})
    assert [item.entity_type for item in found] == ["CARD_OR_ACCOUNT", "PHONE", "EMAIL"]
    assert [item.raw for item in found] == ["123456789", "+91 123456789", "jack@example.com"]
    assert all(text[item.start : item.end] == item.raw for item in found)


def test_contextual_detection_fails_closed_when_model_unavailable():
    detector = Detector()
    if detector.analyzer is not None:
        pytest.skip("A contextual model is installed in this test environment")
    with pytest.raises(RuntimeError, match="Contextual detector unavailable"):
        detector.detect("My name is Alice", {"PERSON"})
