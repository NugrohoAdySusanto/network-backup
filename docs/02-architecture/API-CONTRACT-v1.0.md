# Network Backup Dashboard — API Contract

**Version:** 1.0  
**Status:** Implementation Contract for Backend v1  
**Backend:** FastAPI  
**Base Path:** `/api/v1`  
**Frontend:** Same-origin HTML/Tailwind/Vanilla JavaScript  
**Authentication:** Server-side session + Secure HttpOnly cookie  
**CSRF:** Required for state-changing authenticated requests  
**Application Timezone:** `Asia/Jakarta`  
**Authoritative Database Schema:** `DATABASE-SCHEMA-ERD-v1.0.md`

---

# 1. Contract Goals

This document defines the stable HTTP boundary between the v1 frontend and backend.

The API must preserve the agreed component boundaries:

```text
Frontend
   |
   | HTTP/JSON
   v
FastAPI
   |
   +-- Auth Service
   +-- Zabbix Service
   +-- Backup Service
   +-- Schedule Service
   +-- Retention Service
   +-- S3 Service
   +-- Ceph Health Service
   +-- Notification Service
```

The frontend must never communicate directly with:

```text
Zabbix
Network Devices
Ceph S3
Ceph Manager/Dashboard API
Feishu Webhook
Redis
PostgreSQL
```

---

# 2. General HTTP Rules

## 2.1 Base URL

Frontend uses same-origin relative paths:

```text
/api/v1/...
```

Nginx routes `/api/` to FastAPI.

No public cross-origin API is required in v1.

## 2.2 Content Types

JSON requests:

```http
Content-Type: application/json
Accept: application/json
```

Snapshot download returns binary/text configuration content using a file response.

## 2.3 Timestamps

All API timestamps use ISO 8601 with an explicit timezone offset.

Example:

```text
2026-10-04T01:10:04+07:00
```

PostgreSQL stores timezone-aware timestamps; UI displays in `Asia/Jakarta`.

## 2.4 Request ID

Backend should attach a request identifier to every response:

```http
X-Request-ID: <uuid>
```

If the request already supplies `X-Request-ID`, backend may reuse it after validation or generate a new one.

The same request ID should appear in structured backend logs.

---

# 3. Response Conventions

## 3.1 Successful JSON Response

Use:

```json
{
  "data": {}
}
```

For list endpoints:

```json
{
  "data": {
    "items": [],
    "total": 0,
    "limit": 50,
    "offset": 0
  }
}
```

## 3.2 Successful No-Content Response

Use:

```text
204 No Content
```

when no response body is needed.

## 3.3 Error Response

