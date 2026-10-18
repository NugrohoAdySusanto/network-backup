from __future__ import annotations

import logging
import re
from typing import Callable
from urllib.parse import unquote

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)

# Threat signature regex patterns
_SQLI_PATTERNS = [
    re.compile(r"(?i)(?:\bunion\b\s+select)"),
    re.compile(r"(?i)(?:'|\%27)\s*(?:or|and)\s*.*[=<>].*"),
    re.compile(r"(?i)(?:;\s*drop\s+table)"),
    re.compile(r"(?i)(?:information_schema)"),
    re.compile(r"(?i)(?:sleep\s*\(\s*\d+\s*\))"),
    re.compile(r"(?i)(?:benchmark\s*\(\s*\d+)"),
]

_XSS_PATTERNS = [
    re.compile(r"(?i)<script\b"),
    re.compile(r"(?i)javascript:"),
    re.compile(r"(?i)onerror\s*="),
    re.compile(r"(?i)onload\s*="),
    re.compile(r"(?i)<iframe\b"),
    re.compile(r"(?i)eval\s*\("),
]

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"(?:\.\./|\.\.\\|\%2e\%2e\%2f|\%2e\%2e\/)"),
    re.compile(r"(?i)(?:/etc/passwd|/etc/shadow|boot\.ini|win\.ini)"),
]

_SCANNER_UA_PATTERNS = [
    re.compile(r"(?i)(?:sqlmap|nikto|acunetix|dirbuster|nmap|masscan|havij|wpscan)"),
]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def security_audit_middleware(request: Request, call_next: Callable) -> Response:
    """
    High-performance security inspection middleware.
    Inspects incoming requests for SQLi, XSS, Path Traversal, and Scanner User-Agents.
    Records security incidents to system_audit_logs and blocks malicious requests.
    """
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    path = request.url.path
    query_str = unquote(request.url.query)

    # 1. Scanner User-Agent Check
    for pattern in _SCANNER_UA_PATTERNS:
        if pattern.search(user_agent):
            AuditLogService.record_event_standalone(
                category="SECURITY",
                severity="WARNING",
                event_type="SCANNER_PROBING",
                message=f"Known automated vulnerability scanner detected: {user_agent[:60]}",
                source_ip=client_ip,
                user_agent=user_agent,
                endpoint=f"{request.method} {path}",
                details={"scanner": user_agent[:100], "query": query_str[:200]},
            )
            # We don't always block benign crawlers, but scanners get flagged.

    # 2. Check for SQL Injection
    test_target = f"{path}?{query_str}"
    for pattern in _SQLI_PATTERNS:
        if pattern.search(test_target):
            AuditLogService.record_event_standalone(
                category="SECURITY",
                severity="CRITICAL",
                event_type="SQLI_ATTEMPT",
                message=f"SQL Injection attempt blocked on endpoint: {path}",
                source_ip=client_ip,
                user_agent=user_agent,
                endpoint=f"{request.method} {path}",
                details={"pattern_matched": pattern.pattern, "query_sample": query_str[:200]},
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "MALICIOUS_PAYLOAD_DETECTED",
                        "message": "Potential SQL injection pattern detected and blocked by security inspection.",
                        "details": {"type": "SQL_INJECTION"},
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )

    # 3. Check for XSS Injection
    for pattern in _XSS_PATTERNS:
        if pattern.search(test_target):
            AuditLogService.record_event_standalone(
                category="SECURITY",
                severity="CRITICAL",
                event_type="XSS_ATTEMPT",
                message=f"Cross-Site Scripting (XSS) attempt blocked on endpoint: {path}",
                source_ip=client_ip,
                user_agent=user_agent,
                endpoint=f"{request.method} {path}",
                details={"pattern_matched": pattern.pattern, "query_sample": query_str[:200]},
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "MALICIOUS_PAYLOAD_DETECTED",
                        "message": "Potential cross-site scripting pattern detected and blocked.",
                        "details": {"type": "XSS"},
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )

    # 4. Check for Path Traversal
    for pattern in _PATH_TRAVERSAL_PATTERNS:
        if pattern.search(test_target):
            AuditLogService.record_event_standalone(
                category="SECURITY",
                severity="CRITICAL",
                event_type="PATH_TRAVERSAL_ATTEMPT",
                message=f"Directory traversal / LFI attempt blocked on endpoint: {path}",
                source_ip=client_ip,
                user_agent=user_agent,
                endpoint=f"{request.method} {path}",
                details={"pattern_matched": pattern.pattern, "query_sample": query_str[:200]},
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "MALICIOUS_PAYLOAD_DETECTED",
                        "message": "Directory path traversal sequence detected and blocked.",
                        "details": {"type": "PATH_TRAVERSAL"},
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )

    # 5. Process Request
    response = await call_next(request)

    # 6. Post-execution status tracking (RBAC 403, CSRF 403)
    if response.status_code == 403 and path.startswith("/api/v1/"):
        AuditLogService.record_event_standalone(
            category="SECURITY",
            severity="WARNING",
            event_type="ACCESS_DENIED_403",
            message=f"Access forbidden (RBAC or CSRF violation) on: {request.method} {path}",
            source_ip=client_ip,
            user_agent=user_agent,
            endpoint=f"{request.method} {path}",
            details={"status_code": 403},
        )

    return response
