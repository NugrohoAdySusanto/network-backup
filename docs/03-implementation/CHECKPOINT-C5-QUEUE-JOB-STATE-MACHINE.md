
# Checkpoint C5 — Queue + Backup Job State Machine

**Status:** Queue/state-machine baseline implemented.

## Scope

C5 adds:

```text
persistent backup_jobs creation
Celery enqueue
Redis per-device lock
active-job collision protection
GET job status
GET device job history
fresh Zabbix pre-check in worker
SKIPPED_DEVICE_DOWN
SKIPPED_STATUS_UNKNOWN
state-transition validator
```

## API

```text
POST /api/v1/devices/{device_id}/backup
GET  /api/v1/backup-jobs/{job_id}
GET  /api/v1/devices/{device_id}/backup-jobs
```

`POST Backup Now` returns 202 after the job is persisted/enqueued.
FastAPI never opens SSH.

## State Machine

```text
QUEUED
   |
   v
PRECHECKING_ZABBIX
   |
   +-- DOWN -----> SKIPPED_DEVICE_DOWN
   |
   +-- UNKNOWN --> SKIPPED_STATUS_UNKNOWN
   |
   +-- UP --------> next pipeline stage (C6+)
```

Full contract already reserves:

```text
CONNECTING
COLLECTING
NORMALIZING
VALIDATING
HASHING
UPLOADING
VERIFYING
RETRYING
SUCCESS_CHANGED
SUCCESS_NO_CHANGE
FAILED
```

## Important C5 Safety

C5 deliberately does NOT report a successful backup for an UP device,
because real SSH collection, SHA decision, S3 storage, and snapshots are
not complete yet.

Current C5 scaffold terminates an UP-device execution as:

```text
FAILED
failure_code = PIPELINE_NOT_IMPLEMENTED
```

after proving:

```text
queue works
worker works
Redis lock works
fresh Zabbix pre-check works
job state persistence works
```

This is intentional and must be removed when C6-C9 are implemented.

## Redis Lock

```text
backup-lock:device:{device_id}
```

Prevents scheduled + manual jobs from operating on the same device
simultaneously.

PostgreSQL remains the permanent job history source.

## C5 Validation Gate

1. Backup Now returns 202 quickly.
2. job exists before Celery executes.
3. duplicate active backup for same device returns conflict.
4. per-device Redis lock prevents execution race.
5. DOWN device never opens SSH.
6. UNKNOWN status never opens SSH.
7. DOWN/UNKNOWN become terminal persisted states.
8. job polling works.
9. Viewer cannot create jobs.
10. browser can close while Celery keeps running.
11. invalid state transitions are rejected.
12. an UP job is not falsely marked successful before C6-C9.

## Readiness After C5

After C0-C5 are verified, architecture/control-plane foundations are ready.

Remaining execution/data-plane work is:

```text
C6 Real Netmiko Drivers
C7 SHA-256 Change Detection
C8 Ceph S3 Storage
C9 Snapshot + History
C10 Persistent Daily Scheduler
C11 Retention
C12 Ceph Health + Feishu
C13 Frontend Integration
C14 Full Testing / TA Evidence
```

At this point a single AI Agent Masterplan can safely orchestrate the
remaining checkpoints, provided it is instructed to execute one checkpoint
at a time and pass each validation gate before continuing.
