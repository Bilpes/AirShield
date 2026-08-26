import base64

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_dev_auth_and_local_keys():
    with pytest.raises(ValidationError, match="Production requires OIDC"):
        Settings(
            environment="production",
            auth_mode="dev",
            key_provider="local",
            local_master_key_b64=base64.b64encode(b"m" * 32).decode(),
            local_signing_private_key_b64=base64.b64encode(b"s" * 32).decode(),
            token_index_key_b64=base64.b64encode(b"i" * 32).decode(),
        )


def test_production_rejects_database_tls_without_hostname_verification():
    with pytest.raises(ValidationError, match="hostname verification"):
        Settings(
            environment="production",
            auth_mode="oidc",
            key_provider="openbao",
            oidc_issuer="https://issuer.example",
            oidc_audience="airshield",
            oidc_jwks_url="https://issuer.example/keys",
            openbao_addr="https://openbao.example",
            database_url="postgresql+asyncpg://airshield:test@postgres/airshield?ssl=require",
            allowed_origins="https://airshield.example",
            token_index_key_b64=base64.b64encode(b"i" * 32).decode(),
        )


def test_production_requires_fail_closed():
    with pytest.raises(ValidationError, match="fail closed"):
        Settings(
            environment="production",
            auth_mode="oidc",
            key_provider="openbao",
            oidc_issuer="https://issuer.example",
            oidc_audience="airshield",
            oidc_jwks_url="https://issuer.example/keys",
            openbao_addr="https://openbao.example",
            database_url="postgresql+asyncpg://airshield:test@postgres/airshield?ssl=verify-full",
            allowed_origins="https://airshield.example",
            fail_closed=False,
        )
