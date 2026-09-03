# AirShield — self-hosted English voice privacy firewall

AirShield is a responsive, voice-first privacy control for Healthcare, Finance, Insurance, BPO/Contact Centers, and SaaS/Internal Copilots. The UI shows what participants say inside the trust boundary beside the masked outbound transcript. The production path combines a Next.js App Router UI with a Python/FastAPI control plane, private speech/detection models, an encrypted token vault, signed evidence, retention/deletion, and controlled reidentification.

No Azure Speech, Google Speech-to-Text, AWS Transcribe, or OpenAI transcription API is required.

The responsive product now includes **CareShield Assistant**, an initially open, collapsible protected virtual-intake and synthetic doctor-booking demonstration. Typed or self-hosted voice input shows raw content locally and a separate protected RIA preview with entity count, decision, and receipt. It provides emergency guidance and explicitly does not diagnose, create a clinical record, or make a real appointment.

The **Agent Trust Lab** adds the **PurposeGraph™** privacy-to-action trust layer for AI agents — an IntentSeal contract, a live trust graph, hash-bound approval (CommitLock), an ActionTwin dry-run, a one-use credential broker, MemoryFence quarantine, and causal revocation. It answers, with visible evidence, *"did any datum leave the trusted boundary for a purpose the human actually authorized — and can I prove it?"*. See [docs/AIRSHIELD_PURPOSEGRAPH_LAYER.md](docs/AIRSHIELD_PURPOSEGRAPH_LAYER.md).

The **EgressSeal™ control room** demonstrates four linked market differentiators:

1. **EgressSeal™** — an Ed25519-signed, expiring release proof bound to protected-content digest, policy, destination, ContextFence risk, upstream receipt and one allowlisted action.
2. **Destination Switch** — changing the AI destination prevents the prior destination-bound seal from authorizing the new route and forces policy/risk recalculation.
3. **ContextFence™** — an explainable cumulative-risk meter for mosaic/linkage risk that can remain after individual identifiers are masked.
4. **SafeAction™** — a token-aware synthetic action broker that verifies the seal and lets a trusted connector act without returning resolved raw values to the model.

The embedded EgressSeal signer and SafeAction connector are explicitly development-only demonstrations. Even in development, seal issuance accepts only process-local upstream receipts registered by `/api/protect` with matching content, decision, policy and destination. Production requires an external KMS/HSM trust anchor, verified upstream receipts and real independently secured connectors. The ™ marks denote product-concept branding, not registered trademarks.

## Architecture

- **UI:** Next.js 16, React 19, TypeScript, responsive desktop/tablet/mobile views
- **Control plane:** Python 3.12, FastAPI, async SQLAlchemy/PostgreSQL, Alembic
- **Identity:** OIDC workload JWT, verified Entra tenant/roles or exact portable subject bindings, scoped roles; development auth is rejected in production
- **Key custody:** Azure Key Vault or OpenBao Transit; local keys are development/test only
- **Vault:** per-record AES-256-GCM, random DEK/nonce, purpose-bound AAD, keyed indexes, provider-wrapped DEKs
- **Evidence:** metadata-only tenant hash chain, external signatures, sequence/tail verification, verified JSONL exporter, and mandatory immutable external anchoring
- **Detection:** deterministic recognizers plus a pinned Presidio/spaCy contextual model; production starts and routes fail closed when required detection is unavailable
- **Voice edge:** faster-whisper English ASR and optional pyannote diarization; diarization maintains speaker tracks but never authenticates a person
- **AI:** optional self-hosted Ollama destination after an `allow` policy decision
- **Deployment:** private Azure reference (AKS, Workload Identity, Key Vault, PostgreSQL Flexible Server) and portable Kubernetes/OpenBao overlays

`gateway-service` is the authenticated WebSocket boundary: it validates the host's OIDC session cookie/bearer token, exact Origin, tenant, protocol, rates, sizes, and duration; validates the private edge CA over WSS, injects the rotatable edge secret, and never forwards client trust headers. `edge-service` is the self-hosted English speech adapter. In production it requires an authenticated private gateway and the Python control plane; interim chunks are never marked safe for egress, and the full transcript is rechecked at session end. Its in-memory masking path is development-only—production tokenization and signed evidence live in `control-plane`.

For a complete source map, architecture explanation, local/Compose/manual setup, production deployment sequence, and validation commands, see [AIRSHIELD_SOURCE_AND_RUN_GUIDE.md](AIRSHIELD_SOURCE_AND_RUN_GUIDE.md).

For the client and executive narrative—including architecture, sector uses, business flow, legacy/new-application integration, technology stack, differentiation, ROI, go-to-market, roadmap, risks, and CEO questions—see [AirShield Executive Architecture & Business Dossier](docs/AirShield_Executive_Architecture_and_Business_Dossier.pdf). The editable source is [AIRSHIELD_EXECUTIVE_ARCHITECTURE_AND_BUSINESS.md](docs/AIRSHIELD_EXECUTIVE_ARCHITECTURE_AND_BUSINESS.md).

