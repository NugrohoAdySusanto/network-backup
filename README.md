# NetBackup — Centralized Network Configuration Backup & Security Observability

NetBackup adalah sistem enterprise untuk manajemen pencadangan (backup) konfigurasi perangkat jaringan multi-vendor secara otomatis dan terpusat. Sistem mengintegrasikan sinkronisasi inventaris perangkat dari Zabbix API, penjadwalan terdistribusi melalui Celery Worker & Beat, penyimpanan metadata pada basis data relasional PostgreSQL (11 tabel), koordinasi antrean dan distributed lock dengan Redis, perlindungan kriptografi payload berstandar militer (AES-256-CBC + HMAC-SHA256 Encrypt-then-MAC) pada Ceph RGW / S3-compatible storage, serta sistem pemantauan audit & inspeksi keamanan siber real-time (WAF middleware).

> [!NOTE]
> **Dokumentasi Lengkap Terpadu (Single Consolidated Master Document v2.0):**  
> Seluruh analisis perencanaan, kebutuhan produk (BRD/PRD), arsitektur modular monolith, skema basis data 11 tabel, kontrak REST API, driver contract, spesifikasi kriptografi payload S3, laporan pengujian unit test (**116/116 lulus**), runbook deployment, hingga user manual terangkum dalam satu dokumen master komprehensif:  
> 📄 **[DOKUMENTASI LENGKAP SISTEM NETBACKUP (v2.0)](docs/DOKUMENTASI-LENGKAP-SISTEM-NETBACKUP.md)**  
> Indeks dokumen modular per peran tetap dapat diakses pada [indeks dokumentasi](docs/README.md).

---

## Fitur Utama

- **Sinkronisasi & Monitoring Zabbix**: Auto-discovery perangkat jaringan dari Zabbix Host Group, sinkronisasi IP, port, availability status (ICMP/SNMP), serta penandaan perangkat offline.
- **Multi-Vendor Driver Engine & Dynamic Template Builder**:
  - Driver CLI bawaan dan parametrik untuk Huawei (VRP), Cisco (IOS & NX-OS), HP / Aruba (ProCurve), Fortinet (FortiOS CLI), Sangfor (NGAF CLI), dan Ruijie AP (hardened SSH timeout tolerance & legacy key exchange negotiation `diffie-hellman-group14-sha1`, `ssh-rsa`).
  - Dynamic Worker Template Editor pada dashboard untuk membuat, mengedit, dan menguji driver vendor baru secara mandiri tanpa deploy ulang kode.
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
- **Multi-Repository Storage Manager**:
  - Manajemen beberapa endpoint penyimpanan S3 (misal: klaster Ceph RGW primer dan MinIO/AWS cadangan).
  - Fitur aktivasi repository instan (*active repository switching*) dengan scoping snapshot otomatis.
  - Verifikasi integritas hash dan download snapshot aman oleh akun berpangkat administrator.
- **Kriptografi Payload Kuat (Encrypt-then-MAC)**:
  - Kompresi data konfigurasi dengan `zlib Deflate`.
  - Enkripsi simetris `AES-256-CBC` menggunakan kunci yang diturunkan via `PBKDF2` (HMAC-SHA256, 100.000 iterasi).
  - Perlindungan keaslian dan integritas pesan `HMAC-SHA256` di atas ciphertext untuk mencegah *Padding Oracle Attack*.
  - Visualisasi teknis alur kriptografi interaktif tersedia pada rute [`/crypto-animation.html`](frontend/crypto-animation.html).
- **Role-Based Access Control (RBAC) & Manajemen Pengguna**:
  - Pemisahan hak akses antara `admin` (kontrol penuh sistem, manajemen user, konfigurasi driver, aktivasi storage) dan `viewer` (hak lihat, eksekusi backup, inspeksi snapshot).
  - Fitur ganti password mandiri serta alur *Forgot Password* aman dengan token pemulihan berbasis waktu via email SMTP.
