# CHECKPOINT C24: S3 Repository Lifecycle, Setting Archives, & UI/UX Modernization

## 1. Tujuan dan Ruang Lingkup
Checkpoint C24 mencakup serangkaian penyempurnaan menyeluruh pada alur siklus hidup repositori S3, deduplikasi konfigurasi driver, perapian log audit, serta modernisasi responsif pada antarmuka pengguna (UI/UX):

1. **Siklus Hidup Repositori S3 & Pengarsipan Pengaturan (`repository_device_setting_archives`):**
   - Mengatasi kendala galat 500 dan kegagalan alur diskoneksi/penghapusan repositori S3 (MinIO / Ceph).
   - Mengimplementasikan penyimpanan arsip konfigurasi backup perangkat (`driver_key`, `schedule_enabled`, `daily_time`, `retention_policy`) saat repositori dilepas (*disconnect*), dan merestorasinya secara otomatis saat repositori dihubungkan kembali (*reconnect*).
2. **Penyelarasan Visibilitas Kartu Storage Cluster (Ceph Health):**
   - Menyembunyikan kartu "Storage Cluster (Ceph Health)" secara dinamis dari dashboard utama jika repositori S3 yang terhubung bukan kluster Ceph (misalnya MinIO atau repositori berstatus terputus).
3. **Deduplikasi Konfigurasi Driver Backup:**
   - Menghilangkan dropdown pemilihan driver backup dari modal pop-up *Schedule* untuk mencegah redundansi fungsional dan benturan konfigurasi. Penugasan driver kini dilakukan eksklusif melalui kolom *Backup Worker* pada tabel perangkat.
4. **Indikator Status Sinkronisasi Zabbix & Badge Resmi:**
   - Mengganti badge "Inventory" pada kartu *Total Devices* menjadi badge merek "Zabbix" berwarna merah Zabbix resmi (`#d40000`).
   - Menambahkan status sinkronisasi Zabbix dinamis di bawahnya ("Sync" / "Not-Sync") dengan gaya border badge dan dot indikator yang identik dengan kolom *STATUS* tabel perangkat.
5. **Pencarian Perangkat Responsif (Responsive Live Instant Search):**
   - Menghapus badge statis "ACTIVE" di sebelah tombol *Export*.
   - Menyediakan pencarian *real-time* cerdas:
     - **Desktop View (`≥ 1024px`):** Search bar tampil terbuka penuh.
     - **Tablet & Mobile View (`< 1024px`):** Tampil sebagai tombol *Expandable Search* berikon kaca pembesar yang melebar saat ditekan, dilengkapi tombol tutup (`✕`), pembatalan tombol `Escape`, dan dot indikator biru aktif jika ada filter yang sedang aktif menyaring tabel.
     - Menyaring secara instan: *Hostname*, *IP Address*, *Vendor*, *Model*, *Status*, dan *Worker Driver*.
6. **Perapian Jejak Audit & Keamanan (Audit Log Noise Reduction):**
   - Menghapus pencatatan log sinkronisasi rutin Zabbix dari tabel *Audit & Security Logs* untuk menjaga agar log audit hanya berisi anomali keamanan, ancaman WAF, dan aksi administratif kritis.
7. **Peringatan Batas Waktu Ketidakaktifan Sesi (Inactivity Timeout Warning):**
   - Menyediakan modal dialog peringatan dengan hitung mundur 60 detik sebelum sesi ditutup otomatis demi kepatuhan keamanan enterprise.

---

## 2. Rincian Teknis Implementasi

### A. Skema Basis Data & Model Pengarsipan
- **File Migrasi:** `migrations/versions/016_repo_setting_archives.py`
- **File Model:** `backend/app/models/repository_device_setting_archive.py`
- **Struktur Tabel:** `repository_device_setting_archives`:
  - `id` (BigInteger, PK)
  - `s3_bucket` (String(128), Indexed)
  - `device_hostname` (String(255))
  - `device_zabbix_id` (String(64), Nullable)
  - `driver_key` (String(64), Nullable)
  - `schedule_enabled` (Boolean, Default: false)
  - `daily_time` (Time without timezone, Nullable)
  - `retention_policy` (String(32), Default: 'standard_31')
  - `updated_at` (DateTime with timezone, server_default: now())
  - Unique Constraint: `uq_repo_setting_archives_bucket_hostname` (`s3_bucket`, `device_hostname`)

### B. Alur Service Repositori S3 (`StorageRepositoryService`)
- Saat repositori di-*disconnect* / dinonaktifkan:
  - Konfigurasi dari tabel `device_backup_settings` disalin ke tabel arsip `repository_device_setting_archives` menggunakan kunci komposit `s3_bucket` + `device_hostname`.
  - Status aktif repositori dinonaktifkan (`is_active = False`).
- Saat repositori dihubungkan atau diaktifkan kembali:
  - Sistem mencari arsip konfigurasi pada bucket tersebut dan memulihkannya ke `device_backup_settings`.
- Penghapusan repositori:
  - Repositori aktif dapat didiskoneksikan secara mulus tanpa galat 500, dan repositori non-aktif dapat dihapus aman jika tidak memiliki referensi snapshot terenkripsi aktif.

### C. Backend Dashboard Summary (`backend/app/api/dashboard.py`)
- Memeriksa apakah repositori aktif tergolong Ceph (`is_ceph_storage`). Jika bukan Ceph, `ceph_data` dikosongkan dan kartu disembunyikan di frontend.
- Membaca status sinkronisasi Zabbix dari tabel `integration_status` dengan kunci `zabbix_sync`.
- Mengembalikan payload:
  ```json
  "zabbix": {
    "status": "OK",
    "is_synced": true,
    "summary": "16 network devices synchronized.",
    "last_checked_at": "2026-10-31T12:00:00+00:00"
  }
  ```

### D. Frontend Modernization (`frontend/index.html` & `frontend/js/`)
1. **Total Devices Card ([`frontend/index.html`](file:///opt/network-backup/frontend/index.html#L1005-L1015)):**
   - Badge "Zabbix": `border-[#d40000]/30 bg-[#d40000]/10 text-[#d40000] dark:text-red-400`.
   - Badge status: menggunakan elemen `.status-cell-wrapper` dengan atribut `data-status="active"` (Sync, hijau) atau `data-status="non-active"` (Not-Sync, merah).
2. **Responsive Search Bar ([`frontend/js/devices.js`](file:///opt/network-backup/frontend/js/devices.js#L630-L750)):**
   - Mengimplementasikan `initDeviceSearch()`, `applyDeviceSearchFilter()`, dan `clearDeviceSearch()`.
   - Desktop: selalu terbuka `lg:flex`.
   - Tablet & Mobile: `device-search-toggle-btn` menampilkan indikator dot biru menyala jika filter sedang aktif. Menekan `Escape` atau tombol `✕` menutup bar pencarian secara bersih.
3. **Pembersihan Driver Schedule Modal ([`frontend/js/schedules.js`](file:///opt/network-backup/frontend/js/schedules.js)):**
   - Menghapus elemen `<select id="schedule-driver">` dari markup formulir jadwal dan membersihkan ketergantungan driver dari logika penyimpanan jadwal.

---

## 3. Hasil Pengujian & Status
- Unit test terarah `test_storage_repository.py::test_dashboard_summary_scoped_to_active_repo` lulus 100% (0.58s).
- Pengujian responsivitas pada resolusi desktop (1920x1080), tablet (768px), dan ponsel (375px) mengonfirmasi transisi pencarian dan visibilitas kartu berjalan mulus.

