from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import socket
import ssl
import tempfile
from typing import Any
from urllib.parse import urlparse

import certifi
from cryptography import x509

from app.core.security_logging import log_security_event

logger = logging.getLogger(__name__)


def get_certs_dir() -> str:
    """
    Returns the persistent directory for storing trusted certificates.
    Mounted at /app/app in Docker, ensuring persistence and instant visibility
    across API, worker, and beat services. Falls back to /tmp/certs if non-writable.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    certs_dir = os.path.join(base_dir, "certs")
    try:
        os.makedirs(certs_dir, exist_ok=True)
        test_file = os.path.join(certs_dir, f".write_test_{os.getpid()}")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return certs_dir
    except (PermissionError, OSError):
        fallback_dir = "/tmp/certs"
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir


def get_trusted_s3_ca_path() -> str:
    """Returns the path to the persistent trusted certificates file."""
    return os.path.join(get_certs_dir(), "trusted_s3_ca.crt")


def get_ca_bundle_path() -> str:
    """Returns the path to the consolidated CA bundle file."""
    return os.path.join(get_certs_dir(), "ca-bundle.crt")


def rebuild_ca_bundle() -> str:
    """
    Rebuilds the consolidated CA bundle containing:
    1. Base public CAs (from certifi: AWS, Wasabi, Cloudflare, DigiCert, etc.)
    2. Legacy / local ceph-s3.crt if present
    3. Dynamically trusted on-premise / self-signed certificates from trusted_s3_ca.crt
    """
    bundle_path = get_ca_bundle_path()
    certs_dir = get_certs_dir()

    content_parts: list[str] = []

    # 1. Base certifi bundle
    try:
        certifi_path = certifi.where()
        if os.path.exists(certifi_path):
            with open(certifi_path, "r", encoding="utf-8") as f:
                content_parts.append(f.read().strip())
    except Exception as exc:
        logger.warning("Failed to load certifi CA bundle: %s", exc)

    # 2. Pre-existing ceph-s3.crt candidates
    candidate_paths = [
        "/app/ceph-s3.crt",
        "/usr/local/share/ca-certificates/ceph-s3.crt",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ceph-s3.crt")),
    ]
    for cp in candidate_paths:
        if os.path.exists(cp) and os.path.getsize(cp) > 0:
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    content_parts.append(f.read().strip())
                break
            except Exception as exc:
                logger.warning("Failed to read pre-configured cert %s: %s", cp, exc)

    # 3. Dynamic trusted S3 CA file
    trusted_file = get_trusted_s3_ca_path()
    if os.path.exists(trusted_file) and os.path.getsize(trusted_file) > 0:
        try:
            with open(trusted_file, "r", encoding="utf-8") as f:
                trusted_raw = f.read()
            import re
            blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", trusted_raw, re.DOTALL)
            for block in blocks:
                try:
                    x509.load_pem_x509_certificate(block.encode("utf-8"))
                    content_parts.append(block.strip())
                except Exception as exc:
                    logger.warning("Skipping invalid PEM certificate block: %s", exc)
        except Exception as exc:
            logger.warning("Failed to read dynamic trusted certs: %s", exc)

    combined_bundle = "\n\n".join(part for part in content_parts if part) + "\n"

    # Atomic write
    tmp_path = os.path.join(certs_dir, f".ca-bundle-{os.getpid()}.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(combined_bundle)
        os.replace(tmp_path, bundle_path)
    except Exception as exc:
        logger.error("Failed to write consolidated CA bundle: %s", exc)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return certifi.where()

    return bundle_path


def ensure_ca_bundle() -> str:
    """
    Ensures that the consolidated CA bundle exists and is up to date.
    Returns the path to the consolidated CA bundle.
    """
    bundle_path = get_ca_bundle_path()
    trusted_path = get_trusted_s3_ca_path()

    if not os.path.exists(bundle_path) or os.path.getsize(bundle_path) == 0:
        return rebuild_ca_bundle()

    if os.path.exists(trusted_path):
        try:
            if os.path.getmtime(trusted_path) > os.path.getmtime(bundle_path):
                return rebuild_ca_bundle()
        except OSError:
            pass

    return bundle_path


def parse_endpoint(url: str) -> tuple[str, str, int]:
    """Parses endpoint url and extracts scheme, host, and port."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, host, port