All API errors use:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable safe message.",
    "details": {},
    "request_id": "4de3a92f-..."
  }
}
```

`details` may be `{}` when unnecessary.

Never expose:

```text
password
SSH credential
S3 secret
Zabbix token
Feishu webhook
session id
raw stack trace
raw sensitive configuration
```

---

# 4. Standard Status Codes

| HTTP | Meaning |
|---|---|
| `200` | Request succeeded |
| `201` | Resource created |
| `202` | Background job accepted |
| `204` | Succeeded, no response body |
| `400` | Invalid business request |
| `401` | Not authenticated / invalid session |
| `403` | Authenticated but forbidden |
| `404` | Resource not found |
| `409` | State conflict |
| `410` | Requested retained file is no longer available |
| `422` | Request/schema validation error |
| `429` | Too many requests, where rate limiting is enabled |
| `500` | Internal application error |
| `502` | External integration/storage failure where appropriate |
| `503` | Service temporarily unavailable |

---

# 5. Authentication & Session Contract

## 5.1 Session Cookie

Backend creates an opaque server-side session identifier stored in Redis.

Browser cookie example:

```text
nb_session=<opaque_random_value>
```

Recommended attributes:

```text
HttpOnly
Secure
SameSite=Lax
Path=/
```

`Secure` is mandatory in HTTPS deployment.

The session identifier must never be returned in JSON.

## 5.2 Remember Me

`remember_me=true` uses the longer configured Redis/session-cookie TTL.

`remember_me=false` uses the normal session TTL.

## 5.3 CSRF

All authenticated state-changing requests must include:

```http
X-CSRF-Token: <csrf-token>
```

The CSRF token is associated with the server-side session.

Safe GET requests do not require this header.

---

# 6. Authentication Endpoints

## 6.1 `POST /auth/login`

Public.

### Request

```json
{
  "username": "admin",
  "password": "example-password",
  "remember_me": true
}
```

### Success — `200`

Sets the HttpOnly session cookie.

```json
{
  "data": {
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "is_active": true
    },
    "csrf_token": "opaque-csrf-token"
  }
}
```

### Errors

```text
401 INVALID_CREDENTIALS
403 USER_INACTIVE
429 LOGIN_RATE_LIMITED
```

Do not indicate whether username or password specifically was wrong.

---

## 6.2 `POST /auth/logout`

Authenticated.

Requires CSRF.

### Success

```text
204 No Content
```

Backend removes/invalidates Redis session and clears cookie.

---

## 6.3 `GET /auth/me`

Authenticated.

Used on page load/session restore.

### Success — `200`

```json
{
  "data": {
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "is_active": true
    },
    "csrf_token": "opaque-csrf-token"
  }
}
```

The CSRF token may be returned here so the frontend can restore it after page reload without exposing the session id.

---

## 6.4 `POST /auth/change-password`

Authenticated.

Requires CSRF.

### Request

```json
{
  "current_password": "old-password",
  "new_password": "new-password",
  "confirm_password": "new-password"
}
```

### Success

```text
204 No Content
```

### Errors

```text
400 PASSWORD_CONFIRMATION_MISMATCH
400 PASSWORD_POLICY_FAILED
401 CURRENT_PASSWORD_INVALID
```

After password change, backend may rotate the current session identifier as a security hardening measure.

---

# 7. User Management — Admin Only

## 7.1 `GET /users`

Admin only.

### Response — `200`

```json
{
  "data": {
    "items": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": true,
        "last_login_at": "2026-10-04T08:30:00+07:00",
        "created_at": "2026-10-01T10:00:00+07:00"
      },
      {
        "id": 2,
        "username": "viewer",
        "role": "viewer",
        "is_active": true,
        "last_login_at": null,
        "created_at": "2026-10-01T10:00:00+07:00"
      }
    ],
    "total": 2,
    "limit": 100,
    "offset": 0
  }
}
```

Never return `password_hash`.

---

## 7.2 `POST /users`

Admin only.

Requires CSRF.

### Request

```json
{
  "username": "noc.viewer",
  "password": "initial-password",
  "role": "viewer"
}
```

Allowed roles:

```text
admin
viewer
```

### Success — `201`

```json
{
  "data": {
    "id": 3,
    "username": "noc.viewer",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-10-04T11:00:00+07:00"
  }
}
```

### Errors

```text
409 USERNAME_ALREADY_EXISTS
422 INVALID_ROLE
422 PASSWORD_POLICY_FAILED
```

---

## 7.3 `DELETE /users/{user_id}`

Admin only.

Requires CSRF.

UI calls this "Delete", but backend implementation performs **soft deactivation**:

```text
is_active = false
```

### Success

```text
204 No Content
```

### Errors

```text
400 CANNOT_DEACTIVATE_SELF
409 CANNOT_DEACTIVATE_LAST_ADMIN
404 USER_NOT_FOUND
```

Historical `requested_by` / `updated_by` relations remain intact.

---

# 8. Dashboard Summary

## `GET /dashboard/summary`

Admin and Viewer.

### Response — `200`

```json
{
  "data": {
    "total_devices": 27,
    "scheduled_devices_today": 27,
    "successful_devices_today": 25,
    "backup_success_rate_today": 92.59,
    "ceph": {
      "status": "HEALTH_OK",
      "summary": "Cluster is healthy.",
      "last_checked_at": "2026-10-04T11:50:20+07:00"
    },
    "zabbix": {
      "status": "OK",
      "summary": "27 network devices synchronized.",
      "last_checked_at": "2026-10-04T11:50:30+07:00"
    }
  }
}
```

`backup_success_rate_today` considers **scheduled jobs only**.

Success states:

```text
SUCCESS_CHANGED
SUCCESS_NO_CHANGE
```

Unsuccessful:

```text
FAILED
SKIPPED_DEVICE_DOWN
SKIPPED_STATUS_UNKNOWN
```

Manual backup jobs do not inflate the KPI.

---

# 9. Device Endpoints

## 9.1 `GET /devices`

Admin and Viewer.

Query parameters:

```text
source_present=true|false
status=up|down|unknown
search=<hostname/ip/vendor/model>
limit=50
offset=0
```

Recommended defaults:

```text
source_present=true
limit=100
offset=0
```

### Response — `200`

```json
{
  "data": {
    "items": [
      {
        "id": 27,
        "zabbix_host_id": "10567",
        "hostname": "MKK-Core-Switch",
        "ip_address": "10.11.0.3",
        "vendor": "Ruijie",
        "model": "S5350-24GT4XS-E",
        "host_group": "Network Device",
        "availability_status": "up",
        "availability_checked_at": "2026-10-04T11:50:30+07:00",
        "zabbix_last_sync_at": "2026-10-04T11:50:30+07:00",
        "source_present": true,

        "backup_settings": {
          "driver_key": "ruijie-switch",
          "driver_label": "Ruijie Switch Driver",
          "schedule_enabled": true,
          "daily_time": "01:10",
          "retention_policy": "smart_7_4_12_3"
        },

        "latest_attempt": {
          "job_id": "36dfe989-f29e-4e26-93c2-df5dd4f401d4",
          "state": "FAILED",
          "finished_at": "2026-10-04T01:10:12+07:00",
          "attempt_count": 3,
          "failure_stage": "CONNECTING",
          "failure_code": "CONNECTION_TIMEOUT",
          "failure_message": "SSH connection timeout."
        },

        "latest_success": {
          "job_id": "125b6c03-e93d-4317-a6ee-975db85294e4",
          "state": "SUCCESS_NO_CHANGE",
          "finished_at": "2026-10-03T01:10:04+07:00"
        },

        "change_status": "no_change",
        "active_job": null,

        "permissions": {
          "can_backup": true,
          "can_edit_settings": true,
          "can_download": true
        }
      }
    ],
    "total": 27,
    "limit": 100,
    "offset": 0
  }
}
```

For Viewer:

```json
"permissions": {
  "can_backup": false,
  "can_edit_settings": false,
  "can_download": false
}
```

These permission flags are UI hints only. Backend authorization remains authoritative.

---

## 9.2 `GET /devices/{device_id}`

Admin and Viewer.

Returns the same domain fields as device-list entry, with optional additional detail.

### Errors

```text
404 DEVICE_NOT_FOUND
```

---

## 9.3 `POST /devices/sync-zabbix`

Admin only.

Requires CSRF.

Manually triggers the same Zabbix sync task normally run periodically.

### Success — `202`

```json
{
  "data": {
    "task_id": "celery-task-id",
    "status": "QUEUED"
  }
}
```

This endpoint is optional for the UI but useful operationally.

It must not perform the whole sync inside the HTTP request.

---

# 10. Driver Registry API

## `GET /drivers`

Admin and Viewer.

Returns registered backend drivers.

### Response

```json
{
  "data": {
    "items": [
      {
        "key": "sangfor-nsf",
        "label": "Sangfor NSF Driver",
        "transport": "ssh",
        "implementation": "netmiko",
        "output_extension": "conf"
      },
      {
        "key": "mikrotik-routeros",
        "label": "Mikrotik RouterOS Driver",
        "transport": "ssh",
        "implementation": "netmiko",
        "output_extension": "rsc"
      },
      {
        "key": "ruijie-switch",
        "label": "Ruijie Switch Driver",
        "transport": "ssh",
        "implementation": "netmiko",
        "output_extension": "cfg"
      },
      {
        "key": "ruijie-ap",
        "label": "Ruijie AP Driver",
        "transport": "ssh",
        "implementation": "netmiko",
        "output_extension": "text"
      }
    ]
  }
}
```

`implementation` may later be `custom_ssh` for a specific driver without affecting frontend behavior.

The frontend assigns by `key`, never by Python class name.

---

# 11. Backup Settings API

## 11.1 `GET /devices/{device_id}/backup-settings`

Admin and Viewer.

### Response

```json
{
  "data": {
    "device_id": 27,
    "driver_key": "ruijie-switch",
    "schedule_enabled": true,
    "daily_time": "01:10",
    "retention_policy": "smart_7_4_12_3",
    "next_run_at": "2026-10-05T01:10:00+07:00",
    "last_dispatched_at": "2026-10-04T01:10:00+07:00",
    "updated_at": "2026-10-03T18:40:00+07:00"
  }
}
```

---

## 11.2 `PUT /devices/{device_id}/backup-settings`

Admin only.

Requires CSRF.

Corresponds to row **Save**.

### Request

```json
{
  "driver_key": "ruijie-switch",
  "schedule_enabled": true,
  "daily_time": "01:10",
  "retention_policy": "smart_7_4_12_3"
}
```

Allowed retention values:

```text
standard_31
smart_7_4_12_3
```

Rules:

```text
driver_key must exist in Driver Registry
if schedule_enabled=true => daily_time required
daily_time must use a 5-minute boundary
no other enabled device may use the same daily_time
```

### Success — `200`

```json
{
  "data": {
    "device_id": 27,
    "driver_key": "ruijie-switch",
    "schedule_enabled": true,
    "daily_time": "01:10",
    "retention_policy": "smart_7_4_12_3",
    "next_run_at": "2026-10-05T01:10:00+07:00",
    "updated_at": "2026-10-04T12:00:00+07:00"
  }
}
```

### Errors

```text
404 DEVICE_NOT_FOUND
422 DRIVER_KEY_INVALID
422 SCHEDULE_TIME_REQUIRED
422 SCHEDULE_TIME_NOT_5_MINUTE_SLOT
409 SCHEDULE_SLOT_ALREADY_USED
```

---

## 11.3 `DELETE /devices/{device_id}/backup-settings`

Admin only.

Requires CSRF.

Corresponds to row **Clear**.

Backend clears:

```text
driver_key
schedule_enabled
daily_time
next_run_at
last_dispatched_at
```

Retention preference may remain stored.

It does **not** delete:

```text
device
backup_jobs
snapshots
config_objects
S3 files
```

### Success

```text
204 No Content
```

---

# 12. Manual Backup API

## `POST /devices/{device_id}/backup`

Admin only.

Requires CSRF.

Creates a persistent `backup_jobs` row and enqueues Celery work.

The HTTP request must not open SSH.

### Request

No body required.

Optional body may be accepted as `{}`.

### Success — `202`

```json
{
  "data": {
    "job_id": "36dfe989-f29e-4e26-93c2-df5dd4f401d4",
    "device_id": 27,
    "trigger_type": "manual",
    "state": "QUEUED",
    "created_at": "2026-10-04T12:05:00+07:00"
  }
}
```

### Pre-Enqueue Validation

FastAPI validates:

```text
device exists
source_present=true
driver assigned
user is Admin
no known active job conflict if detectable
```

Do not use cached `availability_status` as the authoritative final gate. The worker performs a fresh Zabbix pre-check.

### Errors

```text
404 DEVICE_NOT_FOUND
409 DEVICE_NOT_IN_ZABBIX_SOURCE
409 DRIVER_NOT_ASSIGNED
409 BACKUP_ALREADY_RUNNING
```

Redis per-device lock remains the final concurrency protection.

---

# 13. Backup Job API

## 13.1 `GET /backup-jobs/{job_id}`

Admin and Viewer.

Used for 2–3 second polling while active.

### Response

```json
{
  "data": {
    "id": "36dfe989-f29e-4e26-93c2-df5dd4f401d4",
    "device": {
      "id": 27,
      "hostname": "MKK-Core-Switch"
    },
    "trigger_type": "manual",
    "driver_key": "ruijie-switch",
    "state": "HASHING",
    "attempt_count": 1,
    "max_attempts": 3,
    "zabbix_status_at_start": "up",
    "change_status": null,
    "failure": null,
    "scheduled_for": null,
    "started_at": "2026-10-04T12:05:01+07:00",
    "finished_at": null,
    "duration_ms": null,
    "created_at": "2026-10-04T12:05:00+07:00"
  }
}
```

Failure example:

```json
{
  "data": {
    "id": "36dfe989-f29e-4e26-93c2-df5dd4f401d4",
    "device": {
      "id": 27,
      "hostname": "MKK-Core-Switch"
    },
    "trigger_type": "scheduled",
    "driver_key": "ruijie-switch",
    "state": "FAILED",
    "attempt_count": 3,
    "max_attempts": 3,
    "zabbix_status_at_start": "up",
    "change_status": null,
    "failure": {
      "stage": "CONNECTING",
      "code": "CONNECTION_TIMEOUT",
      "message": "SSH connection timeout."
    },
    "started_at": "2026-10-04T01:10:00+07:00",
    "finished_at": "2026-10-04T01:10:12+07:00",
    "duration_ms": 12000
  }
}
```

Do not return raw exception traces.

---

## 13.2 `GET /devices/{device_id}/backup-jobs`

Admin and Viewer.

Query:

```text
state=<optional>
trigger_type=manual|scheduled
limit=50
offset=0
```

### Response

```json
{
  "data": {
    "items": [
      {
        "id": "0ec58d15-92db-40a4-8113-f4ccd3338387",
        "device_id": 25,
        "trigger_type": "scheduled",
        "driver_key": "ruijie-switch",
        "state": "SUCCESS_NO_CHANGE",
        "attempt_count": 0,
        "max_attempts": 3,
        "zabbix_status_at_start": "up",
        "zabbix_checked_at": "2026-10-06T00:20:00+07:00",
        "content_sha256": "dca3176f58597dd9a5c8c6e182a4678b4108a0a935fb11039d3a2af3ad90b66c",
        "change_status": "no_change",
        "raw_size_bytes": 2736,
        "normalized_size_bytes": 2673,
        "failure": null,
        "scheduled_for": "2026-10-06T00:20:00+07:00",
        "started_at": "2026-10-06T00:20:01+07:00",
        "finished_at": "2026-10-06T00:20:05+07:00",
        "duration_ms": 3930,
        "created_at": "2026-10-06T00:20:00+07:00",
        "snapshot": {
          "id": 11,
          "display_filename": "config.txt",
          "retention_policy": "smart_7_4_12_3",
          "is_retained": true,
          "retention_marks": ["daily"]
        }
      }
    ],
    "total": 91,
    "limit": 50,
    "offset": 0
  }
}
```

---

# 14. Backup Job State Contract

States exposed through the API:

```text
QUEUED
PRECHECKING_ZABBIX
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

