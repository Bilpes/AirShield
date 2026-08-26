# AirShield Manager Demo Playbook

**Exact talk track, click path, expected results and fallback plan**

**Implementation baseline · d9d83cd · 24 August 2026**

> Demo goal: show that AirShield is not another chatbot. It is a provider-neutral privacy control and proof layer that protects voice/text, measures residual context risk, binds authorization to the destination and permits only seal-verified token-aware actions.

## 1. Audience and desired outcome

This playbook is for the presenter, manager, product reviewer and internal hackathon judges. By the end of the demonstration, the audience should understand:

- why normal bot security does not fully control readable AI payloads;
- what stays inside the customer trust boundary;
- what the AI is allowed to receive;
- why destination changes require a new decision;
- how ContextFence identifies cumulative post-masking risk;
- what an EgressSeal proves;
- how SafeAction avoids giving the model generic vault access;
- what is implemented versus what requires production engineering.

Recommended duration is 12 minutes plus questions. A five-minute compressed version is included later.

## 2. Presenter language to use and avoid

### Use

- “Pre-egress privacy control plane.”
- “Raw content stays inside the controlled boundary.”
- “Protected meaning is destination-authorized.”
- “Diarization tracks speakers; host authentication establishes identity.”
- “Cryptographically functional development demonstration.”
- “Synthetic action; no real booking or system-of-record update.”
- “Supports control objectives; production requires independent review.”

### Avoid

- “No PII can ever leak.”
- “The voice model proves who the person is.”
- “HIPAA/GDPR/PCI certified.”
- “First product in the world.”
- “Zero cost.”
- “The AI securely reidentifies tokens.”
- “This demo is production ready.”

## 3. Environment preparation

### UI and protected-text demonstration

Requirements:

- Node.js 22+
- npm 10+
- Current Chrome, Edge or Firefox
- Screen width of at least 1280 pixels for the main presentation

From the repository root:

```bash
npm ci
npm run dev
```

Open:

```text
http://localhost:4174
```

### Full self-hosted voice path

Use Docker Compose when microphone transcription must be shown:

```bash
docker compose up --build
```

Wait for:

- UI: `http://localhost:4174`
- control plane: `http://localhost:8080/v1/health/ready`
- voice edge: `http://localhost:8001/v1/health`

The first ASR startup can be slow while the development model is loaded. Complete one microphone rehearsal before the live presentation.

### Preflight commands

```bash
curl http://localhost:4174/api/health
npm run typecheck
npm run build
```

Use only the included synthetic data. Close unrelated browser tabs, disable notifications, verify zoom is 100%, and confirm the CareShield widget can be minimized.

## 4. Twelve-minute manager demonstration

| Time | Screen | Message |
|---|---|---|
| 0:00–1:00 | Overview | Business problem and category |
| 1:00–2:30 | Live Shield | Raw local versus protected outbound proof |
| 2:30–6:30 | EgressSeal | Four-priority transaction demonstration |
| 6:30–8:00 | CareShield | Protected domain experience and safety boundaries |
| 8:00–9:30 | Policy/Vault/Audit | Governance, tokenization and evidence |
| 9:30–10:30 | Connections/Settings | Integration and deployment |
| 10:30–12:00 | Summary | Differentiation, current/target and ask |

## 5. Opening: Overview

### Click path

1. Open the application.
2. Minimize CareShield so the full dashboard is visible.
3. Remain on `Overview`.

### Say

> Most bot teams already use authentication, TLS, encryption and sometimes masking. AirShield is different because it controls the data transaction before the AI receives it. It shows what stays inside the boundary, what protected meaning may leave, which destination is authorized and what evidence proves the decision.

Point to:

- protection-path card;
- safe AI requests;
- sensitive entities blocked;
- self-hosted edge status;
- `Open EgressSeal` and `Open Live Shield` actions.

### Expected result

The manager sees a complete platform rather than a single healthcare chatbot. State that dashboard numbers are synthetic hackathon data, not production measurements.

## 6. Live Shield: voice-first proof

### Fast reliable path

1. Select `Live Shield`.
2. Choose `Healthcare` or `Finance`.
3. Select `Run sample` if microphone/ASR readiness is uncertain.
4. Allow transcript turns to appear.

### Full microphone path

1. Confirm the Compose edge is healthy.
2. Select `Start live capture`.
3. Allow microphone permission.
4. Speak a rehearsed synthetic sentence.
5. Select `Stop & protect`.
6. Wait for finalization.

Suggested sentence:

> I am Jordan Lee, my phone is 555-010-8832, and I need a virtual appointment tomorrow at ten.

### Say

