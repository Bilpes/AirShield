from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    asr_model: str = "small.en"
    asr_device: str = "cpu"
    asr_compute_type: str = "int8"
    language: Literal["en"] = "en"
    enable_diarization: bool = False
    pyannote_model: str = "pyannote/speaker-diarization-3.1"
    hf_token: str | None = None
    model_manifest_path: Path = Path("/models/manifest.json")
    model_manifest_sha256: str | None = None
    min_process_bytes: int = Field(default=32_000, ge=4_096, le=5_000_000)
    process_interval_seconds: float = Field(default=2.5, ge=0.25, le=30)
    max_audio_bytes: int = Field(default=100_000_000, ge=1_000_000, le=1_000_000_000)
    max_concurrent_inference: int = Field(default=1, ge=1, le=32)
    allow_origins: str = "http://localhost:4174"

    control_plane_url: str | None = None
    control_plane_ca_file: Path | None = None
    control_plane_token_file: Path | None = None
    control_plane_dev_token: str | None = None
    control_plane_scope: str | None = None
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_federated_token_file: Path | None = None
    gateway_shared_secret: str | None = None
    gateway_previous_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def production_guards(self):
        if self.environment == "production":
            model_path = Path(self.asr_model)
            if not model_path.is_absolute() or not model_path.exists():
                raise ValueError("Production ASR_MODEL must be a preloaded absolute local path")
            if not self.model_manifest_path.is_file() or self.model_manifest_path.is_symlink():
                raise ValueError("Production requires a regular preloaded model manifest")
            if not self.model_manifest_sha256 or not re.fullmatch(
                r"[a-f0-9]{64}", self.model_manifest_sha256
            ):
                raise ValueError("Production requires the pinned model manifest SHA-256")
            if self.enable_diarization:
                diarization_path = Path(self.pyannote_model)
                if not diarization_path.is_absolute() or not diarization_path.exists():
                    raise ValueError("Production PYANNOTE_MODEL must be a preloaded absolute local path")
            if not self.control_plane_url or not self.control_plane_url.startswith("https://"):
                raise ValueError("Production edge requires an HTTPS CONTROL_PLANE_URL")
            if not self.control_plane_ca_file or not self.control_plane_ca_file.is_file():
                raise ValueError("Production edge requires the private control-plane CA file")
            if not self.gateway_shared_secret or len(self.gateway_shared_secret) < 32:
                raise ValueError("Production edge requires a strong gateway shared secret")
            if self.gateway_previous_secret and (
                len(self.gateway_previous_secret) < 32
                or self.gateway_previous_secret == self.gateway_shared_secret
            ):
                raise ValueError("Previous gateway secret must be strong and distinct")
            direct = bool(self.control_plane_token_file)
            azure = all(
                (
                    self.control_plane_scope,
                    self.azure_tenant_id,
                    self.azure_client_id,
                    self.azure_federated_token_file,
                )
            )
            if not direct and not azure:
                raise ValueError("Production edge requires projected or Azure workload identity")
        return self

    @property
    def origin_list(self) -> list[str]:
        return [item.strip() for item in self.allow_origins.split(",") if item.strip()]


settings = Settings()