SKIPPED_DEVICE_DOWN
SKIPPED_STATUS_UNKNOWN

FAILED
```

Terminal states:

```text
SUCCESS_CHANGED
SUCCESS_NO_CHANGE
SKIPPED_DEVICE_DOWN
SKIPPED_STATUS_UNKNOWN
FAILED
```

Frontend mapping:

```text
SUCCESS_CHANGED   => Success / Changed
SUCCESS_NO_CHANGE => Success / No Change
SKIPPED_*         => Skipped
FAILED            => Failed
```

---

# 15. Snapshot / Archive API

## 15.1 `GET /devices/{device_id}/snapshots`

Admin and Viewer.

Default archive view should return retained snapshots only.

Query parameters:

```text
retained_only=true
retention_mark=<optional>
search=<optional>
limit=100
offset=0
```

### Response

```json
{
  "data": {
    "items": [
      {
        "id": 501,
        "device_id": 27,
        "backup_job_id": "uuid",
        "captured_at": "2026-10-04T01:10:04+07:00",
        "change_status": "no_change",
        "retention_policy_at_capture": "smart_7_4_12_3",
        "retention_marks": [
          "DAILY",
          "LATEST_GOOD"
        ],
        "display_filename": "mkk-core-switch_20261004_011004.cfg",
        "is_retained": true,
        "expired_at": null,

        "object": {
          "id": 77,
          "size_bytes": 143289,
          "content_sha256": "64-hex-normalized-content-hash",
          "object_sha256": "64-hex-raw-object-hash",
          "storage_status": "available",
          "uploaded_at": "2026-09-28T01:10:03+07:00",
          "verified_at": "2026-09-28T01:10:04+07:00"
        },

        "download_available": true
      }
    ],
    "total": 26,
    "limit": 100,
    "offset": 0
  }
}
```

For Viewer:

```text
download_available = false
```

even if `storage_status=available`.

---

## 15.2 `GET /snapshots/{snapshot_id}`

Admin and Viewer.

Returns one snapshot with the same metadata fields.

---

## 15.3 `GET /snapshots/{snapshot_id}/download`

Admin only.

No CSRF required because this is a read-only GET, but session authorization is mandatory.

Before streaming:

```text
snapshot exists
is_retained=true
config_object.storage_status=available
S3 object exists
downloaded encrypted bytes match object_sha256
HMAC-SHA256 authenticated (constant-time compare_digest validation)
AES-256-CBC ciphertext decrypted using derived repository key
zlib Deflate stream inflated if 'NBZ1' header is present (with raw fallback)
delivered plaintext matches original content_sha256
```

### Success

Example headers:

```http
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="mkk-core-switch_20261004_011004.cfg"
X-Content-SHA256: <content_sha256>
X-Object-SHA256: <object_sha256>
```

### Errors

```text
403 DOWNLOAD_FORBIDDEN
404 SNAPSHOT_NOT_FOUND
410 SNAPSHOT_OBJECT_EXPIRED
502 S3_OBJECT_UNAVAILABLE
500 OBJECT_CHECKSUM_MISMATCH
500 PAYLOAD_DECRYPTION_FAILED (HMAC failure or corrupt envelope)
```

If checksum or HMAC authentication fails, do not deliver the file.

---

# 16. Ceph Health API

## `GET /health/ceph`

Admin and Viewer.

### HEALTH_OK

```json
{
  "data": {
    "status": "HEALTH_OK",
    "summary": "Cluster is healthy.",
    "details": {},
    "last_checked_at": "2026-10-04T11:50:20+07:00",
    "last_success_at": "2026-10-04T11:50:20+07:00"
  }
}
```

### HEALTH_WARN

```json
{
  "data": {
    "status": "HEALTH_WARN",
    "summary": "1 OSD down; 2 PG degraded.",
    "details": {
      "osd_down": 1,
      "pg_degraded": 2
    },
    "last_checked_at": "2026-10-04T11:50:20+07:00",
    "last_success_at": "2026-10-04T11:50:20+07:00"
  }
}
```

### UNKNOWN

```json
{
  "data": {
    "status": "UNKNOWN",
    "summary": "Unable to query Ceph health API.",
    "details": {
      "reason": "TIMEOUT"
    },
    "last_checked_at": "2026-10-04T11:50:20+07:00",
    "last_success_at": "2026-10-04T11:49:20+07:00"
  }
}
```

`UNKNOWN` must never be silently converted into `HEALTH_ERR`.

---

# 17. Integration Health API

## `GET /health/integrations`

Admin and Viewer.

### Response

```json
{
  "data": {
    "items": [
      {
        "name": "zabbix_sync",
        "status": "OK",
        "summary": "27 devices synchronized.",
        "last_checked_at": "2026-10-04T11:50:30+07:00",
        "last_success_at": "2026-10-04T11:50:30+07:00"
      },
      {
        "name": "ceph_health",
        "status": "HEALTH_OK",
        "summary": "Cluster is healthy.",
        "last_checked_at": "2026-10-04T11:50:20+07:00",
        "last_success_at": "2026-10-04T11:50:20+07:00"
      }
    ]
  }
}
```

---

# 18. RBAC Matrix

| Endpoint/Action | Admin | Viewer |
|---|:---:|:---:|
| Login/logout/me | Yes | Yes |
| Change own password | Yes | Yes |
| List devices | Yes | Yes |
| View backup settings | Yes | Yes |
| Edit/Clear backup settings | Yes | No |
| Backup Now | Yes | No |
| View jobs/history | Yes | Yes |
| View snapshots | Yes | Yes |
| Download snapshot | Yes | No |
| View Ceph health | Yes | Yes |
| List drivers | Yes | Yes |
| Sync Zabbix manually | Yes | No |
| Manage users | Yes | No |

Backend must enforce this independently of frontend visibility.

---

# 19. Error Codes — Core v1

Recommended stable error codes:

```text
INVALID_CREDENTIALS
USER_INACTIVE
SESSION_INVALID
CSRF_INVALID
FORBIDDEN

