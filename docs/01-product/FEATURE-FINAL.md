# Network Backup Dashboard — Final Feature & Functional Specification

**Version:** 1.0  
**Status:** Functional Scope Frozen for v1  
**Project:** Centralized Network Configuration Backup  
**Primary Domain:** Network Management & Maintenance  
**Single Source of Truth:** Zabbix  
**Backup Repository:** Ceph S3 / RGW Storage Pools  
**Primary Backup Transport:** SSH where supported; driver-specific transport allowed  
**Repository Encryption:** AES-256-CBC + HMAC-SHA256 (PBKDF2-HMAC-SHA256 100,000 iterations)  
**Reporting Engine:** Excel (.xlsx) & PDF (.pdf) with Executive Metrics & Charts  
**Alerting:** Feishu / Lark Webhook integration  

---

# 1. System Objective

The system centralizes network-device configuration backup for a multivendor environment. Zabbix remains the authoritative source for network-device identity and operational status, while this application manages:

- backup-driver assignment and custom parametric driver management;
- dynamic S3 storage management with Master Password encryption;
- daily scheduling;
- manual backup;
- queue and worker execution;
- multi-stage backup validation;
- SHA-256 change detection and deduplication;
- configuration version history scoped to active repository;
- Ceph S3 storage integration with SSL certificate verification;
- standard (31-day) and smart GFS (7/4/12/3) retention;
- backup metadata;
- failed and success backup alerting through Feishu webhook;
- Excel and PDF audit export reporting;
- Admin / Viewer access control with strict case-sensitive authentication.

The v1 system **does not perform automated restoration** to network devices.

---

# 2. Scope Boundary

## 2.1 Included in v1

1. Login and backend authentication.
2. Default bootstrap/demo accounts retained.
3. Quick Autofill retained.
4. Admin and Viewer roles.
5. User management by Admin.
6. Zabbix host synchronization from Network Device Group only.
7. Device status read from Zabbix.
8. Vendor/model/IP mapping from Zabbix data.
9. Backup Driver Registry / Adapter pattern.
10. Manual Backup.
11. Daily Scheduled Backup.
12. Backend persistent scheduler.
13. Backup Job Queue.
14. Worker concurrency control.
15. Retry and timeout policy.
16. Multi-stage backup validation.
17. Configuration normalization.
18. SHA-256 fingerprint generation.
19. Changed / No Change detection.
20. Ceph S3 repository integration.
21. Ceph HEALTH_OK / HEALTH_WARN / HEALTH_ERR status.
22. Logical backup snapshots.
23. 31-day standard retention.
24. Smart retention 7 Daily / 4 Weekly / 12 Monthly / 3 Yearly.
25. Persistent backup history metadata.
26. Admin-only backup download.
27. Failed-backup Feishu webhook.
28. Save / Clear row actions.
29. Dark mode.
30. Account preferences and password change.

## 2.2 Initial v1 Exclusions & Delivered v2 Scope

The following features were excluded from the initial v1 baseline:
- Automated restore to network devices.
- Configuration line-by-line diff.
- Cross-version diff.
- Backup Compliance.
- Credential Management UI.
- End-user activity audit trail.
- Multiple S3 repositories.

> **Delivered in v2 Scope (Completed):**
> - **At-Rest Payload Encryption & Authentication:** AES-256-CBC + HMAC-SHA256 Encrypt-then-MAC with PBKDF2-HMAC-SHA256 key derivation (100,000 iterations).
> - **Transparent Compression:** zlib Deflate (Level 6, magic marker `NBZ1`) prior to encryption, saving 60-80% storage bandwidth.
> - **Database Credential Vault Upgrade:** 256-bit AES-256-CBC + HMAC-SHA256 for all stored secrets (`secret_key_encrypted` and `master_key_encrypted`).
> - **Interactive Cryptography Visualizer:** Web-based simulator and live SubtleCrypto laboratory (`/crypto-animation.html`).
> - **Enterprise Reporting:** Native Excel (`.xlsx`) with executive metrics & charts, and PDF (`.pdf`) audit report.

---

# 3. Authentication & RBAC

## 3.1 Login

The website opens with a login modal before dashboard access.

Current mockup behavior is retained conceptually:

- Username field.
- Password field.
- Show / Hide Password.
- Remember Session.
- Quick Autofill.
- Login loading feedback.

Authentication changes from browser-only simulation to **real backend authentication**.

## 3.2 Default Accounts

The current default-account concept is retained for bootstrap/demo use.

> The exact production seeding mechanism and password-storage implementation will be defined during backend architecture design.

## 3.3 Roles

### Admin

Allowed to:

