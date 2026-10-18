# MASTERPLAN-AI-AGENT — Network Backup Dashboard / TA Opsi 3

**Version:** 2.0
**Status:** Authoritative Build Masterplan
**Project:** Centralized Network Configuration Backup — PT Lucky Mom Indonesia
**Architecture:** Modular Monolith + Background Worker
**Primary Agent Workflow:** Build First → Backup Engine → Formal Testing Last
**Application Timezone:** `Asia/Jakarta`

---

# 0. Purpose

This file is the main implementation instruction for the AI coding agent.

The agent must use this repository as an existing designed system, not as an open-ended greenfield project.

The required implementation priority is:

```text
PHASE 1
BUILD THE WEB APPLICATION PLATFORM FIRST
Frontend + Backend + Database + API + Authentication + Zabbix

        ↓

PHASE 2
BUILD THE BACKUP ENGINE
Queue + SSH/Netmiko + SHA-256 + Ceph + Snapshot + Scheduler + Retention + Feishu

        ↓

PHASE 3
FORMAL TESTING / HARDENING / TA EVIDENCE
Full integration, regression, security, performance, documentation
```

Do **not** start by optimizing tests, refactoring architecture, or building the backup engine before the web platform and Zabbix integration are usable.

Minimal smoke checks are allowed during development so broken code is not accumulated, but the formal testing program is intentionally deferred to Phase 3.

---

# 1. Read This Repository in This Order

Before editing code, read:

```text
1. AI-CONTEXT-MANIFEST.md
2. MASTERPLAN-AI-AGENT.md
3. docs/01-product/FEATURE-FINAL.md
4. docs/01-product/DESIGN-FINAL.md
5. docs/01-product/BRIEF-FRONTEND-FINAL.md
6. docs/02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md
7. docs/02-architecture/DATABASE-SCHEMA-ERD-v1.0.md
8. docs/02-architecture/API-CONTRACT-v1.0.md
9. docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md
10. docs/03-implementation/*
11. current source code
12. docs/04-reference/mockup-original.html
```

Do not infer the architecture from source code alone.

---

# 2. Authority Matrix

When documents overlap, use this authority:

| Domain | Authoritative File |
|---|---|
| v1 features / scope | `FEATURE-FINAL.md` |
| visual/UI behavior | `DESIGN-FINAL.md`, then `BRIEF-FRONTEND-FINAL.md` |
| backend architecture / component boundaries | `BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md` |
| database schema / relationships | `DATABASE-SCHEMA-ERD-v1.0.md` |
| HTTP routes / request-response / RBAC | `API-CONTRACT-v1.0.md` |
| driver abstraction | `BACKUP-DRIVER-CONTRACT-v1.0.md` |
| implementation order | this `MASTERPLAN-AI-AGENT.md` |

If a true conflict is found:

```text
STOP
identify the conflicting files
explain the impact
recommend one resolution
wait for approval
```

Do not silently change frozen behavior.

---

# 3. Frozen Technology Stack

Use:

```text
Ubuntu Server 24.04 LTS
Docker Compose
Nginx
HTML5
Tailwind CSS
Vanilla JavaScript ES Modules
Python 3.12
FastAPI
Pydantic / pydantic-settings
SQLAlchemy 2.x
Alembic
PostgreSQL 16+
Redis
Celery
Celery Beat
Netmiko
HTTPX
boto3
Argon2id
pytest
Ruff
mypy
Git
```

Do not introduce without approval:

```text
React
Vue
Next.js
Node backend
Django
microservices
Kubernetes
Kafka
RabbitMQ
JWT in localStorage
```

---

# 4. Frozen Architecture

```text
Browser
   |
 HTTPS
   |
 Nginx
   |
   +---------------------+
   |                     |
Frontend             FastAPI
HTML/Tailwind/JS         |
                         +--------------------------+
                         |            |             |
                    PostgreSQL      Redis      Integrations
                                      |        /    |     \
                                      |     Zabbix Ceph  Feishu
                                      |
                                  Celery Worker
                                      |
                                 BackupService
                                      |
                                 Driver Registry
                                      |
                                 SSH / Netmiko
                                      |
                               Network Devices
```

