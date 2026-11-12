# NetBackup — Centralized Network Configuration Backup & Security Observability

NetBackup adalah sistem enterprise untuk manajemen pencadangan (backup) konfigurasi perangkat jaringan multi-vendor secara otomatis dan terpusat. Sistem mengintegrasikan sinkronisasi inventaris perangkat dari Zabbix API, penjadwalan terdistribusi melalui Celery Worker & Beat, penyimpanan metadata pada basis data relasional PostgreSQL (**12 tabel**), koordinasi antrean dan distributed lock dengan Redis, perlindungan kriptografi terpadu **AES-256-GCM (AEAD)** (*Database Vault `NBV1`*, *Repository Manifest `NBM1`*, dan *Simplified Direct-DEK Payload `NBG2`*) pada Ceph RGW / S3-compatible storage, serta sistem pemantauan audit & inspeksi keamanan siber real-time (WAF middleware).

> [!NOTE]
> **Dokumentasi Lengkap Terpadu (Single Consolidated Master Document):**  
> Seluruh analisis perencanaan, kebutuhan produk (BRD/PRD), arsitektur modular monolith, skema basis data 12 tabel, kontrak REST API, driver contract, spesifikasi kriptografi terpadu AES-256-GCM, laporan pengujian unit test (**112/112 lulus**), runbook deployment, hingga user manual terangkum dalam satu dokumen master komprehensif:  
> 📄 **[DOKUMENTASI LENGKAP SISTEM NETBACKUP](docs/DOKUMENTASI-LENGKAP-SISTEM-NETBACKUP.md)**  
> Indeks dokumen modular per peran tetap dapat diakses pada [indeks dokumentasi](docs/README.md).

---

## Fitur Utama

- **Sinkronisasi & Monitoring Zabbix**: Auto-discovery perangkat jaringan dari Zabbix Host Group, sinkronisasi IP, port, availability status (ICMP/SNMP), serta penandaan perangkat offline.
- **Multi-Vendor Driver Engine & Dynamic Template Builder**:
  - Driver CLI bawaan untuk MikroTik RouterOS (`mikrotik-routeros`), Ruijie AP (`ruijie-ap`, dengan toleransi timeout adaptif dan negosiasi key exchange legacy `diffie-hellman-group14-sha1`, `ssh-rsa`), Ruijie Switch (`ruijie-switch`), dan Sangfor NSF/NGAF (`sangfor-nsf`).
  - Dynamic Worker Template Editor pada dashboard untuk membuat, mengedit, dan menguji driver parametrik vendor baru (misal Huawei VRP, Cisco IOS/NX-OS, HP/Aruba) secara mandiri tanpa deploy ulang kode.
- **Manajemen Backup, Deduplikasi, Discrete Scheduling & Retensi**:
  - Eksekusi backup manual (on-demand) per perangkat maupun terjadwal harian otomatis (Celery Beat).
  - **Penjadwalan Diskrit 5-Menit**: Form jadwal menggunakan dropdown waktu diskrit (Jam `00`-`23`, Menit `:00`, `:05`, s/d `:55`) dengan validasi backend modulo 5 untuk sinkronisasi presisi Celery Beat.
  - Deteksi perubahan konfigurasi (*change detection* & *diff viewer* terintegrasi).
  - Deduplikasi payload menggunakan hashing kriptografi SHA-256 untuk efisiensi penyimpanan S3.
  - Kebijakan retensi otomatis (*retention cleanup*) untuk merapikan arsip lama sesuai kuota hari/versi.
