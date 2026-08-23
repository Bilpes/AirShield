# AirShield source-code and run guide

## 1. What AirShield does

AirShield is an English-only, voice-first privacy enforcement layer for Healthcare, Finance, Insurance, BPO/contact centres, and SaaS/internal copilots. It keeps the raw transcript inside the customer trust boundary, displays it beside a protected transcript, and permits downstream AI routing only after the full transcript receives a final `allow` decision and signed receipt.

It is not a certification product and this repository is not proof of GDPR, HIPAA, PCI DSS, DORA, NIS2, EHDS, or EU AI Act compliance. Production use requires customer-specific legal/privacy review, representative model evaluation, penetration testing, infrastructure validation, and any applicable independent assessment.

## 2. Main flow

1. The browser opens a WSS connection to the trusted gateway.
2. The gateway validates a short-lived host-issued OIDC cookie or bearer token, exact Origin, expected tenant, protocol state, rate, size, and session limits.
3. The gateway rebuilds the session message and forwards audio over private CA-validated WSS. Client trust headers are discarded; the gateway injects its rotatable private edge secret.
4. The edge runs self-hosted English `faster-whisper` and optional `pyannote.audio`. Diarization maintains speaker-track continuity; it does not identify a person.
5. A signed OIDC speaker-track claim is accepted only when the host has trustworthy isolated-channel provenance. The control plane stores a keyed subject digest and issues an unrelated speaker token.
6. Interim transcript pairs are local/provisional and always `safe_for_egress=false`.
7. The Python control plane applies tenant-scoped policy and detection, creates encrypted token mappings, checks the destination, and signs a metadata-only receipt.
8. Session end rechecks the complete transcript. Only a signed final `allow` is egress-eligible; `block`, `review`, missing dependencies, and unsigned responses fail closed.

## 3. Repository map

| Path | Purpose |
|---|---|
| `app/`, `components/`, `lib/` | Responsive Next.js App Router UI and server-only fail-closed proxy routes |
| `control-plane/` | FastAPI control plane, OIDC authorization, policies, encrypted vault, evidence, retention, deletion, and reidentification |
| `gateway-service/` | OIDC-authenticated WebSocket gateway and private edge proxy |
| `edge-service/` | Self-hosted English ASR/diarization adapter and final control-plane enforcement |
| `api/` | OpenAPI and AsyncAPI contracts |
| `deploy/kubernetes/` | Hardened base plus Azure and OpenBao overlays |
| `deploy/azure/` | Private AKS/PostgreSQL/separated Key Vault Bicep reference |
| `examples/` | Python, Node.js, Java, Go, and .NET control-plane clients |
| `docs/` | Architecture, threat model, DPIA/control mapping, model assurance, operations, and release checklist |

## 4. Security design in the source

- Per-record AES-256-GCM with a random DEK and nonce.
- AAD binds tenant, session, token, and entity type.
- DEKs are wrapped by Azure Key Vault or OpenBao Transit; local wrapping is test/development only.
- Independent keyed HMAC indexes avoid unsalted low-entropy lookup hashes.
- Signed per-tenant hash chains include sequence and previous hash; the exporter verifies the chain before writing a private JSONL package.
- OIDC issuer, audience, signature, expiry, subject, tenant, and scopes/roles are checked. Portable Kubernetes tokens use exact subject-to-tenant/scope bindings—never wildcard subjects.
- Cross-tenant queries include tenant predicates and composite tenant foreign keys.
- Reidentification requires purpose/ticket metadata, separate requester and approver, short expiry, and one-time requester retrieval.
- Request bodies, audio, message rates, connection counts, inference concurrency, and session duration are bounded.
- Production model files are preloaded; startup verifies a pinned manifest and every artifact hash before model loading.
- Web, gateway, edge, and control-plane paths use TLS in the production manifests; PostgreSQL requires `ssl=verify-full`.
- Images and GitHub Actions are digest/commit pinned. The spaCy wheel is SHA-256 checked during image build.

## 5. Prerequisites

### UI-only demo

- Node.js 22+
- npm 10+

### Full local stack

- Docker Engine with Compose v2
- At least 8 GB free memory for a CPU edge demonstration; more is recommended
- Microphone permission in a Chromium/Firefox-class browser for live audio

### Manual backend development

