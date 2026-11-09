"""
Point 3: At-Rest Network Config Payload Cryptography Module.
Encrypts and decrypts captured network device configurations before storing in S3 object storage.

Standards:
- Compression: DEFLATE / zlib (RFC 1950 / RFC 1951) with magic header 'NBZ1'
- AEAD Cipher: AES-256 in GCM mode (NIST SP 800-38D / NIST FIPS 197)
- Key Derivation Function (KDF): PBKDF2-HMAC-SHA256 (RFC 8018) deriving 256-bit key with 100,000 iterations
- Nonce: 12 bytes (96 bits) cryptographically random (CSPRNG)
- Salt: 16 bytes cryptographically random (CSPRNG)
- Authentication Tag: 16 bytes (128 bits) GMAC tag over ciphertext and AAD
- Additional Authenticated Data (AAD): Envelope prefix [b"NBG1" || salt || nonce] (32 bytes)
- Modern Envelope Format (v2 GCM):
    [magic (4B, b"NBG1")] || [salt (16B)] || [nonce (12B)] || [ciphertext] || [gmac_tag (16B)]
- Legacy Envelope Format (v1 CBC):
    [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext (PKCS#7 padded)]
"""
from __future__ import annotations

import hashlib
import hmac
import os
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.security_errors import (
    DecryptionError,
    EncryptionError,
    IntegrityVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_key_aes256_gcm, derive_keys_aes256_hmac

MAGIC_GCM_HEADER = b"NBG1"


def encrypt_payload_aes256(
    raw_bytes: bytes,
    master_password: str | None = None,
    key_material: str | None = None,
) -> bytes:
    """
    Compresses payload using zlib (level 6) and encrypts using AES-256-GCM (AEAD).
    The header (magic bytes + salt + nonce) is bound as Additional Authenticated Data (AAD)
    to guarantee envelope tampering prevention.

    Envelope format (AES-256-GCM v2):
      [b"NBG1" (4B)] || [salt (16B)] || [nonce (12B)] || [ciphertext + 16B GMAC tag]

    Supports both direct master password and repository envelope DEK.
    Fail-closed: raises EncryptionError on any failure.
    """
    key = key_material or master_password
    if not key:
        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_FAILED",
            component="payload",
            operation="encrypt_payload",
            result="FAILURE",
            error_class="EncryptionError",
            details="Missing encryption key / master password",
        )
        raise EncryptionError("Encryption key or master password is required for payload encryption.")

    try:
        compressed_bytes = b"NBZ1" + zlib.compress(raw_bytes, level=6)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        enc_key = derive_key_aes256_gcm(key, salt)

        header = MAGIC_GCM_HEADER + salt + nonce  # 32 bytes AAD
        aesgcm = AESGCM(enc_key)
        # encrypt() produces ciphertext + 16-byte authentication tag appended
        ciphertext_and_tag = aesgcm.encrypt(nonce, compressed_bytes, header)

        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_SUCCESS",
            component="payload",
            operation="encrypt_payload",
            result="SUCCESS",
            details="AES-256-GCM AEAD encryption succeeded",
        )
        return header + ciphertext_and_tag
    except Exception as exc:
        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_FAILED",
            component="payload",
            operation="encrypt_payload",
            result="FAILURE",
            error_class="EncryptionError",
            details=f"Payload encryption error: {exc}",
        )
        raise EncryptionError(f"Payload encryption failed: {exc}") from exc


