from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

FORBIDDEN_KEYS = {
    "text",
    "raw",
    "value",
    "ciphertext",
    "authorization",
    "token",
    "audio",
    "transcript",
    "plaintext",
    "original",
}
TOKEN_PATTERN = re.compile(
    r"\[(?:PERSON|PATIENT|CUSTOMER|ACCOUNT|MRN|PHONE|EMAIL|SECRET|ADDRESS|CARD)[^\]]*\]", re.I
)


def scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in FORBIDDEN_KEYS else scrub_value(child)
            for key, child in value.items()
        }
    if isinstance(value, list | tuple):
        return [scrub_value(child) for child in value]
    if isinstance(value, str):
        return TOKEN_PATTERN.sub("[PROTECTED_TOKEN]", value)
    return value


def scrub(_logger, _method, event_dict: dict):
    return scrub_value(event_dict)


def configure_logging(level: str = "INFO"):
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            scrub,  # type: ignore[list-item]
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