- **Antarmuka Web Modern (Full English)**:
  - Tampilan web terstandarisasi 100% Bahasa Inggris tanpa percampuran bahasa.
  - Pilihan tema Light / Dark mode terkalibrasi kontras tinggi.
  - Sticky table header solid (`.bg-surface`) anti-overlap saat data log/arsip di-scroll.

---

## Arsitektur Sistem

```mermaid
flowchart TB
    subgraph Client["Pengguna & Klien"]
        Browser["Web Browser (Admin / Viewer)"]
    end

    subgraph Edge["Reverse Proxy & Gateway"]
        Nginx["Nginx Reverse Proxy (:8081)"]
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
        Postgres[("PostgreSQL 16 (11 Tables Schema)")]
        CephS3[("Ceph RGW / S3 Storage (Encrypted Payloads)")]
    end

    subgraph External["Layanan Eksternal & Infrastruktur"]
        Zabbix["Zabbix Server (Host Inventory API)"]
        Devices["Network Devices (Huawei, Cisco, Aruba, Fortinet, Sangfor)"]
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

## Skema Basis Data (11 Tabel)

Aplikasi menggunakan skema relasional terstruktur yang dikelola melalui migrasi otomatis Alembic:

| No | Nama Tabel | Deskripsi & Tanggung Jawab |
|:--:|---|---|
| 1 | `users` | Akun pengguna sistem dengan kredensial hash argon2/bcrypt, status aktif/terkunci, dan peran RBAC (`admin`/`viewer`). |
| 2 | `devices` | Data inventaris perangkat jaringan (IP, vendor, port, status Zabbix, kredensial SSH terenkripsi). |
| 3 | `device_backup_settings` | Pengaturan backup perangkat: jadwal harian diskrit 5-menit (HH:MM), status aktif, dan retensi hari. |
| 4 | `backup_jobs` | Catatan eksekusi tugas backup (status SUCCESS, FAILED, RUNNING, durasi, trigger manual/scheduled). |
| 5 | `storage_repositories` | Konfigurasi endpoint Ceph S3 / MinIO, bucket, region, kredensial terenkripsi, dan penanda repositori aktif tunggal. |
| 6 | `config_objects` | Payload konfigurasi backup terenkripsi (AES-256-CBC + HMAC-SHA256) pada S3 dengan deduplikasi hash SHA-256. |
| 7 | `snapshots` | Metadata versi backup tersimpan per perangkat (S3 key, size, timestamp, verification status, integrity mark). |
| 8 | `snapshot_retention_marks` | Penanda status retensi snapshot (KEEP / PURGE candidate) untuk rotasi siklus backup otomatis. |
| 9 | `custom_drivers` | Driver kustom vendor perangkat jaringan berbasis modul Python dinamis (command sequence, pager bypass, error regex). |
| 10 | `integration_status` | Status sinkronisasi dan health check integrasi eksternal (Zabbix API, Ceph S3, SMTP). |
| 11 | `system_audit_logs` | Audit trail terpusat & log keamanan WAF (6 kategori: STORAGE, AUTH, SECURITY, AUDIT, BACKUP_JOB, SYSTEM), severity, IP, dan HTTP request_id. |

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

Pastikan variabel-variabel kunci berikut terisi sebelum menjalankan aplikasi:

```ini
# Application Core
APP_SECRET=generate_rahasia_string_acak_minimal_32_karakter
APP_BASE_URL=https://netbackup.makuku.co.id
NGINX_PORT=8081

# Database PostgreSQL
POSTGRES_DB=netbackup
POSTGRES_USER=netbackup_user
POSTGRES_PASSWORD=password_database_anda
DATABASE_URL=postgresql://netbackup_user:password_database_anda@postgres:5432/netbackup

# Redis Broker
REDIS_URL=redis://redis:6379/0

# Zabbix Integration
ZABBIX_URL=http://zabbix.internal/api_jsonrpc.php
ZABBIX_API_TOKEN=token_api_zabbix_anda
ZABBIX_NETWORK_GROUP_ID=15

# Default Device Connection Credentials
NETWORK_DEFAULT_USERNAME=backup_svc
NETWORK_DEFAULT_PASSWORD=password_ssh_perangkat
NETWORK_DEFAULT_ENABLE_PASSWORD=password_enable_bila_ada