Implementation and hackathon deliverables:

- [AirShield Internal Hackathon Pitch](docs/AirShield_Hackathon_Pitch.pdf) — problem, differentiation, four-part product stack, market value, implemented proof, limitations and pilot ask. Editable source: [AIRSHIELD_HACKATHON_PITCH.md](docs/AIRSHIELD_HACKATHON_PITCH.md).
- [AirShield Manager Demo Playbook](docs/AirShield_Manager_Demo_Playbook.pdf) — exact 12-minute and 5-minute talk tracks, click path, expected results, fail-closed demonstration, judge questions and fallback plan. Editable source: [AIRSHIELD_MANAGER_DEMO_PLAYBOOK.md](docs/AIRSHIELD_MANAGER_DEMO_PLAYBOOK.md).
- [AirShield Technical Authority Dossier](docs/AirShield_Technical_Authority_Dossier.pdf) — authoritative implemented architecture, data flows, security controls, EgressSeal/ContextFence/SafeAction protocols, cryptography, evidence, threats, validation and production gates. Editable source: [AIRSHIELD_TECHNICAL_AUTHORITY_DOSSIER.md](docs/AIRSHIELD_TECHNICAL_AUTHORITY_DOSSIER.md).
- [AirShield Requirements and Runbook](docs/AirShield_Requirements_and_Runbook.pdf) — requirements, exact run steps, CareShield/EgressSeal demonstrations, verification and production gates. Editable source: [AIRSHIELD_REQUIREMENTS_AND_RUNBOOK.md](docs/AIRSHIELD_REQUIREMENTS_AND_RUNBOOK.md).
- [AirShield CEO Technical Briefing](docs/AirShield_CEO_Technical_Briefing.pdf) — detailed trust boundaries, technology, encryption/token-vault logic, speaker identity, voice capture, RIA integration and limitations. Editable source: [AIRSHIELD_CEO_TECHNICAL_BRIEFING.md](docs/AIRSHIELD_CEO_TECHNICAL_BRIEFING.md).

Regenerate all five implementation PDFs with `python scripts/build_release_pdfs.py` after installing ReportLab.

## Run the UI demo

The repository includes a non-secret development file at **`/.env.local`**, in the repository root beside `package.json`, `next.config.ts`, and `docker-compose.yml`. It leaves `NEXT_PUBLIC_EDGE_WS_URL` empty, so the browser uses the **same-origin voice proxy**: the UI opens `/edge/ws/voice` on the web app's origin and Next.js forwards it to the voice edge on `localhost:8001`. Never add production credentials to this file.

```bash
npm ci
npm run dev
```

Open `http://localhost:4174`. The **Try the protection API** card uses the deterministic development detector; **Run sample** displays explicitly labelled synthetic transcript data. **Start live capture** never falls back to a browser/vendor speech-recognition API: it requires the self-hosted edge on port `8001` (or an authenticated production gateway) described below. A production build with no configured control plane returns HTTP 503 from protection, session, health, and AI-egress paths rather than silently using the demo detector.

## Run live voice locally — no Docker required

For a demo with **real microphone transcription** running entirely on your machine (no containers, no Postgres, no control plane):

```bash
./run_local.sh
```

This one command:

1. Creates a Python virtualenv for the voice edge and installs its requirements on first run (Python 3.11+; audio decoding uses the PyAV-bundled ffmpeg, so system ffmpeg is not needed).
2. Starts the self-hosted **voice edge** on `http://localhost:8001` (browsers reach it through the same-origin proxy `/edge/ws/voice`, so voice also works from LAN IPs and HTTPS hosts) with the local privacy engine. Interim transcript pairs stay provisional/unsigned; the final session-end decision is signed with a pinned **development-only** HMAC key and returned as `allow` with a real (non-`demo_unsigned`) signature, so Live Shield and CareShield Assistant complete the full signed-egress flow on a laptop.
3. Waits until the edge is healthy (up to 10 minutes on first run while the Whisper model downloads) and then starts the Next.js UI on `http://localhost:4174`.

The UI polls the edge health endpoint every 5 seconds: once it is up, **Start live capture** and the CareShield microphone button enable themselves. Use `ASR_MODEL=small.en ./run_local.sh` for higher transcription accuracy. `./run_local.sh --edge` and `./run_local.sh --web` run the two processes in separate terminals. The Docker Compose stack below remains available as the full-stack option.

## Run the validated control plane locally

