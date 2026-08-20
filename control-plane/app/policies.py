from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .config import get_settings


class EntityRule(BaseModel):
    action: Literal["tokenize", "mask", "redact", "generalize"] = "tokenize"
    threshold: float = Field(ge=0, le=1)
    critical: bool = False


class Policy(BaseModel):
    id: str
    version: str
    language: str = "en"
    mapping_ttl_minutes: int = Field(ge=5, le=10080)
    raw_buffer_ttl_seconds: int = Field(ge=0, le=300)
    review_below_threshold: bool = True
    entities: dict[str, EntityRule]
    allowed_destinations: list[str]
    legal_tags: list[str]

    def destination_allowed(self, destination: str) -> bool:
        return destination in self.allowed_destinations or "*" in self.allowed_destinations


class PolicyRegistry:
    def __init__(self, directory: Path | None = None):
        self.policies: dict[str, Policy] = {}
        for file in (directory or get_settings().policy_directory).glob("*.yaml"):
            value = Policy.model_validate(yaml.safe_load(file.read_text()))
            if value.id in self.policies:
                raise RuntimeError(f"Duplicate policy ID: {value.id}")
            self.policies[value.id] = value
        if not self.policies:
            raise RuntimeError("No policies loaded; fail-closed")

    def get(self, policy_id: str) -> Policy:
        try:
            return self.policies[policy_id]
        except KeyError as exc:
            raise KeyError("Unknown policy") from exc

    def all(self) -> tuple[str, ...]:
        return tuple(sorted(self.policies))


@lru_cache(maxsize=1)
def get_policy_registry() -> PolicyRegistry:
    return PolicyRegistry(get_settings().policy_directory)
