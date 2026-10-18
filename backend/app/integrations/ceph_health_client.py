from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CephHealthResult:
    status: str
    summary: str
    details: dict[str, Any]
    last_checked_at: str
    last_success_at: str | None


class CephHealthClient:
    _cached_token: str | None = None
    _token_expiry: float = 0.0

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        pinned_fingerprint: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (base_url or settings.ceph_health_url).rstrip("/")
        self.static_token = token or settings.ceph_health_token
        self.username = username or settings.ceph_health_username
        self.password = password or settings.ceph_health_password
        if pinned_fingerprint == "":
            self.pinned_fingerprint = None
        elif pinned_fingerprint is not None:
            self.pinned_fingerprint = pinned_fingerprint
        else:
            self.pinned_fingerprint = settings.ceph_health_pinned_fingerprint or None
        self.timeout = timeout

    def _authenticate(self, client: httpx.Client) -> str | None:
        if not self.username or not self.password:
            return None
        auth_url = f"{self.base_url}/api/auth"
        try:
            resp = client.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                headers={
                    "Accept": "application/vnd.ceph.api.v1.0+json",
                    "Content-Type": "application/json",
                },
            )
            if resp.is_success:
                data = resp.json()
                token = data.get("token")
                if token:
                    CephHealthClient._cached_token = token
                    # Cache token for 7 hours (Ceph default TTL is 8h)
                    CephHealthClient._token_expiry = time.time() + (7 * 3600)
                    logger.info("Successfully authenticated with Ceph Dashboard API as user %s", self.username)
                    return token
            logger.warning("Ceph authentication failed (HTTP %s): %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("Ceph authentication request failed to %s: %s", auth_url, exc)
        return None

    def _get_active_token(self, client: httpx.Client) -> str | None:
        now = time.time()
        # 1. Use cached token if still valid
        if CephHealthClient._cached_token and now < CephHealthClient._token_expiry:
            return CephHealthClient._cached_token

        # 2. If credentials are provided, perform auto-login
        if self.username and self.password:
            fresh_token = self._authenticate(client)
            if fresh_token:
                return fresh_token

        # 3. Fallback to static token
        return self.static_token

    def get_health(self) -> CephHealthResult:
        now_iso = datetime.now(timezone.utc).isoformat()

        if not self.base_url:
            return CephHealthResult(
                status="UNKNOWN",
                summary="Ceph health URL not configured.",
                details={"reason": "NOT_CONFIGURED"},
                last_checked_at=now_iso,
                last_success_at=None,
            )

        endpoint = f"{self.base_url}/api/health/minimal"

        verify_opt: Any = True
        if self.base_url.lower().startswith("https://"):
            import hmac
            import ssl
            from app.services.ssl_cert_service import ensure_ca_bundle, fetch_remote_server_cert

            pinned_fp = (self.pinned_fingerprint or "").strip().upper().replace(" ", "")
            if pinned_fp:
                # SEC-02: Out-of-band pinned fingerprint confirmed by operator
                cert_info = fetch_remote_server_cert(self.base_url, timeout=self.timeout)
                if not cert_info:
                    logger.error("Could not fetch remote TLS certificate from Ceph at %s", self.base_url)
                    return CephHealthResult(
                        status="UNKNOWN",
                        summary="Could not retrieve Ceph TLS certificate.",
                        details={"reason": "CERT_FETCH_FAILED"},
                        last_checked_at=now_iso,
                        last_success_at=None,
                    )
                actual_fp = cert_info["fingerprint_sha256"].upper().replace(" ", "")
                if not hmac.compare_digest(actual_fp, pinned_fp):
                    logger.critical(
                        "Ceph TLS certificate fingerprint mismatch! Expected %s, got %s (MITM prevention)",
                        pinned_fp,
                        actual_fp,
                    )
                    return CephHealthResult(
                        status="CRITICAL",
                        summary="Ceph SSL certificate fingerprint mismatch (MITM protection).",
                        details={"reason": "FINGERPRINT_MISMATCH"},
                        last_checked_at=now_iso,
                        last_success_at=None,
                    )

                # Pinned certificate is authentic: construct context trusting ONLY this certificate (no default system root CAs)
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_REQUIRED
                try:
                    ctx.load_verify_locations(cadata=cert_info["pem"])
                except Exception as exc:
                    logger.warning("Failed to load certificate into SSL context: %s", exc)
                verify_opt = ctx
            else:
                # No pinned fingerprint: strictly enforce CA trust bundle and hostname / IP SAN verification
                bundle_path = ensure_ca_bundle()
                ctx = ssl.create_default_context(cafile=bundle_path)
                ctx.check_hostname = True
                ctx.verify_mode = ssl.CERT_REQUIRED
                verify_opt = ctx


        try:
            with httpx.Client(timeout=self.timeout, verify=verify_opt) as client:
                token = self._get_active_token(client)
                if not token:
                    return CephHealthResult(
                        status="UNKNOWN",
                        summary="Ceph credentials or token not configured.",
                        details={"reason": "NO_TOKEN_OR_CREDENTIALS"},
                        last_checked_at=now_iso,
                        last_success_at=None,
                    )

                headers = {
                    "Accept": "application/vnd.ceph.api.v1.0+json",
                    "Authorization": f"Bearer {token}",
                }

                resp = client.get(endpoint, headers=headers)

                # If token expired (401) and we have username/password, re-authenticate and retry
                if resp.status_code == 401 and self.username and self.password:
                    logger.info("Ceph token expired (401), re-authenticating with credentials...")
                    new_token = self._authenticate(client)
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        resp = client.get(endpoint, headers=headers)

                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            logger.warning("Failed to retrieve Ceph health from %s: %s", endpoint, exc)
            return CephHealthResult(
                status="UNKNOWN",
                summary=f"Unable to query Ceph health API: {exc}",
                details={"reason": str(exc)},
                last_checked_at=now_iso,
                last_success_at=None,
            )

        health_data = payload.get("health") or {}
        raw_status = str(health_data.get("status") or "").upper()

        if raw_status in {"HEALTH_OK", "OK"}:
            status = "HEALTH_OK"
            summary = "Cluster is healthy."
        elif raw_status in {"HEALTH_WARN", "WARN", "WARNING"}:
            status = "HEALTH_WARN"
            summary = "Cluster warning detected."
        elif raw_status in {"HEALTH_ERR", "ERR", "ERROR"}:
            status = "HEALTH_ERR"
            summary = "Cluster error detected."
        else:
            status = "UNKNOWN"
            summary = "Unknown Ceph health state."

        # Extract checks summary
        checks = health_data.get("checks")
        check_summaries = []
        if isinstance(checks, list):
            for check in checks:
                msg = check.get("summary", {}).get("message")
                if msg:
                    check_summaries.append(msg)
        elif isinstance(checks, dict):
            for check in checks.values():
                msg = check.get("summary", {}).get("message")
                if msg:
                    check_summaries.append(msg)

        if check_summaries:
            summary = "; ".join(check_summaries[:2])
            if len(check_summaries) > 2:
                summary += f" (+{len(check_summaries) - 2} more)"

        details: dict[str, Any] = {
            "hosts": payload.get("hosts"),
            "pools_count": len(payload.get("pools") or []),
            "checks_count": len(check_summaries),
        }
        df_stats = payload.get("df", {}).get("stats", {})
        if df_stats:
            details["total_bytes"] = df_stats.get("total_bytes")
            details["total_avail_bytes"] = df_stats.get("total_avail_bytes")
            details["total_used_raw_bytes"] = df_stats.get("total_used_raw_bytes")

        return CephHealthResult(
            status=status,
            summary=summary,
            details=details,
            last_checked_at=now_iso,
            last_success_at=now_iso,
        )