USER_NOT_FOUND
USERNAME_ALREADY_EXISTS
CANNOT_DEACTIVATE_SELF
CANNOT_DEACTIVATE_LAST_ADMIN

DEVICE_NOT_FOUND
DEVICE_NOT_IN_ZABBIX_SOURCE
DRIVER_NOT_ASSIGNED
DRIVER_KEY_INVALID
BACKUP_ALREADY_RUNNING

SCHEDULE_TIME_REQUIRED
SCHEDULE_TIME_NOT_5_MINUTE_SLOT
SCHEDULE_SLOT_ALREADY_USED
RETENTION_POLICY_INVALID

JOB_NOT_FOUND

SNAPSHOT_NOT_FOUND
SNAPSHOT_OBJECT_EXPIRED
DOWNLOAD_FORBIDDEN
OBJECT_CHECKSUM_MISMATCH

ZABBIX_UNAVAILABLE
CEPH_HEALTH_UNAVAILABLE
S3_OBJECT_UNAVAILABLE

INTERNAL_ERROR
```

Do not use raw exception/class names as API error codes.

---

# 20. Frontend Polling Contract

v1 does not require WebSocket or SSE.

Recommended polling:

```text
GET /dashboard/summary      every ~15 seconds
GET /devices                every ~15 seconds
GET /backup-jobs/{job_id}   every 2–3 seconds while job is non-terminal
```

Stop job polling when a terminal state is reached.

The backend Zabbix cache sync runs separately approximately every 30 seconds.

---

# 21. API Security Rules

1. Same-origin frontend/backend through Nginx.
2. No S3/Zabbix/SSH/Feishu credentials in JSON responses.
3. Session stored server-side.
4. Session cookie HttpOnly.
5. CSRF required for authenticated writes.
6. Viewer denied at backend, not only UI.
7. Download verifies object checksum before serving.
8. Errors are sanitized.
9. Rate-limit login endpoint if practical.
10. Do not expose FastAPI debug tracebacks in production.
11. Do not create an endpoint that accepts arbitrary SSH command text.
12. Do not create an endpoint that returns raw `.env` or integration credentials.

---

# 22. API Implementation Order

Recommended coding sequence:

```text
1. Common response/error models
2. Auth/session/CSRF
3. Users
4. Device read API
5. Driver registry
6. Backup settings
7. Manual backup enqueue
8. Job polling/history
9. Snapshot/history/download
10. Dashboard summary
11. Ceph/integration health
12. Manual Zabbix sync
```

---

# 23. API Definition of Done

The API contract is implemented correctly when:

1. browser authentication uses HttpOnly server-side session;
2. every write endpoint checks CSRF;
3. Admin/Viewer permissions match the RBAC matrix;
4. device list provides all data required by the existing dashboard row;
5. Save/Clear map cleanly to backup-settings endpoints;
6. Backup Now returns `202` quickly and never performs SSH in the request;
7. job polling shows the agreed state machine;
8. latest failure information can populate Last Backup hover;
9. snapshots expose real logical versions and physical-object metadata;
10. Viewer can see history but cannot download;
11. download validates `object_sha256`, decrypts AES-256-CBC, and uncompresses zlib payload;
12. Ceph `HEALTH_ERR` and application `UNKNOWN` remain distinguishable;
13. API never exposes infrastructure secrets;
14. frontend can operate without direct access to Zabbix/Ceph/network devices.

---

# 24. Report & Export API

## `GET /reports/export`

Authenticated (Admin & Viewer).

Allows exporting centralized backup execution logs and audit records filtered by date range, device, and status.

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format` | string | `xlsx` | Export format: `xlsx`, `pdf`, or `csv` |
| `start_date` | string | 7 days ago | Start datetime (ISO 8601 or `YYYY-MM-DD`) |
| `end_date` | string | now | End datetime (ISO 8601 or `YYYY-MM-DD`) |
| `device_id` | integer | optional | Filter by specific device ID |
| `status` | string | optional | Filter: `success` or `failed` |