- **Audit & Keamanan Siber Real-Time (WAF Middleware & Log Monitoring)**:
  - Middleware inspeksi keamanan aktif untuk mendeteksi dan memblokir ancaman *SQL Injection* (`' UNION SELECT`), *Cross-Site Scripting* (XSS `<script>`), dan *Path Traversal* (`../`).
  - Pencatatan seluruh aktivitas administratif terpusat pada tabel `system_audit_logs` dengan 6 kategori terstandarisasi: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, dan `SYSTEM`.
  - Dilengkapi mekanisme *Automated Historical Log Backfill Engine* untuk memuat rekaman historis dari tabel operasional lain secara idempoten.
  - Setiap rekaman memiliki identifier unik terstandarisasi (`LOG-xxxxxx`), tingkat keparahan (*severity* INFO/WARNING/ERROR/CRITICAL), IP address, dan pelacakan korelasi HTTP `request_id`.
  - Pelaporan audit formal multi-format: unduh ringkasan dan rekaman log ke format **Excel (.xlsx)** dan **PDF formal 2-pass landscape (.pdf)** lengkap dengan kartu KPI, tabel kejadian, dan lembar verifikasi tanda tangan penguji/pimpinan IT.
- **Multi-Repository Storage Manager & Arsip Per-Bucket**:
  - Manajemen beberapa endpoint penyimpanan S3 (misal: klaster Ceph RGW primer dan MinIO/AWS cadangan) langsung melalui Dashboard GUI (**Storage Manager**).
  - Setiap repositori menyimpan kredensial S3 Secret Key & Master Password terenkripsi di database (**Vault `NBV1`**) serta membungkus Data Encryption Key (DEK) 256-bit ke berkas `repo_manifest.enc` di S3 (**Manifest `NBM1`**).
  - Fitur aktivasi/perpindahan repositori instan (*active repository switching*) dengan pengarsipan & pemulihan otomatis jadwal/driver perangkat per bucket (`repository_device_setting_archives`), serta scoping snapshot otomatis.
  - Verifikasi integritas tag AEAD/GMAC & hash SHA-256 dan download snapshot aman khusus administrator.
- **Arsitektur Kriptografi Terpadu AES-256-GCM (AEAD)**:
  - **Point 1 — Database Credential Vault (`vault_crypto.py`, Magic `NBV1`)**: Mengamankan S3 Secret Key dan Master Password pada PostgreSQL menggunakan PBKDF2-HMAC-SHA256 (100.000 iterasi dari `APP_SECRET`), Salt 16-byte, Nonce 12-byte, AAD 32-byte, AES-256-GCM, dan tag GMAC 16-byte (Base64URL).
  - **Point 2 — S3 Repository Manifest Envelope (`manifest_crypto.py`, Magic `NBM1`)**: Membungkus DEK 256-bit acak di dalam `repo_manifest.enc` dengan KEK PBKDF2-HMAC-SHA256 (100.000 iterasi dari Master Password), AES-256-GCM, dan AAD 32-byte. Rotasi Master Password hanya membungkus ulang manifest tanpa mengenkripsi ulang seluruh objek backup.
  - **Point 3 — Simplified Direct-DEK At-Rest Payload (`payload_crypto.py`, Magic `NBG2`)**: Kompresi `zlib Deflate` level 6 (magic `NBZ1`) diikuti enkripsi **AES-256-GCM** langsung memakai DEK 256-bit tanpa PBKDF2/Salt di level payload (header ringkas 16-byte `b"NBG2" || Nonce(12B)` sebagai AAD + tag GMAC 16-byte, dengan akselerasi hardware AES-NI dan mode *Fail-Closed* murni tanpa kode fallback legacy CBC/NBG1).
  - Visualisasi teknis dan simulator Web Crypto API interaktif tersedia pada rute [`/crypto-animation.html`](frontend/crypto-animation.html).
- **Role-Based Access Control (RBAC) & Manajemen Pengguna**:
  - Pemisahan hak akses antara `admin` (kontrol penuh sistem, manajemen user, konfigurasi driver, aktivasi storage) dan `viewer` (hak lihat, eksekusi backup, inspeksi snapshot).
  - Fitur ganti password mandiri serta alur *Forgot Password* aman dengan token pemulihan berbasis waktu via email SMTP.
