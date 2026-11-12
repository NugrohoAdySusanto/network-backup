# CHECKPOINT C19 — S3 Storage Management & Backup Worker Management (Admin-Only)

> [!NOTE]
> **Historical Milestone Record (Superseded Crypto Spec):** Dokumen ini mencatat milestone implementasi C19 (v1) secara historis. Implementasi kriptografi saat ini untuk Database Vault (`NBV1`), Repository Manifest (`NBM1`), dan S3 Payload (`NBG2`) telah dimodernisasi menjadi **AES-256-GCM (AEAD)** — lihat [CHECKPOINT C25](CHECKPOINT-C25-AES-256-GCM-AEAD-PAYLOAD-ENCRYPTION.md) dan [Spesifikasi Enkripsi Backup S3](../03-design/enkripsi-backup-s3.md).

**Execution Date:** 2026-10-07  
**Status:** COMPLETE (Production Verified, 36/36 Unit Tests Passing)

---

## 1. Objective & Scope

Deliver dynamic management of **S3 Storage Repositories** and **Backup Worker Drivers** directly from the Web GUI, integrated into the user account dropdown below *Manage account preferences*, restricted strictly to accounts with the `admin` role.

### Key Capabilities Delivered:
1. **S3 Storage Management:**
   * Configure S3 endpoint, bucket, access key, secret key, and SSL verification from GUI.
   * Connection reachability test with automatic bucket state inspection.
   * **Master Password Initialization (Empty/New Bucket):** Encrypts and writes `repo_manifest.enc` using **PBKDF2-HMAC-SHA256 (100,000 iterations) + AES-256-CBC + HMAC-SHA256**.
   * **Master Password Unlock (Existing Bucket):** Authenticates and mounts existing repository manifests via constant-time HMAC-SHA256 verification.
   * **Repository Data Scoping:** Switching active repositories isolates snapshots, retention records, and download archives in the dashboard without deleting historical database records.
2. **Backup Worker Management:**
   * Manage both system built-in drivers (`mikrotik-routeros`, `ruijie-ap`, `ruijie-switch`, `sangfor-nsf`) and user-defined custom CLI drivers.
   * Parametric SSH CLI engine supporting privilege escalation (`enable` / `super`), custom prompt matching, pagination bypass (`screen-length 0`, `terminal length 0`), interactive spacebar paging, regex line stripping, and output validation rules.
   * Dry-run live device extraction testing directly from GUI without creating snapshots.
3. **Strict RBAC Enforcement:**
   * Endpoints guarded with `require_admin_csrf` (401 for unauthenticated, 403 for non-admin).
   * Account dropdown entries and modal triggers dynamically hidden for viewer accounts.

---

## 2. Database Schema & Migration (`010_storage_and_custom_drivers.py`)

### 2.1 Table: `storage_repositories`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique repository identifier |
| `name` | VARCHAR(128) | NOT NULL | Friendly label (e.g., Primary S3, DR Secondary) |
| `endpoint` | VARCHAR(255) | NOT NULL | Ceph RGW / S3 endpoint URL |
| `bucket` | VARCHAR(128) | NOT NULL | Target S3 bucket name |
| `access_key` | VARCHAR(128) | NOT NULL | S3 Access Key ID |
| `secret_key_encrypted` | VARCHAR(512) | NOT NULL | AES-256-CBC + HMAC-SHA256 encrypted Secret Access Key |
| `master_key_encrypted` | VARCHAR(512) | NULL | AES-256-CBC + HMAC-SHA256 encrypted Master Password |
| `secure` | BOOLEAN | NOT NULL (True) | Enforce TLS certificate verification |
| `is_active` | BOOLEAN | NOT NULL (False) | Currently active mount for snapshots |
| `is_initialized` | BOOLEAN | NOT NULL (True) | Indicates manifest presence in bucket |
| `repo_manifest` | JSONB | NULL | Cached decrypted repository manifest |
| `created_at` | TIMESTAMPTZ | NOT NULL | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last modification timestamp |