- view all devices and backup status;
- select Backup Driver;
- save driver/schedule settings;
- clear assignment/schedule;
- run Backup Now;
- create/change daily schedule;
- select retention policy;
- view backup history;
- download configuration backups;
- manage users;
- change own password.

### Viewer

Allowed to:

- view all devices;
- view Zabbix status;
- view driver assignment;
- view schedule;
- view retention mode;
- view backup history;
- view Changed / No Change;
- view Ceph health;
- change own password.

Not allowed to:

- run backup;
- change driver;
- change schedule;
- change retention;
- use Save/Clear operational actions;
- download configuration;
- manage users.

---

# 4. Header / Global Overview

The dashboard does not use a separate summary page. Global backup information is displayed in the header.

Header elements:

1. **Total Devices**
2. **Backup Success Today**
3. **Ceph Cluster Health**
4. **Account Menu**
5. **Dark Mode Toggle**

## 4.1 Total Devices

Number of network devices synchronized from the configured Zabbix Network Device Group.

## 4.2 Backup Success Today

Recommended formula:

```text
Unique scheduled devices with successful backup run today
---------------------------------------------------------- × 100%
Unique devices scheduled for backup today
```

Both:

```text
SUCCESS_CHANGED
SUCCESS_NO_CHANGE
```

count as successful.

Retry attempts do not inflate the successful-device count.

## 4.3 Ceph Health

Header values:

```text
HEALTH_OK
HEALTH_WARN
HEALTH_ERR
```

This represents **actual Ceph cluster health**, not merely an S3 connectivity probe.

The Ceph-specific mechanism used to obtain this status will be defined during backend architecture design.

---

# 5. Zabbix Integration

## 5.1 Source Scope

Only devices under the configured:

```text
Network Device Group
```

are synchronized.

## 5.2 Data Pulled from Zabbix

Minimum fields:

- Zabbix Host ID
- Hostname
- Device Status
- IP Address
- Vendor / Merk
- Model
- Host Group

## 5.3 Source-of-Truth Rule

```text
Zabbix = Master device identity/status source
Application DB = local synchronized/cache representation
```

The backup application does not become a replacement asset inventory.

If a device is removed or disabled in Zabbix:

- its historical backup records remain;
- the local record may become inactive;
- history is not automatically deleted.

---

# 6. Device Table

Minimum v1 columns:

```text
HOSTNAME
STATUS
IP ADDRESS
MODEL
BACKUP DRIVER
BACKUP
LAST BACKUP
CHANGE STATUS
DOWNLOAD
ACTIONS
```

Retention is displayed as a badge next to the hostname/remarks area:

```text
31 Days
Smart Ret.
```

## 6.1 Status

Read-only and sourced from Zabbix.

Visual states:

```text
Active
Non-Active
```

An inactive device cannot execute a backup job.

---

# 7. Backup Driver Registry / Adapter

The application does **not** use a long `if / elif vendor` chain.

Architecture:

```text
Backup Engine
     |
Driver Registry
     |
     +-- SangforNSFDriver
     +-- MikrotikRouterOSDriver
     +-- RuijieSwitchDriver
     +-- RuijieAPDriver
```

The main engine works with a common driver contract.

Conceptual methods:

```text
connect()
collect_config()
normalize_config()
validate_config()
cleanup()
```

The transport is implementation-specific.

Most devices are expected to use SSH, but a driver may use an API or another supported export method when necessary.

## 7.1 Driver Selection

The **Backup Worker** dropdown in the mockup becomes the **Backup Driver** dropdown.

Example options:

```text
Sangfor NSF Driver
Mikrotik RouterOS Driver
Ruijie Switch Driver
Ruijie AP Driver
```

The selected driver is stored as `driver_key`.

---

# 8. Row Actions: Save & Clear

## 8.1 Save

Save persists:

- selected Backup Driver;
- daily schedule;
- retention policy.

## 8.2 Clear

Clear removes:

- driver assignment;
- schedule assignment.

It does **not** delete:

- device identity;
- Zabbix data;
- backup history;
- existing S3 backup objects.

---

# 9. Manual Backup

Admin may run:

```text
Backup -> Backup Now
```

The browser must not execute device backup directly.

Flow:

```text
Frontend Request
      |
Create Backup Job
      |
Job Queue
      |
Backup Worker
```

The frontend receives a job reference/status and displays progress.

---

# 10. Scheduled Backup

## 10.1 Recurrence

v1 supports:

```text
Daily only
```

The Admin chooses the daily execution time.

## 10.2 Persistence

Schedules are stored in the database and executed by the backend.

They do **not** depend on the browser remaining open.

## 10.3 Retention Selection

Each configured schedule uses one of:

```text
31 Days Standard Retention
Smart Retention 7/4/12/3
```

