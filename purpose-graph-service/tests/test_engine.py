"""Deterministic eval for the PurposeGraph engine (Python mirror)."""
from __future__ import annotations

import pytest

from app.engine import (
    DEMO_ATTACHMENT,
    IntentSeal,
    CommitLock,
    MOCK_TOOLS,
    broker_credential,
    build_action_twin,
    detect_drift,
    evaluate,
    memory_fence,
    sha256_hex,
    short_id,
)


def _contract() -> IntentSeal:
    return IntentSeal.fresh("Refund invoice 4821 within an explicit cap", "refund", 5000, "originating-bank", ["customer_pii", "pan", "account_number", "ifsc"])


def _action(tool: str = "refund", amount: int = 5000, destination: str = "originating-bank", **extra) -> dict:
    params = {"invoice": "4821", "amount": amount, "currency": "INR", "recipient": "original_payment_method", **extra}
    return {"tool_id": tool, "tool_label": MOCK_TOOLS[tool]["label"], "params": params, "destination_id": destination, "destination_label": MOCK_TOOLS[tool]["destination_label"]}


def test_sha256_known_vector() -> None:
    assert sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_benign_within_contract_is_allowed() -> None:
    v = evaluate(_contract(), _action())
    assert v["decision"] == "allow"
    assert v["code"] == "contract_satisfied"


def test_amount_above_cap_blocked() -> None:
    v = evaluate(_contract(), _action(amount=50000))
    assert v["decision"] == "block"
    assert v["code"] == "contract_amount_exceeded"


def test_recipient_mismatch_blocked() -> None:
    v = evaluate(_contract(), _action(destination="external-bank"))
    assert v["decision"] == "block"
    assert v["code"] == "contract_recipient_mismatch"


def test_action_mismatch_blocked() -> None:
    v = evaluate(_contract(), _action(tool="transfer"))
    assert v["decision"] == "block"
    assert v["code"] == "contract_action_mismatch"


def test_prohibited_data_blocked() -> None:
    v = evaluate(_contract(), _action(pan="ABCDE1234F"))
    assert v["decision"] == "block"
    assert v["code"] == "contract_prohibited_data"


def test_commit_lock_valid_then_voided() -> None:
    contract = _contract()
    action = _action()
    lock = CommitLock.issue(contract, action, "agent", "user", "state123")
    assert lock.verify()["valid"] is True
    lock.status = "voided"
    assert lock.verify()["code"] == "lock_voided"


def test_drift_detected_after_approval() -> None:
    contract = _contract()
    lock = CommitLock.issue(contract, _action(), "agent", "user", "state123")
    drift = detect_drift(lock, _action(amount=50000, destination="external-bank"))
    assert drift["drifting"] is True
    assert drift["field"] == "destination"


def test_memory_fence_quarantines_injection() -> None:
    mem = memory_fence(DEMO_ATTACHMENT["hidden_injection"], "n_source", "attachment")
    assert mem["trust"] == "quarantined"
    benign = memory_fence("Refund approved invoice 4821 to the original payment method.", "n_user", "human")
    assert benign["trust"] == "trusted"


def test_action_twin_builds_diff() -> None:
    twin = build_action_twin(_action())
    assert twin["before"] == "No side effect yet"
    assert "after" in twin
    assert any(row["field"] == "amount" for row in twin["changed"])


def test_credential_is_one_use_bound() -> None:
    contract = _contract()
    lock = CommitLock.issue(contract, _action(), "agent", "user", "state123")
    cred = broker_credential(lock, _action())
    assert cred["status"] == "active"
    assert cred["bound_payload_hash"] == short_id(sha256_hex('{"tool":"refund","destination":"originating-bank","params":{"invoice":"4821","amount":5000,"currency":"INR","recipient":"original_payment_method"}}'))
    assert len(cred["bound_payload_hash"]) <= 12