### Success Responses

#### 1. Excel Spreadsheet Format (`format=xlsx` — Default)
- **Status:** `200 OK`
- **Content-Type:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition:** `attachment; filename="network_backup_report_{start}_{end}.xlsx"`
- Generated dynamically with `openpyxl` with full visual formatting:
  1. Corporate Header: PT Lucky Mom Indonesia NOC title and generation metadata.
  2. Executive KPI Summary Cards: Monitored Devices, Total Jobs, SLA %, Deduplicated CAS count, Changed count, and Failure count.
  3. Styled Column Headers: Dark Navy background (`#123C53`) with high-contrast white text.
  4. Auto-Fit Column Widths: Calculated dynamically based on max cell content length plus comfortable padding.
  5. Alternating Row Colors: Clean zebra striping (`#F8FAFC` vs `#FFFFFF`) with thin borders (`#CBD5E1`).
  6. Color-Coded Status: Green for `SUCCESS`, Amber for `SKIPPED`, Red for `FAILED`.
  7. Formatted Numbers & Monospace Fonts: Formatted KB sizes, durations, IP addresses, and SHA-256 hashes.
  8. Auto-Filter & Freeze Panes: Enabled across all headers with top rows frozen for seamless scrolling.

#### 2. PDF Document Format (`format=pdf`)
- **Status:** `200 OK`
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="network_backup_report_{start}_{end}.pdf"`
- Layout: A4 Landscape, generated dynamically with ReportLab.
- Report Components & Visual Optimizations:
  1. Corporate Header: PT Lucky Mom Indonesia NOC header with timestamps in `Asia/Jakarta` (WIB).
  2. Non-Overlapping Executive KPI Cards: Each card contains discrete flowable paragraphs with independent leading and vertical margins to ensure number values and labels never collide or overlap.
  3. Figure 1: Outcome Breakdown Vector Pie Chart & Underlying Summary Data Table.
  4. Figure 2: Distribution by Vendor Vector Pie Chart & Underlying Summary Data Table.
  5. Incident & Failure Diagnostic Audit Log: Filtered section detailing failure stages, error codes, and diagnostics (or 100% reliability confirmation banner).
  6. Detailed Backup Execution Records Table: Features high-contrast crisp white bold column titles (`#`, `Execution Time`, `Device Hostname`, etc.) rendered cleanly over dark slate (`#1e293b`) header rows.
  7. Corporate Digital Signature & Approval Block: Dual sign-off sections for NOC Engineer and IT Infrastructure Supervisor.
  8. Two-pass Numbered Canvas: Running header and footer with total page count (`Page X of Y`).

