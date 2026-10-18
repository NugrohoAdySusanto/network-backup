# Frontend Architecture & Web Interfaces

**Application Title:** Centralized Network Configuration Backup Dashboard  
**Deployment:** Nginx Reverse Proxy (`network-backup-nginx-1`, Port 8081)  
**Styling & Framework:** Tailwind CSS CDN + Vanilla JavaScript ES6+ (Zero Node/NPM build dependency)

---

## 1. Primary Dashboard (`index.html`)

The production Single-Page Application interface connects directly to the FastAPI backend via `/api/v1/`:
* **State Machine & Session Management (`js/app.js`, `js/api.js`):**
  * Server-side Redis sessions authenticated via secure `HttpOnly` cookies.
  * Automatic CSRF token acquisition (`/api/v1/auth/csrf-token`) enforced on all state-changing `POST`, `PUT`, `DELETE` operations.
  * Real-time polling with dynamic job status transitions (`QUEUED` -> `CONNECTING` -> `EXTRACTING` -> `VALIDATING` -> `HASHING` -> `UPLOADING` -> `SUCCESS`).
* **Zabbix Device Management:**
  * Active network device table populated dynamically from Zabbix host groups.
  * Real-time status indicators (`Active`, `Non-Active`, `UNKNOWN`) and availability pre-check gates (`SKIPPED_DEVICE_DOWN`).
* **S3 Storage Management:**
  * Centered connection test pop-up modal (`#s3-test-modal`) with immediate feedback.
  * Encrypted Master Password initialization and unlock workflows for Ceph S3 repositories.
* **Backup Worker Management:**
  * Custom parametric CLI driver builder with live dry-run testing on target devices.
* **Enterprise Reporting:**
  * Date range selector for native Excel (`.xlsx`) and PDF (`.pdf`) audit export.

---

## 2. Interactive Cryptography Visualizer (`crypto-animation.html`)

A standalone educational visualizer and live cryptographic laboratory accessible at:
* **URL:** `http://localhost:8081/crypto-animation.html`
* **Access Points:** Direct header button **"Animasi Kriptografi"** (`#btn-crypto-animation`) and user account dropdown menu.

### Core Features:
1. **Interactive State Machine Stepper & Pipeline Flow:**
   * Step-by-step interactive animations for:
     * **At-Rest S3 Payload Pipeline:** Normalization -> zlib Deflate (Level 6, `NBZ1`) -> PBKDF2-HMAC-SHA256 (100k) -> AES-256-CBC (PKCS#7) -> HMAC-SHA256 (Encrypt-then-MAC).
     * **Database Credential Vault:** Derives 256-bit encryption & HMAC keys from `APP_SECRET_KEY` with legacy Fernet fallback.
     * **S3 Repository Manifest:** Encrypted envelope verification and active repository locking.
2. **SubtleCrypto Live Laboratory:**
   * In-browser cryptographic execution using the Web Cryptography API (`crypto.subtle`).
   * Real-time key derivation, IV generation, PKCS#7 padding, AES-256-CBC encryption, HMAC-SHA256 authentication, and byte-level envelope inspection.
   * Round-trip decrypt and integrity verification testing.
