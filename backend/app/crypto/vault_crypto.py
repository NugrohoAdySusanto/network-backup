"""
Point 1: Database Credential Vault Cryptography Module.
Encrypts and decrypts sensitive database credentials (S3 Secret Keys, Master Passwords)
stored in the PostgreSQL database.

Standards:
- AES-256 in CBC mode (NIST FIPS 197)
- PKCS#7 Padding (RFC 5652)
- Key Derivation: PBKDF2-HMAC-SHA256, 100,000 iterations (RFC 8018)
- Integrity: HMAC-SHA256 (RFC 2104) using Encrypt-then-MAC paradigm
- Format: Base64URL([salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext])
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.config import settings
from app.core.security_errors import (
    CredentialDecryptionError,
    EncryptionError,
    IntegrityVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_keys_aes256_hmac


def encrypt_secret(plain_text: str, key_material: str | None = None) -> str:
    """
    Encrypts sensitive credentials stored in DB using AES-256-CBC with PKCS#7 padding
    and HMAC-SHA256 authentication (Encrypt-then-MAC).

    Envelope format:
      [salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext] -> URL-safe Base64
    """
    if not plain_text:
        return ""

    secret_key = key_material or settings.app_secret
    if not secret_key:
        log_security_event(
            event_code="SEC_VAULT_ENCRYPT_FAILED",
            component="vault",
            operation="encrypt_secret",
            result="FAILURE",
            error_class="EncryptionError",
            details="Missing secret key",
        )
        raise EncryptionError("App secret key is missing for vault encryption.")

    try:
        salt = os.urandom(16)
        iv = os.urandom(16)
        enc_key, mac_key = derive_keys_aes256_hmac(secret_key, salt)

        padder = padding.PKCS7(128).padder()
        raw_data = plain_text.encode("utf-8")
        padded_data = padder.update(raw_data) + padder.finalize()

        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()
        envelope = salt + iv + mac + ciphertext
        res = base64.urlsafe_b64encode(envelope).decode("utf-8")
        log_security_event(
            event_code="SEC_VAULT_ENCRYPT_SUCCESS",
            component="vault",
            operation="encrypt_secret",
            result="SUCCESS",
        )
        return res
    except Exception as exc:
        log_security_event(
            event_code="SEC_VAULT_ENCRYPT_FAILED",
            component="vault",
            operation="encrypt_secret",
            result="FAILURE",
            error_class=exc.__class__.__name__,
            details="Vault encryption error",
        )
        raise EncryptionError(f"Vault encryption failed: {exc}") from exc


def decrypt_secret(cipher_text: str, key_material: str | None = None) -> str:
    """
    Decrypts database credentials fail-closed.
    Primary: AES-256-CBC + HMAC-SHA256 (256-bit).
    Fallback: Legacy Fernet (AES-128-CBC) ONLY when data is positively identified
    as legacy Fernet format. Never returns cipher_text as a fallback.
    """
    if not cipher_text:
        return ""

    secret_key = key_material or settings.app_secret
    if not secret_key:
        log_security_event(
            event_code="SEC_VAULT_DECRYPT_FAILED",
            component="vault",
            operation="decrypt_secret",
            result="FAILURE",
            error_class="CredentialDecryptionError",
            details="Missing secret key",
        )
        raise CredentialDecryptionError("App secret key is missing for vault decryption.")

    # Positively identify legacy Fernet format (standard urlsafe base64 starting with 'gAAAAA')
    if cipher_text.startswith("gAAAAA"):
        try:
            from cryptography.fernet import Fernet
            secret = secret_key.encode("utf-8")
            derived = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
            f = Fernet(derived)
            plaintext = f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_SUCCESS",
                component="vault",
                operation="decrypt_secret_legacy_fernet",
                result="SUCCESS",
            )
            return plaintext
        except Exception as exc:
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_FAILED",
                component="vault",
                operation="decrypt_secret_legacy_fernet",
                result="FAILURE",
                error_class="CredentialDecryptionError",
                details="Legacy Fernet decryption failed",
            )
            raise CredentialDecryptionError(f"Legacy Fernet decryption failed: {exc}") from exc

    # Primary AES-256-CBC + HMAC-SHA256 envelope
    try:
        raw = base64.urlsafe_b64decode(cipher_text.encode("utf-8"))
    except Exception as exc:
        log_security_event(
            event_code="SEC_VAULT_DECRYPT_FAILED",
            component="vault",
            operation="decrypt_secret",
            result="FAILURE",
            error_class="CredentialDecryptionError",
            details="Invalid base64 encoding",
        )
        raise CredentialDecryptionError("Invalid base64 encoding for vault ciphertext.") from exc

    if len(raw) < 80:
        log_security_event(
            event_code="SEC_VAULT_DECRYPT_FAILED",
            component="vault",
            operation="decrypt_secret",
            result="FAILURE",
            error_class="CredentialDecryptionError",
            details="Ciphertext envelope too short",
        )
        raise CredentialDecryptionError("Vault envelope too short (minimum 80 bytes).")

    salt = raw[:16]
    iv = raw[16:32]
    mac = raw[32:64]
    ciphertext = raw[64:]

    try:
        enc_key, mac_key = derive_keys_aes256_hmac(secret_key, salt)
        expected_mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()

        if not hmac.compare_digest(expected_mac, mac):
            log_security_event(
                event_code="SEC_VAULT_HMAC_MISMATCH",
                component="vault",
                operation="decrypt_secret",
                result="FAILURE",
                error_class="IntegrityVerificationError",
            )
            raise IntegrityVerificationError("Credential vault HMAC integrity check failed.")

        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        res = plaintext.decode("utf-8")
        log_security_event(
            event_code="SEC_VAULT_DECRYPT_SUCCESS",
            component="vault",
            operation="decrypt_secret",
            result="SUCCESS",
        )
        return res
    except IntegrityVerificationError:
        raise
    except Exception as exc:
        log_security_event(
            event_code="SEC_VAULT_DECRYPT_FAILED",
            component="vault",
            operation="decrypt_secret",
            result="FAILURE",
            error_class="CredentialDecryptionError",
            details="Vault AES block decryption failed",
        )
        raise CredentialDecryptionError(f"Vault AES decryption failed: {exc}") from exc
