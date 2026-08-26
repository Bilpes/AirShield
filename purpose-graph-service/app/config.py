"""Settings for the PurposeGraph service."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # External KMS/HSM signing is out of scope for the demo build; a dev key is
    # used unless a real key provider is supplied. Never ship a real secret in
    # source control.
    signing_key: str = "airshield-purposegraph-development-key"
    environment: str = "development"
    session_ttl_seconds: int = 300

    class Config:
        env_prefix = "PURPOSEGRAPH_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
