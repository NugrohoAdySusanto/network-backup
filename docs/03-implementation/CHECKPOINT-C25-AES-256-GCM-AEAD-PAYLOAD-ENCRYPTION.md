# CHECKPOINT C25 — v2.1 Upgrade: At-Rest Payload Encryption Upgrade to AES-256-GCM (AEAD)

**Execution Date:** 2026-11-09  
**Status:** COMPLETE (All Targeted Standalone & Storage Repository Crypto Unit Tests Passing 100%)  
**Project:** Centralized Network Configuration Backup — PT Lucky Mom Indonesia  
**Application Timezone:** `Asia/Jakarta` (WIB, UTC+7)

---

## 1. Executive Summary

In response to advanced cryptographic hardening and research optimization requirements for the undergraduate thesis (TA), the at-rest S3 configuration payload encryption scheme was upgraded from **AES-256-CBC with HMAC-SHA256 (Encrypt-then-MAC)** to modern **AES-256-GCM (Authenticated Encryption with Associated Data / AEAD)**:

### Delivered Capabilities:
1. **Modern True AEAD Architecture:**
   * Consolidated confidentiality and authenticity into a single mathematical pass using Galois/Counter Mode (GCM).
   * Eliminated PKCS#7 block padding and all susceptibility to Padding Oracle attacks (CVE POODLE / Bleichenbacher style padding vectors).
2. **Cryptographic Header Binding via AAD (Additional Authenticated Data):**
   * The binary envelope header (32 bytes: `b"NBG1"` magic bytes + 16-byte PBKDF2 Salt + 12-byte CSPRNG Nonce) is cryptographically bound into the GMAC authentication calculation as Additional Authenticated Data (AAD).
   * Prevents envelope tampering, IV/nonce substitution, and header splicing.
3. **Optimized Key Derivation (KDF):**
   * PBKDF2-HMAC-SHA256 with 100,000 iterations derives a 32-byte (256-bit) symmetric key via `derive_key_aes256_gcm`.
4. **Binary Envelope Layout (AES-256-GCM v2):**
   ```text
   +-------------------+--------------------+--------------------+--------------------------------+--------------------+
   | Magic `b"NBG1"`   | Salt (16 Bytes)    | Nonce (12 Bytes)   | Ciphertext (Variable, Stream)  | GMAC Tag (16 Bytes)|
   | (4 Bytes)         | CSPRNG             | NIST SP 800-38D    | zlib Compressed (NBZ1)         | AEAD Output        |
   +-------------------+--------------------+--------------------+--------------------------------+--------------------+
   |<----------------- 32-Byte Header (AAD Bound) -------------->|
   ```
5. **Fail-Closed Security Gate:**
   * Any bit-flip or manipulation of the ciphertext, tag, salt, or nonce results in `cryptography.exceptions.InvalidTag`, which is immediately caught and logged as `SEC_PAYLOAD_INTEGRITY_FAILED` and raises `IntegrityVerificationError`. No unverified plaintext is ever emitted.
6. **Transparent Backward Compatibility:**
   * Decryption logic in `payload_crypto.py` inspects the magic marker. If `b"NBG1"` is absent and length $\ge 80$ bytes, it safely falls back to verifying legacy HMAC-SHA256 and decrypting AES-256-CBC payloads.

---

## 2. Technical Implementation Details

### 2.1 Key Derivation (`backend/app/crypto/kdf.py`)
```python
def derive_key_aes256_gcm(password: str, salt: bytes) -> bytes:
    """
    Derives a single 32-byte (256-bit) encryption key for AES-256-GCM
    using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))
```

### 2.2 Payload Encryption & Decryption (`backend/app/crypto/payload_crypto.py`)
- **Encryption:**
  1. Compresses raw network configuration using `zlib.compress(level=6)` and prepends `b"NBZ1"`.
  2. Generates 16-byte random salt and 12-byte random nonce using `os.urandom`.
  3. Derives 32-byte AES-256 key from repository DEK.
  4. Prepares 32-byte AAD header: `MAGIC_GCM_HEADER (NBG1) + salt + nonce`.
  5. Executes `AESGCM(enc_key).encrypt(nonce, compressed_bytes, header)`.
  6. Returns concatenated binary envelope: `header + ciphertext_and_tag`.
- **Decryption:**
  1. Checks if data starts with `MAGIC_GCM_HEADER` (`b"NBG1"`).
  2. If GCM: parses salt (`4:20`), nonce (`20:32`), ciphertext+tag (`32:`), and AAD (`:32`).
  3. Decrypts via `AESGCM.decrypt(nonce, ciphertext_and_tag, aad)`.
  4. On `InvalidTag`, logs security alert and raises `IntegrityVerificationError`.
  5. Falls back to legacy `_decrypt_legacy_payload_cbc` if header does not match `NBG1`.
  6. Decompresses zlib stream if marked with `b"NBZ1"`.

---

## 3. Verification & Test Evidence

Targeted test execution confirmed 100% success rate:
- `tests/unit/test_crypto_standalone.py`:
  - `test_kdf_standalone` [PASSED]
  - `test_point1_vault_crypto_roundtrip` [PASSED]
  - `test_point2_manifest_envelope_crypto_roundtrip` [PASSED]
  - `test_point3_payload_crypto_roundtrip` [PASSED] (Verifies `NBG1` magic header, AES-256-GCM AEAD encryption/decryption, tamper detection on tag/ciphertext, tamper detection on nonce AAD header, and fallback to legacy AES-256-CBC)
  - `test_integrated_3points_flow` [PASSED]
- `tests/unit/test_storage_repository.py`:
  - `test_payload_encryption_and_decryption_aes256` [PASSED]
  - `test_password_rotation_re_wraps_dek_and_payload_remains_decryptable` [PASSED]
- `tests/unit/test_review_hardening_items.py`:
  - 6 password rotation & DEK preservation tests [PASSED]

