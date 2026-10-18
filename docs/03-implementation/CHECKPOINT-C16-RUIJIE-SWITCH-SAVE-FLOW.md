# Checkpoint C16 — Ruijie Switch Driver, Save Persistence Flow, & Driver Specifications

**Date:** 2026-10-06  
**Status:** Completed & Verified  
**Feature Scope:** Ruijie Switch Driver (`ruijie-switch`), Table Row Save Workflow, CSV Format Removal, Sangfor NSF `.bcf` Architecture, and MikroTik `.rsc` vs `.backup` Rationale.

---

## 1. Summary of Implementation

### 1. Removal of CSV Export Format
- Retired the raw CSV export format across frontend UI and backend API.
- Export modal (`#export-dialog`) now offers:
  1. **Excel (.xlsx)**: Primary default format for structured data manipulation.
  2. **PDF Document**: Formal executive reporting and compliance audits.
- Backend endpoint `GET /api/v1/reports/export` validated with regex `^(xlsx|pdf)$`.

### 2. Save Button Persistence Workflow
- **Problem Addressed:** Previously, selecting a Backup Worker or setting a schedule could cause confusion regarding when changes were saved to PostgreSQL.
- **Solution Implemented:**
  - Selecting a Backup Worker in the table row stages changes in memory (`d._pending.driver_key`).
  - Configuring or disabling a schedule in the Schedule Modal stages changes in memory (`d._pending.schedule_enabled`, `daily_time`, `retention_policy`) without immediate database mutation.
  - The row's **Save** button (`.save-btn`) activates with a pulsing emerald ring and label `Save*`.
  - Settings are **only** persisted to PostgreSQL when the user clicks the row's **Save** button.
  - If the user reloads the browser before pressing Save, all pending changes are discarded and clean DB values are restored.
  - Background auto-refresh polling (every 20s) automatically pauses while any row has pending unsaved edits to protect the user's working copy.

### 3. Ruijie Switch Driver (`ruijie-switch`)
- **Key:** `ruijie-switch`
- **Output File:** `config.txt` (extension `txt`).
- **Privilege Mode Support:**
  - Automatically enters enable mode using the privilege secret password configured via `NETWORK_SSH_ENABLE_PASSWORD` or per-device settings.
- **Legacy Cryptographic Algorithm Support:**
  - Dynamically registers legacy Key Exchange algorithms (`diffie-hellman-group14-sha1`, `diffie-hellman-group-exchange-sha1`) and `ssh-rsa` host key verification in Paramiko transport for compatibility with enterprise switch firmware.
- **Normalization & Validation:**
  - Strips dynamic headers (`Building configuration...`, `Current configuration : <N> bytes`, `! Time: ...`).
  - Validates minimum length and checks for CLI error tokens.
- **Verification Evidence:**
  - Tested against physical/live device `MKK-HQ_DMZ` (`10.11.10.2:22345`):
    - Initial backup: `SUCCESS_CHANGED` (baseline snapshot created in S3, size 2736 bytes).
    - Consecutive backup: `SUCCESS_NO_CHANGE` (CAS deduplication confirmed in 3930 ms).

### 4. Firewall Driver Architecture (Sangfor NSF & `.bcf` Format)
- Sangfor NGAF / NSF firewall backups produce `.bcf` (*Binary Configuration File*).
- `.bcf` files are proprietary binary and encrypted by Sangfor to protect sensitive network secrets (VPN pre-shared keys, SSL certificates, local user databases, and security rules).
- The system stores `.bcf` directly into Content Addressable Storage (CAS) with raw binary SHA-256 calculation for deduplication and snapshot retention.
- Driver metadata set to `output_extension="bcf"` and `filename="config.bcf"`.

### 5. MikroTik Configuration Architecture: `.rsc` vs `.backup`
- **Why `.rsc` is used by the Dashboard:**
  1. **Content Addressable Storage (CAS) Deduplication:** `.rsc` is readable script export. By hashing normalized `.rsc`, the system can detect whether anything changed (`SUCCESS_NO_CHANGE` vs `SUCCESS_CHANGED`) and avoid redundant S3 uploads.
  2. **Audit Trail & Line-by-Line Diffs:** NOC engineers can inspect exact line additions/deletions. `.backup` is an opaque binary blob that cannot be diffed.
  3. **Hardware & Firmware Portability:** `.rsc` can be edited and imported onto different MikroTik models or CHRs. In contrast, `.backup` contains hardware-specific MAC addresses and low-level state that can cause boot failure if restored to different hardware.

---

## 2. Files Modified & Created

- [`backend/app/drivers/ruijie_switch.py`](file:///opt/network-backup/backend/app/drivers/ruijie_switch.py): Full Ruijie Switch driver implementation.
- [`backend/app/drivers/sangfor_nsf.py`](file:///opt/network-backup/backend/app/drivers/sangfor_nsf.py): Updated output extension to `bcf` and filename `config.bcf`.
- [`backend/app/drivers/base.py`](file:///opt/network-backup/backend/app/drivers/base.py): Added `enable_password` to `DeviceConnectionContext`.
- [`backend/app/config.py`](file:///opt/network-backup/backend/app/config.py): Added `network_ssh_enable_password`.
- [`.env`](file:///opt/network-backup/.env) & [`.env.example`](file:///opt/network-backup/.env.example): Added `NETWORK_SSH_ENABLE_PASSWORD`.
- [`backend/app/services/backup_execution_service.py`](file:///opt/network-backup/backend/app/services/backup_execution_service.py): Passed enable password to connection context.
- [`backend/app/api/reports.py`](file:///opt/network-backup/backend/app/api/reports.py): Removed CSV format from endpoint.
- [`frontend/index.html`](file:///opt/network-backup/frontend/index.html): Removed CSV export tab.
- [`frontend/js/reports.js`](file:///opt/network-backup/frontend/js/reports.js): Removed CSV logic.
- [`frontend/js/devices.js`](file:///opt/network-backup/frontend/js/devices.js): Staged pending changes, pulse styling on Save button, and auto-refresh pause on dirty rows.
- [`frontend/js/schedules.js`](file:///opt/network-backup/frontend/js/schedules.js): Modal stages schedule changes in memory and prompts to click row Save button.
- [`docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md`](file:///opt/network-backup/docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md): Added Section 33 with driver specifications.
- [`docs/02-architecture/API-CONTRACT-v1.0.md`](file:///opt/network-backup/docs/02-architecture/API-CONTRACT-v1.0.md): Removed CSV export parameters.

---

## 3. Verification Evidence

1. **Unit Test Suite:**
   ```bash
   docker exec network-backup-api-1 python -m pytest tests/unit
   # 23 passed in 1.19s (100% PASS)
   ```
2. **Ruijie Switch Backup Verification (`MKK-HQ_DMZ`):**
   - Execution 1: `SUCCESS_CHANGED (baseline)` -> snapshot `config.txt` created in S3 (2736 bytes).
   - Execution 2: `SUCCESS_NO_CHANGE (no_change)` -> content SHA-256 matched, no redundant snapshot created.
3. **Save Persistence Verification:**
   - Worker selection and schedule changes remain staged in memory (`d._pending`).
   - Save button activates with visual pulse (`Save*`).
   - Refreshing before clicking Save reverts table without database change.
   - Clicking Save updates database via `PUT /devices/{id}/backup-settings` and syncs cleanly.
