import json

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth import principal_from_claims
from app.config import Settings


def test_exact_portable_workload_binding_supplies_tenant_and_minimum_scopes():
    subject = "system:serviceaccount:airshield:airshield-edge"
    settings = Settings(
        workload_bindings_json=json.dumps(
            {
                subject: {
                    "tenant_id": "tenant-nordic-01",
                    "scopes": ["airshield.protect", "airshield.bind"],
                }
            }
        )
    )
    principal = principal_from_claims(settings, {"sub": subject})
    assert principal.tenant_id == "tenant-nordic-01"
    assert principal.scopes == frozenset({"airshield.protect", "airshield.bind"})


def test_portable_binding_rejects_conflicting_signed_tenant():
    subject = "system:serviceaccount:airshield:airshield-web"
    settings = Settings(
        workload_bindings_json=json.dumps(
            {subject: {"tenant_id": "tenant-a", "scopes": ["airshield.protect"]}}
        )
    )
    with pytest.raises(HTTPException) as caught:
        principal_from_claims(settings, {"sub": subject, "tid": "tenant-b"})
    assert caught.value.status_code == 403


def test_workload_binding_cannot_grant_administrative_scope():
    with pytest.raises(ValidationError, match="unsupported or empty scope"):
        Settings(
            workload_bindings_json=json.dumps(
                {
                    "system:serviceaccount:airshield:airshield-edge": {
                        "tenant_id": "tenant-a",
                        "scopes": ["airshield.admin"],
                    }
                }
            )
        )