#### 3. CSV Format (`format=csv`)
- **Status:** `200 OK`
- **Content-Type:** `text/csv; charset=utf-8`
- **Content-Disposition:** `attachment; filename="network_backup_report_{start}_{end}.csv"`
- Includes UTF-8 BOM (`\ufeff`) for raw data ingestion and data science pipelines.
- 19 standard execution audit columns.

### Error Responses

```text
400 INVALID_DATE_RANGE (start_date > end_date)
401 SESSION_INVALID
422 INVALID_DATETIME_FORMAT
```

---

# 14. S3 Storage Repository Management APIs

Access restricted strictly to accounts with role `admin` with valid CSRF tokens (`require_admin_csrf`).

## 14.1 POST `/api/v1/storage/test`
Validates reachability of S3 endpoint and bucket credentials and inspects bucket for presence of `repo_manifest.enc`.

### Request Body:
```json
{
  "endpoint": "https://10.11.50.50:7443",
  "bucket": "network-backup",
  "access_key": "PDV4...",
  "secret_key": "...",
  "secure": true
}
```

### Success Response:
```json
{
  "data": {
    "success": true,
    "manifest_exists": false,
    "bucket": "network-backup",
    "endpoint": "https://10.11.50.50:7443"
  }
}
```

## 14.2 GET `/api/v1/storage/repositories`
Lists all configured storage repositories with masked credentials and linked snapshot count.