The architecture is a **Modular Monolith**.

Do not split it into microservices.

---

# 5. Mandatory Component Boundaries

| Component | Responsible For | Must Not Do |
|---|---|---|
| Frontend | UI, input, display | SSH, Zabbix token, S3 secret |
| FastAPI | API, auth, request validation | long-running SSH |
| PostgreSQL | permanent application state | task queue |
| Redis | session, queue, temporary locks | permanent history |
| Zabbix Service | device sync and live availability | config backup |
| Backup Service | backup workflow orchestration | vendor CLI details |
| Driver | SSH, collect, normalize, validate | DB/S3/Zabbix/Feishu |
| S3 Service | Ceph S3 object I/O | retention policy |
| Retention Service | snapshot/object protection decisions | SSH |
| Notification Service | Feishu webhook | determine backup outcome |

Forbidden examples:

```text
Frontend -> network device SSH
Frontend -> Zabbix token
Driver -> PostgreSQL
Driver -> Ceph S3
Driver -> Feishu
Driver -> Zabbix
FastAPI request -> synchronous long SSH backup
```

---

# 6. Current Source Baseline

The supplied source contains baseline work for:

```text
C0 Project Scaffold
C1 SQLAlchemy Models + Alembic
C2 Authentication + RBAC
C3 Zabbix Integration
C4 Driver Registry + Settings
C5 Queue + Job State Machine
```

Treat this code as a **starting implementation**, not unquestionable truth.

The agent may fix coding defects while preserving the approved contracts.

The agent must not change schema/API/architecture semantics merely to make implementation easier.

---

# 7. BUILD PRIORITY — IMPORTANT

The user explicitly wants the project built in this order:

```text
FIRST:
web application
frontend
backend
database
API
authentication/RBAC
Zabbix integration

SECOND:
backup engine
SSH
hashing
Ceph
history
scheduler
retention
notifications

LAST:
formal testing
hardening
TA evidence
```

Therefore do not use the older checkpoint numbering as the main execution order.

Checkpoint documents remain technical references, but this masterplan defines the current build sequence.

---

# 8. PHASE 1 — BUILD THE WEB PLATFORM FIRST

Goal:

> Produce a usable web application that authenticates users, reads real network devices from Zabbix, stores application data in PostgreSQL, exposes stable FastAPI endpoints, and displays the real data in the approved frontend.

Backup execution may still be disabled or marked "not implemented" at the end of this phase.

## Phase 1A — Project Runtime

Make the repository runnable with:

```text
nginx
api
postgres
redis
worker
beat
```

Required result:

```text
docker compose up -d --build
```

starts the application stack.

At this stage only fix runtime blockers. Do not spend time on deep test coverage.

---

# 9. PHASE 1B — Database Foundation

Use the approved schema:

```text
users
devices
device_backup_settings
backup_jobs
config_objects
snapshots
snapshot_retention_marks
integration_status
```

Requirements:

```text
SQLAlchemy models load correctly
Alembic migrations are usable
PostgreSQL is authoritative
no browser/localStorage operational database
```

Do not merge:

```text
backup_jobs
snapshots
config_objects
```

They are separate concepts.

---

# 10. PHASE 1C — Authentication + RBAC

Build real backend authentication.

Required behavior:

```text
Argon2id password hashes
Redis server-side sessions
HttpOnly cookie
CSRF on writes
Admin
Viewer
Remember Me
Change Password
Admin user management
soft-deactivate users
```

Do not use:

```text
JWT localStorage
plaintext user passwords
browser-only account database
```

Roles:

```text
Admin
Viewer
```

Viewer is read-only for operational functions and cannot download configuration backup files.

---

# 11. PHASE 1D — Zabbix Integration

