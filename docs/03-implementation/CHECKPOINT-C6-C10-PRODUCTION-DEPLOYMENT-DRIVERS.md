# Checkpoint C6-C10 — Production Deployment & Multivendor Drivers

**Date:** 2026-10-04  
**Status:** Completed & Verified in Production  

---

## 1. Summary of Completed Components

This checkpoint covers the full production deployment, multivendor backup driver implementation, Ceph S3 storage deduplication, Celery Beat automated scheduling, and Web UI integration.

---

## 2. Implemented Drivers (`app/drivers/`)

### 2.1 MikroTik RouterOS (`mikrotik-routeros`)
- **Key:** `mikrotik-routeros`
- **Label:** `Mikrotik RouterOS Driver`
- **Port:** 22
- **Command:** `/export compact`
- **Output Extension:** `.rsc`
- **Normalization:** Strips volatile timestamps (e.g. `# oct/04/2026 17:19:39 by RouterOS`).
- **Target Tested:** MikroTik CCR1016-12G (`10.11.0.2`). Verified successful backup & download.

### 2.2 Ruijie AP (`ruijie-ap`)
- **Key:** `ruijie-ap`
- **Label:** `Ruijie AP Driver`
- **Port:** 22345
- **Transport:** Netmiko (`device_type: "ruijie_os"`) with legacy `ssh-rsa` host key support (SHA-1 signature enabled in Paramiko Transport).
- **Export Command:** `show running-config`
- **Output Extension:** `.text`
- **Filename:** `config.text` (Mandatory: Ruijie AP firmware requires this exact filename for import/restore).
- **Normalization:** Strips `Building configuration...`, `Current configuration: \d+ bytes`, `! Time: ...`, trailing prompt `MKK-HQ_AP-01#`, and trailing whitespace.
- **Target Tested:** `MKK-HQ_AP-01` (`10.11.1.228`, model AP850-AR(V3)). Verified successful backup & download.

### 2.3 Ruijie Switch (`ruijie-switch`)
- **Key:** `ruijie-switch`
- **Label:** `Ruijie Switch Driver`
- **Port:** 22345
- **Export Command:** `show running-config`
- **Output Extension:** `.cfg`

### 2.4 Sangfor Firewall (`sangfor-nsf`)
- **Key:** `sangfor-nsf`
- **Label:** `Sangfor NSF Driver`
- **Port:** 22
- **Output Extension:** `.conf`

---

## 3. Storage & Deduplication Architecture

1. **Dual-Layer SHA-256:**
   - `object_sha256`: Hash of raw binary bytes collected from the device, stored in `config_objects.object_sha256` for physical Ceph S3 integrity verification.
   - `content_sha256`: Hash of normalized text, used for change detection (`baseline`, `changed`, `no_change`) and Content-Addressable Storage (CAS) deduplication in Ceph S3.
2. **Download Integrity:**
   - Endpoint: `GET /api/v1/snapshots/{id}/download`.
   - Streaming directly from Ceph S3 with SHA-256 checksum verification before delivery.
   - Sends `Content-Disposition: attachment; filename="{display_filename}"` and header `X-Content-SHA256`.

---

## 4. Scheduler & Dashboard Metrics

1. **Celery Beat Dispatcher (`scheduler_tasks.py`):**
   - Runs `dispatch_due_backups` every 60 seconds.
   - Queries `device_backup_settings` where `schedule_enabled = True` and `next_run_at <= now()`.
   - Dispatches Celery task `network_backup.execute_backup` and calculates next daily run.
2. **Dashboard Summary (`dashboard.py`):**
   - Timezone-aware calculation based on `settings.app_timezone` (`Asia/Jakarta`).
   - Counts successful backups today across active/scheduled devices for both manual and automated backups.
