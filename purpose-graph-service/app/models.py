"""Pydantic schemas for the PurposeGraph service."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ActionName = Literal[
    "reset",
    "confirmIntent",
    "ingestSource",
    "proposeExploit",
    "proposeCorrect",
    "approve",
    "attackDrift",
    "execute",
    "revoke",
]


class TrustGraphRequest(BaseModel):
    action: ActionName = "reset"
    purpose: Optional[str] = None
    maximum_amount: Optional[float] = None
    permitted_recipient: Optional[str] = None
    prohibited_data: Optional[list[str]] = None


class TrustGraphResponse(BaseModel):
    ok: bool = True
    action: str
    decision: Optional[dict[str, Any]] = None
    approval: Optional[dict[str, Any]] = None
    state: dict[str, Any] = Field(default_factory=dict)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    trace: dict[str, Any] = Field(default_factory=dict)