Zabbix is the Single Source of Truth for device identity/status.

Sync:

```text
Zabbix Network Device Host Group
```

Required device fields:

```text
zabbix_host_id
hostname
management IP
vendor
model
availability_status
source_present
last sync/check timestamp
```

Vendor/model source:

```text
Zabbix Host Inventory
```

Availability source:

```text
configured item, default icmpping
```

Normalized status:

```text
UP
DOWN
UNKNOWN
```

Two-layer model:

```text
Layer 1:
background sync around every 30 seconds for dashboard display

Layer 2:
fresh live Zabbix check immediately before future backup execution
```

At Phase 1 the important outcome is that the dashboard reflects actual Zabbix devices and status.

---

# 12. PHASE 1E — Backend API

Build/finish API routes required by the frontend.

Minimum Phase 1 routes:

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/change-password

GET    /api/v1/users
POST   /api/v1/users
DELETE /api/v1/users/{id}

GET  /api/v1/devices
GET  /api/v1/devices/{id}
POST /api/v1/devices/sync-zabbix

GET /api/v1/drivers

GET    /api/v1/devices/{id}/backup-settings
PUT    /api/v1/devices/{id}/backup-settings
DELETE /api/v1/devices/{id}/backup-settings
```

Backup endpoints may exist from the current scaffold but must not be presented as completed backup functionality until Phase 2.

Use the exact response/error/RBAC contract in:

```text
docs/02-architecture/API-CONTRACT-v1.0.md
```

---

# 13. PHASE 1F — Driver Registry / Settings UI Foundation

At this phase the production drivers may remain metadata-only.

Registry keys:

```text
sangfor-nsf
mikrotik-routeros
ruijie-switch
```

Admin can manually assign the driver to each device.

The assignment must be persisted in:

```text
device_backup_settings.driver_key
```

Schedule UI may also be built now:

```text
Daily only
5-minute time slots
different slot per device
31-day retention
Smart 7/4/12/3
```

It is acceptable that actual scheduled backup execution is not yet active.

This allows the web UI to be finished before the backup engine.

---

# 14. PHASE 1G — FRONTEND INTEGRATION

This is a major priority.

Use the approved existing visual mockup.

Do **not** redesign from scratch.

Refactor the frontend into:

```text
frontend/
├── index.html
├── css/app.css
└── js/
    ├── api.js
    ├── auth.js
    ├── devices.js
    ├── backups.js
    ├── schedules.js
    ├── archives.js
    ├── users.js
    └── theme.js
```

Replace mock/demo implementation progressively.

Remove production dependence on:

```text
static device arrays
localStorage account database
fake hash generator
fake archives
fake vendor config
browser setTimeout scheduler
browser-generated backup files
```

Keep the approved design:

```text
login modal
NOC-style header
device table
driver dropdown
schedule modal
archive modal
account management modal
dark/light mode
responsive behavior
```

---

# 15. PHASE 1H — FRONTEND DATA CONTRACT

The frontend must load real backend data.

On application load:

```text
GET /auth/me
        |
        +-- valid -> dashboard
        |
        +-- invalid -> login modal
