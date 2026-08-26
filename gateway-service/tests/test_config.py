import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_oidc_tenant_and_edge_secret():
    with pytest.raises(ValidationError, match="OIDC_ISSUER"):
        Settings(environment="production")


def test_production_rejects_wildcard_origin():
    with pytest.raises(ValidationError, match="exact HTTPS origins"):
        Settings(
            environment="production",
            oidc_issuer="https://issuer.example.com",
            oidc_audience="api://airshield-browser",
            oidc_jwks_url="https://issuer.example.com/keys",
            expected_tenant_id="tenant-a",
            edge_gateway_secret="x" * 32,
            allow_origins="*",
        )