def fetch_remote_server_cert(endpoint_url: str, timeout: float = 5.0) -> dict[str, Any] | None:
    """
    Retrieves the TLS certificate presented by the remote server and parses its details.
    """
    scheme, host, port = parse_endpoint(endpoint_url)
    if scheme != "https":
        return None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Determine if host is an IP address
    server_hostname = host
    try:
        ipaddress.ip_address(host)
        # If it's an IP address, some older TLS stacks don't like SNI with IPs;
        # in Python 3.10+ OpenSSL allows or ignores, but let's keep host
    except ValueError:
        pass

    with socket.create_connection((host, port), timeout=timeout) as s:
        with ctx.wrap_socket(s, server_hostname=server_hostname) as ss:
            der = ss.getpeercert(binary_form=True)
            if not der:
                raise ssl.SSLError(f"No certificate returned by {host}:{port}")
            pem = ssl.DER_cert_to_PEM_cert(der)
            cert = x509.load_der_x509_certificate(der)
            sha256 = ":".join(f"{b:02X}" for b in hashlib.sha256(der).digest())

            return {
                "host": host,
                "port": port,
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "fingerprint_sha256": sha256,
                "not_valid_before": cert.not_valid_before_utc.isoformat() if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after_utc.isoformat() if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.isoformat(),
                "pem": pem,
            }


def is_endpoint_trusted(endpoint_url: str, timeout: float = 5.0, check_hostname: bool = True) -> bool:
    """
    Checks if the endpoint TLS certificate is already trusted by the current CA bundle.
    By default enforces hostname/IP SAN verification (check_hostname=True) (SEC-02).
    """
    scheme, host, port = parse_endpoint(endpoint_url)
    if scheme != "https":
        return True

    bundle_path = ensure_ca_bundle()
    ctx = ssl.create_default_context(cafile=bundle_path)
    ctx.check_hostname = check_hostname
    ctx.verify_mode = ssl.CERT_REQUIRED

    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            with ctx.wrap_socket(s, server_hostname=host):
                return True
    except (ssl.SSLCertVerificationError, ssl.SSLError):
        return False
    except Exception as exc:
        # Network errors (connection refused, timeout) are not certificate trust errors
        logger.debug("TLS check encountered non-cert error: %s", exc)
        return False