### Success Response:
```json
{
  "data": [
    {
      "id": "00000000-0000-0000-0000-000000000001",
      "name": "Primary S3 Repository",
      "endpoint": "https://10.11.50.50:7443",
      "bucket": "network-backup",
      "access_key_masked": "PDV4****CNAE",
      "secure": true,
      "is_active": true,
      "is_initialized": true,
      "snapshot_count": 22,
      "created_at": "2026-10-07T14:36:52Z"
    }
  ]
}
```

## 14.3 GET `/api/v1/storage/active`
Retrieves details of the currently active mounted storage repository.

## 14.4 POST `/api/v1/storage/repositories/init`
Initializes a new or empty bucket by encrypting and uploading `repo_manifest.enc` with a Master Password, saving and activating the repository. The Master Password is used with PBKDF2-HMAC-SHA256 (100,000 iterations) to derive repository cipher and HMAC keys. Credentials and master key are stored in the PostgreSQL Database Credential Vault using 256-bit AES-256-CBC + HMAC-SHA256.

### Request Body:
```json
{
  "name": "Secondary DR Pool",
  "endpoint": "https://s3.example.com",
  "bucket": "dr-bucket",
  "access_key": "...",
  "secret_key": "...",
  "secure": true,
  "master_password": "Minimum8CharsPassword"
}
```

