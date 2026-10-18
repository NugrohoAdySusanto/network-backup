"""
Point 3: At-Rest Network Config Payload Cryptography Module.
Encrypts and decrypts captured network device configurations before storing in S3 object storage.

Standards:
- Compression: DEFLATE / zlib (RFC 1950 / RFC 1951) with magic header 'NBZ1'
- AES-256 in CBC mode (NIST FIPS 197)
- PKCS#7 Padding (RFC 5652)
- PBKDF2-HMAC-SHA256 (RFC 8018)
- Integrity: HMAC-SHA256 (RFC 2104) with strict Encrypt-then-MAC authentication
- Envelope Format: [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext]
"""
from __future__ import annotations

import hashlib
import hmac
import os
import zlib

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.security_errors import (
    DecryptionError,
    EncryptionError,
    IntegrityVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_keys_aes256_hmac


def encrypt_payload_aes256(
    raw_bytes: bytes,
    master_password: str | None = None,
    key_material: str | None = None,
) -> bytes:
    """
    Compresses payload using zlib (level 6) and encrypts using AES-256-CBC
    with PKCS#7 padding and HMAC-SHA256 authentication (Encrypt-then-MAC).

    Envelope format:
      [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext]
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
        iv = os.urandom(16)
        enc_key, mac_key = derive_keys_aes256_hmac(key, salt)

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(compressed_bytes) + padder.finalize()

        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()
        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_SUCCESS",
            component="payload",
            operation="encrypt_payload",
            result="SUCCESS",
        )
        return salt + iv + mac + ciphertext
    except Exception as exc:
        log_security_event(
            event_code="SEC_PAYLOAD_ENCRYPT_FAILED",
            component="payload",
            operation="encrypt_payload",
            result="FAILURE",
            error_class="EncryptionError",
            details="Payload encryption error",
        )
        raise EncryptionError(f"Payload encryption failed: {exc}") from exc


def decrypt_payload_aes256(
    data: bytes,
    master_password: str | None = None,
    key_material: str | None = None,
) -> bytes:
    """
    Verifies HMAC before AES decryption.
    Supports both direct master password and repository envelope DEK.
    Fail-closed: on HMAC mismatch raises IntegrityVerificationError.
    On decryption failure raises DecryptionError. Never returns unverified/raw data.
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

    if len(data) < 80:
        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="DecryptionError",
            details="Payload envelope too short",
        )
        raise DecryptionError("Payload is too short to be a valid encrypted envelope (minimum 80 bytes).")

    salt = data[:16]
    iv = data[16:32]
    mac = data[32:64]
    ciphertext = data[64:]

    enc_key, mac_key = derive_keys_aes256_hmac(key, salt)
    expected_mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()

    # Crucial security verification: HMAC verified BEFORE AES decryption!
    if not hmac.compare_digest(expected_mac, mac):
        log_security_event(
            event_code="SEC_PAYLOAD_INTEGRITY_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="IntegrityVerificationError",
            details="Payload HMAC mismatch",
        )
        raise IntegrityVerificationError("Payload HMAC verification failed: invalid key material or corrupted ciphertext.")

    try:
        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(padded_plaintext) + unpadder.finalize()

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
                raise DecryptionError(f"Decompression of decrypted payload failed: {zerr}") from zerr

        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_SUCCESS",
            component="payload",
            operation="decrypt_payload",
            result="SUCCESS",
        )
        return decrypted
    except DecryptionError:
        raise
    except Exception as exc:
        log_security_event(
            event_code="SEC_PAYLOAD_DECRYPT_FAILED",
            component="payload",
            operation="decrypt_payload",
            result="FAILURE",
            error_class="DecryptionError",
            details="Payload AES block decryption error",
        )
        raise DecryptionError(f"Payload AES decryption failed: {exc}") from exc
