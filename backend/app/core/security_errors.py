from __future__ import annotations


class SecurityError(Exception):
    """Base exception for all security and cryptographic operations."""
    code = "SECURITY_ERROR"


class EncryptionError(SecurityError):
    """Raised when an encryption operation fails."""
    code = "ENCRYPTION_FAILED"


class DecryptionError(SecurityError):
    """Raised when a decryption operation fails."""
    code = "DECRYPTION_FAILED"


class IntegrityVerificationError(SecurityError):
    """Raised when HMAC or payload integrity verification fails (mismatch or tampering)."""
    code = "INTEGRITY_VERIFICATION_FAILED"


class CredentialDecryptionError(DecryptionError):
    """Raised when database credential vault decryption fails."""
    code = "CREDENTIAL_DECRYPTION_FAILED"


class RepositoryManifestVerificationError(SecurityError):
    """Raised when repository manifest cannot be verified or decrypted."""
    code = "REPOSITORY_MANIFEST_VERIFICATION_FAILED"