```

Dashboard:

```text
GET /devices
```

Admin device actions:

```text
GET /drivers
GET/PUT/DELETE backup-settings
```

User management:

```text
GET/POST/DELETE /users
```

The frontend must never receive:

```text
Zabbix API token
SSH password
S3 secret
Feishu webhook
PostgreSQL credentials
Redis credentials
```

---

# 16. PHASE 1 COMPLETION CONDITION

Phase 1 is considered functionally built when:

```text
application opens through Nginx
real login works
Admin/Viewer roles work
real PostgreSQL data is used
real Zabbix devices appear
real Zabbix status appears
vendor/model/IP appear from Zabbix
Admin can assign driver
Admin can save Daily time and retention
Viewer is read-only
frontend no longer depends on mock device/user data
browser can be closed without affecting backend services
```

Do not block Phase 1 completion on real SSH backup.

---

# 17. PHASE 2 — BUILD THE BACKUP ENGINE

Only after Phase 1 is usable, proceed to actual backup functionality.

Phase 2 sequence:

```text
2A Queue + Job State Machine
2B Real Netmiko Drivers
2C Configuration Validation/Normalization
2D SHA-256 Changed / No Change
2E Ceph S3 Storage
2F Logical Snapshot + History
2G Persistent Daily Scheduler
2H Retention
2I Ceph Health
2J Feishu Alerts
2K Backup Frontend Completion
```

---

# 18. PHASE 2A — Queue + Job State

Use:

```text
Redis
Celery
PostgreSQL backup_jobs
per-device Redis lock
```

API:

```text
POST /devices/{id}/backup
GET /backup-jobs/{job_id}
GET /devices/{id}/backup-jobs
```

FastAPI must return quickly.

SSH must execute in Celery Worker.

---

# 19. PHASE 2B — Real Netmiko Drivers

Implement one real vendor at a time.

Preferred implementation order:

```text
1. Mikrotik
2. Ruijie
3. Sangfor
```

Use actual tested commands only.

Do not invent commands.

Driver public contract remains:

```text
connect()
collect_config()
normalize_config()
validate_config()
cleanup()
```

All drivers use Netmiko where reliable.

If one device cannot be handled by Netmiko, a custom Python SSH implementation may exist **inside that driver only**.

---

# 20. PHASE 2C — Validation + Normalization

A successful SSH connection is not enough.

Validate:

```text
non-empty config
reasonable size
no CLI error response
expected vendor/config structure
```

Normalize only known volatile fields.

Do not aggressively alter real configuration.

---

# 21. PHASE 2D — SHA-256

Use:

```text
content_sha256
= normalized configuration
= Changed / No Change

