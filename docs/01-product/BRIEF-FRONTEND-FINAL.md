# Network Backup Dashboard — Final Frontend Brief

**Version:** 1.0  
**Status:** Frontend Functional Brief Frozen for v1  
**Reference:** Existing `mockup.html` is the visual baseline.

---

# 1. Frontend Goal

Transform the current single-page demo mockup into a real frontend for a centralized network configuration backup system without changing the established NOC visual identity.

The frontend must stop simulating operational data and instead consume real backend data for:

- authentication;
- users/roles;
- Zabbix-synchronized devices;
- device status;
- driver assignment;
- daily schedule;
- retention;
- backup job state;
- SHA-256 Changed / No Change;
- backup history;
- Ceph health;
- Feishu-related failure status where exposed.

---

# 2. v1 Page Model

v1 remains a **single primary dashboard page with modal workflows**.

No multi-page SPA structure is required at this stage.

Primary UI areas:

```text
Login Modal
   |
Main Dashboard
   |
   +-- Header KPI
   +-- Device Table
   +-- Backup Action Menu
   +-- Schedule Modal
   +-- Backup Archive Modal
   +-- Account / User Management Modal
   +-- Inline Feedback / Toast
```

---

# 3. Login

## UI retained

- Network Backup Portal
- Username
- Password
- Show/Hide
- Remember Session
- Quick Autofill
- Theme Toggle
- Sign In

## Backend behavior

Frontend sends credentials to backend.

Frontend must no longer validate against a JavaScript array/localStorage account list.

Expected conceptual response:

```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

Session/token mechanics will be finalized in backend architecture.

---

# 4. Role-Aware UI

## Admin

Show:

- Backup Driver select.
- Backup Now.
- Schedule.
- Save.
- Clear.
- Download.
- User Management.

## Viewer

Read-only.

Hide or disable:

- editable driver dropdown;
- Backup Now;
- Schedule mutation;
- Save;
- Clear;
- Download;
- User Management.

Viewer may still:

- view device status;
- view last backup;
- view retention;
- view Changed/No Change;
- open backup history;
- view Ceph health.

---

# 5. Header Data Contract

Frontend requires:

```text
total_devices
scheduled_today
successful_devices_today
backup_success_rate_today
ceph_health
current_user
```

Visual mapping:

```text
Total Devices
Backup Success Today
Ceph Health
Account
Theme
```

Ceph status values:

```text
HEALTH_OK
HEALTH_WARN
HEALTH_ERR
```

---

# 6. Device Table Data

Each device row requires a structure conceptually equivalent to:

```json
{
  "id": 12,
  "zabbix_host_id": "10567",
  "hostname": "MKK-Core-Switch",
  "status": "active",
  "ip_address": "10.11.0.3",
  "vendor": "Ruijie",
  "model": "S5350-24GT4XS-E",
  "driver_key": "ruijie-switch",
  "driver_label": "Ruijie Switch Driver",
  "retention_policy": "smart",
  "schedule": {
    "enabled": true,
    "daily_time": "01:00"
  },
  "last_backup": {
    "timestamp": "2026-10-03T01:00:00+07:00",
    "result": "SUCCESS_NO_CHANGE",
    "change_status": "no_change"
  }
}
```

Exact API shape will be defined during backend design.

---

# 7. Device Table Columns

Frontend renders:

```text
Hostname
Status
IP Address
Model
Backup Driver
Backup
Last Backup
Change
Download
Actions
```

## Status

Mapping:

```text
active     -> Active green pill
inactive   -> Non-Active red pill
```

## Change

Mapping:

```text
changed    -> Changed
no_change  -> No Change
null       -> —
```

Changed must use amber rather than danger red.

---

# 8. Backup Driver Interaction

The dropdown is populated from backend Driver Registry metadata.

Conceptually:

```json
[
  {
    "key": "sangfor-nsf",
    "label": "Sangfor NSF Driver"
  },
  {
    "key": "mikrotik-routeros",
    "label": "Mikrotik RouterOS Driver"
  },
  {
    "key": "ruijie-switch",
    "label": "Ruijie Switch Driver"
  }
]
```

The frontend must not infer vendor logic.

It only stores/selects:

```text
driver_key
```

---

# 9. Save Action

For Admin.

Save persists current editable row configuration:

- driver_key;
- daily schedule;
- retention policy.

Expected UX:

```text
Saving...
Saved successfully.
```

On failure:

```text
Failed to save device settings.
```

Save does not initiate a backup unless explicitly designed later.

---

# 10. Clear Action

For Admin.

Clear removes:

- driver assignment;
- schedule.

Clear must ask for confirmation because it modifies operational configuration.

Example:

```text
Clear backup assignment for MKK-Core-Switch?
This will remove the selected driver and daily schedule.
Existing backup history will not be deleted.
```

Retention/history/S3 objects remain untouched.

---

# 11. Backup Now

For Admin.

Action behavior:

```text
POST backup request
      |
