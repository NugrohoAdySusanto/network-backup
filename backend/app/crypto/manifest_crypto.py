"""
Point 2: S3 Repository Manifest Cryptography Module (Envelope Encryption).
Implements master-key envelope wrapping for repository Data Encryption Keys (DEK).

Standards:
- Envelope Encryption (NIST SP 800-57 Part 1)
- AES-256-CBC (NIST FIPS 197)
- PKCS#7 Padding (RFC 5652)
- PBKDF2-HMAC-SHA256 (RFC 8018)
- HMAC-SHA256 Integrity Verification (RFC 2104)
- Envelope Format: [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext]
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.security_errors import (
    EncryptionError,
    IntegrityVerificationError,
    RepositoryManifestVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_keys_aes256_hmac


def create_repo_manifest(
    master_password: str,
    repo_id: str | None = None,
    dek: str | None = None,
) -> bytes:
    """
    Creates an encrypted repository manifest using AES-256-CBC and HMAC-SHA256.
    The master_password acts as the Key Encryption Key (KEK) wrapping the
    repository Data Encryption Key (DEK).

    Envelope format:
      [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext (PKCS7 padded)]
    """
    if not master_password:
        raise EncryptionError("Master password is required for repository manifest creation.")

    try:
        salt = os.urandom(16)
        iv = os.urandom(16)
        enc_key, mac_key = derive_keys_aes256_hmac(master_password, salt)

        # Generate new random 256-bit DEK or preserve provided DEK across rotation
        repo_dek = dek or secrets.token_hex(32)

        payload = {
            "magic": "NETWORK_BACKUP_REPO_V1",
            "cipher": "AES-256-CBC+HMAC-SHA256",
            "repo_id": repo_id or str(uuid.uuid4()),
            "dek": repo_dek,
            "dek_hex": repo_dek,
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "salt_hex": salt.hex(),
            "status": "active",
        }
        plaintext = json.dumps(payload).encode("utf-8")

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()
        log_security_event(
            event_code="SEC_MANIFEST_CREATE_SUCCESS",
            component="manifest",
            operation="create_repo_manifest",
            result="SUCCESS",
            repository_id=payload["repo_id"],
        )
        return salt + iv + mac + ciphertext
    except Exception as exc:
        log_security_event(
            event_code="SEC_MANIFEST_CREATE_FAILED",
            component="manifest",
            operation="create_repo_manifest",
            result="FAILURE",
            error_class="EncryptionError",
            details="Manifest encryption failed",
        )
        raise EncryptionError(f"Repository manifest encryption failed: {exc}") from exc


def get_repo_dek(manifest: dict, master_password: str) -> str:
    """
    Extracts the Data Encryption Key (DEK) from a decrypted repository manifest.
    If the manifest is from a legacy repository that lacks an envelope DEK,
    falls back cleanly to master_password for backward compatibility.
    """
    if not manifest:
        return master_password
    return manifest.get("dek") or manifest.get("dek_hex") or master_password


def verify_and_read_repo_manifest(data: bytes, master_password: str) -> dict:
    """
    Verifies and decrypts repository manifest data fail-closed.
    Primary: AES-256-CBC + HMAC-SHA256.
    Fallback: Legacy Fernet (AES-128-CBC) ONLY when data matches known legacy format.
    Raises RepositoryManifestVerificationError or IntegrityVerificationError on any failure.
    """
    if not master_password:
        raise RepositoryManifestVerificationError("Master password is required to verify manifest.")
    if not data or len(data) < 32:
        raise RepositoryManifestVerificationError("Repository manifest data is empty or too short.")

    if len(data) >= 80:
        salt = data[:16]
        iv = data[16:32]
        mac = data[32:64]
        ciphertext = data[64:]

        try:
            enc_key, mac_key = derive_keys_aes256_hmac(master_password, salt)
            expected_mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()

            if hmac.compare_digest(expected_mac, mac):
                cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
                decryptor = cipher.decryptor()
                padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

                unpadder = padding.PKCS7(128).unpadder()
                plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

                parsed = json.loads(plaintext.decode("utf-8"))
                if parsed.get("magic") != "NETWORK_BACKUP_REPO_V1":
                    log_security_event(
                        event_code="SEC_MANIFEST_MAGIC_MISMATCH",
                        component="manifest",
                        operation="verify_manifest",
                        result="FAILURE",
                        error_class="RepositoryManifestVerificationError",
                    )
                    raise RepositoryManifestVerificationError("Repository manifest magic header mismatch.")

                log_security_event(
                    event_code="SEC_MANIFEST_VERIFY_SUCCESS",
                    component="manifest",
                    operation="verify_manifest",
                    result="SUCCESS",
                    repository_id=parsed.get("repo_id"),
                )
                return parsed
        except (RepositoryManifestVerificationError, IntegrityVerificationError):
            raise
        except Exception:
            pass

    # Check legacy Fernet manifest if data matches legacy layout (salt 16B + Fernet starting with gAAAAA)
    if len(data) >= 32 and data[16:22] == b"gAAAAA":
        try:
            from cryptography.fernet import Fernet
            salt = data[:16]
            encrypted_data = data[16:]
            kdf = hashlib.pbkdf2_hmac("sha256", master_password.encode("utf-8"), salt, 100_000, dklen=32)
            fernet = Fernet(base64.urlsafe_b64encode(kdf))
            decrypted = fernet.decrypt(encrypted_data)
            parsed = json.loads(decrypted.decode("utf-8"))
            if parsed.get("magic") == "NETWORK_BACKUP_REPO_V1":
                log_security_event(
                    event_code="SEC_MANIFEST_VERIFY_SUCCESS",
                    component="manifest",
                    operation="verify_manifest_legacy",
                    result="SUCCESS",
                    repository_id=parsed.get("repo_id"),
                )
                return parsed
        except Exception as exc:
            log_security_event(
                event_code="SEC_MANIFEST_VERIFY_FAILED",
                component="manifest",
                operation="verify_manifest_legacy",
                result="FAILURE",
                error_class="RepositoryManifestVerificationError",
                details="Legacy manifest verification failed",
            )
            raise RepositoryManifestVerificationError(f"Legacy repository manifest verification failed: {exc}") from exc

    log_security_event(
        event_code="SEC_MANIFEST_VERIFY_FAILED",
        component="manifest",
        operation="verify_manifest",
        result="FAILURE",
        error_class="RepositoryManifestVerificationError",
    )
    raise RepositoryManifestVerificationError(
        "Repository manifest verification failed: invalid master password, HMAC mismatch, or corrupt envelope."
    )
