"""FastAPI application for the AirShield PurposeGraph service."""
from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .engine import (
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
from .models import TrustGraphRequest, TrustGraphResponse

app = FastAPI(title="AirShield PurposeGraph", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4174", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _Graph:
    """In-memory session store. Swap for a persistent store in production."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.consent_ok = True
        self.nodes: list[dict[str, Any]] = [
            {"id": "n_consent", "kind": "consent", "status": "active", "group": "human", "label": "Consent (revocable)", "detail": "User consent grant"},
            {"id": "n_user", "kind": "user", "status": "active", "group": "human", "label": "User (Karan Malhotra)", "detail": "Authenticated agent operator"},
            {"id": "n_intent", "kind": "intent", "status": "pending", "group": "human", "label": "IntentSeal contract", "detail": "Machine-readable human intent"},
            {"id": "n_agent", "kind": "agent", "status": "active", "group": "agent", "label": "Fina-bot", "detail": "Agent + model"},
        ]
        self.edges: list[dict[str, Any]] = [
            {"from": "n_consent", "to": "n_intent", "kind": "consent", "label": "grants consent", "status": "open"},
            {"from": "n_user", "to": "n_intent", "kind": "consent", "label": "expresses intent", "status": "open"},
            {"from": "n_intent", "to": "n_agent", "kind": "authorization", "label": "authorizes (binding)", "status": "open"},
        ]
        self.intent: IntentSeal | None = None
        self.lock: Any = None
        self.twin: dict[str, Any] | None = None
        self.last: dict[str, Any] | None = None
        self.approval: dict[str, Any] | None = None
        self.memory: dict[str, Any] | None = None
        self.credential: dict[str, Any] | None = None
        self.executed = False
        self.applied: str | None = None
        self.drift: dict[str, Any] | None = None
        self.logs: list[dict[str, Any]] = []

    def log(self, phase: str, actor: str, message: str, tone: str, verdict: str | None = None, code: str | None = None) -> None:
        self.logs.append({"phase": phase, "actor": actor, "message": message, "tone": tone, "verdict": verdict, "code": code})

    def snapshot(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "intentSeal": vars(self.intent) if self.intent else None,
            "lock": vars(self.lock) if self.lock else None,
            "memory": self.memory,
            "credential": self.credential,
            "consentRevoked": not self.consent_ok,
            "executed": self.executed,
            "applied": self.applied,
            "drift": self.drift,
            "logs": self.logs[-40:],
        }

    # -- narrative steps ----------------------------------------------------
    def confirm_intent(self, contract: IntentSeal) -> None:
        self.intent = contract
        self._node_status("n_intent", "active")
        self._edge_status("n_consent", "n_intent", "confirmed")
        self._edge_status("n_user", "n_intent", "confirmed")
        self._edge_status("n_intent", "n_agent", "confirmed")
        self.log("intent", "IntentSeal", "Voice/text intent parsed into a machine-readable contract. Agent's natural-language explanation is NOT treated as authorization.", "seal", "intent_sealed")

    def ingest_source(self) -> None:
        self._node("n_source", "source", "source", "invoice_4821.pdf", "Attached synthetic document", "active")
        self._edge("n_agent", "n_source", "data-flow", "reads attachment", "open")
        self.log("source", "Agent", "Read attachment. Provenance marked untrusted.", "info")
        self._node("n_inject", "source", "source", "Hidden instruction", "Prompt injection inside attachment", "active", risk="high")
        self._edge("n_source", "n_inject", "derivation", "contains hidden instruction", "open")
        self.log("source", "Safety harness", "Prompt shield-style scan flags a hidden instruction in the attachment.", "warn", "injection_detected")
        self.memory = memory_fence(DEMO_ATTACHMENT["hidden_injection"], "n_source", "attachment:invoice_4821.pdf")
        self._node("n_memwrite", "memory", "data", "Memory write attempt", "Proposed persistent memory entry", "quarantined")
        self._edge("n_inject", "n_memwrite", "memory", "writes memory", "quarantined")
        self.log("memory", "MemoryFence", "Untrusted attachment requested a persistent memory write. Quarantined; provenance pinned; TTL and tenant boundary enforced.", "revoke", "memory_quarantined")

    def propose_exploit(self) -> None:
        action = {
            "tool_id": "transfer", "tool_label": MOCK_TOOLS["transfer"]["label"],
            "params": {"account": "492188407721", "ifsc": "HDFC0001234", "amount": 50000, "currency": "INR", "narrative": "approved refund"},
            "destination_id": "external-bank", "destination_label": MOCK_TOOLS["transfer"]["destination_label"],
        }
        self.last = evaluate(self.intent, action)
        self.twin = build_action_twin(action)
        self._node("n_tool_transfer", "tool", "agent", "External transfer", "Synthetic payments connector", "active")
        self._edge("n_agent", "n_tool_transfer", "execution", "proposes transfer", "open")
        self._node("n_dest_external", "destination", "boundary", "External bank", "492188407721 · unapproved", "active", risk="high")
        self._edge("n_tool_transfer", "n_dest_external", "data-flow", "routes to external", "open")
        self.log("gate", "PurposeGraph gate", self.last["reason"], "block", self.last["code"])

    def propose_correct(self) -> None:
        action = {
            "tool_id": "refund", "tool_label": MOCK_TOOLS["refund"]["label"],
            "params": {"invoice": "4821", "amount": 5000, "currency": "INR", "recipient": "original_payment_method"},
            "destination_id": "originating-bank", "destination_label": MOCK_TOOLS["refund"]["destination_label"],
        }
        self._node_status("n_tool_transfer", "blocked")
        self.last = evaluate(self.intent, action)
        self.twin = build_action_twin(action)
        self._node("n_tool_refund", "tool", "agent", "Refund · original method", "Synthetic banking connector", "active")
        self._edge("n_agent", "n_tool_refund", "execution", "proposes refund", "open")
        self._node("n_dest_orig", "destination", "boundary", "Original payment method", "Bank 4821 · approved", "active")
        self._edge("n_tool_refund", "n_dest_orig", "data-flow", "routes to bank 4821", "open")
        self.log("gate", "PurposeGraph gate", self.last["reason"], "allow", self.last["code"])
        self.log("twin", "ActionTwin", "Dry-run shows the exact before/after state difference. Nothing is committed yet.", "flow", "action_twin")

    def approve(self) -> None:
        action = {
            "tool_id": "refund", "tool_label": MOCK_TOOLS["refund"]["label"],
            "params": {"invoice": "4821", "amount": 5000, "currency": "INR", "recipient": "original_payment_method"},
            "destination_id": "originating-bank", "destination_label": MOCK_TOOLS["refund"]["destination_label"],
        }
        state_hash = sha256_hex(json.dumps(sorted({n["id"] for n in self.nodes})) + self.intent.hash)
        self.lock = CommitLock.issue(self.intent, action, "fina-bot-v3", "karan.malhotra@northbank.example", state_hash)
        self.approval = {"granted": True, "code": "approved", "reason": "Human approval bound to the exact tool, destination, payload hash and state hash."}
        self._node("n_approval", "approval", "human", "Human approval (CommitLock)", "Hash-bound one-time approval", "active")
        self._edge("n_approval", "n_tool_refund", "authorization", "approves (one-time)", "confirmed")
        self.log("approval", "CommitLock", "Approval bound to lock over agent identity, authenticated user, exact tool, exact destination, canonical payload hash and current state hash.", "seal", "commit_lock")

    def attack_drift(self) -> None:
        tampered = {
            "tool_id": "transfer", "tool_label": MOCK_TOOLS["transfer"]["label"],
            "params": {"account": "492188407721", "ifsc": "HDFC0001234", "amount": 50000, "currency": "INR", "narrative": "approved refund"},
            "destination_id": "external-bank", "destination_label": MOCK_TOOLS["transfer"]["destination_label"],
        }
        self.drift = detect_drift(self.lock, tampered)
        check = self.lock.verify()
        self.last = evaluate(self.intent, tampered)
        if self.drift["drifting"] or not check["valid"]:
            self.lock.status = "voided"
            self.approval = {"granted": False, "code": "commit_lock_voided", "reason": "A field changed after approval; the CommitLock no longer matches."}
            self._node_status("n_approval", "voided")
            self.log("gate", "PurposeGraph gate", f"POST-APPROVAL DRIFT: proposed destination changed. The valid approval no longer matches the proposed execution.", "revoke", "lock_voided")

    def execute(self) -> None:
        if self.lock is None or self.lock.status != "issued":
            return
        check = self.lock.verify()
        if not check["valid"]:
            self.last = {"decision": "block", "code": "lock_invalid_during_execute", "reason": "Cannot execute: the approval is not currently valid.", "enforcements": ["No tool call", "No credential"]}
            return
        action = {
            "tool_id": "refund", "tool_label": MOCK_TOOLS["refund"]["label"],
            "params": {"invoice": "4821", "amount": 5000, "currency": "INR", "recipient": "original_payment_method"},
            "destination_id": "originating-bank", "destination_label": MOCK_TOOLS["refund"]["destination_label"],
        }
        self.credential = broker_credential(self.lock, action)
        self.executed = True
        self.lock.status = "consumed"
        self.credential["status"] = "consumed"
        self.applied = "Refund ₹5,000 for invoice 4821 routed to the original payment method (bank 4821)."
        self._node("n_credential", "credential", "boundary", "One-use credential", "Borrowed by broker at execution", "consumed")
        self._edge("n_credential", "n_tool_refund", "authorization", "issues one-use credential", "open")
        self._node("n_receipt", "receipt", "boundary", "Execution receipt", "Signed synthetic connector action", "executed")
        self._edge("n_tool_refund", "n_receipt", "execution", "emits receipt", "confirmed")
        self.log("execute", "Broker", "One-use credential attached at execution time only. The model never receives the real secret.", "seal", "credential_issued")
        self.log("execute", "Receipt", "Synthetic connector action completed and signed; model received no raw values. Credential consumed.", "allow", "receipt_issued")

    def revoke(self) -> None:
        self.consent_ok = False
        self._node_status("n_consent", "revoked")
        self._node_status("n_approval", "revoked")
        for edge in self.edges:
            if edge["from"] in ("n_consent",) or (edge["to"] in ("n_intent", "n_approval") and edge["from"] == "n_consent"):
                edge["status"] = "revoked"
        if self.credential and self.credential["status"] == "active":
            self.credential["status"] = "revoked"
        if self.memory:
            self.memory["trust"] = "quarantined"
        self.log("revoke", "Causal revocation", "Consent revoked. PurposeGraph traversed the graph and cancelled pending one-use capabilities, queued tools and uncommitted memory writes.", "revoke", "causal_revocation")

    # -- helpers ------------------------------------------------------------
    def _node(self, id_: str, kind: str, group: str, label: str, detail: str, status: str, risk: str | None = None) -> None:
        for n in self.nodes:
            if n["id"] == id_:
                n.update({"status": status, "risk": risk or n.get("risk")})
                return
        self.nodes.append({"id": id_, "kind": kind, "group": group, "label": label, "detail": detail, "status": status, "risk": risk})

    def _node_status(self, id_: str, status: str) -> None:
        for n in self.nodes:
            if n["id"] == id_:
                n["status"] = status

    def _edge(self, frm: str, to: str, kind: str, label: str, status: str) -> None:
        for e in self.edges:
            if e["from"] == frm and e["to"] == to:
                e["status"] = status
                return
        self.edges.append({"from": frm, "to": to, "kind": kind, "label": label, "status": status})

    def _edge_status(self, frm: str, to: str, status: str) -> None:
        for e in self.edges:
            if e["from"] == frm and e["to"] == to:
                e["status"] = status

    def response(self) -> dict[str, Any]:
        intent = self.intent
        return {
            "state": {
                "binding_hash": vars(self.lock).get("canonical_payload_hash") if self.lock else None,
                "lock_status": self.lock.status if self.lock else None,
                "contract_hash": short_id(intent.hash) if intent else None,
                "consent_revoked": not self.consent_ok,
                "executed": self.executed,
                "memory": self.memory["trust"] if self.memory else None,
            },
            "decision": self.last,
            "approval": self.approval,
        }


import json  # noqa: E402

_store = _Graph()


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "purposegraph"}


@app.post("/v1/trust-graph/run", response_model=TrustGraphResponse)
def run(req: TrustGraphRequest) -> TrustGraphResponse:
    _store._reset() if req.action == "reset" else None
    if req.action == "confirmIntent":
        _store.confirm_intent(IntentSeal.fresh(req.purpose or "Refund invoice 4821 within an explicit cap", "refund", req.maximum_amount or 5000, req.permitted_recipient or "originating-bank", req.prohibited_data or ["customer_pii", "pan", "account_number", "ifsc"]))
    elif req.action == "ingestSource":
        _store.ingest_source()
    elif req.action == "proposeExploit":
        _store.propose_exploit()
    elif req.action == "proposeCorrect":
        _store.propose_correct()
    elif req.action == "approve":
        _store.approve()
    elif req.action == "attackDrift":
        _store.attack_drift()
    elif req.action == "execute":
        _store.execute()
    elif req.action == "revoke":
        _store.revoke()
    return TrustGraphResponse(ok=True, action=req.action, **_store.response(), snapshot=_store.snapshot(), trace={"progress": min(1.0, _store.logs.__len__() * 0.1)})
