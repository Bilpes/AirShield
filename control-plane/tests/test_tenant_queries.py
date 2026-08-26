from pathlib import Path


def test_service_queries_include_tenant_predicates():
    source = Path("app/service.py").read_text()
    tenant_scoped_models = [
        "SessionRecord",
        "IdentityBinding",
        "TokenMapping",
        "IdempotencyRecord",
        "ReidentificationRequest",
    ]
    for model in tenant_scoped_models:
        assert f"{model}.tenant_id" in source


def test_evidence_lookup_is_tenant_scoped():
    source = Path("app/routes.py").read_text()
    assert "EvidenceEvent.tenant_id == principal.tenant_id" in source
