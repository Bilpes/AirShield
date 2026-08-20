"""AirShield control-plane client — Python 3.9+ standard library."""
import json
import os
import uuid
from urllib.request import Request, urlopen

BASE_URL = os.getenv("AIRSHIELD_URL", "http://127.0.0.1:8080")
TOKEN = os.getenv("AIRSHIELD_TOKEN", "development-only")


def post(path: str, payload: dict) -> dict:
    request = Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:
        return json.load(response)


session = post("/v1/sessions", {"policy": "finance-eu-us-v1", "language": "en", "ttl_minutes": 60})
result = post(
    "/v1/protect",
    {
        "session_id": session["session_id"],
        "text": "Email alice@example.com and card 4111 1111 1111 1111.",
        "policy": "finance-eu-us-v1",
        "destination": "approved-finance-llm",
        "idempotency_key": str(uuid.uuid4()),
    },
)
if result["decision"] != "allow":
    raise RuntimeError(f"Egress denied: {result['receipt']['reason_codes']}")
print(result["protected_text"])
print(result["receipt"]["receipt_id"], result["receipt"]["signing_algorithm"])