object_sha256
= raw bytes stored in S3
= object integrity verification
```

Change state:

```text
baseline
changed
no_change
```

No line-by-line diff in v1.

---

# 22. PHASE 2E — Ceph S3

Use:

```text
boto3
Ceph RGW / S3 compatible endpoint
private bucket
```

Physical objects are separate from logical snapshots.

Recommended key:

```text
network-config/{device_id}/objects/{content_sha256}.{extension}
```

Do not use S3 native versioning as the primary logical history mechanism.

---

# 23. PHASE 2F — Snapshot / History

Successful jobs create logical snapshots.

No Change:

```text
new backup job
new logical snapshot
existing physical config object
```

Changed:

```text
new backup job
new logical snapshot
new physical config object
```

Keep operational job history even after storage retention expires.

---

# 24. PHASE 2G — Daily Scheduler

Daily only.

Each device gets its own time.

Slots use 5-minute boundaries:

```text
01:00
01:05
01:10
...
```

PostgreSQL stores:

```text
daily_time
next_run_at
last_dispatched_at
```

Celery Beat periodically runs a dispatcher.

The browser must not be the scheduler.

---

# 25. PHASE 2H — Retention

Standard:

```text
31 days
```

Smart:

```text
7 daily
4 weekly
12 monthly
3 yearly
```

Always protect:

```text
LATEST_GOOD
```

A physical S3 object may be garbage-collected only when no retained snapshot references it.

---

# 26. PHASE 2I — Ceph Health

UI states:

```text
HEALTH_OK
HEALTH_WARN
HEALTH_ERR
UNKNOWN
```

`UNKNOWN` means the application cannot determine Ceph health.

It is not equivalent to `HEALTH_ERR`.

Expose reason/details to the frontend hover/detail.

---

# 27. PHASE 2J — Feishu [COMPLETED - 2026-10-06]

Implemented via `backend/app/integrations/feishu_client.py` and `backend/app/services/notification_service.py`.

Dispatches immediately on final unsuccessful states (`FAILED`, `SKIPPED_DEVICE_DOWN`, `SKIPPED_STATUS_UNKNOWN`).

Verified with:
- Rich interactive card (`msg_type: "interactive"`) with red header banner
- Automatic plain-text fallback
- Full 12-parameter payload: device, vendor, model, IP, driver, job id, time (WIB), final state, failure stage, failure reason, attempt count, last successful backup
- Tracking in `integration_status` table (`name = 'feishu_webhook'`)
- Live physical test verification against MikroTik router `MKK-HQ_Router` (`10.11.0.2:22345`) resulting in `AUTHENTICATION_FAILED` and verified `200 OK` delivery to Feishu bot webhook.

No frontend webhook call. All notifications handled by backend.

---

# 28. PHASE 2K — Backup Frontend Completion

After the backup engine works, finish UI elements that depend on it:

```text
Backup Now
active job status
Last Backup
error hover
Changed / No Change
snapshot/archive modal
Admin download
Ceph Health
```

`Last Backup` must display the latest attempt.

On failure hover show:

```text
stage
error
attempts
last successful backup
```

---

# 29. PHASE 3 — FORMAL TESTING LAST

Formal testing starts only after Phase 1 + Phase 2 functionality is substantially built.

This does not prohibit minimal smoke checks while coding.

Formal Phase 3 covers:

```text
Docker/startup verification
Alembic migration verification
unit tests
API tests
RBAC tests
CSRF/session tests
Zabbix integration tests
real device driver tests
Celery queue tests
job state tests
Ceph upload/download tests
checksum tests
snapshot tests
scheduler tests
retention tests
Feishu tests
frontend end-to-end tests
failure simulations
security review
TA performance/evidence collection
```

Do not spend the early build phase trying to perfect coverage percentages.

---

# 30. Formal TA Evidence in Phase 3

Collect measurable evidence such as:

```text
manual vs automated backup process time
backup success rate
Changed/No Change accuracy
false-change normalization behavior
physical S3 object reuse
logical recovery point count
retention result
failure detection
Zabbix pre-check behavior
resource usage where relevant
```

This evidence will support BAB III/BAB IV later.

---

# 31. Frontend-First Build Rule

When a backend endpoint is ready, connect it to the approved frontend instead of creating a separate temporary admin UI.

Avoid building duplicate interfaces.

Example:

```text
Auth endpoint ready
-> wire Login Modal

Device endpoint ready
-> wire Device Table

Settings API ready
-> wire driver/schedule modal
```

This keeps the final web product growing continuously.

---

# 32. Existing Mockup Rule

`docs/04-reference/mockup-original.html` is a visual reference.

`frontend/index.html` is the active frontend.

The agent may refactor the active frontend into modules but must preserve the approved design and user flow.

Do not copy fake/mock operational logic into the real backend.

---

# 33. Zabbix Rule

Zabbix owns:

```text
device identity
management IP
vendor/model inventory
availability/status
```

Application database owns:

```text
driver assignment
schedule
retention
job history
snapshots
S3 object metadata
users
```

Do not duplicate Zabbix as a second independent device inventory editor.

---

# 34. Driver Rule

Driver assignment is manual from the web.

Do not auto-select a driver solely based on vendor.

Driver Registry may expose vendor hints but assignment remains explicit.

---

# 35. Security Rules

Never expose:

```text
SSH password
Zabbix API token
S3 secret
Ceph token
Feishu webhook
PostgreSQL password
Redis credentials
session ID in JSON
```

Never log plaintext secrets.

No arbitrary command endpoint.

Viewer permissions must be enforced by backend.

---

# 36. Secrets / Environment

Real secrets belong in:

```text
.env
```

Do not commit `.env`.

Commit:

```text
.env.example
```

The agent may add environment variables when necessary but must document them and avoid changing approved semantics.

---

# 37. Database Change Rule

After the database is initialized:

```text
all schema changes require Alembic migration
```

Do not manually patch production tables.

If the agent believes the frozen schema is insufficient:

```text
report
explain impact
propose migration
wait for approval
```

---

# 38. Source Control Rule

Recommended Git commits by functional milestone:

```text
build/runtime
database
auth-rbac
zabbix
frontend-auth
frontend-devices
driver-settings
backup-queue
driver-mikrotik
driver-ruijie
driver-sangfor
change-detection
ceph-storage
snapshot-history
scheduler
retention
ceph-health-feishu
frontend-backup
formal-testing
```

Avoid one giant commit.

---

# 39. AI Agent Work Report

At the end of each work session, report:

```text
Work Area:
Status: BUILT / PARTIAL / BLOCKED

