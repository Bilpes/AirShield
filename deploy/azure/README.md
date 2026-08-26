# Azure private reference deployment

This Bicep reference provisions a private AKS cluster with OIDC/workload identity, a zone-redundant private PostgreSQL Flexible Server, a purge-protected Premium control vault with separate HSM-backed wrap/signing keys, an isolated gateway-secret vault, private DNS/endpoints, and centralized diagnostics.

## Deployment sequence

1. Copy `main.bicepparam.example` outside source control and supply the database credentials, token index key, and edge/gateway secret through an approved secret store in the deployment pipeline.
2. Validate with `az bicep build --file main.bicep` and an Azure what-if in the target subscription.
3. Deploy at subscription scope, install/verify the Azure Key Vault CSI and policy add-ons, and replace all `REPLACE_*` values in `deploy/kubernetes/overlays/azure`.
4. Create/review the Entra control-plane application roles and scope; assign `airshield.protect` only to the web identity and `airshield.protect` plus `airshield.bind` only to the voice-edge identity; then configure issuer/audience/JWKS values. The control-plane identity receives only the control vault rights; the gateway identity receives Secrets User only on the separate gateway vault; web and edge identities receive no Key Vault rights.
5. Restrict the overlay's standard-NetworkPolicy HTTPS egress to Entra endpoints using Azure Firewall or a reviewed FQDN-aware CNI policy.
6. Build, scan, sign, attest, and pin the web, trusted-gateway, voice-edge, and control-plane image digests plus model artifacts. Never deploy a placeholder digest.
7. Apply Alembic migrations as a separately approved one-shot job before application rollout.
8. Apply the Azure Kubernetes overlay and verify private DNS, workload federation, Key Vault RBAC, PostgreSQL `verify-full` TLS, readiness, evidence signatures, backup restore, and retention jobs.

The template intentionally does not create public ingress. Expose only the included trusted WebSocket gateway through an internal TLS/WSS gateway/private-link path appropriate to the customer landing zone; the edge remains ClusterIP-only. The host must issue the short-lived HttpOnly OIDC session cookie, and Azure Firewall or an FQDN-aware CNI must constrain gateway/edge identity egress. Password authentication is retained for application bootstrap; mature deployments should assess Entra PostgreSQL authentication and a supported async token-refresh strategy. The Bicep must pass tenant-specific security, cost, region availability, policy, and legal review before use.
