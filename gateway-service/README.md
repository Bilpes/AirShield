# AirShield trusted WebSocket gateway

This is the only supported browser ingress to the production voice edge. It validates an organization-issued OIDC session, requires an exact browser Origin, enforces one configured tenant per deployment, reconstructs the control protocol, and injects `x-airshield-edge-auth` on the private edge hop. Client copies of that header are never forwarded.

## Authentication contract

Browsers cannot add an `Authorization` header to the native WebSocket constructor. The trusted host or ingress therefore supplies a short-lived, `Secure`, `HttpOnly`, appropriately scoped `airshield_session` cookie containing the OIDC access/session JWT. Non-browser SDK callers may use `Authorization: Bearer ...`. The token must have issuer, audience, expiry, subject, and the configured tenant claim. Do not place tokens in WebSocket URLs, query strings, local storage, or application logs.

The gateway does not decide that a diarized voice is a real person. OIDC proves the host session identity. A host may bind that identity to a speaker track only when it has trustworthy channel provenance (for example, an isolated authenticated microphone channel). In that case the issuer adds the signed `airshield_speaker_track` claim; the gateway injects the signed subject/track assertion on the private hop, the edge calls the scoped `airshield.bind` route, and the control plane stores only a keyed subject digest plus an unrelated speaker token. With no valid claim, the speaker stays unknown. Diarization alone provides continuity, not identity proof.

## Boundary controls

- Exact Origin and tenant checks.
- RS256/ES256 OIDC signature validation through a cached JWKS.
- Connection, message-rate, message-size, cumulative-audio, session-duration, and final-decision time limits.
- English-only, allowlisted policy/session state machine.
- Private WSS edge destination, private-CA verification, and gateway-secret injection.
- No forwarding of arbitrary client JSON or trust headers.
- A final edge privacy outcome must arrive before the session is complete.

The in-memory connection limit applies per replica. Enforce an aggregate connection/rate policy at the approved ingress or API gateway as well. Configure TLS/WSS, DDoS controls, access logging without URL tokens, certificate rotation, private DNS, and FQDN-restricted JWKS egress in the landing zone.

## Local validation

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check app tests
MYPYPATH=. .venv/bin/mypy --ignore-missing-imports app
PYTHONPATH=. .venv/bin/pytest -q
```

Production startup fails unless OIDC, tenant, private-edge, exact-origin, and strong shared-secret settings pass validation. The sample manifests contain placeholders and are not directly deployable.