def auto_trust_endpoint_certificate(
    endpoint_url: str,
    expected_fingerprint: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """
    Verified TLS certificate pinning (SEC-02):
    1. Checks if the HTTPS endpoint is already trusted by the operator CA bundle with hostname validation.
    2. If not trusted:
       - Requires expected_fingerprint confirmed out-of-band by the operator.
       - Compares the remote certificate's SHA-256 fingerprint with expected_fingerprint using constant-time comparison.
       - Only if the fingerprint matches is the certificate added to trusted_s3_ca.crt and the CA bundle rebuilt.
       - If expected_fingerprint is not provided or mismatches, fails closed and rejects automatic trusting.
    """
    import hmac

    scheme, host, port = parse_endpoint(endpoint_url)
    if scheme != "https":
        return {
            "trusted": True,
            "action": "skipped",
            "fingerprint": None,
            "subject": None,
            "message": "HTTP endpoint (no TLS)",
        }

    # 1. If already trusted by operator CA bundle with hostname validation:
    if is_endpoint_trusted(endpoint_url, timeout=timeout, check_hostname=True):
        return {
            "trusted": True,
            "action": "already_trusted",
            "fingerprint": None,
            "subject": None,
            "message": "SSL certificate already trusted and verified",
        }

    # 2. Fetch remote certificate
    cert_info = fetch_remote_server_cert(endpoint_url, timeout=timeout)
    if not cert_info:
        return {
            "trusted": False,
            "action": "failed",
            "fingerprint": None,
            "subject": None,
            "message": f"Could not retrieve TLS certificate from {host}:{port}",
        }

    actual_fp = cert_info["fingerprint_sha256"].upper().replace(" ", "")

    # 3. If operator provided out-of-band expected fingerprint, verify before pinning
    if expected_fingerprint:
        expected_normalized = expected_fingerprint.strip().upper().replace(" ", "")
        if not hmac.compare_digest(actual_fp, expected_normalized):
            logger.critical(
                "Certificate fingerprint mismatch for %s:%d! Expected %s, presented %s (MITM prevention)",
                host,
                port,
                expected_normalized,
                actual_fp,
            )
            return {
                "trusted": False,
                "action": "failed",
                "fingerprint": cert_info["fingerprint_sha256"],
                "subject": cert_info["subject"],
                "message": (
                    f"Certificate fingerprint mismatch: expected {expected_fingerprint}, "
                    f"but server presented {cert_info['fingerprint_sha256']}."
                ),
            }

        # Fingerprint strictly matches out-of-band confirmation: safely pin to trusted_s3_ca.crt
        pem_to_add = cert_info["pem"].strip()
        trusted_file = get_trusted_s3_ca_path()

        existing_content = ""
        if os.path.exists(trusted_file):
            try:
                with open(trusted_file, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            except Exception as exc:
                logger.warning("Failed to read %s: %s", trusted_file, exc)

        if pem_to_add not in existing_content:
            with open(trusted_file, "a", encoding="utf-8") as f:
                f.write(f"\n# Trusted S3 endpoint: {host}:{port} ({cert_info['fingerprint_sha256']})\n")
                f.write(pem_to_add + "\n")
            logger.info(
                "Pinned operator-verified TLS certificate for %s:%d (SHA-256: %s)",
                host,
                port,
                cert_info["fingerprint_sha256"],
            )

        # Rebuild CA bundle
        rebuild_ca_bundle()

        try:
            log_security_event(
                event_code="TLS_CERT_PINNED",
                component="storage_repository",
                operation="pin_certificate",
                result="SUCCESS",
                details=f"endpoint={endpoint_url} fingerprint={cert_info['fingerprint_sha256']}",
            )
        except Exception:
            pass

        return {
            "trusted": True,
            "action": "pinned",
            "fingerprint": cert_info["fingerprint_sha256"],
            "subject": cert_info["subject"],
            "issuer": cert_info["issuer"],
            "message": f"TLS certificate verified and pinned (SHA-256: {cert_info['fingerprint_sha256']})",
        }

    # 4. If no expected_fingerprint was provided, fail closed (no blind auto-trust)
    logger.warning(
        "Untrusted TLS certificate presented by %s:%d (SHA-256: %s). Out-of-band confirmation required.",
        host,
        port,
        cert_info["fingerprint_sha256"],
    )
    return {
        "trusted": False,
        "action": "unverified",
        "fingerprint": cert_info["fingerprint_sha256"],
        "subject": cert_info["subject"],
        "issuer": cert_info["issuer"],
        "message": (
            f"Endpoint certificate is not trusted. Out-of-band operator verification required "
            f"(presented SHA-256 fingerprint: {cert_info['fingerprint_sha256']})."
        ),
    }


def pin_endpoint_certificate(
    endpoint_url: str,
    expected_fingerprint: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Convenience helper to pin an endpoint certificate with verified out-of-band fingerprint."""
    return auto_trust_endpoint_certificate(
        endpoint_url=endpoint_url,
        expected_fingerprint=expected_fingerprint,
        timeout=timeout,
    )