def decrypt_payload_aes256(
    data: bytes,
    master_password: str | None = None,
    key_material: str | None = None,
) -> bytes:
    """
    Decrypts configuration payload.
    Supports modern AES-256-GCM (prefixed with b"NBG1") and provides graceful fallback
    to legacy AES-256-CBC + HMAC-SHA256 for historical snapshots.

    Fail-closed:
      - On authentication tag or HMAC mismatch: raises IntegrityVerificationError.
      - On decryption or decompression failure: raises DecryptionError.
      - Never returns unverified, truncated, or raw ciphertext.
    """
    key = key_material or master_password
    if not key:
        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="DecryptionError",
            details="Missing decryption key / master password",
        )
        raise DecryptionError("Decryption key or master password is required for payload decryption.")

    if len(data) < 48:
        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="DecryptionError",
            details="Payload envelope too short",
        )
        raise DecryptionError("Payload is too short to be a valid encrypted envelope (minimum 48 bytes).")

    # =========================================================================
    # Branch 1: Modern AES-256-GCM AEAD Envelope (Starts with b"NBG1")
    # =========================================================================
    if data.startswith(MAGIC_GCM_HEADER):
        salt = data[4:20]
        nonce = data[20:32]
        ciphertext_and_tag = data[32:]
        aad = data[:32]  # Entire header is authenticated via AAD

        enc_key = derive_key_aes256_gcm(key, salt)
        try:
            aesgcm = AESGCM(enc_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext_and_tag, aad)
        except InvalidTag as exc:
            log_security_event(
                event_code="SEC_PAYLOAD_INTEGRITY_FAILED",
                component="payload",
                operation="decrypt_payload_gcm",
                result="FAILURE",
                error_class="IntegrityVerificationError",
                details="Payload GCM authentication tag mismatch or wrong key",
            )
            raise IntegrityVerificationError(
                "Payload authentication failed: invalid key material or corrupted ciphertext."
            ) from exc
        except Exception as exc:
            log_security_event(
                event_code="SEC_PAYLOAD_DECRYPT_FAILED",
                component="payload",
                operation="decrypt_payload_gcm",
                result="FAILURE",
                error_class="DecryptionError",
                details=f"Payload GCM decryption error: {exc}",
            )
            raise DecryptionError(f"Payload AES-GCM decryption failed: {exc}") from exc

    # =========================================================================
    # Branch 2: Legacy AES-256-CBC + HMAC-SHA256 Envelope (Length >= 80)
    # =========================================================================
    else:
        if len(data) < 80:
            log_security_event(
                event_code="SEC_PAYLOAD_DECRYPT_FAILED",
                component="payload",
                operation="decrypt_payload_legacy",
                result="FAILURE",
                error_class="DecryptionError",
                details="Legacy payload envelope too short (minimum 80 bytes)",
            )
            raise DecryptionError("Legacy payload is too short to be a valid encrypted envelope (minimum 80 bytes).")

        salt = data[:16]
        iv = data[16:32]
        mac = data[32:64]
        ciphertext = data[64:]

        enc_key, mac_key = derive_keys_aes256_hmac(key, salt)
        expected_mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()

        # Strict Encrypt-then-MAC verification before decryption
        if not hmac.compare_digest(expected_mac, mac):
            log_security_event(
                event_code="SEC_PAYLOAD_INTEGRITY_FAILED",
                component="payload",
                operation="decrypt_payload_legacy",
                result="FAILURE",
                error_class="IntegrityVerificationError",
                details="Legacy payload HMAC mismatch",
            )
            raise IntegrityVerificationError(
                "Payload HMAC verification failed: invalid key material or corrupted ciphertext."
            )

        try:
            cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(padded_plaintext) + unpadder.finalize()
        except Exception as exc:
            log_security_event(
                event_code="SEC_PAYLOAD_DECRYPT_FAILED",
                component="payload",
                operation="decrypt_payload_legacy",
                result="FAILURE",
                error_class="DecryptionError",
                details=f"Legacy payload AES block decryption error: {exc}",
            )
            raise DecryptionError(f"Legacy payload AES decryption failed: {exc}") from exc

    # =========================================================================
    # Shared: Decompress zlib if payload is compressed with 'NBZ1'
    # =========================================================================
    if decrypted.startswith(b"NBZ1"):
        try:
            decompressed = zlib.decompress(decrypted[4:])
            log_security_event(
                event_code="SEC_PAYLOAD_DECRYPT_SUCCESS",
                component="payload",
                operation="decrypt_payload_zlib",
                result="SUCCESS",
            )
            return decompressed
        except Exception as zerr:
            log_security_event(
                event_code="SEC_PAYLOAD_DECRYPT_FAILED",
                component="payload",
                operation="decrypt_payload_zlib",
                result="FAILURE",
                error_class="DecryptionError",
                details=f"Decompression failed: {zerr}",
            )
            raise DecryptionError(f"Decompression of decrypted payload failed: {zerr}") from zerr

    log_security_event(
        event_code="SEC_PAYLOAD_DECRYPT_SUCCESS",
        component="payload",
        operation="decrypt_payload",
        result="SUCCESS",
    )
    return decrypted
