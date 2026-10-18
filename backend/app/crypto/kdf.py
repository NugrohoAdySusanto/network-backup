"""
Key Derivation Function (KDF) & Cryptographic Primitives Module.
Standards:
- PBKDF2-HMAC-SHA256 (RFC 8018 / NIST SP 800-132)
- HMAC (RFC 2104)
- Constant-time comparison to prevent timing attacks.
"""
from __future__ import annotations

import hashlib
import hmac

from app.core.security_errors import SecurityError


def constant_time_equal(left: str, right: str) -> bool:
    """
    Performs constant-time comparison of two strings to prevent timing attacks.
    """
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def derive_keys_aes256_hmac(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """
    Derives 64 bytes using PBKDF2-HMAC-SHA256 (100,000 iterations):
    - 32 bytes for AES-256 cipher key
    - 32 bytes for HMAC-SHA256 authentication key

    Parameters:
        password: Secret passphrase or master key material.
        salt: Exactly 16 cryptographically random bytes.

    Returns:
        tuple[bytes, bytes]: (aes_key, mac_key), each 32 bytes (256 bits).
    """
    if not password:
        raise SecurityError("Password/key material cannot be empty for key derivation.")
    if not salt or len(salt) != 16:
        raise SecurityError("Salt must be exactly 16 bytes for PBKDF2 key derivation.")

    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000, dklen=64)
    enc_key = kdf[:32]
    mac_key = kdf[32:]
    return enc_key, mac_key


# Alias for internal backwards compatibility
_derive_keys_aes256_hmac = derive_keys_aes256_hmac
