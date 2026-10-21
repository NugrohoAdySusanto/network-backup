# CHECKPOINT C22: System Audit, Observability, and Cybersecurity WAF Logging

## 1. Tujuan dan Ruang Lingkup
Checkpoint ini mengimplementasikan sistem observabilitas keamanan terpusat dan jejak audit (*audit trail*) enterprise untuk NetBackup, mencakup:
1. Pembuatan tabel basis data relasional ke-11: `system_audit_logs`.
2. Middleware inspeksi keamanan siber real-time (*Web Application Firewall* / WAF) untuk mendeteksi dan menggagalkan serangan *SQL Injection*, *Cross-Site Scripting* (XSS), dan *Path Traversal*.
3. Layanan jejak audit terstruktur (`AuditLogService`) dengan taksonomi 6 kategori lengkap: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, dan `SYSTEM`.
4. Mesin migrasi dan sinkronisasi log riwayat lampau (*historical logs backfill engine*) yang menyinkronkan seluruh riwayat pekerjaan backup, registrasi/login user, dan repositori storage ke dalam sistem audit.
5. Mesin ekspor laporan audit multi-format: format spreadsheet Excel (`.xlsx`) dan format formal PDF (*Two-Pass Canvas*) bertanda air (*watermarked*) dengan kartu KPI ringkasan.

---

## 2. Komponen Teknis yang Dibangun

### A. Skema Basis Data: `system_audit_logs` (Alembic Revision 015)
- Dibuat melalui migrasi `migrations/versions/015_system_audit_logs.py`.
- Kolom:
  - `id` (BIGINT, Primary Key, Autoincrement)
  - `created_at` (TIMESTAMPTZ, Default UTC)
  - `category` (VARCHAR(32), Indexed) — Nilai: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`.
  - `severity` (VARCHAR(16), Indexed) — Nilai: `CRITICAL`, `WARNING`, `ERROR`, `INFO`.
  - `event_type` (VARCHAR(64), Indexed) — Contoh: `SQLI_ATTEMPT`, `LOGIN_FAILED`, `STORAGE_MOUNTED`, `BACKUP_JOB_COMPLETED`.
  - `source_ip` (VARCHAR(64), Indexed)
  - `user_agent` (VARCHAR(255))
  - `user_id` (BIGINT, FK `users.id` ON DELETE SET NULL)
  - `username` (VARCHAR(128))
  - `endpoint` (VARCHAR(255))
  - `message` (TEXT, Ringkasan kejadian terstandarisasi Bahasa Inggris)
  - `details` (JSONB, Payload detail kejadian)
- Indeks filter majemuk: `ix_audit_logs_filter (created_at DESC, category, severity)`.

### B. WAF Security Inspection Middleware
- Berkas: `backend/app/core/security_middleware.py`.
- Memeriksa URL query string dan body payload untuk pola:
  - SQL Injection (`' OR 1=1`, `UNION SELECT`, `DROP TABLE`, dll.).
  - XSS (`<script>`, `javascript:`, onerror injection).
  - Path Traversal (`../`, `..\`).
- Ketika ancaman terdeteksi, request langsung digagalkan (HTTP 400/403) dan insiden dicatat ke `system_audit_logs` dengan kategori `SECURITY` dan severity `CRITICAL`.

### C. Mesin Backfill Riwayat Log
- Berkas: `backend/app/backfill_audit_logs.py` dan hook otomatis di `backend/app/api/audit_logs.py` (`_ensure_historical_logs`).
- Secara idempoten memindai seluruh record `BackupJob`, `User`, `StorageRepository`, dan `DeviceBackupSetting` untuk menjamin seluruh data riwayat masa lalu selalu tampil lengkap pada antarmuka audit log.
- Memigrasikan seluruh pesan lama ke standar Bahasa Inggris murni.

### D. Export Engine (Excel & PDF)
- Berkas: `backend/app/services/audit_export_service.py`.
- Excel: Multi-sheet OpenPyXL dengan lembar Executive KPI Summary dan lembar Detailed Incident Log dengan pewarnaan baris otomatis sesuai severity.
- PDF: ReportLab 2-pass canvas dengan running header, running footer "Page X of Y", watermark institusi, kartu statistik KPI, dan lembar verifikasi tanda tangan penguji.

---

## 3. Hasil Pengujian Otomatis
- Seluruh rangkaian uji pada `tests/unit/test_audit_logs.py` (**8/8 tests passed**):
  - `test_audit_log_create_and_query`: LULUS.
  - `test_audit_log_stats_calculation`: LULUS.
  - `test_audit_export_service_excel`: LULUS.
  - `test_audit_export_service_pdf`: LULUS.
  - `test_security_middleware_blocks_sqli`: LULUS.
  - `test_security_middleware_blocks_xss`: LULUS.
  - `test_security_middleware_blocks_path_traversal`: LULUS.
  - `test_security_middleware_passes_benign_request`: LULUS.
