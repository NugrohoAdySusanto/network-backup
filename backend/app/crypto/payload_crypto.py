"""
Point 3: At-Rest Network Config Payload Cryptography Module.
Encrypts and decrypts captured network device configurations before storing in S3 object storage.

Standards:
- Compression: DEFLATE / zlib (RFC 1950 / RFC 1951) with magic marker 'NBZ1'
- AEAD Cipher: AES-256 in GCM mode (NIST SP 800-38D / NIST FIPS 197)
- Direct 256-bit Key: Key material resolved directly from repository DEK (no PBKDF2 stretching)
- Nonce: 12 bytes (96 bits) cryptographically random (CSPRNG)
- Authentication Tag: 16 bytes (128 bits) GMAC tag over ciphertext and AAD
- Additional Authenticated Data (AAD): Envelope prefix [b"NBG2" || nonce] (16 bytes)
- Envelope Format (v3 Simplified AES-256-GCM):
    [magic (4B, b"NBG2")] || [nonce (12B)] || [ciphertext] || [gmac_tag (16B)]
"""
from __future__ import annotations

import hashlib
import os
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.security_errors import (
    DecryptionError,
    EncryptionError,
    IntegrityVerificationError,
    SecurityError,
)
from app.core.security_logging import log_security_event

MAGIC_GCM_HEADER = b"NBG2"


def _resolve_symmetric_key(key: str | bytes) -> bytes:
    """
    Resolves a 32-byte (256-bit) symmetric key from key material:
    - If 32 raw bytes: used directly.
    - If 64-char hex string (standard DEK token): decoded directly to 32 bytes.
    - Otherwise (passphrase/master password): hashed with single-pass SHA-256 to produce 32 bytes.
    """
    if isinstance(key, bytes):
        if len(key) == 32:
            return key
        return hashlib.sha256(key).digest()
    if isinstance(key, str):
        if len(key) == 64:
            try:
                return bytes.fromhex(key)
            except ValueError:
                pass
        return hashlib.sha256(key.encode("utf-8")).digest()
    raise SecurityError("Invalid key material type for symmetric key derivation.")


def encrypt_payload_aes256(
    raw_bytes: bytes,
    master_password: str | None = None,
    key_material: str | None = None,
) -> bytes:
    """
    Compresses payload using zlib (level 6) and encrypts using simplified AES-256-GCM (AEAD).
    The header (b"NBG2" + nonce 12B) is bound as Additional Authenticated Data (AAD)
    to guarantee envelope tampering prevention without PBKDF2 overhead.

    Envelope format:
      [b"NBG2" (4B)] || [nonce (12B)] || [ciphertext + 16B GMAC tag]
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
        nonce = os.urandom(12)
        enc_key = _resolve_symmetric_key(key)

        header = MAGIC_GCM_HEADER + nonce  # 16 bytes AAD
        aesgcm = AESGCM(enc_key)
        ciphertext_and_tag = aesgcm.encrypt(nonce, compressed_bytes, header)

        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_SUCCESS",
            component="payload",
            operation="encrypt_payload",
            result="SUCCESS",
            details="Simplified AES-256-GCM AEAD encryption succeeded",
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
    Decrypts configuration payload using simplified AES-256-GCM (AEAD) fail-closed.
    Envelope must begin with magic marker b"NBG2" (minimum 32 bytes).
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

    if not data or len(data) < 32 or not data.startswith(MAGIC_GCM_HEADER):
        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="DecryptionError",
            details="Payload envelope invalid, too short, or unrecognized magic marker",
        )
        raise DecryptionError("Payload is not a valid NBG2 encrypted envelope (minimum 32 bytes).")

    nonce = data[4:16]
    ciphertext_and_tag = data[16:]
    aad = data[:16]  # 16-byte AAD header: b"NBG2" (4B) + nonce (12B)

    enc_key = _resolve_symmetric_key(key)
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

    # Decompress zlib if payload is compressed with 'NBZ1'
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