---

# 11. Backup Job Queue

A queue separates user requests/schedules from device execution.

Purpose:

- prevent too many simultaneous SSH sessions;
- control backend resource consumption;
- support retry;
- provide deterministic job state.

Concurrency limit will be finalized during backend architecture design.

---

# 12. Job States

Baseline v1 states:

```text
QUEUED
CONNECTING
COLLECTING
NORMALIZING
VALIDATING
HASHING
UPLOADING
VERIFYING
SUCCESS_CHANGED
SUCCESS_NO_CHANGE
RETRYING
FAILED
```

Future v2 security stages may be inserted as:

```text
HASHING
ENCRYPTING
AUTHENTICATING
UPLOADING
```

without redesigning the overall job model.

---

# 13. Retry & Timeout

The backup engine must support:

- connection timeout;
- command/export timeout;
- maximum retry attempts;
- retry delay.

If retry is exhausted:

```text
FAILED
```

is recorded and Feishu notification is sent.

Exact timeout and retry values are intentionally not frozen until real device PoC is performed.

---

# 14. Backup Validation

A backup is not successful merely because an SSH command returned.

Validation pipeline:

```text
Device reachable / connect success?
        |
Authentication success?
        |
Export/command success?
        |
Configuration received?
        |
Content non-empty?
        |
Driver-specific validation success?
        |
Normalization success?
        |
SHA-256 generated?
        |
S3 reference/object valid?
        |
SUCCESS
```

Possible failure codes include:

```text
DEVICE_OFFLINE
CONNECTION_TIMEOUT
AUTHENTICATION_FAILED
COMMAND_FAILED
EMPTY_CONFIG
INVALID_CONFIG
NORMALIZATION_FAILED
HASH_FAILED
S3_UPLOAD_FAILED
S3_VERIFY_FAILED
```

---

# 15. Configuration Normalization

Normalization is mandatory before SHA-256 change detection.

Purpose:

Remove dynamic export content that does not represent a real configuration change, such as:

```text
Generated Time
Export Timestamp
Session Metadata
Dynamic banner/header values
```

Flow:

```text
Raw Configuration
       |
driver.normalize_config()
       |
Normalized Configuration
       |
SHA-256
```

Normalization logic is driver-specific.

---

# 16. SHA-256 Change Detection

Full SHA-256 is represented as:

```text
64 hexadecimal characters
```

Flow:

```text
Normalized Config
       |
SHA-256
       |
Compare with latest successful normalized config hash
       |
   +---+---+
   |       |
 Same   Different
   |       |
No Change Changed
```

v1 only displays:

```text
Changed
No Change
```

No line-level diff is included.

---

# 17. Behavior When Configuration Does Not Change

The backup job **still executes every scheduled day**.

Reason:

- confirms the device is reachable;
- confirms the backup driver still works;
- retrieves current config;
- validates current config;
- proves the SHA-256 comparison;
- creates a daily successful backup-run record.

However, if normalized SHA-256 is unchanged, a duplicate S3 object does **not** need to be stored again.

Example:

```text
01 Oct -> Snapshot A1 -> Physical Object X
02 Oct -> Snapshot A2 -> Physical Object X
03 Oct -> Snapshot A3 -> Physical Object X
04 Oct -> Snapshot A4 -> Physical Object X
```

On a change:

```text
05 Oct -> Snapshot A5 -> Physical Object Y
```

This creates application-level content reuse/deduplication while still maintaining complete operational history.

---

# 18. Ceph S3 Repository

v1 uses a single repository:

```text
Ceph S3
```

Configuration is backend-only.

Conceptual environment values:

```text
S3_ENDPOINT
S3_BUCKET
S3_ACCESS_KEY
S3_SECRET_KEY
S3_SECURE
```

Secrets are not edited from the website.

Configuration files are not permanently stored on the application server.

---

# 19. Application-Level Versioning

The application uses logical snapshots, not S3-native object versioning as the primary version model.

Example:

```text
Device: MKK-Core-Switch

Snapshot 101 -> 2026-10-01 01:00
Snapshot 102 -> 2026-10-02 01:00
Snapshot 103 -> 2026-10-03 01:00
```

Multiple logical snapshots may refer to the same physical S3 object if configuration content is unchanged.

---

# 20. Retention

## 20.1 Standard Retention

```text
31 Days
```

Logical snapshots for the latest 31 days are retained.

## 20.2 Smart Retention

```text
7 Daily
4 Weekly
12 Monthly
3 Yearly
```

One physical object may serve multiple retained logical snapshots.

## 20.3 Object Deletion Rule

A physical S3 object may be deleted only when no retained logical snapshot references it.

---

# 21. Backup History

