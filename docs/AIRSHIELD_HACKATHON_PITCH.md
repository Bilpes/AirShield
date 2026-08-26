# AirShield Internal Hackathon Pitch

**Provider-neutral privacy control and proof for AI voice, text and actions**

**Implementation baseline · d9d83cd · 24 August 2026**

> Most products secure access to the bot. AirShield controls what the bot, model and downstream tools are allowed to see before data crosses the trust boundary—and produces evidence of that decision.

## 1. The thirty-second pitch

AirShield is a self-hosted, pre-egress privacy control plane for voice and text AI. It keeps raw identity and regulated data inside the organization's trust boundary, sends only protected meaning to an approved destination, measures cumulative context risk, binds each release to a destination-specific signed EgressSeal™, and gates operational tools through a token-aware SafeAction™ broker.

The user and reviewer can see the proof: raw local transcript on one side, protected outbound transcript on the other, the policy decision, ContextFence™ score, destination, receipt and signed release seal.

## 2. The problem

Organizations want AI to understand useful context, but the same voice call, prompt or ticket often contains identity, health, payment, account, claim, customer and enterprise-secret data. Traditional controls answer only part of the question:

- authentication answers who may access the application;
- TLS protects transport but not what an authorized destination reads;
- provider privacy mode applies after data reaches the provider;
- field masking can miss identity reconstructed from combinations of safe-looking facts;
- application logs record events but do not necessarily prove what content was authorized;
- an AI tool with generic vault access can turn protected tokens back into a data-exfiltration interface.

The missing control is an independent decision point that answers: **what exact protected content may this exact destination receive, for what purpose, with what cumulative risk, and what evidence proves it?**

## 3. Yes, secure bot builders already use security

AirShield does not claim that encryption, authentication, redaction, Whisper, Presidio or audit logging are individually new. Good bot teams already use many of them.

The differentiation is the complete provider-neutral transaction:

1. authenticate outside the model;
2. capture voice/text inside the customer boundary;
3. detect and protect sensitive content;
4. measure residual context/linkage risk;
5. authorize the exact destination;
6. sign a destination-bound release seal;
7. permit only an allowlisted token-aware action;
8. retain evidence without storing raw content in receipts.

The primitives are components. The enforceable workflow and proof layer are the product.

## 4. The AirShield product stack

[[EGRESSSEAL_DIAGRAM]]

### Priority 1 — EgressSeal™

A release proof signed over the protected-content digest, upstream receipt, policy, destination ID and route, ContextFence result, one permitted action, issue time, expiry and nonce. Content or destination changes cannot reuse the same authorization for a different route.

### Priority 2 — Destination Switch

A destination is security context, not a cosmetic dropdown. The same protected payload may be allowed for organization-private AI, evaluated more narrowly for a managed regional RIA, held for research, or blocked for a public general AI. Switching destination requires a new route-specific protection receipt and seal.

### Priority 3 — ContextFence™

An explainable risk meter for the mosaic problem left after field masking. It scores stable-token linkage, entity combinations, sensitive semantics, timing/dose/scheduling detail, relationship graphs, context length and destination exposure. It returns allow, review or block against a destination-specific threshold.

### Priority 4 — SafeAction™

The model proposes an operation using protected tokens. A trusted broker verifies the seal, content digest, expiry, destination and one policy-derived action. Resolution stays inside the connector; raw values are not returned to the model. The hackathon produces a signed synthetic action receipt.

The ™ marks denote product-concept branding, not registered trademark status.

## 5. Voice-first proof, not a hidden middleware claim

AirShield's Live Shield shows what participants say inside the trust boundary beside what is being masked for the outbound AI. Interim transcript pairs are provisional. Full-turn content is rechecked at session end; only a signed final allow is designed to be egress-eligible.

The production voice path uses a trusted WebSocket gateway, self-hosted English `faster-whisper`, optional `pyannote.audio`, policy/detection and signed evidence. No Azure Speech, Google Speech-to-Text, AWS Transcribe or OpenAI transcription API is required.

Diarization is not presented as identity. The host authenticates the person through SSO, OTP, portal/CRM/EHR check-in, IVR or another approved control and supplies a signed isolated-channel binding. Unknown speakers remain unknown.

## 6. Implemented experiences

| Experience | What the demo proves |
|---|---|
| Overview | Cross-sector privacy posture, protection path, synthetic metrics and navigation |
| Live Shield | Raw-local versus protected-outbound voice/text, policy scenarios, speaker mapping and finalization behavior |
| EgressSeal control room | Destination switching, ContextFence factors, signed release proof, verification and SafeAction |
| CareShield Assistant | Protected symptom intake, emergency language, virtual-doctor guidance and synthetic booking |
| Policy Studio | Sector policy templates, entity actions, thresholds and fail-closed settings |
| Token Vault | Token mapping, reidentification workflow concepts and trust-boundary controls |
| Audit Trail | Decision/evidence presentation and chain-verification experience |
| Connections | API, SDK and application integration patterns |
| Performance Lab | Synthetic validation scenarios and quality-gate concepts |
| Settings | Private deployment and operational configuration concepts |

## 7. Horizontal market scope

| Sector | Protected workflow | SafeAction opportunity |
|---|---|---|
| Healthcare | Intake, virtual care, notes and clinician assistance | Reserve approved slot or write minimum authorized fields to EHR |
| Finance | Service calls, dispute investigation and support copilots | Open dispute review without exposing account identity to the model |
| Insurance | Claims intake, adjuster assistance and summarization | Create claim-review task through scoped connector |
| BPO / Contact Centers | Agent assist, quality and summarization | Create refund-review request without model-side identity resolution |
| SaaS / Internal Copilots | Tickets, search, coding and incident response | Create restricted ticket with connector-only field release |

