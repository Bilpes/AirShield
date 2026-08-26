from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    scopes: frozenset[str]
    claims: dict

    def has(self, permission: str) -> bool:
        return permission in self.scopes or "airshield.admin" in self.scopes


class OIDCVerifier:
    def __init__(self, settings: Settings):
        if not settings.oidc_jwks_url:
            raise ValueError("OIDC_JWKS_URL is required for OIDC authentication")
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=3600)

    def verify(self, token: str) -> dict:
        try:
            key = self.jwks.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                audience=self.settings.oidc_audience,
                issuer=self.settings.oidc_issuer,
                options={"require": ["exp", "iat", "sub"]},
                leeway=30,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid workload identity"
            ) from exc


@lru_cache(maxsize=1)
def verifier() -> OIDCVerifier:
    return OIDCVerifier(get_settings())


def _scope_set(claims: dict) -> frozenset[str]:
    scopes = set(str(claims.get("scp", "")).split())
    roles = claims.get("roles", [])
    if isinstance(roles, list):
        scopes.update(str(role) for role in roles)
    return frozenset(item for item in scopes if item)


def principal_from_claims(settings: Settings, claims: dict) -> Principal:
    subject = str(claims["sub"])
    claim_tenant = claims.get(settings.tenant_claim)
    binding = settings.workload_bindings.get(subject)
    if binding:
        bound_tenant = str(binding["tenant_id"])
        if claim_tenant and str(claim_tenant) != bound_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Tenant claim conflicts with binding"
            )
        scopes = binding["scopes"]
        if not isinstance(scopes, list):  # guarded by Settings; retain fail-closed defense
            raise HTTPException(status_code=500, detail="Invalid workload binding")
        return Principal(
            subject=subject,
            tenant_id=bound_tenant,
            scopes=frozenset(str(scope) for scope in scopes),
            claims=claims,
        )
    if not claim_tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant claim is missing")
    return Principal(
        subject=subject,
        tenant_id=str(claim_tenant),
        scopes=_scope_set(claims),
        claims=claims,
    )


async def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_dev_tenant: Annotated[str | None, Header()] = None,
    x_dev_subject: Annotated[str | None, Header()] = None,
) -> Principal:
    settings = get_settings()
    if settings.auth_mode == "dev":
        if settings.environment == "production":
            raise HTTPException(status_code=500, detail="Unsafe authentication configuration")
        return Principal(
            subject=x_dev_subject or "developer@example.local",
            tenant_id=x_dev_tenant or "tenant-demo",
            scopes=frozenset(
                {
                    "airshield.protect",
                    "airshield.bind",
                    "airshield.reidentify.request",
                    "airshield.reidentify.approve",
                    "airshield.evidence.read",
                    "airshield.delete",
                    "airshield.admin",
                }
            ),
            claims={"auth_mode": "dev"},
        )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer workload token required")
    claims = await asyncio.to_thread(verifier().verify, credentials.credentials)
    return principal_from_claims(settings, claims)


def require(permission: str) -> Callable:
    async def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if not principal.has(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}"
            )
        return principal

    return dependency
