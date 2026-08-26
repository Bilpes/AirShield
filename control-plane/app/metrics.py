from prometheus_client import Counter, Histogram

PROTECTION_REQUESTS = Counter(
    "airshield_protection_requests_total", "Protection decisions", ["decision", "policy"]
)
PROTECTION_LATENCY = Histogram("airshield_protection_seconds", "Protection latency")
ENTITY_COUNTS = Counter("airshield_entities_protected_total", "Protected entities", ["entity_type", "policy"])
REIDENTIFICATION = Counter(
    "airshield_reidentification_total", "Re-identification workflow events", ["event", "outcome"]
)
# Tenant, subject, token, raw value, and session are deliberately forbidden as metric labels.
