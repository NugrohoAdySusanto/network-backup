# Kontrak REST API NetBackup

## Lingkup dan sumber kebenaran

API memakai FastAPI dengan base path `/api/v1`. Daftar route di dokumen ini berasal dari aplikasi pada `backend/app/api/`; schema interaktif tersedia pada `/docs` hanya ketika `APP_ENV` bukan `production`, sedangkan dokumen OpenAPI JSON tersedia pada `/openapi.json`.

Frontend memakai path same-origin. URL produksi yang didokumentasikan adalah `https://netbackup.makuku.co.id`.

## Aturan umum

- Request dan respons JSON memakai `application/json`, kecuali download snapshot dan export laporan.
- Timestamp API memakai ISO 8601 dengan offset timezone.
- Middleware mengembalikan `X-Request-ID` dan memakai ID tersebut pada log terstruktur.
- Endpoint yang tidak ditandai publik membutuhkan cookie session `nb_session`.
- Operasi perubahan yang terautentikasi membutuhkan header `X-CSRF-Token`.
- Endpoint admin menolak peran viewer dengan `403`.
- Credential, session ID, konfigurasi perangkat, dan stack trace tidak boleh muncul pada pesan error.

Respons sukses JSON dibungkus sebagai berikut:

```json
{
  "data": {}
}
```