The platform integrates through OpenAPI/AsyncAPI and examples for Java, .NET, Python, Node.js and Go. The deployment direction supports Azure-private environments and cloud-neutral Kubernetes/OpenBao.

## 8. Architecture and trust boundary

[[ARCHITECTURE_DIAGRAM]]

The recommended path is:

`trusted host → authenticated gateway → self-hosted voice/protection edge → Python control plane → encrypted token vault/evidence → approved AI/RIA → SafeAction broker → system of record`

The downstream AI receives protected meaning and unrelated tokens. It does not receive a generic reidentification endpoint. Raw identity is resolved, when authorized, only inside a separately controlled connector path.

## 9. Why this is different from adjacent categories

| Typical category | Common strength | Gap AirShield targets |
|---|---|---|
| Secure bot framework | Authentication, secrets and application controls | Privacy policy can be duplicated and inconsistent across bots |
| Cloud DLP/redaction API | Strong entity catalogs and managed operations | Raw data may already have left the customer boundary; provider-specific |
| AI gateway/firewall | Model routing, prompt controls and observability | Often text-first; may not include voice identity, reversible tokens and action resolution |
| Contact-center suite | Integrated media and agent workflows | Platform/channel-specific rather than provider-neutral control plane |
| Provider privacy mode | Retention/training controls | Destination still receives readable content |
| Encryption/token vault | Strong data-at-rest protection | Does not decide context risk, destination or AI actions |

AirShield's market claim should be the **combination** of pre-egress voice/text protection, user-visible proof, destination-bound authorization, cumulative context risk, identity-safe speaker binding, reversible tokenization, token-aware actions and verifiable evidence—not an unsupported claim that no competitor protects data.

## 10. Business value hypothesis

Potential measurable outcomes are:

- less duplicated privacy code across bot teams;
- faster security/privacy approval for controlled AI pilots;
- reduced raw-data exposure and breach blast radius;
- one policy layer across model providers and applications;
- easier migration between AI providers;
- lower manual redaction effort;
- stronger incident investigation and customer evidence;
- safe automation without giving the model direct identity access.

Likely sponsors include the CISO, Chief Privacy Officer, AI platform team, enterprise architecture, contact-center platform owners and regulated-business technology leadership. ROI must be measured in pilots; no guaranteed savings are claimed by this hackathon.

## 11. What is implemented now

- Responsive Next.js 16 / React 19 interface for desktop, tablet and mobile.
- Python FastAPI control plane with authorization, policy, detection, token vault, evidence, deletion and controlled reidentification routes.
- Self-hosted English voice edge and authenticated gateway design.
- Industry policy packs for Healthcare, Finance, Insurance, Contact Center and Internal Copilot.
- Per-record AES-256-GCM token mappings with random DEK/nonce, AAD and provider-wrapped DEKs.
- Azure Key Vault, OpenBao and development key-provider abstractions.
- OIDC/workload principal, tenant/scope and production fail-closed controls.
- Signed evidence chain and verified export design.
- EgressSeal development protocol using a process-local receipt registry and Ed25519 key.
- Destination Switch with private, managed, research and blocked public routes.
- ContextFence explainable cumulative-risk scoring.
- SafeAction token-only synthetic broker and signed action receipt.
- CareShield protected virtual-intake and synthetic appointment demonstration.
- OpenAPI/AsyncAPI, SDK examples, Docker Compose, Kubernetes and Azure reference assets.
- Requirements/runbook and executive/technical PDF documentation.

## 12. What the hackathon does not claim

- No real appointment, EHR, banking, claims, CRM or ticket transaction is performed.
- EgressSeal's embedded key and receipt registry are process-local development controls, not a production trust anchor.
- ContextFence is an explainable policy signal, not proof of anonymity.
- The SafeAction connector resolves no real identity.
- A comprehensive output/TTS DLP gateway is not complete.
- Models have not completed representative Nordic/EU and US production qualification.
- Live Azure/Kubernetes subscription, scale, disaster-recovery and penetration validation remain required.
- The repository is not a compliance certificate, legal opinion or medical device.

These boundaries are strengths in the presentation: the team distinguishes a working protocol demonstration from production authorization.

## 13. Defensibility and product moat

The open-source models and cryptographic primitives are reproducible. The defensible layer can become:

- customer policy/destination registry and integration graph;
- evaluated sector model packs and leakage test corpus;
- token-aware connector marketplace;
- receipt/evidence verification service;
- longitudinal ContextFence policy and attack intelligence;
- legacy/contact-center adapters;
- operational trust earned through independent validation;
- customer-specific deployment and key-custody integrations.

The proposed category is not “another redactor.” It is a **privacy control and proof plane for AI transactions**.

## 14. Roadmap

| Phase | Outcome | Exit evidence |
|---|---|---|
| Hackathon proof | Complete UX and working local protocols | Clean build, synthetic demo, signed local seal/action |
| Controlled pilot | One sector, channel and destination | Representative evaluation, monitored allow/review/block, security review |
| Action pilot | One low-risk reversible real connector | Broker threat model, least privilege, idempotency and action audit |
| Regulated production | Private deployment with external key/evidence custody | Independent review, rotation/DR tests, operational ownership |
| Platform scale | Multi-sector adapters and policy/evidence services | SLOs, tenant-isolation evidence and automated release gates |

## 15. Closing ask

Approve a controlled pilot that selects one sector, one English channel, one approved AI destination and one low-risk synthetic or reversible action. Measure privacy leakage, utility, latency, operational cost and integration effort. Do not begin with autonomous high-risk decisions.

> AirShield's promise is not that AI becomes trusted. It is that every AI data transaction must earn a destination-bound, risk-aware and verifiable permission before useful meaning leaves the boundary.