- **Antarmuka Web Modern**:
  - Tampilan operasional terstandarisasi Bahasa Inggris untuk konsistensi log, badge, dan status.
  - Live Search perangkat instan responsif, kartu status Zabbix Sync/Not-Sync, visibilitas dinamis Ceph Cluster Health, serta modal peringatan Session Inactivity Timeout.
  - Pilihan tema Light / Dark mode terkalibrasi kontras tinggi serta sticky table header solid anti-overlap saat data log/arsip di-scroll.

---

## Arsitektur Sistem

```mermaid
flowchart TB
    subgraph Client["Pengguna & Klien"]
        Browser["Web Browser (Admin / Viewer)"]
    end

    subgraph Edge["Reverse Proxy & Gateway"]
        Nginx["Nginx Reverse Proxy (:8080 default / NGINX_PORT)"]
    end

    subgraph App["Backend Core (FastAPI)"]
        WAF["Security Inspection Middleware (SQLi / XSS / Traversal)"]
        Auth["Auth & RBAC Service (Session, CSRF, Token)"]
        AuditService["Audit Log & Security Service"]
        ExportService["Multi-Format Export Engine (Excel & PDF)"]
        APIRoutes["REST API Endpoints (/api/v1)"]
    end

    subgraph Workers["Distributed Task Processing"]
        Redis["Redis (Broker & Coordination)"]
        CeleryWorker["Celery Worker (SSH / Netmiko Driver)"]
        CeleryBeat["Celery Beat (Periodic Scheduler)"]
    end

    subgraph Persistence["Storage & Database"]
        Postgres[("PostgreSQL 16 (12 Tables Schema)")]
        CephS3[("Ceph RGW / S3 Storage (Encrypted NBG2 / NBM1)")]
    end

    subgraph External["Layanan Eksternal & Infrastruktur"]
        Zabbix["Zabbix Server (Host Inventory API)"]
        Devices["Network Devices (MikroTik, Ruijie, Sangfor, Custom CLI)"]
        SMTP["SMTP Mail Server (Password Recovery)"]
    end

    Browser -->|HTTPS / HTTP| Nginx
    Nginx -->|Static Assets| Browser
    Nginx -->|Reverse Proxy /api/| WAF
    WAF --> Auth
    Auth --> APIRoutes
    APIRoutes --> AuditService
    AuditService --> Postgres
    APIRoutes --> ExportService
    APIRoutes --> Postgres
    APIRoutes --> Redis
    APIRoutes --> Zabbix
    APIRoutes --> CephS3
    Auth -.->|Reset Email| SMTP

    CeleryBeat -->|Schedule Tasks| Redis
    Redis -->|Dispatch Jobs| CeleryWorker
    CeleryWorker -->|Fetch Credentials| Postgres
    CeleryWorker -->|SSH / CLI Backup| Devices
    CeleryWorker -->|Upload Encrypted Payload| CephS3
    CeleryWorker -->|Save Snapshot & Logs| Postgres
```

---

## Skema Basis Data (12 Tabel)

Aplikasi menggunakan skema relasional terstruktur (12 tabel ORM / migrasi Alembic `001` s/d `016`, dengan verifikasi kontrak startup pada 11 tabel inti di `backend/app/main.py`):

