from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    edge_websocket_url: str = "ws://airshield-edge:8001/ws/voice"
    edge_ca_file: Path | None = None
    edge_gateway_secret: str | None = None
    allow_origins: str = "http://localhost:4174"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    tenant_claim: str = "tid"
    expected_tenant_id: str | None = None
    speaker_track_claim: str = "airshield_speaker_track"
    session_cookie_name: str = "airshield_session"
    dev_session_token: str | None = None
    max_connections: int = Field(default=200, ge=1, le=100_000)
    max_message_bytes: int = Field(default=1_048_576, ge=4_096, le=10_000_000)
    max_session_audio_bytes: int = Field(default=100_000_000, ge=1_000_000, le=1_000_000_000)
    max_messages_per_second: int = Field(default=20, ge=1, le=1_000)
    max_session_seconds: int = Field(default=3_600, ge=60, le=14_400)
    final_wait_seconds: int = Field(default=15, ge=1, le=60)

    @model_validator(mode="after")
    def production_guards(self):
        if self.environment == "production":
            required = {
                "OIDC_ISSUER": self.oidc_issuer,
                "OIDC_AUDIENCE": self.oidc_audience,
                "OIDC_JWKS_URL": self.oidc_jwks_url,
                "EXPECTED_TENANT_ID": self.expected_tenant_id,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"Production gateway requires {', '.join(missing)}")
            if not self.oidc_issuer.startswith("https://") or not self.oidc_jwks_url.startswith("https://"):
                raise ValueError("Production OIDC endpoints must use HTTPS")
            if not self.edge_gateway_secret or len(self.edge_gateway_secret) < 32:
                raise ValueError("Production gateway requires a strong edge secret")
            for origin in self.origin_list:
                parsed_origin = urlparse(origin)
                if (
                    "*" in origin
                    or parsed_origin.scheme != "https"
                    or not parsed_origin.netloc
                    or parsed_origin.path not in {"", "/"}
                    or parsed_origin.query
                    or parsed_origin.fragment
                ):
                    raise ValueError("Production origins must be exact HTTPS origins")
            if not self.edge_websocket_url.startswith("wss://"):
                raise ValueError("Production gateway must use encrypted WSS to the private edge")
            if not self.edge_ca_file or not self.edge_ca_file.is_file():
                raise ValueError("Production gateway requires the private edge CA file")
        return self

    @property
    def origin_list(self) -> list[str]:
        return [item.strip().rstrip("/") for item in self.allow_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