Respons error aplikasi:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Pesan aman untuk klien",
    "details": null,
    "request_id": "<REQUEST_ID>"
  }
}
```

Validasi FastAPI dapat menghasilkan status `422`. Source route belum mendeklarasikan seluruh respons domain 4xx dan 5xx pada OpenAPI.

## Autentikasi

| Method dan path | Akses | Input utama | Hasil |
|---|---|---|---|
| `POST /api/v1/auth/login` | Publik | `username`, `password`, `remember_me` opsional | `200`, user dan token CSRF; memasang cookie session |
| `POST /api/v1/auth/logout` | Login dan CSRF | Tidak ada body | `204` dan menghapus session |
| `GET /api/v1/auth/me` | Login | Tidak ada | `200`, user dan token CSRF |
| `POST /api/v1/auth/change-password` | Login dan CSRF | `current_password`, `new_password`, `confirm_password` | `204` dan menghapus seluruh session user |
| `POST /api/v1/auth/forgot-password` | Publik | `email` | `200` dengan pesan netral |
| `POST /api/v1/auth/reset-password` | Publik | `token`, `new_password`, `confirm_password` | `200` dan menghapus seluruh session user |

`forgot-password` tidak boleh mengungkap apakah email terdaftar.

## Dashboard dan perangkat

| Method dan path | Akses | Parameter atau body | Hasil utama |
|---|---|---|---|
| `GET /api/v1/dashboard/summary` | Login | Tidak ada | Ringkasan perangkat, backup, dan integrasi |
| `GET /api/v1/devices` | Login | `source_present`, `status`, `search`, `limit`, `offset` | Daftar perangkat terfilter |
| `POST /api/v1/devices/sync-zabbix` | Admin dan CSRF | Tidak ada | `202`, task sinkronisasi |
| `GET /api/v1/devices/{device_id}` | Login | `device_id` | Detail perangkat |
| `POST /api/v1/devices/{device_id}/backup` | Admin dan CSRF | `device_id` | `202`, job backup baru |
| `GET /api/v1/devices/{device_id}/backup-jobs` | Login | `state`, `trigger_type`, `limit`, `offset` | Histori job perangkat |
| `GET /api/v1/devices/{device_id}/snapshots` | Login | `retained_only`, `search`, `limit`, `offset` | Snapshot perangkat |
| `GET /api/v1/devices/{device_id}/backup-settings` | Login | `device_id` | Pengaturan backup |
| `PUT /api/v1/devices/{device_id}/backup-settings` | Admin dan CSRF | Lihat schema pengaturan | Pengaturan tersimpan |
| `DELETE /api/v1/devices/{device_id}/backup-settings` | Admin dan CSRF | `device_id` | `204`, pengaturan dikosongkan |
| `GET /api/v1/backup-jobs/{job_id}` | Login | UUID `job_id` | Detail job |

Body update pengaturan:

```json
{
  "driver_key": "<DRIVER_KEY_OR_NULL>",
  "schedule_enabled": true,
  "daily_time": "01:30:00",
  "retention_policy": "standard_31"
}
```

Nilai retention yang didukung adalah `standard_31` dan `smart_7_4_12_3`. Jadwal aktif membutuhkan driver dan waktu pada slot lima menit yang belum dipakai perangkat lain.

## Driver

| Method dan path | Akses | Input | Hasil utama |
|---|---|---|---|
| `GET /api/v1/drivers` | Login | Tidak ada | Driver bawaan dan driver kustom aktif |
| `POST /api/v1/drivers/custom` | Admin dan CSRF | `CustomDriverPayload` | Driver kustom dibuat |
| `PUT /api/v1/drivers/custom/{key}` | Admin dan CSRF | `CustomDriverPayload` | Driver kustom diperbarui |
| `DELETE /api/v1/drivers/custom/{key}` | Admin dan CSRF | `key` | Driver kustom dinonaktifkan/dihapus sesuai service |
| `POST /api/v1/drivers/test` | Admin dan CSRF | Definisi driver dan target uji | Hasil uji koneksi/koleksi yang sudah disanitasi |

Field lengkap dan batas perilaku driver berada di [Kontrak Backup Driver](BACKUP-DRIVER-CONTRACT-v1.0.md). Endpoint test adalah operasi sensitif dan tidak boleh mengembalikan credential.

## Storage repository

| Method dan path | Akses | Input | Hasil utama |
|---|---|---|---|
| `POST /api/v1/storage/test` | Admin dan CSRF | Endpoint, bucket, access key, secret key, `secure` | Hasil validasi koneksi |
| `POST /api/v1/storage/repositories/init` | Admin dan CSRF | Data repository dan `master_password` | Repository dan manifest baru |
| `POST /api/v1/storage/repositories/unlock` | Admin dan CSRF | Data repository dan `master_password` | Repository lama diverifikasi dan dipasang |
| `GET /api/v1/storage/repositories` | Admin | Tidak ada | Daftar repository tanpa secret |
| `GET /api/v1/storage/active` | Login | Tidak ada | Repository aktif atau `null` |
| `POST /api/v1/storage/repositories/{repo_id}/activate` | Admin dan CSRF | UUID repository | Mengaktifkan satu repository |
| `POST /api/v1/storage/disconnect` | Admin dan CSRF | Tidak ada | Menonaktifkan repository aktif |
| `DELETE /api/v1/storage/repositories/{repo_id}` | Admin dan CSRF | UUID repository | Menghapus record yang memenuhi aturan service |
| `POST /api/v1/storage/repositories/{repo_id}/rotate-password` | Admin dan CSRF | Password master lama dan baru | Manifest dibungkus ulang |
| `POST /api/v1/repositories/{repo_id}/rotate-password` | Admin dan CSRF | Sama seperti path storage | Alias kompatibilitas untuk rotasi yang sama |

Body init:

```json
{
  "name": "<REPOSITORY_NAME>",
  "endpoint": "<S3_ENDPOINT>",
  "bucket": "<BUCKET>",
  "access_key": "<ACCESS_KEY>",
  "secret_key": "<SECRET_KEY>",
  "secure": true,
  "master_password": "<MASTER_PASSWORD>"
}
```

Body unlock memakai field yang sama. Body rotasi memakai `current_master_password` dan `new_master_password`. Respons tidak boleh mengulang secret key atau password master. Detail payload backup berada di [Spesifikasi Enkripsi Backup S3](../03-design/enkripsi-backup-s3.md).

## Snapshot dan retention

| Method dan path | Akses | Parameter | Hasil utama |
|---|---|---|---|
| `GET /api/v1/snapshots/{snapshot_id}` | Login | ID snapshot | Metadata snapshot |
| `GET /api/v1/snapshots/{snapshot_id}/download` | Admin | ID snapshot | File konfigurasi hasil restore dan verifikasi |
| `POST /api/v1/snapshots/retention/run` | Admin dan CSRF | Query `dry_run`, default `true` | Ringkasan evaluasi retention |

Download dapat gagal bila snapshot expired, objek tidak tersedia, repository asal tidak aktif, integritas gagal, atau hash plaintext tidak cocok.

## Pengguna

| Method dan path | Akses | Input | Hasil utama |
|---|---|---|---|
| `GET /api/v1/users` | Admin | `limit`, `offset`, `include_inactive` | Daftar user tanpa nilai autentikasi tersimpan |
| `POST /api/v1/users` | Admin dan CSRF | `username`, `email` opsional, `password`, `role` | `201`, user baru |
| `DELETE /api/v1/users/{user_id}` | Admin dan CSRF | ID user | `204`, user dinonaktifkan |

Role yang diterima adalah `admin` dan `viewer`. Admin tidak boleh menonaktifkan dirinya sendiri melalui operasi ini.

## Laporan dan health

| Method dan path | Akses | Parameter | Hasil utama |
|---|---|---|---|
| `GET /api/v1/reports/export` | Login | `format`, `start_date`, `end_date`, `device_id`, `status` | File XLSX atau PDF |
| `GET /api/v1/health/ceph` | Login | Tidak ada | Status Ceph terakhir |
| `GET /api/v1/healthz` | Publik | Tidak ada | Liveness API pada namespace versi |
| `GET /healthz` | Publik | Tidak ada | Liveness API untuk proxy/container |

Kedua endpoint health dasar menyatakan proses API hidup. Keduanya bukan jaminan seluruh dependency siap.

## Audit dan Security Logs

| Method dan path | Akses | Parameter | Hasil utama |
|---|---|---|---|
| `GET /api/v1/logs` | Login | `page`, `page_size`, `category`, `severity`, `event_type`, `search`, `start_date`, `end_date` | Daftar log terpaginasi (dengan auto-backfill data riwayat) |
| `GET /api/v1/logs/stats` | Login | `start_date`, `end_date` | Agregat metrik KPI, total insiden, dan breakdown kategori/keparahan |
| `GET /api/v1/logs/export` | Login | `format` (`xlsx`/`pdf`), `category`, `severity`, `event_type`, `search`, `start_date`, `end_date` | File biner laporan audit terstruktur (.xlsx atau .pdf) |
| `GET /api/v1/logs/{log_id}` | Login | ID log numerik | Objek detail lengkap log termasuk payload JSON `details` |

Kategori yang didukung: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`.  
Tingkat keparahan (*severity*): `CRITICAL`, `WARNING`, `ERROR`, `INFO`.

## Status HTTP yang dipakai

| Status | Arti kontrak |
|---:|---|
| 200 | Operasi sinkron berhasil |
| 201 | Resource dibuat |
| 202 | Pekerjaan background diterima |
| 204 | Berhasil tanpa body |
| 400 | Request bisnis tidak valid |
| 401 | Session tidak ada atau tidak valid |
| 403 | Hak akses atau CSRF gagal |
| 404 | Resource tidak ditemukan |
| 409 | Konflik state atau constraint |
| 410 | Snapshot/file tidak lagi retained |
| 422 | Schema request tidak valid |
| 500 | Kesalahan aplikasi |
| 502 | Dependency eksternal gagal |
| 503 | Service belum tersedia |

## Perubahan kontrak

Setiap perubahan route wajib memperbarui source FastAPI, test API, dokumen ini, dan traceability PRD dalam commit yang sama. OpenAPI hasil aplikasi harus menjadi pemeriksaan pertama untuk mendeteksi drift.
