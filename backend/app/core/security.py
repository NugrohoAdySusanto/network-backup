from __future__ import annotations

import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

from app.config import settings
from app.core.errors import AppError


_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def normalize_username(username: str) -> str:
    return username.strip()


def validate_password_policy(password: str) -> None:
    if len(password) < settings.password_min_length:
        raise AppError(
            status_code=422,
            code="PASSWORD_POLICY_FAILED",
            message=(
                f"Password must be at least "
                f"{settings.password_min_length} characters."
            ),
        )

    if len(password) > settings.password_max_length:
        raise AppError(
            status_code=422,
            code="PASSWORD_POLICY_FAILED",
            message=(
                f"Password must be no more than "
                f"{settings.password_max_length} characters."
            ),
        )


def hash_password(password: str) -> str:
    validate_password_policy(password)
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


from app.core.security_errors import (
    CredentialDecryptionError,
    DecryptionError,
    EncryptionError,
    IntegrityVerificationError,
    RepositoryManifestVerificationError,
    SecurityError,
)
from app.core.security_logging import log_security_event

# ---------------------------------------------------------------------------
# Cryptographic Module Re-exports
# The 3 standalone encryption points are modularized in `app.crypto`:
# - Point 1 (Vault DB): `app.crypto.vault_crypto`
# - Point 2 (S3 Manifest): `app.crypto.manifest_crypto`
# - Point 3 (S3 Payload): `app.crypto.payload_crypto`
# - Shared Primitives & KDF: `app.crypto.kdf`
# ---------------------------------------------------------------------------
from app.crypto import (
    _derive_keys_aes256_hmac,
    constant_time_equal,
    create_repo_manifest,
    decrypt_payload_aes256,
    decrypt_secret,
    derive_key_aes256_gcm,
    derive_keys_aes256_hmac,
    encrypt_payload_aes256,
    encrypt_secret,
    get_repo_dek,
    verify_and_read_repo_manifest,
)

__all__ = [
    "normalize_username",
    "validate_password_policy",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "constant_time_equal",
    "derive_keys_aes256_hmac",
    "_derive_keys_aes256_hmac",
    "encrypt_secret",
    "decrypt_secret",
    "create_repo_manifest",
    "verify_and_read_repo_manifest",
    "get_repo_dek",
    "encrypt_payload_aes256",
    "decrypt_payload_aes256",
    "SecurityError",
    "EncryptionError",
    "DecryptionError",
    "CredentialDecryptionError",
    "IntegrityVerificationError",
    "RepositoryManifestVerificationError",
    "log_security_event",
]

