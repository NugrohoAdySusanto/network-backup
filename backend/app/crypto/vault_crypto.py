"""
Point 1: Database Credential Vault Cryptography Module.
Encrypts and decrypts sensitive database credentials (S3 Secret Keys, Master Passwords)
stored in the PostgreSQL database.

Standards:
- AEAD Cipher: AES-256 in GCM mode (NIST SP 800-38D / NIST FIPS 197)
- Key Derivation: PBKDF2-HMAC-SHA256, 100,000 iterations (RFC 8018) deriving 256-bit key
- Nonce: 12 bytes (96 bits) cryptographically random (CSPRNG)
- Salt: 16 bytes cryptographically random (CSPRNG)
- Authentication Tag: 16 bytes (128 bits) GMAC tag appended to ciphertext
- Additional Authenticated Data (AAD): Envelope prefix [b"NBV1" || salt || nonce] (32 bytes)
- Modern Envelope Format (v2 GCM):
    Base64URL([magic (4B, b"NBV1")] || [salt (16B)] || [nonce (12B)] || [ciphertext] || [gmac_tag (16B)])
- Legacy Envelope Format (v1 CBC):
    Base64URL([salt (16B)] || [iv (16B)] || [hmac (32B)] || [ciphertext (PKCS#7 padded)])
- Legacy Fernet Format:
    Base64URL string starting with 'gAAAAA'
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings
from app.core.security_errors import (
    CredentialDecryptionError,
    EncryptionError,
    IntegrityVerificationError,
)
from app.core.security_logging import log_security_event
from app.crypto.kdf import derive_key_aes256_gcm, derive_keys_aes256_hmac

MAGIC_VAULT_HEADER = b"NBV1"


def encrypt_secret(plain_text: str, key_material: str | None = None) -> str:
    """
    Encrypts sensitive credentials stored in DB using AES-256-GCM (AEAD).
    Header [b"NBV1" (4B) || salt (16B) || nonce (12B)] is bound as AAD.

    Envelope format (AES-256-GCM v2):
      Base64URL([b"NBV1" (4B)] || [salt (16B)] || [nonce (12B)] || [ciphertext + 16B GMAC tag])
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
        nonce = os.urandom(12)
        enc_key = derive_key_aes256_gcm(secret_key, salt)

        header = MAGIC_VAULT_HEADER + salt + nonce  # 32 bytes AAD
        aesgcm = AESGCM(enc_key)
        raw_data = plain_text.encode("utf-8")
        ciphertext_and_tag = aesgcm.encrypt(nonce, raw_data, header)

        envelope = header + ciphertext_and_tag
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
    Primary: Modern AES-256-GCM AEAD (prefixed with b"NBV1").
    Fallback 1: Legacy AES-256-CBC + HMAC-SHA256 (length >= 80 bytes).
    Fallback 2: Legacy Fernet (AES-128-CBC) ONLY when data starts with 'gAAAAA'.
    Never returns cipher_text as a fallback.
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

    # Branch 3: Positively identify legacy Fernet format (starting with 'gAAAAA')
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

    # Branch 1: Modern AES-256-GCM AEAD envelope (Starts with b"NBV1")
    if raw.startswith(MAGIC_VAULT_HEADER):
        if len(raw) < 48:
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_FAILED",
                component="vault",
                operation="decrypt_secret",
                result="FAILURE",
                error_class="CredentialDecryptionError",
                details="Vault GCM envelope too short",
            )
            raise CredentialDecryptionError("Vault GCM envelope too short (minimum 48 bytes).")

        salt = raw[4:20]
        nonce = raw[20:32]
        ciphertext_and_tag = raw[32:]
        aad = raw[:32]  # Entire header is authenticated via AAD

        enc_key = derive_key_aes256_gcm(secret_key, salt)
        try:
            aesgcm = AESGCM(enc_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext_and_tag, aad)
            res = decrypted.decode("utf-8")
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_SUCCESS",
                component="vault",
                operation="decrypt_secret_gcm",
                result="SUCCESS",
            )
            return res
        except InvalidTag:
            log_security_event(
                event_code="SEC_VAULT_INTEGRITY_FAILED",
                component="vault",
                operation="decrypt_secret_gcm",
                result="FAILURE",
                error_class="IntegrityVerificationError",
                details="Credential vault GCM tag mismatch or wrong key",
            )
            raise IntegrityVerificationError("Credential vault GCM authentication tag mismatch or wrong key.")
        except Exception as exc:
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_FAILED",
                component="vault",
                operation="decrypt_secret_gcm",
                result="FAILURE",
                error_class="CredentialDecryptionError",
                details=f"Vault GCM decryption failed: {exc}",
            )
            raise CredentialDecryptionError(f"Vault GCM decryption failed: {exc}") from exc

    # Branch 2: Legacy AES-256-CBC + HMAC-SHA256 envelope (Length >= 80)
    if len(raw) >= 80:
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
                    operation="decrypt_secret_legacy_cbc",
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
                operation="decrypt_secret_legacy_cbc",
                result="SUCCESS",
            )
            return res
        except IntegrityVerificationError:
            raise
        except Exception as exc:
            log_security_event(
                event_code="SEC_VAULT_DECRYPT_FAILED",
                component="vault",
                operation="decrypt_secret_legacy_cbc",
                result="FAILURE",
                error_class="CredentialDecryptionError",
                details="Vault AES block decryption failed",
            )
            raise CredentialDecryptionError(f"Vault AES legacy decryption failed: {exc}") from exc

    # If neither modern GCM nor legacy CBC nor Fernet
    log_security_event(
        event_code="SEC_VAULT_DECRYPT_FAILED",
        component="vault",
        operation="decrypt_secret",
        result="FAILURE",
        error_class="CredentialDecryptionError",
        details="Ciphertext envelope unrecognized or too short",
    )
    raise CredentialDecryptionError("Vault envelope too short or unrecognized format.")