### 2.2 Table: `custom_drivers`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique driver identifier |
| `key` | VARCHAR(64) | UNIQUE, NOT NULL | Slug identifier (e.g., `huawei_vrp`) |
| `label` | VARCHAR(128) | NOT NULL | Display name (e.g., `Huawei VRP Switch`) |
| `vendor_hint` | VARCHAR(128) | NOT NULL | Vendor classification hint |
| `model_hint` | VARCHAR(128) | NOT NULL | Hardware model hint |
| `transport` | VARCHAR(32) | NOT NULL ('ssh') | Transport protocol |
| `default_port` | INTEGER | NOT NULL (22) | Default SSH port |
| `connect_timeout` | INTEGER | NOT NULL (15) | Socket timeout in seconds |
| `command_timeout` | INTEGER | NOT NULL (60) | CLI execution timeout in seconds |
| `need_enable` | BOOLEAN | NOT NULL (False) | Requires elevated privilege mode |
| `enable_command` | VARCHAR(64) | NULL | Enable command (default: `enable`) |
| `enable_prompt_pattern`| VARCHAR(64) | NULL | Regex pattern for elevated prompt |
| `disable_paging_command`| VARCHAR(128)| NULL | Paging disable command |
| `paging_mode` | VARCHAR(32) | NOT NULL ('none') | `none`, `disable_command`, `interactive` |
| `backup_command` | VARCHAR(255) | NOT NULL | Extraction command |
| `output_extension` | VARCHAR(16) | NOT NULL ('txt') | File extension for downloaded config |
| `strip_patterns` | JSONB | NOT NULL ([]) | Array of regex lines to remove |
| `validation_min_length` | INTEGER | NOT NULL (30) | Minimum valid byte length |
| `validation_required_keyword`| VARCHAR(128)| NULL | Mandatory keyword in output |
| `is_active` | BOOLEAN | NOT NULL (True) | Driver availability flag |

### 2.3 Foreign Keys & Data Migration:
* Added `repository_id` (UUID, nullable, FK to `storage_repositories.id`) to `config_objects` and `snapshots`.
* Backfilled default repository `00000000-0000-0000-0000-000000000001` from existing `.env` configuration.
* All existing 22 production snapshots and config objects linked to active repository.

---

## 3. Backend Implementation

### 3.1 Security & Manifest Encryption (`backend/app/core/security.py`)
* `encrypt_secret(plain_text, key_material=None)`: AES-256-CBC encryption with HMAC-SHA256 authenticated envelope (Encrypt-then-MAC) using key derived from `APP_SECRET` (upgraded from 128-bit Fernet).
* `decrypt_secret(cipher_text, key_material=None)`: AES-256-CBC decryption with HMAC integrity verification, plus legacy Fernet fallback for backward compatibility.
* `create_repo_manifest(master_password, repo_id=None)`:
  * Generates 16-byte cryptographically secure random salt.
  * Derives 32-byte key using PBKDF2-HMAC-SHA256 with 100,000 iterations.
  * Encrypts repository payload (`magic: "NETWORK_BACKUP_REPO_V1"`, `repo_id`, timestamp, salt).
  * Returns `salt (16 bytes) + ciphertext`.
* `verify_and_read_repo_manifest(data, master_password)`: Verifies key against payload; returns parsed dict on success or `None` on failure.

### 3.2 S3 Service & Storage Repository Service
* **`S3Service` (`backend/app/services/s3_service.py`):**
  * Dynamically resolves credentials from `StorageRepository` in PostgreSQL.
  * Supports explicit `repo_id` parameter to route downloads or operations to specific repositories.
  * Added `check_repo_manifest()`, `put_repo_manifest()`, and `get_repo_manifest()`.
* **`StorageRepositoryService` (`backend/app/services/storage_repository_service.py`):**
  * `test_connection()`: Validates S3 connectivity and checks if `repo_manifest.enc` exists in target bucket.
  * `initialize_repository()`: Generates encrypted manifest, stores to bucket, creates active repository record in DB.
  * `unlock_and_activate()`: Validates password against `repo_manifest.enc`, mounts and activates repository.
  * `activate_repository()`: Switches active repository without deleting old records.
  * `list_repositories()`: Lists all configured repositories with masked keys and snapshot counts.