## 14.5 POST `/api/v1/storage/repositories/unlock`
Verifies master password against existing `repo_manifest.enc` in bucket (authenticating HMAC-SHA256 and decrypting AES-256-CBC), saves and activates repository in database with credentials encrypted using 256-bit AES-256-CBC.

## 14.6 POST `/api/v1/storage/repositories/{repo_id}/activate`
Switches the active storage repository. Dashboard snapshots, device last backup status, and archives immediately scope to the activated pool.

## 14.7 POST `/api/v1/storage/disconnect`
Disconnects / unmounts the currently active storage repository. Deactivates all repository records in database without deleting snapshots or archives. Dashboard snapshot views switch to disconnected state.

---

# 15. Backup Worker Management APIs

## 15.1 GET `/api/v1/drivers`
Returns list of all registered backup workers (both system built-in and active custom CLI drivers). Available to all authenticated users.

### Success Response:
```json
{
  "data": {
    "items": [
      {
        "key": "mikrotik-routeros",
        "label": "Mikrotik RouterOS Driver",
        "vendor_hint": "Mikrotik",
        "model_hint": "RouterOS",
        "transport": "ssh",
        "output_extension": "rsc",
        "is_builtin": true,
        "is_active": true
      },
      {
        "id": "1195391c-586b-42e4-bb3e-fea1e016b876",
        "key": "huawei_vrp",
        "label": "Huawei VRP Switch",
        "vendor_hint": "Huawei",
        "model_hint": "S5700",
        "transport": "ssh",
        "default_port": 22,
        "connect_timeout": 15,
        "command_timeout": 30,
        "need_enable": false,
        "backup_command": "display current-configuration",
        "output_extension": "cfg",
        "is_builtin": false,
        "is_active": true
      }
    ]
  }
}
```

## 15.2 POST `/api/v1/drivers/custom`
Registers a new custom parametric CLI backup worker. Restricted to `admin`.

## 15.3 PUT `/api/v1/drivers/custom/{key}`
Updates settings of an existing custom driver. Restricted to `admin`.

## 15.4 DELETE `/api/v1/drivers/custom/{key}`
Deletes a custom driver (blocked with 409 conflict if assigned to any device). Restricted to `admin`.

## 15.5 POST `/api/v1/drivers/test`
Executes a dry-run test extraction on a live device using provided parametric configuration. Restricted to `admin`.