What was implemented:
- ...

Files changed:
- ...

Database migration:
- none / file name

Environment variables added/changed:
- ...

Backend endpoints added/changed:
- ...

Frontend behavior added/changed:
- ...

External integration used:
- ...

Known blockers:
- ...

Next recommended build step:
- ...
```

During Phase 1 and Phase 2, testing report may be limited to smoke/build verification.

Formal test matrix belongs in Phase 3.

---

# 40. Stop Conditions

Stop and ask for approval when:

```text
a frozen architecture change is required
database contract must change
API contract must change materially
a new external service is proposed
vendor command is uncertain
a destructive network command would be required
Zabbix field mapping does not match real environment
Ceph API/RGW behavior contradicts assumptions
```

Do not improvise around these issues silently.

---

# 41. What the Agent Should Build First

The first active coding objective is:

```text
MAKE THE WEB APPLICATION REAL
```

Concrete order:

```text
1. make Docker stack run
2. make DB migrations work
3. make backend auth work
4. make real Zabbix sync work
5. make device API work
6. make driver/settings API work
7. replace frontend mock login
8. replace frontend static devices
9. replace frontend localStorage users
10. connect driver/schedule settings
11. make dashboard usable with real Zabbix data
```

Only then:

```text
start real backup execution
```

---

# 42. Phase 1 Target Demo

Before backup engine development, the application should already demonstrate:

```text
open web
login as Admin
see real Zabbix network devices
see UP/DOWN/UNKNOWN
see IP/vendor/model
assign backup driver
set daily backup time
set retention
Save
logout
login as Viewer
verify read-only view
manage user from Admin account
browser refresh keeps session/backend data
```

This is the first meaningful product milestone.

---

# 43. Phase 2 Target Demo

After backup engine:

```text
Admin clicks Backup Now
job becomes QUEUED
fresh Zabbix pre-check
SSH connects
config collected
config normalized
SHA calculated
Changed/No Change determined
Ceph object uploaded/reused
logical snapshot created
Last Backup updated
history visible
download works for Admin
Viewer cannot download
Feishu alerts final failures
daily schedule works without browser
retention preserves Latest Known Good
```

---

# 44. Final Definition of Done

v1 is complete when all of these are true:

```text
real backend authentication
real PostgreSQL persistence
real Redis session/queue
real Zabbix integration
real frontend/API integration
Admin/Viewer RBAC
manual driver assignment
daily schedule settings
real Netmiko collection
SHA-256 Changed/No Change
Ceph S3 physical storage
logical snapshots/history
31-day retention
Smart 7/4/12/3 retention
Latest Known Good protection
Ceph health
Feishu final failure alert
Admin download
Viewer read-only
browser-independent scheduling
formal Phase 3 testing completed
TA evidence collected
Excel (.xlsx) and PDF audit export reporting with date range picker & charts (C15)
Backup Status history logs and Ruijie Switch support (C16-C17)
Feishu alerting webhook with failure root-cause cards (C18)
S3 Storage Management with Master Password (PBKDF2 + AES-256-CBC + HMAC-SHA256 repo_manifest.enc) & active repository scoping (C19-C20)
Backup Worker Management with custom parametric CLI engine & dry-run test (C19)
Strict case-sensitive identity authentication with zero case tolerance (C20)
Pre-flight verification QA checklist & v2 engineering roadmap documented (C20)
```

---

# 45. v1 Feature Additions & Enhancements

Formally approved user enhancements delivered into v1:

```text
- Excel (.xlsx) and PDF (.pdf) audit report exporter with date picker range, charts & executive metrics (C15).
- Ruijie Switch command prompt save flow & backup history log column on devices table (C16-C17).
- Feishu / Lark real-time webhook alerting for failures and successes (C18).
- S3 Storage Management (Admin-only): dynamically configure, test connection with pop-up modal, initialize with Master Password (PBKDF2-HMAC-SHA256 100,000 iterations + AES-256-CBC + HMAC-SHA256 repo_manifest.enc), unlock, and mount isolated S3 repositories (C19).
- Active repository scoping (Hybrid Architecture): device backup status and execution history dynamically scoped to the connected S3 repository without cross-repo leakage (C20).
- Backup Worker Management (Admin-only): manage system built-in drivers and register custom parametric CLI drivers (SSH privilege escalation, pagination bypass, regex filtering, and live validation) (C19).
- Strict case-sensitive username authentication: exact match without case folding (C20).
- Checkpoint C20 Pre-flight verification checklist and v2 technical roadmap (C20).
```

---

> Continue from the supplied source repository. Preserve the approved architecture and visual design. Prioritize Phase 1: make the web application fully operational using FastAPI, PostgreSQL, Redis sessions, the approved API contract, real Zabbix integration, and the existing frontend. Do not start real SSH backup implementation until the web application can display real Zabbix devices and persist Admin-configured driver/schedule/retention settings. After Phase 1, implement the backup engine in Phase 2. Perform formal comprehensive testing only in Phase 3, while still using minimal smoke checks during development to prevent broken builds.

---

# 47. v2 Scope Execution (Epic 1 Completed & Cryptographic Unification)

Approved v2 features implemented and verified:

```text
- Epic 1: At-Rest Configuration Payload Compression & Encryption (zlib + AES-256-CBC + HMAC-SHA256)
  * Zero-trust storage for S3 backup objects with zlib Deflate (Level 6) compression ('NBZ1' magic marker, ~75% size reduction).
  * Cryptographic binary envelope layout:
    [salt: 16B] || [iv: 16B] || [hmac: 32B] || [ciphertext: PKCS7 padded].
  * Transparent cryptographic decryption and zlib inflation on download for authorized Admin requests with constant-time HMAC-SHA256 validation.
  * Key derivation via PBKDF2-HMAC-SHA256 with 100,000 iterations from repository master password.