### 3.3 Parametric Driver & Registry (`backend/app/drivers/parametric.py`, `registry.py`)
* Implements `BackupDriver` interface:
  * Connects over Netmiko with generic SSH parameters.
  * Handles privilege mode elevation if `need_enable` is true.
  * Disables pagination via command or interactive spacebar keystrokes.
  * Strips lines matching regex patterns (e.g. timestamps, passwords, prompts).
  * Validates output length and required keywords.
* `DriverRegistry` dynamically queries `CustomDriver` table and registers parametric drivers alongside built-in drivers.

### 3.4 API Endpoints (`/api/v1/storage` & `/api/v1/drivers`)
* `POST /api/v1/storage/test` (Admin) — Uji jangkauan endpoint & deteksi keberadaan manifest di bucket
* `GET  /api/v1/storage/repositories` (Admin) — Daftar semua repository tersimpan
* `GET  /api/v1/storage/active` (Admin) — Info repository aktif saat ini
* `POST /api/v1/storage/repositories/init` (Admin) — Inisialisasi manifest baru dengan master password
* `POST /api/v1/storage/repositories/unlock` (Admin) — Buka kunci manifest tersimpan dengan master password
* `POST /api/v1/storage/repositories/{id}/activate` (Admin) — Beralih repository aktif
* `POST /api/v1/storage/disconnect` (Admin) — Putuskan koneksi repository aktif (unmount)
* `GET  /api/v1/drivers` (Authenticated) — Daftar driver bawaan dan custom
* `POST /api/v1/drivers/custom` (Admin) — Daftarkan driver custom CLI baru
* `PUT  /api/v1/drivers/custom/{key}` (Admin) — Perbarui konfigurasi driver custom
* `DELETE /api/v1/drivers/custom/{key}` (Admin) — Hapus driver custom
* `POST /api/v1/drivers/test` (Admin) — Dry-run ekstraksi konfigurasi langsung ke perangkat target

---

## 4. Frontend Implementation

### 4.1 Account Dropdown Integration (`frontend/index.html`)
Inside `#admin-menu` below `Manage account preferences`:
```html
<button id="s3-management-btn" type="button" class="admin-only-feature ...">
  S3 Storage Management
</button>
<button id="workers-management-btn" type="button" class="admin-only-feature ...">
  Backup Worker Management
</button>
```

### 4.2 Role-Based Visibility (`frontend/js/auth.js`)
* Added `applyRolePermissions()` invoked during authentication check and login.
* Toggles `.admin-only-feature` elements (`display: none` for viewer, `display: ""` for admin).

### 4.3 S3 Storage Management Modal (`frontend/js/storage.js`)
* **Status Card & Active Repository Binding:** Dynamically displays active repository details (Name, Target Bucket, Endpoint URL, TLS status, and mounted snapshots). Fixed response unwrapping to seamlessly support active storage entity data directly from `/api/v1/storage/active`.
* **Configured Repositories Table:** Lists all registered storage pools with masked access keys, live snapshot counters, and 1-click active mount switching.
* **Three-Button Connection Workflow:**
  1. **Reset:** Clears input fields, resets SSL verification to enabled, disables `Next` button, unlocks Step 1 fields, and hides Step 2.
  2. **Test Connection:** Validates endpoint reachability, bucket access, and detects presence of `repo_manifest.enc`.
     * **Enforced SSL for HTTPS:** If the endpoint URL uses HTTPS (`https://`), SSL Certificate Validation is mandatory on both frontend and backend.
     * **Result Pop-Up Modal:** Instead of placing alerts at the top of the dialog, connection test outcomes are presented in a dedicated centered pop-up modal (`#s3-test-modal`) detailing endpoint, bucket, TLS state, and manifest detection status.
     * **Continue to Next Step Action:** The success pop-up provides a direct button to proceed immediately, automatically advancing to Step 2 while locking Step 1 connection parameters.
  3. **Next:** Once clicked or triggered from the pop-up, locks all Step 1 inputs (Repository Name, Target Bucket, Endpoint, Access Key, Secret Key, SSL verification checkbox, and connection action buttons) in read-only disabled state to prevent accidental modifications or tampering. Reveals Step 2 (Master Password entry) with focus on the relevant password input.