backend creates job
      |
frontend receives job id/state
      |
UI shows Queued / Running status
```

The button must not stay blocked until SSH completes.

Possible UI messages:

```text
Backup queued.
Connecting...
Collecting configuration...
Validating...
No Change detected.
Backup completed.
```

---

# 12. Schedule Modal

v1 is **Daily only**.

Fields:

```text
Daily Backup Time
Retention Policy
```

Retention:

```text
31 Days
Smart Retention
```

Smart tooltip:

```text
7 Daily
4 Weekly
12 Monthly
3 Yearly
```

No date picker is required for v1 recurring schedule.

Recommended control:

```text
<input type="time">
```

instead of `datetime-local`.

---

# 13. Archive Modal

Opened from History/Download area.

Data is real backend metadata.

Recommended row fields:

```text
Timestamp
Retention Tier
Filename/Snapshot
Size
SHA-256
Changed/No Change
Object Status
Action
```

## Admin

Can download retained object.

## Viewer

No download action.

Viewer sees metadata/history only.

---

# 14. SHA-256 Display

Full SHA-256 is 64 hexadecimal characters.

Table may display shortened digest:

```text
7bd9e3a5...bf218c92
```

Interaction may provide:

- tooltip full digest;
- copy action.

No fake hash generator remains in production frontend.

---

# 15. Integrity / Status Labels

v1 terminology:

```text
Checksum OK
Object Verified
Changed
No Change
```

Do not display:

```text
AES-256 Encrypted
HMAC Verified
Authenticated
```

until v2 actually implements them.

---

# 16. Job Status UI

Recommended state mapping:

```text
QUEUED             -> Queued
CONNECTING         -> Connecting
COLLECTING         -> Collecting
NORMALIZING        -> Processing
VALIDATING         -> Validating
HASHING            -> Checking Change
UPLOADING          -> Uploading
VERIFYING          -> Verifying
RETRYING           -> Retrying
SUCCESS_CHANGED    -> Success / Changed
SUCCESS_NO_CHANGE  -> Success / No Change
FAILED             -> Failed
```

A small badge/spinner can appear in the relevant device row during an active job.

---

# 17. Failed Backup Feedback

When backend returns final failure:

Frontend displays:

- red error notice;
- failure summary;
- retry count if supplied.

Feishu notification itself is handled by backend.

The frontend does not call Feishu directly.

---

# 18. Ceph Health Frontend

Header consumes actual backend-provided Ceph health.

Mapping:

```text
HEALTH_OK   -> green
HEALTH_WARN -> amber
HEALTH_ERR  -> red
```

If status cannot be fetched:

recommended visual:

```text
UNKNOWN
```

This fallback should be supported even if the normal business states are only OK/WARN/ERR.

---

# 19. Account Modal

Retain existing structure.

## Everyone

- change own password.

## Admin only

- list users;
- add user;
- remove user;
- role selection: Admin / Viewer.

Frontend protections:

- cannot delete own active account;
- cannot remove last Admin.

Backend remains authoritative and must enforce the same rules.

---

# 20. Data Persistence Rules

The frontend must no longer use localStorage for operational data such as:

- users;
- device assignments;
- schedules;
- retention;
- backup history.

Client-side storage may still be used for non-operational preferences such as:

```text
theme_preference
```

Session persistence depends on the selected authentication architecture.

---

# 21. Removed v1 Demo Logic

Delete/replace frontend code that:

- creates static `initialData` devices;
- uses Cisco demo devices;
- generates fake hashes;
- generates synthetic archives;
- generates fake vendor configs;
- uses browser `setTimeout()` as production scheduler;
- executes backup only while browser is open;
- stores users in localStorage;
- stores operational device changes only in memory;
- resets devices on `End demo session`;
- exports CSV;
- prints PDF report;
- downloads generated manifest.

---

# 22. Existing Mockup Elements to Reuse

The following should be preserved as much as practical:

- CSS design tokens;
- DM Sans;
- Space Mono;
- Light/Dark variables;
- table spacing;
- Active/Non-Active badges;
- popover styling;
- glassmorphism modal;
- focus styling;
- login modal layout;
- account modal layout;
- archive modal layout;
- row action styling;
- retention pills;
- responsive table shell;
- `aria-live` notification pattern.

---

# 23. Existing Mockup Elements to Rename / Modify

```text
Visitor            -> Viewer
Backup Worker      -> Backup Driver
Backups Completed  -> Backup Success Today
S3 Status          -> Ceph Health
End demo session   -> Logout
31 Days demo data  -> Real 31 Days retention
DEMO DASHBOARD     -> Remove
Simulation footer  -> Production/system footer
```

---

# 24. Frontend Loading / Empty / Error States

Must support:

## Device sync loading

```text
Synchronizing network devices from Zabbix...
```

## No devices

```text
No network devices found in the configured Zabbix group.
```

## Zabbix unavailable

```text
Unable to synchronize with Zabbix.
Showing last synchronized device data.
```

## No backup history

```text
No backup history available for this device.
```

## Ceph error

```text
Ceph cluster health is unavailable.
```

## Driver not assigned

```text
Backup Driver not configured.
```

---

# 25. Frontend Validation

Before Backup Now:

- device must be Active;
- driver must be assigned.

Before Save:

- valid driver;
- if scheduling is enabled, valid daily time;
- retention selected.

Before Download:

- role must be Admin;
- snapshot object must still be retained/available.

---

# 26. Frontend Security Behavior

UI hiding is not security enforcement.

Even when a Viewer cannot see Download/Backup buttons, backend authorization must independently deny those operations.

Frontend must not contain:

- Ceph access key;
- Ceph secret key;
- network-device service password;
- Zabbix API secret.

---

# 27. v2 Frontend Hooks

The v1 UI should leave room for later additions without redesigning the table architecture.

Future fields/badges may include:

```text
Encrypted
HMAC Verified
Export CSV
Export PDF
View Changes
```

Do not implement them in v1.

---

# 28. Frontend Completion Criteria

Frontend v1 is complete when:

1. real login works;
2. Admin / Viewer UI rules work;
3. real Zabbix device list renders;
4. device state is read-only;
5. real driver registry populates dropdown;
6. Admin can Save/Clear settings;
7. Admin can queue Backup Now;
8. daily schedule is configurable;
9. 31-day / Smart retention can be selected;
10. active backup job state is visible;
11. Changed / No Change is displayed;
12. archive history comes from backend;
13. Admin can download retained configuration;
14. Viewer cannot download;
15. Ceph health is shown;
16. account/user management uses backend;
17. dark mode works;
18. no demo-generated operational data remains.
