# AirShield production architecture

## Purpose and boundary

AirShield is an English, voice-first privacy enforcement layer. Raw audio and raw transcript stay inside the customer trust boundary. A self-hosted speech/diarization path creates speaker tracks; a trusted host identity flow may bind a track to a person. The detector and policy engine replace sensitive spans before any approved AI destination receives text. Diarization maintains track continuity—it does not prove identity.

```text
Browser/telephony -> OIDC WebSocket gateway -> private edge STT + diarization -> raw local pane
                                      |
                                      v
trusted host identity -> speaker binding -> detector/policy -> token vault
                                                      |          |
                                                      v          v
                                              protected pane   PostgreSQL
                                                      |
                                           destination allowlist
                                                      |
                                               approved local AI
                                                      |
                                      signed, hash-chained receipt
```

## Trust boundaries

1. **Endpoint/local UI:** may display ephemeral raw transcript to an authorized operator. Browser speech APIs are not the production speech boundary.
2. **Trusted gateway:** validates the host-issued OIDC cookie/bearer token, exact Origin, and expected tenant; reconstructs an allowlisted English session protocol; enforces connection, rate, byte, and duration limits; validates the private edge CA over WSS; and injects its secret only on that private edge hop. It is the only browser-reachable voice path.
3. **Private edge:** runs version-pinned self-hosted models and sends text to the control plane. Interim chunk results are provisional and always `safe_for_egress=false`; only a final full-context `allow` with a signed receipt is eligible for routing. Raw audio/transcript must not enter general logs or evidence.
4. **Control plane:** validates workload OIDC, extracts the signed tenant claim, applies destination and entity policy, and owns reidentification authorization.
5. **Vault/database:** stores only AES-256-GCM ciphertext, random nonces, provider-wrapped per-record DEKs, keyed lookup digests, and metadata. Every query is tenant-scoped; composite foreign keys preserve tenant relationships.
6. **Key custody:** Azure Key Vault or OpenBao Transit wraps DEKs and signs evidence. Application pods receive workload identity, not long-lived KMS credentials.
7. **AI destination:** receives protected text only after an `allow` decision. `block` and `review` are not safe-for-egress states.
8. **Evidence export:** signed tenant chains must be periodically anchored to customer-controlled immutable storage. The database chain detects row edits/gaps/tail deletion against ledger state, but only an external anchor detects rollback of the entire database and state together.

## Cryptography

- Random 256-bit DEK and 96-bit nonce for every mapping; AES-256-GCM authenticates ciphertext.
- AAD binds tenant, session, token, and entity type so copied or relabeled records do not decrypt.
- Provider-specific RSA-OAEP-256 wrapping (Azure), Transit wrapping (OpenBao), or development-only local AES-GCM wrapping.
- Keyed HMAC-SHA-256 lookup values prevent unsalted dictionary lookup.
- Per-tenant evidence sequence and previous hash are serialized with PostgreSQL advisory locks and row locks. Each event hash is externally signed.
- Expiry or approved deletion removes the wrapped DEK and ciphertext from the live database. Backups may retain historical rows until their configured expiry; backup lifecycle and key-version retirement are therefore part of the erasure design.

## Identity and tenant isolation

Production callers use OIDC workload JWTs. Entra callers take the configurable tenant claim and roles only from a verified token. Portable projected service-account tokens—which normally have neither application tenant nor scope claims—must match an exact operator-configured subject-to-tenant/scope binding; any conflicting signed tenant claim is rejected. Roles/scopes gate protect, bind, evidence, delete, request-reidentification, and approve-reidentification operations. The development header identity mode is rejected in production.

A host app authenticates a caller through SSO, OTP, IVR, CRM/EHR check-in, or a separately governed biometric process. For the voice gateway, a signed speaker-track claim is accepted only when the host has trustworthy isolated-channel provenance; the edge then uses the scoped binding route. AirShield stores a keyed digest of the host subject and emits an unrelated speaker token to the LLM. Without that signed provenance, speakers remain unknown. Reidentification requires a specific purpose and ticket, a distinct approver, and one-time retrieval by the original requester.

## Deployment profiles

- **Azure private reference:** private AKS API, separate workload identities, a Premium control vault/HSM keys, an isolated gateway-secret vault, private PostgreSQL Flexible Server, private DNS/endpoints, diagnostics, and digest-pinned images. The Next.js workload has a separate identity with no Key Vault permissions.
- **Portable Kubernetes:** projected OIDC service-account identity, OpenBao Agent Kubernetes auth and Transit, cluster NetworkPolicy, and an external/operated PostgreSQL service. SPIFFE/SPIRE can replace the projected token when the control-plane issuer/audience contract is preserved.

No public ingress is included. Customer landing zones must provide private ingress, controlled egress, DNS, certificates, WAF/API gateway where needed, vulnerability admission policy, and immutable audit export.