* **Master Password Initialization / Unlock:**
  * If bucket is clean/uninitialized: prompts for New Master Password and confirmation to encrypt and write `repo_manifest.enc`.
  * If manifest is detected: prompts for existing Master Password to unlock and mount repository.

### 4.4 Backup Worker Management Modal (`frontend/js/workers.js`)
* **Driver Registry View:** Displays all registered drivers categorized as `SYSTEM BUILT-IN` (immutable) or `CUSTOM CLI` (editable and removable).
* **Rapid Templates (1-Click Presets):**
  * `Huawei Switch / Router (VRP)`: `display current-configuration`, `screen-length 0 temporary`, keyword validation `sysname`.
  * `Cisco IOS Switch / Router`: `show running-config`, `terminal length 0`, privilege elevation `enable`, keyword validation `version`.
  * `Cisco Nexus (NX-OS)`: `show running-config`, `terminal length 0`, keyword validation `version`.
  * `HP / Aruba ProCurve`: `show running-config`, `no page`, keyword validation `hostname`.
  * `Fortinet FortiGate Firewall (CLI)`: `show full-configuration`, `set output standard`, keyword validation `config system`.
  * `Sangfor NGAF Firewall (CLI)`: `show running-configuration`, extension `.txt`.
* **Parametric Configuration Fields:**
  * **Driver Key & Label:** Unique identifier (e.g., `huawei_vrp`) and interface display label.
  * **Vendor / Model Hint:** Informational metadata tags.
  * **Port & Timeouts:** Default SSH port (22), socket connection timeout, and execution timeout.
  * **Privilege Elevation:** Enable command and prompt regex pattern when elevated privileges are required.
  * **Pagination Handling:** CLI command to disable pagination (`terminal length 0`, etc.) or simulated interactive spacebar pagination.
  * **Line Strip Patterns:** Configurable regex patterns to strip volatile lines (timestamps, pagination prompts, session headers).
  * **Integrity Validation:** Minimum output byte length and mandatory required keywords to prevent saving partial or truncated outputs.
* **Dry-Run Testing:** Real-time test extraction to a target device directly from the modal before committing changes.

### 4.5 Interface Standardization & Language Localization
* Converted the entire frontend interface to standard enterprise English across modals, status badges, forms, table headers, and notification banners.
* Removed artificial emojis and decorative characters.
* Standardized role indicators to clean text badges (`Administrator`, `Viewer`).

---

## 5. Security & Cryptographic Architecture

### 5.1 Master Password & Manifest Envelope (AES-256-CBC + HMAC-SHA256)
* **Key Derivation Function (KDF):** PBKDF2-HMAC-SHA256
  * **Salt:** 16 bytes generated via `os.urandom(16)`.
  * **Iteration Count:** 100,000 iterations.
  * **Derived Key Material:** 64 bytes (512 bits) derived via `hashlib.pbkdf2_hmac("sha256", password, salt, 100_000, dklen=64)`:
    * `enc_key = kdf[:32]`: 32 bytes (256 bits) for AES-256-CBC encryption.
    * `mac_key = kdf[32:]`: 32 bytes (256 bits) for HMAC-SHA256 authentication.
