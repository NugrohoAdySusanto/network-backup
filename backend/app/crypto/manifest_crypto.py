"""
Point 2: S3 Repository Manifest Cryptography Module (Envelope Encryption).
Implements master-key envelope wrapping for repository Data Encryption Keys (DEK).

Standards:
- Envelope Encryption (NIST SP 800-57 Part 1)
- AEAD Cipher: AES-256 in GCM mode (NIST SP 800-38D / NIST FIPS 197)
- Key Derivation Function (KDF): PBKDF2-HMAC-SHA256 (RFC 8018) deriving 256-bit key with 100,000 iterations
- Nonce: 12 bytes (96 bits) cryptographically random (CSPRNG)
- Salt: 16 bytes cryptographically random (CSPRNG)
- Authentication Tag: 16 bytes (128 bits) GMAC tag appended to ciphertext
- Additional Authenticated Data (AAD): Envelope prefix [b"NBM1" || salt || nonce] (32 bytes)
- Modern Envelope Format (v2 GCM):
    [magic (4B, b"NBM1")] || [salt (16B)] || [nonce (12B)] || [ciphertext] || [gmac_tag (16B)]
- Legacy Envelope Format (v1 CBC):
    [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext (PKCS#7 padded)]
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

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.security_errors import (
    EncryptionError,
    IntegrityVerificationError,
    RepositoryManifestVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_key_aes256_gcm, derive_keys_aes256_hmac

MAGIC_MANIFEST_HEADER = b"NBM1"


def create_repo_manifest(
    master_password: str,
    repo_id: str | None = None,
    dek: str | None = None,
) -> bytes:
    """
    Creates an encrypted repository manifest using AES-256-GCM (AEAD).
    The master_password acts as the Key Encryption Key (KEK) wrapping the
    repository Data Encryption Key (DEK).
    Header [b"NBM1" (4B) || salt (16B) || nonce (12B)] is bound as AAD.

    Envelope format (AES-256-GCM v2):
      [b"NBM1" (4B)] || [salt (16B)] || [nonce (12B)] || [ciphertext + 16B GMAC tag]
    """
    if not master_password:
        raise EncryptionError("Master password is required for repository manifest creation.")

    try:
        salt = os.urandom(16)
        nonce = os.urandom(12)
        enc_key = derive_key_aes256_gcm(master_password, salt)

        # Generate new random 256-bit DEK or preserve provided DEK across rotation
        repo_dek = dek or secrets.token_hex(32)

        payload = {
            "magic": "NETWORK_BACKUP_REPO_V1",
            "cipher": "AES-256-GCM",
            "repo_id": repo_id or str(uuid.uuid4()),
            "dek": repo_dek,
            "dek_hex": repo_dek,
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "salt_hex": salt.hex(),
            "status": "active",
        }
        plaintext = json.dumps(payload).encode("utf-8")

        header = MAGIC_MANIFEST_HEADER + salt + nonce  # 32 bytes AAD
        aesgcm = AESGCM(enc_key)
        ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, header)

        log_security_event(
            event_code="SEC_MANIFEST_CREATE_SUCCESS",
            component="manifest",
            operation="create_repo_manifest",
            result="SUCCESS",
            repository_id=payload["repo_id"],
        )
        return header + ciphertext_and_tag
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
    Primary: Modern AES-256-GCM AEAD (prefixed with b"NBM1").
    Fallback 1: Legacy AES-256-CBC + HMAC-SHA256 (length >= 80 bytes).
    Fallback 2: Legacy Fernet (AES-128-CBC) ONLY when data matches known legacy format.
    Raises RepositoryManifestVerificationError or IntegrityVerificationError on any failure.
    """
    if not master_password:
        raise RepositoryManifestVerificationError("Master password is required to verify manifest.")
    if not data or len(data) < 32:
        raise RepositoryManifestVerificationError("Repository manifest data is empty or too short.")

    # Branch 1: Modern AES-256-GCM AEAD (Starts with b"NBM1")
    if data.startswith(MAGIC_MANIFEST_HEADER):
        if len(data) < 48:
            raise RepositoryManifestVerificationError("Manifest GCM envelope too short (minimum 48 bytes).")

        salt = data[4:20]
        nonce = data[20:32]
        ciphertext_and_tag = data[32:]
        aad = data[:32]  # Entire header is authenticated via AAD

        try:
            enc_key = derive_key_aes256_gcm(master_password, salt)
            aesgcm = AESGCM(enc_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext_and_tag, aad)
            parsed = json.loads(decrypted.decode("utf-8"))

            if parsed.get("magic") != "NETWORK_BACKUP_REPO_V1":
                log_security_event(
                    event_code="SEC_MANIFEST_MAGIC_MISMATCH",
                    component="manifest",
                    operation="verify_manifest_gcm",
                    result="FAILURE",
                    error_class="RepositoryManifestVerificationError",
                )
                raise RepositoryManifestVerificationError("Repository manifest magic header mismatch.")

            log_security_event(
                event_code="SEC_MANIFEST_VERIFY_SUCCESS",
                component="manifest",
                operation="verify_manifest_gcm",
                result="SUCCESS",
                repository_id=parsed.get("repo_id"),
            )
            return parsed
        except InvalidTag:
            log_security_event(
                event_code="SEC_MANIFEST_VERIFY_FAILED",
                component="manifest",
                operation="verify_manifest_gcm",
                result="FAILURE",
                error_class="RepositoryManifestVerificationError",
                details="Manifest GCM authentication tag mismatch or wrong master password",
            )
            raise RepositoryManifestVerificationError(
                "Repository manifest verification failed: invalid master password or tampered manifest."
            )
        except RepositoryManifestVerificationError:
            raise
        except Exception as exc:
            log_security_event(
                event_code="SEC_MANIFEST_VERIFY_FAILED",
                component="manifest",
                operation="verify_manifest_gcm",
                result="FAILURE",
                error_class="RepositoryManifestVerificationError",
                details=f"Manifest GCM parsing error: {exc}",
            )
            raise RepositoryManifestVerificationError(f"Repository manifest verification failed: {exc}") from exc

    # Branch 2: Legacy AES-256-CBC + HMAC-SHA256 envelope (Length >= 80)
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
                        operation="verify_manifest_legacy_cbc",
                        result="FAILURE",
                        error_class="RepositoryManifestVerificationError",
                    )
                    raise RepositoryManifestVerificationError("Repository manifest magic header mismatch.")

                log_security_event(
                    event_code="SEC_MANIFEST_VERIFY_SUCCESS",
                    component="manifest",
                    operation="verify_manifest_legacy_cbc",
                    result="SUCCESS",
                    repository_id=parsed.get("repo_id"),
                )
                return parsed
        except (RepositoryManifestVerificationError, IntegrityVerificationError):
            raise
        except Exception:
            pass

    # Branch 3: Check legacy Fernet manifest if data matches legacy layout (salt 16B + Fernet starting with gAAAAA)
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
                    operation="verify_manifest_legacy_fernet",
                    result="SUCCESS",
                    repository_id=parsed.get("repo_id"),
                )
                return parsed
        except Exception as exc:
            log_security_event(
                event_code="SEC_MANIFEST_VERIFY_FAILED",
                component="manifest",
                operation="verify_manifest_legacy_fernet",
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
        "Repository manifest verification failed: invalid master password, tag/HMAC mismatch, or corrupt envelope."
    )
