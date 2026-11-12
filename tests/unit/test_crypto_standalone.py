"""
Unit tests for modular cryptographic package (app.crypto).
Verifies that each of the 3 encryption points can function as a standalone module:
- Point 1: Database Vault Cryptography (vault_crypto.py)
- Point 2: S3 Repository Manifest Envelope (manifest_crypto.py)
- Point 3: At-Rest Network Config Payload (payload_crypto.py)
- Key Derivation: PBKDF2-HMAC-SHA256 (kdf.py)
"""
import pytest
from app.crypto.kdf import constant_time_equal, derive_keys_aes256_hmac
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
from app.core.security_errors import (
    CredentialDecryptionError,
    DecryptionError,
    EncryptionError,
    IntegrityVerificationError,
    RepositoryManifestVerificationError,
)


def test_kdf_standalone():
    """Verify PBKDF2-HMAC-SHA256 key derivation produces two independent 32-byte keys."""
    salt = b"0123456789abcdef"
    enc_key, mac_key = derive_keys_aes256_hmac("MyTestPassword123!", salt)
    assert len(enc_key) == 32
    assert len(mac_key) == 32
    assert enc_key != mac_key

    # Constant time equal
    assert constant_time_equal("secret_token_123", "secret_token_123") is True
    assert constant_time_equal("secret_token_123", "secret_token_456") is False


def test_point1_vault_crypto_roundtrip():
    """Point 1: Test DB Vault AES-256-GCM (AEAD) encryption, tamper detection, and fallback."""
    import base64
    import hashlib
    import hmac
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    secret_text = "s3_aws_secret_key_super_confidential_999!"
    custom_master = "MasterKeyForVault123!@#"

    # Encrypt with custom key
    encrypted = encrypt_secret(secret_text, key_material=custom_master)
    assert isinstance(encrypted, str)
    assert encrypted != secret_text

    # Verify modern envelope format: begins with magic b"NBV1"
    raw = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
    assert raw[:4] == b"NBV1"
    assert len(raw) >= 48

    # Decrypt with custom key
    decrypted = decrypt_secret(encrypted, key_material=custom_master)
    assert decrypted == secret_text

    # Decrypt with wrong key fails with IntegrityVerificationError
    with pytest.raises(IntegrityVerificationError):
        decrypt_secret(encrypted, key_material="WrongPassword12345!")

    # Tamper nonce in AAD header (byte 25) -> fails integrity verification
    tampered_nonce = bytearray(raw)
    tampered_nonce[25] ^= 0x01
    with pytest.raises(IntegrityVerificationError):
        decrypt_secret(base64.urlsafe_b64encode(tampered_nonce).decode("utf-8"), key_material=custom_master)

    # Tamper ciphertext / tag (last byte) -> fails integrity verification
    tampered_tag = bytearray(raw)
    tampered_tag[-1] ^= 0x01
    with pytest.raises(IntegrityVerificationError):
        decrypt_secret(base64.urlsafe_b64encode(tampered_tag).decode("utf-8"), key_material=custom_master)

    # Backward compatibility: verify fallback to legacy AES-256-CBC + HMAC-SHA256
    legacy_salt = b"0123456789abcdef"
    legacy_iv = b"fedcba9876543210"
    enc_key, mac_key = derive_keys_aes256_hmac(custom_master, legacy_salt)
    padder = padding.PKCS7(128).padder()
    padded_plain = padder.update(secret_text.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(legacy_iv))
    legacy_cipher = cipher.encryptor().update(padded_plain) + cipher.encryptor().finalize()
    legacy_mac = hmac.new(mac_key, legacy_salt + legacy_iv + legacy_cipher, hashlib.sha256).digest()
    legacy_envelope = base64.urlsafe_b64encode(legacy_salt + legacy_iv + legacy_mac + legacy_cipher).decode("utf-8")

    assert decrypt_secret(legacy_envelope, key_material=custom_master) == secret_text


