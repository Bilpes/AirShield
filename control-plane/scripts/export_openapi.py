from __future__ import annotations

from pathlib import Path

import yaml

from app.main import app

SCOPES = {
    ("/v1/sessions", "post"): "airshield.protect",
    ("/v1/protect", "post"): "airshield.protect",
    ("/v1/sessions/{session_id}/bindings", "post"): "airshield.bind",
    ("/v1/sessions/{session_id}/data", "delete"): "airshield.delete",
    ("/v1/reidentification-requests", "post"): "airshield.reidentify.request",
    ("/v1/reidentification-requests/{request_id}/approve", "post"): "airshield.reidentify.approve",
    ("/v1/reidentification-requests/{request_id}/result", "get"): "airshield.reidentify.request",
    ("/v1/evidence/{event_id}", "get"): "airshield.evidence.read",
    ("/v1/evidence/verify", "post"): "airshield.admin",
}

DESCRIPTIONS = {
    "/v1/protect": "Protect text and issue a signed, hash-chained, metadata-only egress receipt.",
    "/v1/sessions": "Create a tenant-scoped protection session.",
    "/v1/sessions/{session_id}/bindings": (
        "Bind a trusted host identity digest to a diarized speaker track. "
        "Diarization does not authenticate the person."
    ),
    "/v1/sessions/{session_id}/data": (
        "Delete live token mappings and identity bindings for a tenant-scoped session; "
        "record a metadata-only deletion event."
    ),
    "/v1/reidentification-requests": "Request purpose- and ticket-bound reidentification.",
    "/v1/reidentification-requests/{request_id}/approve": (
        "Approve with a principal distinct from the requester."
    ),
    "/v1/reidentification-requests/{request_id}/result": (
        "One-time plaintext result for the original requester after approval."
    ),
    "/v1/evidence/{event_id}": (
        "Retrieve a tenant-scoped egress receipt; receipts contain no raw protected value."
    ),
    "/v1/evidence/verify": "Verify the complete tenant evidence hash chain and external signatures.",
}


def export(path: Path) -> None:
    schema = app.openapi()
    schema["info"] = {
        "title": "AirShield Privacy Control Plane API",
        "version": "1.0.0",
        "description": (
            "Tenant-isolated English PII/PHI/PCI protection, signed evidence, identity binding, "
            "deletion, and dual-control reidentification. Production callers authenticate with "
            "workload OIDC JWTs. Source code alone is not certification or compliance evidence."
        ),
    }
    schema["servers"] = [
        {"url": "https://airshield-control.internal", "description": "Private customer deployment"}
    ]
    for route, item in schema["paths"].items():
        for method, operation in item.items():
            if not isinstance(operation, dict):
                continue
            operation.pop("parameters", None)  # Development-only identity headers are not production API.
            if route in DESCRIPTIONS:
                operation["description"] = DESCRIPTIONS[route]
            scope = SCOPES.get((route, method))
            if scope:
                operation["x-required-scope"] = scope
                operation.setdefault("responses", {})["401"] = {
                    "description": "Missing or invalid workload identity"
                }
                operation["responses"]["403"] = {"description": "Tenant or scope authorization denied"}
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "OIDC JWT",
        "description": "Trusted workload JWT; a verified signed claim scopes every tenant operation.",
    }
    path.write_text(yaml.safe_dump(schema, sort_keys=False, width=110))


if __name__ == "__main__":
    export(Path(__file__).resolve().parents[2] / "api" / "openapi.yaml")
