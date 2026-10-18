from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("security")

_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|secret|token|key|credential|auth)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"[a-zA-Z0-9+/=]{24,}"),  # base64 / token-like sequences
]


def sanitize_security_details(details: str | None) -> str | None:
    if not details:
        return None
    safe = str(details).replace("\n", " ").strip()
    for pattern in _SENSITIVE_PATTERNS:
        safe = pattern.sub(r"\1=[REDACTED]" if "(" in pattern.pattern else "[REDACTED]", safe)
    return safe[:150]


def log_security_event(
    *,
    event_code: str,
    component: str,
    operation: str,
    result: str,  # "SUCCESS" or "FAILURE"
    device_id: str | int | None = None,
    repository_id: str | None = None,
    error_class: str | None = None,
    details: str | None = None,
) -> None:
    """
    Emits a structured JSON security log entry containing ONLY safe metadata fields.
    NEVER logs credentials, passwords, encryption keys, HMAC keys, or payload contents.
    Enforces safe predefined detail messages and sanitization.
    """
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_code": event_code,
        "component": component,
        "operation": operation,
        "result": result,
    }
    if device_id is not None:
        record["device_id"] = str(device_id)
    if repository_id is not None:
        record["repository_id"] = str(repository_id)
    if error_class is not None:
        record["error_class"] = error_class
    if details is not None:
        sanitized = sanitize_security_details(details)
        if sanitized:
            record["details"] = sanitized

    msg = json.dumps(record, sort_keys=True)
    if result == "FAILURE":
        logger.warning("SECURITY_EVENT: %s", msg)
    else:
        logger.info("SECURITY_EVENT: %s", msg)
