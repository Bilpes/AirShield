from __future__ import annotations

import base64
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ALLOWED_WORKLOAD_SCOPES = {
    "airshield.protect",
    "airshield.bind",
    "airshield.evidence.read",
    "airshield.delete",
}


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://airshield:airshield@localhost:5432/airshield"

    auth_mode: Literal["oidc", "dev"] = "dev"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    tenant_claim: str = "tid"
    workload_bindings_json: str = "{}"

    key_provider: Literal["azure", "openbao", "local"] = "local"
    azure_key_vault_url: str | None = None
    azure_wrap_key_name: str = "airshield-wrap"
    azure_sign_key_name: str = "airshield-receipt-sign"
    openbao_addr: str | None = None
    openbao_token_file: Path = Path("/var/run/secrets/openbao/token")
    openbao_transit_mount: str = "transit"
    openbao_wrap_key: str = "airshield-wrap"
    openbao_sign_key: str = "airshield-sign"
    local_master_key_b64: str | None = None
    local_signing_private_key_b64: str | None = None
    token_index_key_b64: str | None = None

    policy_directory: Path = Path(__file__).resolve().parent.parent / "policies"
    fail_closed: bool = True
    allow_raw_in_api: bool = False
    max_text_bytes: int = Field(default=262_144, ge=1, le=10_000_000)
    allowed_origins: str = "http://localhost:4174"
    log_level: str = "INFO"
    evidence_retention_days: int = Field(default=2555, ge=365)
    audit_export_required: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def production_guards(self):
        try:
            bindings = json.loads(self.workload_bindings_json)
        except json.JSONDecodeError as exc:
            raise ValueError("WORKLOAD_BINDINGS_JSON must be valid JSON") from exc
        if not isinstance(bindings, dict):
            raise ValueError("WORKLOAD_BINDINGS_JSON must be an object keyed by exact OIDC subject")
        for subject, binding in bindings.items():
            if not isinstance(subject, str) or not subject or not isinstance(binding, dict):
                raise ValueError("Every workload binding requires an exact subject and object value")
            tenant_id = binding.get("tenant_id")
            scopes = binding.get("scopes")
            if not isinstance(tenant_id, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", tenant_id
            ):
                raise ValueError("Every workload binding requires a safe bounded tenant_id")
            if (
                not isinstance(scopes, list)
                or not scopes
                or not all(isinstance(scope, str) and scope in ALLOWED_WORKLOAD_SCOPES for scope in scopes)
            ):
                raise ValueError("Workload bindings contain an unsupported or empty scope set")
        if self.environment == "production":
            if self.auth_mode != "oidc":
                raise ValueError("Production requires OIDC workload identity")
            if self.key_provider == "local":
                raise ValueError("Production forbids the local key provider")
            if not all((self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url)):
                raise ValueError("Production requires OIDC issuer, audience, and JWKS URL")
            if not self.oidc_issuer.startswith("https://") or not self.oidc_jwks_url.startswith("https://"):
                raise ValueError("Production OIDC endpoints must use HTTPS")
            try:
                database = make_url(self.database_url)
                ssl_mode = str(database.query.get("ssl", "")).lower()
            except Exception as exc:
                raise ValueError("Production DATABASE_URL is invalid") from exc
            if database.drivername != "postgresql+asyncpg" or ssl_mode != "verify-full":
                raise ValueError("Production requires async PostgreSQL TLS with hostname verification")
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
                    raise ValueError("Production CORS origins must be exact HTTPS origins")
            if self.key_provider == "azure" and not (
                self.azure_key_vault_url and self.azure_key_vault_url.startswith("https://")
            ):
                raise ValueError("Production Azure key custody requires an HTTPS Key Vault URL")
            if self.key_provider == "openbao" and not (
                self.openbao_addr and self.openbao_addr.startswith("https://")
            ):
                raise ValueError("Production OpenBao key custody requires an HTTPS address")
            if not self.fail_closed:
                raise ValueError("Production must fail closed")
            if self.allow_raw_in_api:
                raise ValueError("Production API responses must not expose raw detected values")
            if not self.audit_export_required:
                raise ValueError("Production requires immutable audit export")
        if not self.token_index_key_b64:
            raise ValueError("TOKEN_INDEX_KEY_B64 is required")
        try:
            index = base64.b64decode(self.token_index_key_b64, validate=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("TOKEN_INDEX_KEY_B64 must be valid base64") from exc
        if len(index) < 32:
            raise ValueError("TOKEN_INDEX_KEY_B64 must decode to at least 32 bytes")
        if self.key_provider == "local":
            if not self.local_master_key_b64 or not self.local_signing_private_key_b64:
                raise ValueError("Local master and signing keys are required for the local key provider")
            try:
                master = base64.b64decode(self.local_master_key_b64, validate=True)
                signing = base64.b64decode(self.local_signing_private_key_b64, validate=True)
            except (TypeError, ValueError) as exc:
                raise ValueError("Local key settings must be valid base64") from exc
            if len(master) != 32:
                raise ValueError("LOCAL_MASTER_KEY_B64 must decode to 32 bytes")
            if len(signing) != 32:
                raise ValueError("LOCAL_SIGNING_PRIVATE_KEY_B64 must decode to 32 bytes")
        return self

    @property
    def origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def workload_bindings(self) -> dict[str, dict[str, object]]:
        return json.loads(self.workload_bindings_json)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