def test_point2_manifest_envelope_crypto_roundtrip():
    """Point 2: Test S3 Repository Manifest AES-256-GCM envelope encryption, rotation, and fallback."""
    import hashlib
    import hmac
    import json
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    master_kek = "MasterPasswordRepoKEK987#"
    repo_id = "repo-uuid-test-1234"

    # Create manifest
    manifest_bytes = create_repo_manifest(master_kek, repo_id=repo_id)
    assert isinstance(manifest_bytes, bytes)
    assert len(manifest_bytes) >= 80

    # Modern format magic header NBM1
    assert manifest_bytes[:4] == b"NBM1"

    # Verify and parse manifest
    parsed = verify_and_read_repo_manifest(manifest_bytes, master_kek)
    assert parsed["magic"] == "NETWORK_BACKUP_REPO_V1"
    assert parsed["cipher"] == "AES-256-GCM"
    assert parsed["repo_id"] == repo_id
    assert "dek" in parsed

    # Extract DEK
    dek = get_repo_dek(parsed, master_kek)
    assert len(dek) == 64  # 32 bytes hex

    # Verify fail-closed with wrong master password
    with pytest.raises(RepositoryManifestVerificationError):
        verify_and_read_repo_manifest(manifest_bytes, "IncorrectMasterPass!")

    # Tamper nonce in AAD header (byte 25) -> fails manifest verification
    tampered_nonce = bytearray(manifest_bytes)
    tampered_nonce[25] ^= 0x01
    with pytest.raises(RepositoryManifestVerificationError):
        verify_and_read_repo_manifest(bytes(tampered_nonce), master_kek)

    # Tamper tag (last byte) -> fails manifest verification
    tampered_tag = bytearray(manifest_bytes)
    tampered_tag[-1] ^= 0x01
    with pytest.raises(RepositoryManifestVerificationError):
        verify_and_read_repo_manifest(bytes(tampered_tag), master_kek)

    # Backward compatibility: verify fallback to legacy AES-256-CBC + HMAC-SHA256 manifest
    legacy_salt = b"0123456789abcdef"
    legacy_iv = b"fedcba9876543210"
    enc_key, mac_key = derive_keys_aes256_hmac(master_kek, legacy_salt)
    legacy_payload = {
        "magic": "NETWORK_BACKUP_REPO_V1",
        "cipher": "AES-256-CBC+HMAC-SHA256",
        "repo_id": repo_id,
        "dek": "legacy_dek_hex_1234567890abcdef",
        "status": "active",
    }
    padder = padding.PKCS7(128).padder()
    padded_plain = padder.update(json.dumps(legacy_payload).encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(legacy_iv))
    legacy_cipher = cipher.encryptor().update(padded_plain) + cipher.encryptor().finalize()
    legacy_mac = hmac.new(mac_key, legacy_salt + legacy_iv + legacy_cipher, hashlib.sha256).digest()
    legacy_manifest = legacy_salt + legacy_iv + legacy_mac + legacy_cipher

    legacy_parsed = verify_and_read_repo_manifest(legacy_manifest, master_kek)
    assert legacy_parsed["magic"] == "NETWORK_BACKUP_REPO_V1"
    assert legacy_parsed["dek"] == "legacy_dek_hex_1234567890abcdef"


def test_point3_payload_crypto_roundtrip():
    """Point 3: Test At-Rest Network Config Payload zlib compression + Simplified AES-256-GCM (AEAD)."""
    config_data = b"hostname Core-Switch-01\ninterface GigabitEthernet0/1\n switchport mode access\n vlan 10\n"
    key_material = "64charHexDEK0123456789abcdef0123456789abcdef0123456789abcdef01234567"

    # Encrypt payload with Simplified AES-256-GCM (v3)
    encrypted_blob = encrypt_payload_aes256(config_data, key_material=key_material)
    assert isinstance(encrypted_blob, bytes)
    assert encrypted_blob != config_data
    assert len(encrypted_blob) >= 48
    # Modern format magic header NBG2
    assert encrypted_blob[:4] == b"NBG2"

    # Decrypt payload
    decrypted_config = decrypt_payload_aes256(encrypted_blob, key_material=key_material)
    assert decrypted_config == config_data

    # Fail closed on wrong key
    with pytest.raises(IntegrityVerificationError):
        decrypt_payload_aes256(encrypted_blob, key_material="WrongKeyMaterialHexHere1234567890!")

    # Fail closed on tamper: tamper ciphertext / tag
    tampered_tag = bytearray(encrypted_blob)
    tampered_tag[-1] ^= 0x01
    with pytest.raises(IntegrityVerificationError):
        decrypt_payload_aes256(bytes(tampered_tag), key_material=key_material)

    # Fail closed on tamper: tamper nonce in AAD header (byte 10 within 4..16 nonce)
    tampered_nonce = bytearray(encrypted_blob)
    tampered_nonce[10] ^= 0x01
    with pytest.raises(IntegrityVerificationError):
        decrypt_payload_aes256(bytes(tampered_nonce), key_material=key_material)

    # Fail closed on corrupt envelope or missing NBG2 magic header
    with pytest.raises(DecryptionError):
        decrypt_payload_aes256(b"CORRUPT_ENVELOPE_DATA_WITHOUT_MAGIC_HEADER_12345", key_material=key_material)


def test_integrated_3points_flow():
    """Simulate full lifecycle: Vault KEK -> Manifest DEK -> Encrypted Config Payload."""
    # 1. Database Vault stores Master Password encrypted under APP_SECRET
    app_secret = "ClusterAppSecret2026!"
    master_password = "UserEnteredMasterPassword@2026"
    stored_in_db = encrypt_secret(master_password, key_material=app_secret)

    # 2. Worker decrypts master password from DB Vault
    recovered_master = decrypt_secret(stored_in_db, key_material=app_secret)
    assert recovered_master == master_password

    # 3. Worker creates/reads Manifest on S3 to retrieve DEK
    manifest_bytes = create_repo_manifest(recovered_master, repo_id="repo-01")
    manifest = verify_and_read_repo_manifest(manifest_bytes, recovered_master)
    dek = get_repo_dek(manifest, recovered_master)

    # 4. Worker encrypts network configuration with DEK and stores in S3
    raw_config = b"sysname Router-HQ\nospf 1\n area 0.0.0.0\n  network 10.0.0.0 0.0.0.255\n"
    s3_object = encrypt_payload_aes256(raw_config, key_material=dek)

    # 5. User downloads config: worker decrypts s3_object using DEK
    downloaded = decrypt_payload_aes256(s3_object, key_material=dek)
    assert downloaded == raw_config