```bash
cd control-plane
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.seed_dev_keys        # copy output into a local .env; never commit it
alembic upgrade head               # point DATABASE_URL at PostgreSQL
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Install the pinned English spaCy model for contextual detection. Production `FAIL_CLOSED=true` refuses startup without it. The container image verifies the published `en_core_web_sm` wheel against its pinned SHA-256 before installation; production pipelines should mirror, scan, sign, and attest it.

To proxy Next.js through the control plane in development:

```env
CONTROL_PLANE_URL=http://127.0.0.1:8080
CONTROL_PLANE_DEV_TOKEN=development-only
```

The server-side proxy never forwards a browser-supplied bearer token. In Kubernetes it reads a projected workload token; on Azure it exchanges the injected federated token for the configured control-plane scope.

## Development Compose stack

```bash
docker compose up --build
```

This starts the UI, control plane, migration job, PostgreSQL, and voice edge. The compose file intentionally uses visible development-only credentials and dev authentication. It is not a production deployment. Add `--profile local-llm` for Ollama.

## API example

```bash
curl -X POST http://localhost:4174/api/protect \
  -H 'Content-Type: application/json' \
  -d '{
    "text":"Email alice@example.com and card 4111 1111 1111 1111",
    "policy":"Financial services · PCI",
    "destination":"Banking support AI"
  }'
```

The Next.js server maps display policy names to versioned control-plane IDs, creates a tenant-scoped session when needed, supplies an idempotency key, and returns protected text plus a signed receipt. Direct clients can use the contract in `api/openapi.yaml`.

## Speaker-to-person mapping

1. The host authenticates the participant through SSO, OTP, IVR, CRM/EHR check-in, or another approved mechanism.
2. Local diarization labels continuity tracks such as `SPEAKER_A`; it does not determine who the person is.
3. Only when the host has trustworthy isolated-channel provenance, its issuer adds a signed speaker-track claim; the gateway and scoped edge binding route then associate that OIDC subject. AirShield persists only a keyed subject digest.
4. The AI receives an unrelated token such as `[SPEAKER_8A91C2]`; unknown speakers remain unknown.
5. Reidentification needs a specific purpose/ticket, a different approver, and one-time retrieval by the original requester.

## Validation commands

```bash
# Run from the repository root.
(cd control-plane && .venv/bin/ruff format --check app tests migrations evaluation scripts \
  && .venv/bin/ruff check app tests migrations evaluation scripts \
  && .venv/bin/mypy app scripts && .venv/bin/pytest -q \
  && .venv/bin/python evaluation/evaluate.py evaluation/fixtures/regex-gate.jsonl --require-perfect \
  && .venv/bin/alembic upgrade head --sql)

control-plane/.venv/bin/ruff check --config control-plane/pyproject.toml edge-service/app edge-service/tests
MYPYPATH=edge-service control-plane/.venv/bin/mypy --ignore-missing-imports edge-service/app
(cd edge-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)

control-plane/.venv/bin/ruff check --config gateway-service/pyproject.toml gateway-service/app gateway-service/tests
MYPYPATH=gateway-service control-plane/.venv/bin/mypy --ignore-missing-imports gateway-service/app
(cd gateway-service && PYTHONPATH=. ../control-plane/.venv/bin/pytest -q tests)

npm run typecheck
npm run build

# Manifests / Azure
kustomize build deploy/kubernetes/overlays/azure | kubeconform -strict -
az bicep build --file deploy/azure/main.bicep
```

Synthetic evaluation fixtures are smoke tests and explicitly do **not** satisfy the production model gate. Production promotion requires representative, legally sourced Nordic/EU and US English datasets and every slice gate in `control-plane/evaluation/quality-gates.yaml`.

## Security, privacy, and deployment artifacts

- [Production architecture](docs/PRODUCTION_ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [DPIA and regulatory control starter](docs/DPIA_CONTROL_MAPPING.md)
- [Model assurance](docs/MODEL_ASSURANCE.md)
- [Operations and evidence](docs/OPERATIONS_EVIDENCE.md)
- [Release checklist](docs/SECURITY_REVIEW_CHECKLIST.md)
- [Kubernetes deployment](deploy/kubernetes/README.md)
- [Azure private reference](deploy/azure/README.md)
- [OpenAPI](api/openapi.yaml) and [AsyncAPI](api/asyncapi.yaml)
- Java, .NET, Python, Node.js, and Go examples under `examples/`

## Compliance and certification limitation

This repository is not, by itself, GDPR-, HIPAA-, PCI DSS-, NIS2-, DORA-, EHDS-, EU-AI-Act-, SOC-2-, or ISO-certified/compliant. Applicability depends on customer role, country, sector, data flow, model use, contracts, operations, and evidence. Independent legal, privacy, security, model, penetration, and applicable assessor review remains required. HHS does not recognize a private HIPAA Security Rule certification, and PCI validation scope/method is determined by the enforcing entities and assessor—not by application source code.
