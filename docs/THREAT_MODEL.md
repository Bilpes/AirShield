# AirShield threat model

**Method:** STRIDE plus privacy abuse cases. **Assets:** raw audio/transcript, identity bindings, token mappings/DEKs, signing keys, tenant policy, receipts, model artifacts, admin approvals, and destination credentials.

| Threat / abuse case | Primary controls in this repository | Residual risk / required validation |
|---|---|---|
| Cross-tenant read or write | Verified tenant claim; tenant predicates; composite tenant/session and tenant/mapping FKs; tenant-specific evidence chains | PostgreSQL RLS is not yet implemented; perform adversarial API/DB tests and consider RLS as defense in depth |
| Forged workload or tenant | OIDC issuer/audience/signature checks; Entra scope/role checks; exact portable subject-to-tenant/scope mappings; conflicting tenant rejection; production rejects dev auth | Entra/app-role and portable issuer configuration is customer-specific; test key rotation, stale JWKS, replay, clock skew, mapping errors, and compromised workload scenarios |
| Direct or forged browser access to the voice edge | OIDC gateway session, exact Origin/tenant checks, reconstructed protocol, CA-validated private WSS edge, rotatable injected secret, and NetworkPolicy | Landing-zone TLS/WSS, aggregate DDoS/rate controls, secure cookie issuance, FQDN-restricted JWKS egress, and penetration tests remain required |
| Raw value in logs/metrics/evidence | Forbidden-key recursion, structured scrubber, no raw metric labels, route templates rather than IDs | Application exceptions and third-party libraries need log review; use DLP scans on log sinks |
| Ciphertext copying or tampering | Per-record random AES-GCM; purpose-bound AAD; wrapped DEK key ID | KMS/IAM compromise remains high impact; test rotation, disabled key versions, and corrupted nonce/AAD/ciphertext |
| Offline guessing of lookup index | Secret HMAC key with tenant/session/entity context | Low-entropy values are exposed if the HMAC key is stolen; rotate and protect it as a secret |
| Evidence edit, gap, fork, or tail deletion | Canonical event hash, previous hash, signed digest, PostgreSQL advisory serialization, ledger-state comparison | Full DB rollback can roll back both chain and state; external immutable anchoring and timestamping are mandatory |
| Reidentification misuse | Separate request/approve scopes; requester/approver separation; purpose/ticket; 15-minute expiry; one-time requester retrieval | Colluding admins or compromised identities remain; require customer IAM/PAM, alerts, periodic access review, and sampled case review |
| Deletion bypass | Tenant-scoped approved endpoint; automatic expiry job; deletion evidence; mapping DEK/ciphertext removal | Database backups retain rows until backup expiry; key-version and backup-retention procedures must be designed and tested |
| Detector false negative / Unicode evasion | Versioned policies, contextual detector health gate, deterministic recognizers, fail-closed startup/routing, release gates | Regex fixtures are only smoke tests. Homoglyphs, spacing, ASR errors, accents, noise, domain jargon, and novel identifiers require representative evaluation and normalization |
| Streaming boundary split | Interim edge pairs are explicitly provisional/non-egress; session end rechecks the full cumulative transcript and requires a signed `allow` receipt | Representative chunk-boundary, long-session memory, reconnect, codec, and adversarial streaming tests remain release-blocking |
| Prompt injection in transcript | Downstream receives protected text; summary prompt instructs no reconstruction; destination allowlist | Privacy masking is not prompt-injection defense. Add model gateway content controls and sandbox downstream tools |
| Speaker confusion or spoofing | Diarization is track continuity only; gateway accepts a signed track claim only for host-attested isolated-channel provenance; control plane digests the subject; unknown remains unknown | Validate channel provenance and claim issuance; voice biometric use requires separate anti-spoofing, consent, bias, and legal review; never infer identity from an LLM |
| Model or policy supply-chain compromise | Digest-pinned base images/actions, SHA-checked spaCy wheel, startup verification of the promoted model manifest/files, CI gates, policy version in receipts | Registry signature/admission enforcement, full transitive Python hash locks, provenance, malware scans, and reproducible builds remain release requirements |
| KMS/signing outage | Readiness fails; protection fails closed; no unsigned production receipt | Availability impact is intentional; test circuit breaking, alerting, retry budget, and regional recovery |
| Denial of service / oversized input | Gateway connection/rate/byte/duration limits, request-size middleware, timeouts, HPA/resource limits, and low-cardinality metrics | Gateway counters are per replica; add aggregate ingress quotas, queue bounds, and load/soak tests |
| SSRF / destination escape | Destinations are policy identifiers, not caller URLs; internal fixed control-plane URL | Ollama/control-plane environment URLs are privileged deployment config; restrict egress and configuration changes |

## Highest-priority abuse tests

1. Repeat every endpoint with tenant B against tenant A IDs/tokens/receipts.
2. Corrupt each nonce, ciphertext, wrapped DEK, AAD field, event payload, signature, sequence, and ledger tail.
3. Race first receipt, same mapping, same idempotency key, approval, one-time consume, and delete.
4. Split identifiers across streaming chunks and introduce Unicode controls, homoglyphs, spelling, pauses, and ASR substitutions.
5. Disable the contextual model, KMS, JWKS, database, and immutable exporter and confirm no AI egress.
6. Attempt same-person approval, expired approval, replayed result, generic purpose, forged ticket, and scope escalation.