- Database Credential Vault Upgrade:
  * Upgraded PostgreSQL secret storage (storage_repositories.secret_key_encrypted and master_key_encrypted) from 128-bit Fernet to AES-256-CBC + HMAC-SHA256 (PBKDF2-HMAC-SHA256 100,000 iterations from APP_SECRET).
  * Zero-downtime backward compatibility fallback ensures legacy Fernet rows can still be decrypted.
  * Active repository in database successfully migrated to AES-256 envelope format.

- Educational Web Animation & Live Simulator:
  * Implemented at /crypto-animation.html (accessible via dashboard button "Animasi Kriptografi").
  * Visualizes step-by-step pipeline for all 4 cryptographic & compression features:
    1. Payload Compression & Encryption (zlib + AES-256-CBC)
    2. Database Credential Vault (AES-256-CBC)
    3. S3 Repository Manifest (PBKDF2 + AES-256-CBC)
    4. CAS Content-Addressable Deduplication (Dual SHA-256)
- Strategic Secret Management Roadmap:
  * Infisical KMS analyzed as next-generation enterprise secrets architecture (Envelope Encryption / Centralized Key Management Service).
  * Designated as future improvement roadmap for the next project lifecycle.

- Pruned Scope: Epics 2 through 8 (Visual Diff Engine, Drift Detection, Restore/Rollback, Multi-Target Replication, Enterprise MFA/SSO, RBAC 2.0, Automated Compliance) permanently pruned and removed from project codebase and scope per user specifications.
```
