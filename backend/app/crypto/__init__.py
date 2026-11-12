"""
Cryptographic Package for Network Backup System.
Organized into standalone modules representing the three critical encryption points:

- Point 1 (Vault): `vault_crypto.py` - Database Credential Vault (AES-256-GCM AEAD)
- Point 2 (Manifest): `manifest_crypto.py` - S3 Repository Envelope Manifest (KEK wrapping DEK, AES-256-GCM AEAD)
- Point 3 (Payload): `payload_crypto.py` - At-Rest Configuration Payload (zlib + Simplified Direct AES-256-GCM AEAD)
- Shared Primitives: `kdf.py` - Key Derivation (PBKDF2-HMAC-SHA256, 100k iterations)
"""
from __future__ import annotations

from app.crypto.kdf import (
    _derive_keys_aes256_hmac,
    constant_time_equal,
    derive_key_aes256_gcm,
    derive_keys_aes256_hmac,
)
from app.crypto.manifest_crypto import (
    create_repo_manifest,
    get_repo_dek,
    verify_and_read_repo_manifest,
)
from app.crypto.payload_crypto import (
    decrypt_payload_aes256,
    encrypt_payload_aes256,
)
from app.crypto.vault_crypto import (
    decrypt_secret,
    encrypt_secret,
)

__all__ = [
    "derive_key_aes256_gcm",
    "derive_keys_aes256_hmac",
    "_derive_keys_aes256_hmac",
    "constant_time_equal",
    "encrypt_secret",
    "decrypt_secret",
    "create_repo_manifest",
    "verify_and_read_repo_manifest",
    "get_repo_dek",
    "encrypt_payload_aes256",
    "decrypt_payload_aes256",
]