- Python 3.12 (production image version)
- PostgreSQL 16/17
- `ffmpeg` and `libsndfile` for local voice processing

## 6. Fastest run: responsive synthetic UI

From the repository root:

```bash
npm ci
npm run dev
```

Open `http://localhost:4174`.

This mode demonstrates all responsive screens, sector scenarios, policies, vault concepts, evidence, connections, and performance views. The **Try the protection API** card uses the development-only local detector and masks entered names, contextual account IDs, phone values, email addresses, and the other deterministic patterns. Select **Run sample** to show clearly labelled synthetic raw/protected transcript pairs. Actual microphone transcription requires the self-hosted voice edge described below; the UI deliberately does not fall back to a browser/vendor speech-recognition service.

The initially open **CareShield Assistant** adds a protected virtual-intake flow without replacing any AirShield screen. Enter only synthetic symptoms: the raw text appears in a local-only bubble while the RIA demo receives the protected result with entity count, decision, and receipt. Its general-physician slot and reservation are synthetic; it performs no diagnosis, emergency care, clinical record creation, or real booking. Minimize the widget to inspect the underlying product.

## 7. Full local Docker Compose stack

```bash
docker compose up --build
```

Open `http://localhost:4174`.

The development stack starts:

- Next.js UI on `4174`
- Python control plane on `8080`
- PostgreSQL with a one-shot Alembic migration
- English voice edge on `8001`

The Compose file intentionally uses visible development credentials and an explicit insecure localhost WebSocket build flag. Never deploy it as production.

To include local Ollama:

```bash
docker compose --profile local-llm up --build
```

The first development ASR run may populate the local model cache and take longer than later runs. Production does not download models at runtime.

To verify live capture:

1. Open **Live shield** and select **Start live capture**. This requests microphone permission automatically; **Connect microphone** is optional preflight.
2. Speak an English sentence containing test identifiers. Raw text appears only in the left trust-boundary pane; the protected version appears on the right.
3. Select **Stop & protect**. The edge now forces processing of the final audio chunk, including short utterances that did not reach the periodic streaming threshold.
4. Use **Reset** to stop the recorder, release the microphone, close the socket, and clear both transcript panes. The separate protection-card reset clears typed API data.

If the UI reports that the voice edge is unavailable, verify that port `8001` is reachable and that `NEXT_PUBLIC_EDGE_WS_URL` was present at **web build time**. Microphone capture requires HTTPS except on `localhost`. Production must point the browser to the authenticated gateway over `wss://`, not directly to the edge.

Stop and remove containers:

```bash
docker compose down
```

Remove development data as well:

```bash
docker compose down -v
```

## 8. Manual control-plane run

```bash
cd control-plane
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.seed_dev_keys
```

Copy the generated development values into `control-plane/.env`, then set a PostgreSQL development URL and run:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8080 --no-proxy-headers
```

For local development, use `ENVIRONMENT=development`, `AUTH_MODE=dev`, and `KEY_PROVIDER=local`. Production startup rejects those settings.

Verify readiness:

```bash
curl http://127.0.0.1:8080/v1/health/ready
```

Run a direct client from the repository root:

```bash
python examples/python/client.py
node examples/node/client.mjs
```

## 9. Manual UI-to-control-plane development

The repository includes a non-secret development file at `/.env.local`, in the repository root beside `package.json`:

```env
NEXT_PUBLIC_EDGE_WS_URL=ws://localhost:8001/ws/voice
AIRSHIELD_RUNTIME_MODE=development
AIRSHIELD_ALLOW_DEVELOPMENT_RUNTIME=true
AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE=true
```

It intentionally contains only local hackathon defaults. Never add credentials, production hostnames, or production tokens to the committed file. If the control plane is also run manually, add these values only to your private uncommitted environment or shell:

```env
CONTROL_PLANE_URL=http://127.0.0.1:8080
CONTROL_PLANE_DEV_TOKEN=development-only
```

Then run:

```bash
npm ci
npm run dev
```

The Next.js server creates and reuses a control-plane session for non-voice LiveShield operations. Browser bearer headers are never forwarded.

## 10. Voice edge and gateway development

The Compose stack is the easiest supported local voice run. For component work:

```bash
# Edge tests
(cd edge-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)