> The left pane is local raw content. The right pane is what AirShield protects for outbound use. Interim speech chunks are provisional because sensitive context can cross chunk boundaries. The complete turn is rechecked before final authorization.

Then point to `Speaker ↔ person map` and say:

> Diarization never authenticates a person. It maintains voice tracks. Identity comes from the host's SSO, OTP, IVR, portal or isolated-channel assertion. Without that provenance, the speaker remains unknown.

### Expected result

Raw and protected transcript panes are visually distinct. Do not imply that a development or unsigned voice result is egress-authorized.

## 7. EgressSeal control room: main innovation demo

Select `EgressSeal™` in the sidebar or `Seal` in mobile navigation.

[[EGRESSSEAL_DIAGRAM]]

### Step 1 — Choose a synthetic industry transaction

1. Keep `Healthcare` selected.
2. Retain the supplied synthetic text.
3. Point out `Raw local input · synthetic only`.

Say:

> Field-level protection is necessary but not sufficient. The remaining context, the destination and the intended action must also be controlled.

### Step 2 — Destination Switch

1. Select `Organization private AI`.
2. Point out approved status and base risk.
3. Briefly show the other destinations without selecting them yet.

Say:

> Destination is part of the authorization. A seal for the private organization route cannot authorize a public or research route.

### Step 3 — Protect and request a seal

1. Select `Protect & request seal`.
2. Wait for the protected outbound preview.
3. Point to the upstream receipt, protected entities and policy decision.

Expected protected content resembles:

```text
I am [PERSON_1], phone [PHONE_1]. I have had a headache since yesterday and need a virtual appointment tomorrow at 10:00 AM.
```

Say:

> The UI does not create a seal from a client assertion alone. In development, `/api/protect` registers a process-local upstream receipt. EgressSeal requires its protected digest, decision, policy and destination to match before signing.

### Step 4 — ContextFence risk meter

Point to:

- score and allow/review/block disposition;
- destination threshold;
- stable-token linkage;
- entity combinations;
- semantic context;
- quasi-identifier detail.

Say:

> Masking each field does not guarantee the combined story is anonymous. ContextFence makes the residual mosaic risk visible and applies a destination-specific threshold.

### Step 5 — Verify EgressSeal

1. Point to the seal ID, destination, development signing key and expiry.
2. Select `Verify EgressSeal`.
3. Confirm `Signature verified`.

Say:

> EgressSeal binds protected content, policy, destination, risk, upstream receipt, expiry and one allowed action. Verification checks the Ed25519 signature, protected-content digest, signing key and expiry before the action broker unlocks.

Clearly state:

> This process-local key is a hackathon trust anchor. Production must use a pinned external KMS or HSM key and authoritative receipt verification.

### Step 6 — Run SafeAction

1. Select `Run SafeAction`.
2. Point to the five broker checks.
3. Point to `Raw values visible to model: false`.
4. Point to the signed synthetic action receipt.

Say:

> The AI proposes with tokens. The broker verifies the seal and one allowlisted action. Resolution stays connector-only. The model never receives a generic resolve-token capability.

State that no real appointment or clinical record was created.

## 8. Deliberate fail-closed demonstration

This is the strongest proof that the controls are not decorative.

### Destination block

1. Select `Public general AI`.
2. Notice that the prior private-route seal is no longer displayed for the new route.
3. Select `Protect & request seal`.
4. Confirm `Egress remains closed` and `destination not approved`.

Say:

> The text may be field-protected, but policy still denies this destination. Protection and authorization are separate decisions.

### Conditional research route

1. Select `Research sandbox`.
2. Request a seal.
3. Explain that the lower threshold can return review when the same protected context is too linkable for research.

### Optional tamper explanation

Do not modify code during the normal demo. Explain:

> The API tests also change the protected content after sealing and attempt an unregistered receipt, a different destination and the wrong action. Digest, receipt and action checks reject each attempt.

## 9. CareShield domain demonstration

1. Restore `CareShield Assistant`.
2. Enter or select a synthetic symptom statement.
3. Submit it.
4. Point to the local raw user bubble.
5. Point to `Sent to RIA demo — protected text`.
6. Point to entity count, decision and receipt.
7. Select `Reserve demo` only after an allowed protected result.

Say:

> CareShield is not the platform boundary; it is one experience using the AirShield boundary. The demonstration performs no diagnosis, no clinical-record creation and no real appointment.

### Emergency branch

Select `I may have emergency signs`, or enter obvious emergency language, and show immediate local-emergency guidance. No RIA or booking action should proceed.

## 10. Governance screens

### Policy Studio

Show sector policy templates and explain entity-specific mask, tokenize, block and review behavior. Destination policy and detector confidence influence the result.

