# Indeks Dokumentasi NetBackup

Dokumentasi ini menjelaskan keadaan aplikasi yang tercermin pada kode di branch aktif. Jika terdapat perbedaan antara dokumen dan kode, kode menjadi sumber kebenaran dan dokumen harus diperbaiki.

> [!TIP]
> **Dokumentasi Tunggal Terpadu (Master Consolidated Document):**  
> Bagi pembaca, penguji, atau dosen penilai yang memerlukan **satu dokumen komprehensif** yang menggabungkan seluruh aspek (Plan, Product, Architecture, Requirements, Database ERD aktual 12 tabel, API Contract, Driver Contract, Spesifikasi Kriptografi Terpadu AES-256-GCM, Implementation Checkpoints C01-C25, Testing QA 112/112, Runbook Deployment, hingga Manual Pengguna & FAQ), silakan membuka:  
> 📄 **[DOKUMENTASI LENGKAP SISTEM NETBACKUP](DOKUMENTASI-LENGKAP-SISTEM-NETBACKUP.md)**  
> Seluruh diagram dan tabel dalam dokumen master tersebut telah diaudit dan disinkronkan dengan kode sumber aplikasi.

## Pilih dokumen berdasarkan peran

| Kamu siapa | Mulai dari | Lanjutkan ke |
|---|---|---|
| Manajemen, klien, atau Project Manager | [Project Charter](01-planning/project-charter.md) | [Proposal Proyek](01-planning/proposal-proyek.md) |
| Product Manager atau Business Analyst | [BRD](02-requirements/brd.md) | [PRD](01-product/FEATURE-FINAL.md) |
| Software Engineer atau Data Architect | [TDD](02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md) | [Arsitektur Database dan ERD](02-architecture/DATABASE-SCHEMA-ERD-v1.0.md), [Kontrak API](02-architecture/API-CONTRACT-v1.0.md), [Kontrak Driver](02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md), [Dependency](03-design/dependencies.md) |
| Engineer atau reviewer keamanan | [Enkripsi Backup S3](03-design/enkripsi-backup-s3.md) | [Test Script](04-testing/test-script.md) |
| UI/UX Designer atau Frontend Engineer | [Spesifikasi UI](01-product/DESIGN-FINAL.md) | [PRD](01-product/FEATURE-FINAL.md) |
| QA Engineer atau Tester | [Test Script](04-testing/test-script.md) | [Template Berita Acara UAT](04-testing/berita-acara-uat.md) |
| DevOps atau Tim Support | [Runbook](05-operations/runbook.md) | [README proyek](../README.md) |
| Pengguna akhir | [Manual dan FAQ](05-operations/manual-faq.md) | [README proyek](../README.md) |

## Daftar dokumen aktif

### Overview dan planning

- [Project Charter](01-planning/project-charter.md)
- [Proposal Proyek](01-planning/proposal-proyek.md)

### Requirements

- [Business Requirements Document](02-requirements/brd.md)
- [Product Requirements Document](01-product/FEATURE-FINAL.md)

### Desain dan arsitektur

- [Technical Design Document](02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md)
- [Arsitektur dan Skema Database](02-architecture/DATABASE-SCHEMA-ERD-v1.0.md)
- [Spesifikasi Enkripsi Backup S3](03-design/enkripsi-backup-s3.md)
- [Rumus dan Perhitungan Enkripsi S3](03-design/rumus-perhitungan-enkripsi-s3.md)
- [Kontrak REST API](02-architecture/API-CONTRACT-v1.0.md)
- [Kontrak Backup Driver](02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md)
- [Spesifikasi UI](01-product/DESIGN-FINAL.md)
- [Dependency dan Runtime](03-design/dependencies.md)

### Pengujian

- [Test Script](04-testing/test-script.md)
- [Template Berita Acara UAT](04-testing/berita-acara-uat.md)

### Rilis dan operasional

- [Runbook](05-operations/runbook.md)
- [Buku Manual dan FAQ](05-operations/manual-faq.md)

### Dokumen pendukung yang dipertahankan

- Checkpoint implementasi pada [`03-implementation/`](03-implementation/) (termasuk [C22: System Audit & Security Logs](03-implementation/CHECKPOINT-C22-SYSTEM-AUDIT-AND-SECURITY-LOGS.md), [C23: Schedule Enforcement & Driver Hardening](03-implementation/CHECKPOINT-C23-SCHEDULE-ENFORCEMENT-AND-DRIVER-HARDENING.md), [C24: S3 Lifecycle & UI/UX Modernization](03-implementation/CHECKPOINT-C24-UI-UX-REFINEMENT-AND-S3-LIFECYCLE.md), dan [C25: AES-256-GCM AEAD Modernization](03-implementation/CHECKPOINT-C25-AES-256-GCM-AEAD-PAYLOAD-ENCRYPTION.md))
- Mockup referensi pada [`04-reference/`](04-reference/)

Dokumen pendukung tidak dihapus. Jika isinya berbeda dari dokumen arsitektur utama, gunakan dokumen arsitektur utama dan source code sebagai acuan implementasi terkini.

## Aturan pemeliharaan

1. [Enkripsi Backup S3](03-design/enkripsi-backup-s3.md) adalah sumber kanonis algoritma, ukuran field, derivasi kunci, dan format file. Ringkasan atau visualisasi di tempat lain harus konsisten dan menautkan ke dokumen tersebut.
2. Perubahan model atau migrasi harus diikuti pembaruan [Arsitektur Database](02-architecture/DATABASE-SCHEMA-ERD-v1.0.md).
3. Perubahan route, request, response, atau kode error harus diikuti pembaruan [Kontrak API](02-architecture/API-CONTRACT-v1.0.md).
4. Requirement baru harus memiliki ID dan minimal satu test case terkait.
5. Jangan menaruh password, key, token, nama bucket sensitif, atau kredensial nyata di dokumentasi.
6. Hasil UAT, tanggal, penanggung jawab, dan tanda tangan hanya boleh diisi oleh pihak yang berwenang.

## Sumber kebenaran teknis

| Area | Sumber kode |
|---|---|
| Konfigurasi aplikasi | `backend/app/config.py`, `.env.example` |
| REST API dan OpenAPI | `backend/app/main.py`, `backend/app/api/`, `backend/app/schemas/` |
| Model database | `backend/app/models/`, `migrations/versions/` |
| Alur backup | `backend/app/services/backup_execution_service.py` |
| Penyimpanan S3 | `backend/app/services/s3_service.py` |
| Kriptografi | `backend/app/crypto/vault_crypto.py`, `manifest_crypto.py`, `payload_crypto.py`, `kdf.py` |
| Scheduler dan retention | `backend/app/celery_app.py`, `backend/app/tasks/`, `backend/app/services/retention_service.py` |
| Frontend | `frontend/index.html`, `frontend/js/`, `frontend/css/app.css` |