# Gateway tests
(cd gateway-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)
```

Production voice prerequisites are intentionally stricter:

- trusted host OIDC cookie/bearer issuance;
- exact gateway Origin and tenant;
- private WSS edge certificate and CA;
- distinct current/staged gateway secrets;
- HTTPS control-plane certificate and CA;
- projected/Azure workload identity with only `airshield.protect` and, for edge binding, `airshield.bind`;
- preloaded read-only ASR/diarization files plus a signed release manifest;
- representative ASR, diarization, detector, and end-to-end quality gates.

## 11. Production Kubernetes/Azure sequence

The manifests contain `REPLACE_*` placeholders and cannot be deployed safely without release engineering.

1. Build, scan, sign, attest, and digest-pin the web, gateway, edge, and control-plane images.
2. Build the web image with the exact external `wss://.../ws/voice` gateway URL. Do not use the local insecure-edge flag.
3. Provision web/gateway/edge/control-plane certificates and private CA bundles.
4. Provision PostgreSQL credentials and CA with `ssl=verify-full`.
5. Provision the separated control and gateway secret stores; configure distinct managed identities.
6. Preload the `airshield-models` PVC and set the promoted `MODEL_MANIFEST_SHA256`.
7. Replace OIDC issuer, JWKS, audience, tenant, identity, vault, image, DNS, and host placeholders.
8. Render and validate all overlays, run an Azure what-if, apply Alembic as an approved one-shot job, then deploy.
9. Test direct-edge denial, tenant isolation, secret/certificate rotation, dependency outages, model tampering, NetworkPolicy, restore, deletion, and immutable evidence export.

Commands:

```bash
kustomize build deploy/kubernetes/overlays/azure | kubeconform -strict -ignore-missing-schemas -
kustomize build deploy/kubernetes/overlays/openbao | kubeconform -strict -ignore-missing-schemas -
az bicep build --file deploy/azure/main.bicep
```

See `deploy/kubernetes/README.md` and `deploy/azure/README.md` for the complete release checklist.

## 12. Validation

From the repository root after creating `control-plane/.venv`:

```bash
(cd control-plane && .venv/bin/ruff check app tests migrations evaluation scripts)
(cd control-plane && .venv/bin/mypy app scripts)
(cd control-plane && .venv/bin/pytest -q)
(cd edge-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)
(cd gateway-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)
(cd control-plane && .venv/bin/pip-audit --local)
(cd control-plane && .venv/bin/pip-audit -r ../edge-service/requirements.txt)
npm audit --audit-level=high
npm run typecheck
npm run build
```

The included synthetic evaluator is only a regression smoke test:

```bash
(cd control-plane && .venv/bin/python evaluation/evaluate.py evaluation/fixtures/regex-gate.jsonl --require-perfect)
```

It deliberately reports `production_gate_satisfied: false`; only a representative, legally sourced and approved evaluation can satisfy the production gate.

## 13. Evidence export

After configuring production database and key-verification access:

```bash
cd control-plane
python scripts/export_evidence.py \
  --tenant tenant-approved-01 \
  --output /secure-staging/evidence.jsonl
```

The exporter verifies the chain, persisted tail, and signatures before writing mode-0600 JSONL plus a SHA-256 sidecar. Upload immediately to independently administered retention-locked storage and record an external timestamp/object version. The sidecar alone is not an immutable anchor.

## 14. Important remaining release work

- Run real faster-whisper, optional pyannote, contextual Presidio, codec, long-session, and adversarial stream evaluations on representative approved data.
- Run PostgreSQL concurrency/load/restore tests in the target managed service.
- Validate every regional Azure resource, quota, policy, role assignment, certificate controller, firewall/FQDN rule, and private endpoint in a live subscription.
- Add customer-specific aggregate gateway quotas and DDoS/WAF policy.
- Complete independent legal, privacy, security, model, penetration, and applicable sector/PCI assessment.

For deeper review, start with:

- `docs/AirShield_Requirements_and_Runbook.pdf`
- `docs/AirShield_CEO_Technical_Briefing.pdf`
- `docs/PRODUCTION_ARCHITECTURE.md`
- `docs/THREAT_MODEL.md`
- `docs/MODEL_ASSURANCE.md`
- `docs/OPERATIONS_EVIDENCE.md`
- `docs/DPIA_CONTROL_MAPPING.md`
- `docs/SECURITY_REVIEW_CHECKLIST.md`