* **Authenticated Encryption Envelope (Encrypt-then-MAC):**
  * **Cipher:** AES-256 in CBC mode with PKCS#7 block padding (128-bit block boundary).
  * **Initialization Vector (IV):** 16 bytes cryptographically secure random bytes via `os.urandom(16)`.
  * **Integrity Authentication:** HMAC-SHA256 computed over `salt (16B) || iv (16B) || ciphertext`.
  * **Binary Envelope Layout:**
    ```
    [salt: 16B] || [iv: 16B] || [hmac: 32B] || [ciphertext: PKCS7 padded]
    ```
    Total header overhead: 64 bytes.
  * **Manifest Payload Schema:**
    ```json
    {
      "magic": "NETWORK_BACKUP_REPO_V1",
      "cipher": "AES-256-CBC+HMAC-SHA256",
      "repo_id": "<uuid>",
      "initialized_at": "<iso8601>",
      "salt_hex": "<hex-encoded-16-bytes>",
      "status": "active"
    }
    ```
  * **Decryption & Verification:** Validates MAC via constant-time comparison (`hmac.compare_digest`) before decryption. Includes automatic fallback for legacy Fernet tokens to guarantee zero-downtime backward compatibility.

### 5.2 SSL / TLS Verification Enforcement
* **Strict Transport Validation:** When SSL Certificate Validation is checked (`secure=True`), Boto3 strictly enforces TLS certificate authority verification against the system CA trust store.
* **HTTPS Mandate:** Any attempt to configure an `https://` endpoint with SSL Certificate Validation unchecked is blocked on both client and backend routers.
* **CA Trust Store Synchronization:** The internal Ceph RGW certificate is integrated into the system trust store (`/etc/ssl/certs/ca-certificates.crt`), allowing strict TLS verification to succeed cleanly.

### 5.3 Safe Method Authorization & CSRF Separation
* **Idempotent Read Endpoints (`GET /storage/active`, `GET /storage/repositories`):**
  * Protected via `require_admin` (Admin role authentication check).
  * Excluded from CSRF token enforcement (`require_admin_csrf`) to adhere to RFC 7231 HTTP standards where read-only `GET` requests do not require anti-forgery tokens.
* **State-Mutating Operations (`POST /storage/test`, `POST /storage/repositories/init`, `POST /storage/disconnect`):**
  * Strictly protected via `require_admin_csrf` (requiring valid `X-CSRF-Token` header).
* **Client-Side Header Propagation:** Frontend API client (`fetchAPI`) ensures `X-CSRF-Token` headers are attached seamlessly across all requests when present in storage.

### 5.4 Active Repository Scoping (Hybrid Architecture)
* **Metadata Scoping:** `backup_jobs` table enhanced with `repository_id` foreign key referencing `storage_repositories.id`.
* **Dynamic Scoped Queries:**
  * Endpoint `GET /devices` filters `last_backup` strictly against the currently active repository ID.
  * Endpoint `GET /devices/{id}/backup-jobs` queries only job executions and snapshots belonging to the active repository.
* **Storage-Catalog Alignment:** When a repository is empty or a fresh bucket is attached, device status automatically displays `No Backup` / `Not yet` with empty history logs (0 items), preventing cross-repository leakage.
* **Database State Hygiene:** Removed legacy orphaned test records whose physical artefacts no longer reside in S3.

### 5.5 Strict Case-Sensitive Identity Authentication
* **Exact Username Matching:** `normalize_username` in `backend/app/core/security.py` updated to perform strict whitespace stripping without case folding (`.strip()`).
* **Zero Tolerance for Case Variations:** Accounts such as `admin` require the exact lowercase identifier; inputs with casing differences (e.g. `Admin`) are strictly rejected with `INVALID_CREDENTIALS` (HTTP 401).

---

## 6. Verification & Automated Testing

* **Unit Test Suite:** All 37 unit tests pass successfully (`pytest tests/unit`):
  * `test_storage_repository.py`: PBKDF2-HMAC-SHA256 64-byte key derivation, AES-256-CBC encryption and HMAC-SHA256 verification, HTTPS SSL enforcement, secret key masking, and database entity lifecycle.
  * `test_custom_drivers.py`: Parametric driver regex stripping, keyword validation failure handling, minimum length enforcement, and registry integration.
  * `test_schema_contract.py`: Table schema verification and model serialization contracts.
  * `test_security.py` & `test_auth_schemas.py`: Strict case-preserving username normalization and Argon2id verification.
* **Container Health:** All runtime containers (`api`, `worker`, `beat`, `nginx`, `postgres`, `redis`) verified active and healthy.