All backup-run metadata is persistent, including after the associated file/object expires from retention.

Minimum history information:

- Device
- Job ID
- Trigger type
- Driver
- Start time
- End time
- Duration
- Retry count
- Result
- Failure reason/code
- SHA-256
- Changed / No Change
- Snapshot reference
- S3 object status
- File size
- Retention policy

An expired object does not delete the historical execution record.

---

# 22. Backup Archive / Download

## Admin

May:

- open archive history;
- search archive list;
- download an available retained configuration.

## Viewer

May:

- open/view history;
- view metadata;
- view retention;
- view Changed / No Change.

May **not** download a configuration backup.

---

# 23. Integrity Status Wording in v1

The mockup currently uses:

```text
Verified
```

For v1, wording must not imply HMAC cryptographic authentication because HMAC is not yet implemented.

Recommended baseline wording:

```text
Checksum OK
Object Verified
```

SHA-256 currently serves as the change/content fingerprint.

When HMAC-SHA256 is added in v2, authentication/integrity wording can be upgraded accordingly.

---

# 24. Failed Backup Alert

Channel:

```text
Feishu Webhook
```

Alert is sent after retry policy is exhausted.

Minimum content:

- Hostname
- Vendor
- Model
- IP
- Driver
- Timestamp
- Attempts
- Failure code/reason

---

# 25. Account Management

Admin can:

- add users;
- remove users;
- assign Admin or Viewer role.

Both Admin and Viewer can change their own password.

User records move from mockup browser `localStorage` to the application database.

---

# 26. Theme

Light and Dark Mode are both retained.

The theme may remain a client-side UI preference.

---

# 27. v2 Scope & Delivery Status

## Delivered Security & Encryption (Completed)

```text
1. At-Rest S3 Payload Pipeline:
   - zlib Deflate Compression (Level 6, magic header 'NBZ1') saving 60-80% storage bandwidth
   - PBKDF2-HMAC-SHA256 Key Derivation (100,000 iterations, 16B salt) from Master Password
   - AES-256-CBC Encryption (PKCS#7 padding, 16B random IV)
   - HMAC-SHA256 Encrypt-then-MAC Authentication (32B tag)
   - Constant-time MAC comparison (timing-attack resistant via hmac.compare_digest)
   - Transparent decompression & decryption on download (with legacy raw fallback)

2. Database Credential Vault (PostgreSQL):
   - Upgraded to 256-bit AES-256-CBC + HMAC-SHA256
   - PBKDF2-HMAC-SHA256 (100,000 iterations) derived from APP_SECRET_KEY
   - Stored in storage_repositories.secret_key_encrypted & master_key_encrypted (VARCHAR(512))
   - Zero-downtime backward compatibility fallback for legacy Fernet tokens (gAAAAA...)

3. S3 Repository Manifest:
   - Encrypted manifest envelope (repo_manifest.enc) with Master Password
   - Validates bucket ownership, active status, and key derivation

4. Cryptography Visualizer & Live Lab:
   - Standalone interactive web animation and SubtleCrypto live simulator at /crypto-animation.html
   - Direct header button and user menu access from dashboard

5. Secret Management Strategic Analysis (Infisical KMS):
   - Comprehensive security analysis completed; earmarked as future roadmap for next project.
```

## Delivered Enterprise Reporting (Completed)

```text
Excel (.xlsx) Export with charts and KPIs
PDF (.pdf) Audit Report with date range filter
```

## Pruned / Excluded Items

Per user requirements, non-essential roadmap items were explicitly excluded from the codebase:

```text
Configuration line-level visual diff (Excluded)
Cross-version diffing engine (Excluded)
Configuration drift detection (Excluded)
Automated restore / rollback (Excluded)
```

---

# 28. v1 Completion Criteria

v1 is functionally complete when the application can:

1. authenticate users;
2. enforce Admin / Viewer access;
3. synchronize real network devices from Zabbix;
4. show real device status;
5. assign vendor-specific backup drivers;
6. save/clear driver and daily schedule settings;
7. execute manual backup;
8. execute persistent daily schedules;
9. queue backup jobs;
10. retry failed jobs;
11. validate real collected configuration;
12. normalize configuration;
13. calculate 64-hex SHA-256 fingerprint;
14. determine Changed / No Change;
15. reuse existing physical object when unchanged;
16. store changed configuration in Ceph S3;
17. maintain logical snapshots;
18. enforce 31-day or Smart 7/4/12/3 retention;
19. preserve all backup-run metadata;
20. allow Admin-only downloads;
21. display real Ceph HEALTH_OK / HEALTH_WARN / HEALTH_ERR;
22. send final failed-job alerts through Feishu;
23. support light/dark mode.