| No | Nama Tabel | Deskripsi & Tanggung Jawab |
|:--:|---|---|
| 1 | `users` | Akun pengguna sistem dengan kredensial hash Argon2id, email pemulihan, status aktif, dan peran RBAC (`admin`/`viewer`). |
| 2 | `devices` | Data inventaris perangkat jaringan (IP, vendor, port, status Zabbix, penanda `source_present`). |
| 3 | `device_backup_settings` | Pengaturan backup perangkat: driver key, jadwal harian diskrit 5-menit (`HH:MM`), status aktif, dan kebijakan retensi. |
| 4 | `backup_jobs` | Catatan eksekusi tugas backup (state machine `QUEUED` s/d terminal, durasi, trigger manual/scheduled, diagnostics). |
| 5 | `storage_repositories` | Konfigurasi endpoint Ceph S3 / MinIO, bucket, kredensial & master key terenkripsi (**Vault `NBV1`** AES-256-GCM), `repo_manifest`, dan penanda repositori aktif tunggal. |
| 6 | `config_objects` | Objek konfigurasi terkompresi (`NBZ1`) & terenkripsi (**Direct-DEK AES-256-GCM AEAD `NBG2`**) pada S3 dengan deduplikasi hash SHA-256. |
| 7 | `snapshots` | Metadata versi backup logis tersimpan per perangkat (display filename, timestamp, retention status, `config_object_id`). |
| 8 | `snapshot_retention_marks` | Penanda status retensi snapshot (`STANDARD_WINDOW`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `LATEST_GOOD`) untuk rotasi GFS. |
| 9 | `custom_drivers` | Driver kustom vendor perangkat jaringan berbasis engine parametrik CLI (command sequence, paging bypass, validation regex). |
| 10 | `integration_status` | Status sinkronisasi dan health check integrasi eksternal (Zabbix API, Ceph Health, SMTP). |
| 11 | `system_audit_logs` | Audit trail terpusat & log keamanan WAF (6 kategori: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`), severity, source IP, dan `request_id`. |
| 12 | `repository_device_setting_archives` | Arsip pengaturan backup perangkat (`driver_key`, jadwal, retensi) per nama bucket S3 untuk restorasi otomatis saat switch/reconnect repositori. |

---

## Prasyarat Sistem

1. **Docker Engine** (versi 24.0+) dan **Docker Compose v2** (versi 2.20+).
2. Akses jaringan ke:
   - Klaster Ceph Object Gateway (RGW) atau MinIO S3-compatible storage.
   - Server Zabbix (API token dengan hak baca host group network).
   - Perangkat jaringan target (protokol SSH port 22).
   - Server SMTP (bila fitur pemulihan password diaktifkan).
3. Sertifikat CA internal S3 pada `backend/ceph-s3.crt` (apabila endpoint S3 menggunakan HTTPS private CA).
4. Berkas `known_hosts` yang valid (apabila *strict host key checking* diaktifkan).

---

## Konfigurasi Lingkungan (.env)

Salin berkas template konfigurasi:

```bash
cp .env.example .env
```

Pastikan variabel-variabel kunci pada `.env` (mengacu ke `.env.example`) terisi sebelum menjalankan aplikasi:

```ini
# Application Core
APP_NAME=Network Backup Dashboard
APP_ENV=development
APP_TIMEZONE=Asia/Jakarta
APP_SECRET=replace-with-a-long-random-secret
APP_BASE_URL=http://localhost:8080
NGINX_PORT=8080

# Database PostgreSQL
POSTGRES_DB=network_backup
POSTGRES_USER=network_backup
POSTGRES_PASSWORD=replace-me
DATABASE_URL=postgresql+psycopg://network_backup:replace-me@postgres:5432/network_backup

# Redis Broker & Server-Side Session
REDIS_URL=redis://redis:6379/0
SESSION_REDIS_URL=redis://redis:6379/1

# Zabbix Integration
ZABBIX_URL=https://zabbix.example.internal
ZABBIX_API_TOKEN=replace-me
ZABBIX_NETWORK_GROUP_ID=replace-me

# Network Device SSH Service Account (Shared Read-Only Credential)
NETWORK_SSH_USERNAME=netbackup-ro
NETWORK_SSH_PASSWORD=replace-me
NETWORK_SSH_ENABLE_PASSWORD=replace-me
SSH_STRICT_HOST_KEY_CHECKING=true

# Ceph RGW / S3 Fallback Env (Utamanya dikelola dinamis via Dashboard GUI Storage Manager + Vault DB)
S3_ENDPOINT=https://ceph-rgw.example.internal:7443
S3_BUCKET=network-config-backup
S3_ACCESS_KEY=replace-me
S3_SECRET_KEY=replace-me
S3_SECURE=true

# Ceph Cluster Health & Alerts
CEPH_HEALTH_URL=https://ceph-manager.example.internal
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/replace-me

# SMTP Settings (Optional - Password Recovery)
SMTP_HOST=smtp.example.internal
SMTP_PORT=465
SMTP_USER=replace-me
SMTP_PASSWORD=replace-me
SMTP_USE_SSL=true
SMTP_FROM_EMAIL=no-reply@example.internal
```

> [!NOTE]
> Konfigurasi repositori S3 (endpoint, bucket, access/secret key terenkripsi Vault `NBV1`, serta inisialisasi Master Password / manifes `NBM1`) dalam operasional utama dikelola langsung melalui antarmuka **Storage Manager** pada dashboard dan disimpan di tabel `storage_repositories`.

> [!WARNING]
> Berkas `.env` berisi rahasia autentikasi dan kredensial infrastruktur nyata. **Jangan pernah mengunggah (.commit) berkas `.env` ke repositori git publik.**

---

## Menjalankan Aplikasi

Jalankan seluruh stack kontainer dengan Docker Compose:

```bash
# Build dan jalankan seluruh service di latar belakang
docker compose up -d --build

# Periksa status seluruh kontainer
docker compose ps

# Periksa log service migrator untuk memastikan migrasi database sukses
docker compose logs migrator
```

Service `migrator` akan menjalankan `alembic upgrade head` secara otomatis sebelum kontainer `api`, `worker`, dan `beat` beroperasi.

### URL Akses

- **Akses Lokal / Intranet**: `http://<IP-Host>:<NGINX_PORT>` (default `8080`)
- **Domain Produksi**: `https://netbackup.makuku.co.id`

### Verifikasi Kesehatan (Health Check)

```bash
curl --fail http://localhost:8080/healthz
# atau melalui domain:
curl --fail https://netbackup.makuku.co.id/healthz
```

Respons JSON yang diharapkan:
```json
{"status": "ok", "service": "Network Backup Dashboard", "environment": "development"}
```

---

## Inisialisasi Akun Pengguna (Bootstrap)

Untuk membuat akun administrator pertama kali secara aman:

1. Aktifkan konfigurasi bootstrap sementara pada `.env`:
   ```ini
   BOOTSTRAP_USERS_ENABLED=true
   BOOTSTRAP_ADMIN_PASSWORD=PasswordKuatAdmin123!
   BOOTSTRAP_VIEWER_PASSWORD=PasswordKuatViewer123!
   ```
2. Jalankan perintah bootstrap CLI:
   ```bash
   docker compose run --rm api python -m app.cli.bootstrap_users
   ```
3. Setelah akun berhasil dibuat, ubah kembali `BOOTSTRAP_USERS_ENABLED=false` dan hapus password bootstrap dari `.env`.

---

## Pengujian Otomatis (Automated Testing)

Aplikasi dilengkapi pengujian unit dan integrasi komprehensif yang mencakup skenario keamanan, alur backup, driver, enkripsi, dan pelaporan:

```bash
# Menjalankan pengujian unit suite pada direktori tests/:
PYTHONPATH=backend /opt/network-backup/venv/bin/python -m pytest tests/ -v

# Atau secara ringkas:
PYTHONPATH=backend /opt/network-backup/venv/bin/python -m pytest tests/ -q
```

**Status Pengujian Terkini:**
```text
112 passed in 9.12s
```
- Total test cases (`tests/unit/`): **112 passed, 0 failed** (100% lulus).
- Cakupan pengujian:
  - Autentikasi Argon2id, session cookie (`nb_session`), CSRF, dan manajemen hak akses RBAC.
  - Kriptografi terpadu AES-256-GCM AEAD: Vault (`NBV1`), Manifest KEK/DEK (`NBM1`), dan Simplified Direct-DEK Payload (`NBG2` + kompresi zlib `NBZ1`), termasuk penolakan *bit-flipping* AAD/ciphertext/tag (*Fail-Closed*).
  - Mitigasi keamanan WAF: Pemblokiran SQLi, XSS, dan Path Traversal.
  - Driver CLI parsing, timeout handling, paging bypass, availability checking, dan Ruijie AP SSH hardening.
  - Multi-export generation: Validasi struktur format Excel (`.xlsx`) dan ReportLab PDF (`.pdf`) 2-pass landscape.
  - Audit & Security Logs: Validasi 6 kategori (`STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`) dan automated idempotent backfill.

---

## Struktur Direktori Repositori

```text
/opt/network-backup/
├── backend/                  # Kode sumber backend FastAPI
│   ├── app/
│   │   ├── api/              # Controller REST API (auth, devices, logs, storage, jobs, snapshots, drivers, reports, users)
│   │   ├── cli/              # Skrip CLI administratif (bootstrap_users)
│   │   ├── core/             # Auth session, CSRF, WAF security_middleware, error taxonomy, state machine, lock
│   │   ├── crypto/           # Paket kriptografi AES-256-GCM (vault_crypto, manifest_crypto, payload_crypto, kdf)
│   │   ├── drivers/          # Driver perangkat jaringan (mikrotik_routeros, ruijie_ap, ruijie_switch, sangfor_nsf, parametric)
│   │   ├── integrations/     # Klien eksternal (Zabbix API, Ceph Health, Feishu webhook)
│   │   ├── models/           # Definisi model SQLAlchemy ORM (12 tabel)
│   │   ├── repositories/     # Query & akses database
│   │   ├── schemas/          # Schema validasi Pydantic
│   │   ├── services/         # Business logic layer (backup, audit, S3, retention, export, storage_repository)
│   │   └── tasks/            # Background tasks Celery (backup execution, retention cleanup, zabbix sync)
│   ├── ceph-s3.crt           # Sertifikat SSL CA S3 Object Storage
│   └── Dockerfile            # Kontainer build backend
├── frontend/                 # Web client dashboard statis (Vanilla JS + Tailwind CSS)
│   ├── css/                  # Stylesheet kustom & tema
│   ├── js/                   # Modul logika antarmuka (api, auth, devices, schedules, archives, storage, audit_logs, workers, reports, users, theme)
│   ├── index.html            # Dashboard operasional utama
│   └── crypto-animation.html # Visualisasi & simulator interaktif pipeline AES-256-GCM (NBG2)
├── migrations/               # Skrip migrasi skema basis data Alembic (001 s/d 016)
├── nginx/                    # Konfigurasi reverse proxy Nginx
├── tests/                    # Rangkaian pengujian otomatis pytest (tests/unit/)
├── docs/                     # Dokumentasi perencanaan, arsitektur, runbook, dan pengujian
├── docker-compose.yml        # Definisi orkestrasi kontainer aplikasi
├── alembic.ini               # Konfigurasi migration engine
├── .env.example              # Template konfigurasi environment variables
└── README.md                 # Dokumentasi ringkas sistem
```

---

## Rujukan Dokumentasi

Dokumentasi teknis terperinci dapat dipelajari pada berkas-berkas berikut:
- **[Dokumentasi Lengkap Sistem NetBackup (Master Terpadu v2.0)](docs/DOKUMENTASI-LENGKAP-SISTEM-NETBACKUP.md)**
- [Spesifikasi Enkripsi & Integritas Payload S3](docs/03-design/enkripsi-backup-s3.md)
- [Kontrak REST API Backend](docs/02-architecture/API-CONTRACT-v1.0.md)
- [Arsitektur Basis Data & Relasi ERD](docs/02-architecture/DATABASE-SCHEMA-ERD-v1.0.md)
- [Kontrak & Spesifikasi Driver Perangkat](docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md)
- [Runbook Pengoperasian & Pemeliharaan Sistem](docs/05-operations/runbook.md)
- [Buku Manual Pengguna & FAQ Operasional](docs/05-operations/manual-faq.md)