### Token Vault

Explain:

- raw-to-token mapping is encrypted per record;
- AES-256-GCM uses a fresh DEK and nonce;
- AAD binds tenant, session, token and entity type;
- DEKs are wrapped by Azure Key Vault or OpenBao in the production design;
- reidentification requires purpose, ticket, separate approval, expiry and one-time retrieval.

Do not claim that the current schema has complete crypto/AAD version fields or that Python guarantees memory zeroization.

### Audit Trail

Show metadata-only evidence, sequence and previous-hash linkage. Explain that production evidence requires external immutable anchoring; a local sidecar is not an immutable authority.

## 11. Integration and deployment

### Connections

Show API and examples for:

- Java
- .NET
- Python
- Node.js
- Go

Explain reverse-proxy, SDK, sidecar, event and media-stream adapter patterns for legacy applications.

### Settings

Explain the two deployment directions:

- Azure-private: AKS, Workload Identity, Key Vault and PostgreSQL;
- cloud-neutral Kubernetes: workload identity, OpenBao Transit, private database and certificate infrastructure.

Production browser voice uses authenticated `wss://` through the gateway—not direct public access to the private edge.

## 12. Five-minute compressed demo

1. **Overview — 30 seconds:** state the pre-egress control-plane problem.
2. **Live Shield sample — 45 seconds:** show raw versus protected transcript.
3. **EgressSeal — 2 minutes:** protect, inspect ContextFence, verify seal and run SafeAction.
4. **Destination block — 45 seconds:** switch to Public general AI and show seal withheld.
5. **CareShield — 30 seconds:** show protected domain integration and safety language.
6. **Close — 30 seconds:** horizontal scope, current limitations and controlled-pilot ask.

If only one experience can be shown, choose EgressSeal because it combines protection, destination, residual risk, cryptographic proof and safe action.

## 13. Expected judge questions and concise answers

| Question | Recommended answer |
|---|---|
| Isn't this Presidio plus Whisper? | Those are detection/capture components. The product is tenant policy, destination authorization, ContextFence, encrypted tokens, EgressSeal, SafeAction and evidence as one enforced transaction. |
| Why not redact in every bot? | That duplicates controls, causes policy drift and gives application teams the ability to weaken privacy. AirShield creates one independent boundary. |
| Provider already offers zero retention | The provider can still receive readable raw data. AirShield minimizes before receipt and works across providers. |
| Can a detector miss PII? | Yes. No honest detector guarantees perfect recall. Production needs layered detectors, representative evaluation, review thresholds, output DLP and enforced routing. |
| Does diarization authenticate identity? | No. Host authentication and trusted channel binding establish identity; diarization only maintains continuity. |
| Is EgressSeal production signing? | No. The protocol works with a process-local Ed25519 key. Production requires KMS/HSM trust and authoritative receipt verification. |
| Can ContextFence prove anonymity? | No. It is an explainable residual-risk policy signal that requires evaluation and governance. |
| Does SafeAction perform a real booking? | No. It proves seal-gated token-only broker behavior with a synthetic connector. |
| Is this compliant? | It supports control objectives. Compliance depends on the complete customer deployment, contracts, operations and independent assessment. |
| What is the unique claim? | Provider-neutral pre-egress voice/text protection plus destination-bound proof, cumulative context risk, identity-safe speaker binding and token-aware actions. |

## 14. Failure and fallback plan

| Failure | Fallback |
|---|---|
| Microphone denied | Use `Run sample`; explain that no cloud speech fallback is used |
| Voice edge still loading | Continue with typed protection and EgressSeal |
| Port 4174 unavailable | Stop the conflicting process and restart; do not change ports immediately before demo |
| Protection API unavailable | Show fail-closed error and explain why no seal/action is possible |
| Seal withheld unexpectedly | Confirm Organization private AI, synthetic input and a new `/api/protect` receipt |
| Browser refresh invalidates result | Repeat protect → seal → verify; development state is intentionally process-local |
| Docker model download slow | Use UI-only mode and clearly label voice as not running |
| Screen crowded | Minimize CareShield and use desktop width/100% zoom |

Carry the PDFs and screenshots locally. Do not depend on external web resources during the presentation.

## 15. Final close

Say:

> AirShield does not ask us to trust the chatbot. It makes each AI data transaction earn permission. Useful meaning leaves only after protection, destination selection, cumulative-risk evaluation and a verifiable seal. Operational actions then pass through a token-aware broker rather than giving the AI identity access. The next step is a controlled single-sector pilot with measured leakage, utility, latency and cost.

End with the pilot ask; do not end on compliance claims or the synthetic booking.