# Ceph RGW / S3 Storage
S3_ENDPOINT=https://s3-ceph.internal:8443
S3_BUCKET=netbackup-vault
S3_ACCESS_KEY=access_key_s3
S3_SECRET_KEY=secret_key_s3
S3_REGION=us-east-1

# SMTP Settings (Optional - Password Recovery)
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@makuku.co.id
SMTP_PASSWORD=password_smtp
SMTP_FROM=netbackup-noreply@makuku.co.id
```

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

- **Akses Lokal / Intranet**: `http://<IP-Host>:8081`
- **Domain Produksi**: `https://netbackup.makuku.co.id`

### Verifikasi Kesehatan (Health Check)

```bash
curl --fail http://localhost:8081/healthz
# atau melalui domain:
curl --fail https://netbackup.makuku.co.id/healthz
```

Respons JSON yang diharapkan:
```json
{"status": "ok", "app": "NetBackup", "version": "2.0.0"}
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
# Menjalankan pengujian melalui virtual environment lokal:
/opt/network-backup/venv/bin/python -m pytest -v

# Atau secara ringkas:
/opt/network-backup/venv/bin/python -m pytest -q
```

**Status Pengujian Terkini:**
```text
============================== 116 passed in 17.50s ==============================
```
- Total test cases: **116 passed, 0 failed** (100% lulus).
- Cakupan pengujian:
  - Autentikasi, session cookie, CSRF, dan manajemen hak akses RBAC.
  - Kompresi Deflate, enkripsi AES-256-CBC, PBKDF2 KDF, dan verifikasi HMAC-SHA256.
  - Mitigasi keamanan WAF: Pemblokiran SQLi, XSS, dan Path Traversal.
  - Driver CLI parsing, timeout handling, paging bypass, availability checking, dan Ruijie AP SSH hardening.
  - Multi-export generation: Validasi struktur format Excel (`.xlsx`) dan ReportLab PDF (`.pdf`) 2-pass landscape.
  - Audit & Security Logs: Validasi skema tabel ke-11, pencatatan 6 kategori (`STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`), dan automated idempotent backfill.

---

## Struktur Direktori Repositori

```text
/opt/network-backup/
├── backend/                  # Kode sumber backend FastAPI
│   ├── app/
│   │   ├── api/              # Controller REST API (auth, devices, logs, storage, jobs, workers)
│   │   ├── cli/              # Skrip CLI administratif (bootstrap_users)
│   │   ├── crypto/           # Implementasi kriptografi (AES-256-CBC, HMAC, PBKDF2)
│   │   ├── drivers/          # Driver perangkat jaringan (SSH/Telnet multi-vendor)
│   │   ├── middleware/       # WAF Security inspection & audit middleware
│   │   ├── models/           # Definisi model SQLAlchemy ORM (11 tabel)
│   │   ├── schemas/          # Schema validasi Pydantic
│   │   ├── services/         # Business logic layer (backup, audit, S3, retention, export)
│   │   └── tasks/            # Background tasks Celery (backup execution, retention cleanup)
│   ├── ceph-s3.crt           # Sertifikat SSL CA S3 Object Storage
│   └── Dockerfile            # Kontainer build backend
├── frontend/                 # Web client dashboard statis (Vanilla JS + Tailwind CSS)
│   ├── css/                  # Stylesheet kustom & tema
│   ├── js/                   # Modul logika antarmuka (api, auth, devices, audit_logs, storage, dll)
│   ├── index.html            # Dashboard operasional utama
│   └── crypto-animation.html # Visualisasi alur enkripsi & HMAC interaktif
├── migrations/               # Skrip migrasi skema basis data Alembic (001 s/d 015)
├── nginx/                    # Konfigurasi reverse proxy Nginx
├── tests/                    # Rangkaian pengujian otomatis pytest (unit & integration)
├── docs/                     # Dokumentasi perencanaan, arsitektur, runbook, dan pengujian
├── docker-compose.yml        # Definisi orkestrasi kontainer aplikasi
├── alembic.ini               # Konfigurasi migration engine
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
