from pathlib import Path

import yaml


def test_openapi_is_production_contract_without_dev_identity_headers():
    contract_path = Path(__file__).resolve().parents[2] / "api" / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text())
    assert contract["info"]["version"] == "1.0.0"
    assert contract["paths"]["/v1/sessions/{session_id}/data"]["delete"]["x-required-scope"] == (
        "airshield.delete"
    )
    assert "x-dev-tenant" not in contract_path.read_text().lower()


def test_asyncapi_requires_gateway_identity_and_raw_local_boundary():
    contract_path = Path(__file__).resolve().parents[2] / "api" / "asyncapi.yaml"
    contract = yaml.safe_load(contract_path.read_text())
    gateway = contract["servers"]["customerGateway"]
    assert gateway["security"] == [{"browserSession": []}, {"workloadJwt": []}]
    assert "private edge is never browser-reachable" in gateway["description"]
    pair = contract["components"]["messages"]["TranscriptPair"]["payload"]["properties"]
    assert pair["safe_for_egress"]["const"] is False
    raw_description = contract["components"]["messages"]["RawTranscript"]["description"]
    assert "never route" in raw_description
