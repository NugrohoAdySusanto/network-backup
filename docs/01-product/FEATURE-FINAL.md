# Product Requirements Document NetBackup

## Ringkasan produk

NetBackup adalah aplikasi web internal untuk mengelola backup konfigurasi perangkat jaringan. Produk menyinkronkan inventaris dari Zabbix, menjalankan backup melalui worker Celery, menyimpan metadata di PostgreSQL, menggunakan Redis untuk antrean dan lock, serta menyimpan file backup pada S3.

## Pengguna

| Peran | Kemampuan utama |
|---|---|
| Admin | Menjalankan operasi backup, mengubah pengaturan, mengelola repository, driver, pengguna, retention, dan laporan. |
| Viewer | Melihat dashboard, perangkat, pengaturan, pekerjaan, dan snapshot tanpa menjalankan operasi admin. |

## Ruang lingkup

### Termasuk

- Login, logout, profil pengguna, perubahan password, dan reset password melalui email.
- Pengelolaan pengguna oleh admin.
- Sinkronisasi perangkat dari Zabbix.
- Daftar perangkat, status availability, dan ringkasan backup terakhir.
- Driver bawaan dan driver parametrik.
- Pengaturan driver, jadwal harian, dan retention per perangkat.
- Backup manual dan terjadwal.
- Riwayat pekerjaan, snapshot, download, retention, dan laporan.
- Pengelolaan repository S3.
- Enkripsi file backup pada alur upload dan verifikasi/dekripsi pada alur restore.

### Di luar scope

Detail kriptografi login, session, transport HTTPS, SSH, dan penyimpanan secret aplikasi berada di luar scope TA; komponen tersebut hanya menjadi dependensi aplikasi.

## User story

- Sebagai admin, saya ingin menyinkronkan perangkat dari Zabbix agar daftar target mengikuti inventaris jaringan.
- Sebagai admin, saya ingin memilih driver dan jadwal agar backup berjalan sesuai kebutuhan perangkat.
- Sebagai admin, saya ingin memicu backup manual agar perubahan penting dapat segera dicadangkan.
- Sebagai operator, saya ingin melihat state dan pesan kegagalan agar dapat menentukan tindakan perbaikan.
- Sebagai admin, saya ingin mengunduh snapshot retained agar file konfigurasi dapat dipakai untuk pemulihan manual.
- Sebagai admin, saya ingin berpindah repository tanpa mencampur arsip dari repository lain.
- Sebagai viewer, saya ingin memantau hasil tanpa memperoleh tombol operasi admin.
- Sebagai auditor, saya ingin mengekspor riwayat dalam XLSX atau PDF.

## Functional requirements

| ID | Requirement | Kriteria penerimaan | Desain | Test |
|---|---|---|---|---|
| FR-01 | Sistem menyediakan login, logout, dan profil pengguna aktif. | Login valid membuat sesi; login tidak valid ditolak; logout mengakhiri sesi; `/auth/me` mengembalikan pengguna aktif. | TDD bagian akses pengguna; API bagian Auth | TC-AUTH-01 sampai TC-AUTH-03 |
| FR-02 | Admin dapat membuat, melihat, dan menonaktifkan pengguna. | Viewer ditolak; username unik; peran hanya `admin` atau `viewer`; penghapusan adalah deaktivasi. | Database `users`; API bagian Users | TC-USER-01 sampai TC-USER-03 |
| FR-03 | Pengguna dapat mengubah password dan meminta reset melalui email. | Konfirmasi password harus cocok; token reset tidak valid ditolak; respons forgot-password tidak membocorkan keberadaan akun. | API bagian Auth | TC-AUTH-04 sampai TC-AUTH-06 |
| FR-04 | Admin dapat menyinkronkan perangkat dari Zabbix dan pengguna dapat melihat daftar/detail perangkat. | Sinkronisasi membuat atau memperbarui perangkat; perangkat yang hilang ditandai `source_present=false`; daftar mendukung filter dan pagination yang diimplementasikan. | TDD bagian Zabbix; Database `devices` | TC-DEV-01 sampai TC-DEV-03 |
| FR-05 | Sistem menyediakan registry driver bawaan dan driver parametrik. | Driver aktif muncul pada registry; admin dapat membuat, mengubah, menguji, dan menghapus driver kustom; driver bawaan tidak dapat dihapus melalui endpoint kustom. | Kontrak Driver; API bagian Drivers | TC-DRV-01 sampai TC-DRV-04 |
| FR-06 | Admin dapat menyimpan atau menghapus pengaturan backup perangkat. | Jadwal hanya memakai slot lima menit; waktu aktif harus unik; retention hanya menerima nilai yang didukung; viewer tidak dapat mengubah. | Database `device_backup_settings`; API bagian Backup Settings | TC-SET-01 sampai TC-SET-04 |
| FR-07 | Admin dapat memicu backup manual. | API membuat job `QUEUED`, menolak perangkat tanpa konfigurasi yang diperlukan, dan menolak pekerjaan aktif ganda untuk perangkat yang sama. | TDD bagian pipeline; API bagian Backup Jobs | TC-BKP-01 sampai TC-BKP-03 |
| FR-08 | Scheduler membuat backup saat `next_run_at` jatuh tempo. | Hanya setting aktif dengan driver dan perangkat aktif yang diproses; jadwal berikutnya diperbarui; enqueue gagal menghasilkan job `FAILED`. | TDD bagian scheduler | TC-SCH-01 sampai TC-SCH-03 |
| FR-09 | Pekerjaan mengikuti state machine yang ditentukan. | Transisi di luar daftar ditolak; terminal state tidak dapat dipindah; job kehilangan lease dan lebih tua dari batas watchdog menjadi `FAILED`. | TDD bagian state machine | TC-JOB-01 sampai TC-JOB-03 |
| FR-10 | Worker melakukan pre-check, pengambilan, normalisasi, validasi, hashing, upload, dan verifikasi. | Perangkat down/unknown menghasilkan state skip yang sesuai; konfigurasi tidak valid gagal sebelum upload; upload baru diikuti GET, verifikasi kriptografis, dan hash plaintext. | TDD bagian pipeline | TC-BKP-04 sampai TC-BKP-08 |
| FR-11 | Sistem mendeteksi perubahan dan menggunakan ulang objek yang masih valid. | Konten pertama berstatus baseline; konten berbeda berstatus changed; konten sama memakai objek lama hanya setelah restore dan hash lolos. | TDD bagian deduplikasi; Database `config_objects` | TC-DED-01 sampai TC-DED-03 |
| FR-12 | Admin dapat menguji, menginisialisasi, membuka, mengaktifkan, memutus, dan menghapus repository S3. | Hanya satu repository aktif; init menolak manifest yang sudah ada; unlock memverifikasi manifest; delete mengikuti validasi referensi data. | TDD bagian S3; API bagian Storage | TC-S3-01 sampai TC-S3-06 |
| FR-13 | Admin dapat merotasi master password repository tanpa memutus akses ke backup lama. | Password lama diverifikasi; DEK dipertahankan; manifest ditulis bersyarat; payload lama tetap dapat dipulihkan dengan repository setelah rotasi. | Enkripsi Backup S3; API bagian Storage | TC-CRYPTO-07 |
| FR-14 | File baru dienkripsi sebelum upload ke S3. | Tidak ada plaintext yang dikirim sebagai body objek baru; kegagalan kunci atau enkripsi membuat pekerjaan gagal. | Enkripsi Backup S3 | TC-CRYPTO-01 sampai TC-CRYPTO-03 |
| FR-15 | Admin dapat mengunduh snapshot retained dari repository yang sesuai. | Snapshot expired ditolak; repository yang salah/tidak aktif ditolak; HMAC diverifikasi sebelum dekripsi; hash plaintext harus cocok sebelum respons dikirim. | Enkripsi Backup S3; API bagian Snapshots | TC-CRYPTO-04 sampai TC-CRYPTO-06, TC-SNP-01 |
| FR-16 | Sistem menyimpan snapshot dan menampilkan riwayat per perangkat. | Setiap job sukses memiliki maksimal satu snapshot; snapshot menunjuk objek dan repository; daftar hanya menampilkan data sesuai filter implementasi. | Database `snapshots`; API bagian Snapshots | TC-SNP-02 sampai TC-SNP-04 |
| FR-17 | Retention menandai dan menghapus arsip sesuai kebijakan. | Dry-run tidak mengubah data; latest known good dilindungi; objek tanpa snapshot retained masuk `pending_delete` sebelum purge. | TDD bagian retention; Database retention | TC-RET-01 sampai TC-RET-04 |
| FR-18 | Dashboard dan health endpoint menampilkan status sistem yang tersedia. | `/healthz` dan `/api/v1/healthz` merespons tanpa autentikasi; summary dan Ceph health mengikuti hak akses endpoint. | API bagian Dashboard dan Health | TC-HLT-01 sampai TC-HLT-03 |
| FR-19 | Admin dapat mengekspor laporan XLSX atau PDF. | Format lain ditolak; filter tanggal/status diterapkan; nama file dan media type sesuai format. | API bagian Reports | TC-RPT-01 sampai TC-RPT-03 |
| FR-20 | Sistem mengirim notifikasi untuk hasil terminal yang dikonfigurasi. | Kegagalan pengiriman notifikasi tidak mengubah hasil utama job; isi notifikasi tidak memuat secret. | TDD bagian notifikasi | TC-NTF-01 sampai TC-NTF-02 |
| FR-21 | UI menerapkan perbedaan tindakan admin dan viewer. | Kontrol admin disembunyikan untuk viewer; backend tetap menolak request viewer jika request dibuat di luar UI. | Spesifikasi UI; API seluruh endpoint admin | TC-UI-01 sampai TC-UI-03 |
| FR-22 | Sistem menyediakan pemantauan log audit terpusat dan deteksi ancaman keamanan (WAF). | SQLi, XSS, Path Traversal diblokir otomatis; event tercatat terstruktur; mendukung filter kategori (`STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`), severity, dan search keyword/ID. | TDD bagian Security; API bagian Audit Logs | TC-LOG-01, TC-LOG-02, TC-LOG-05 sampai TC-LOG-08 |
| FR-23 | Sistem menyediakan ekspor laporan log audit multi-format (XLSX dan PDF 2-pass). | Filter periode waktu dan kategori diterapkan konsisten; format Excel menghasilkan worksheet ber-styling; format PDF menghasilkan dokumen formal landscape ber-watermark dan lembar otorisasi. | TDD bagian Export; API bagian Audit Logs | TC-LOG-03, TC-LOG-04 |
| FR-24 | Sistem memaksakan penjadwalan backup diskrit kelipatan 5 menit. | UI dialog schedule hanya menyediakan opsi menit `:00`, `:05`, ..., `:55`; backend menolak setting di luar slot kelipatan 5 atau slot yang berkonflik. | Spesifikasi UI; API bagian Backup Settings | TC-SET-01 sampai TC-SET-03 |
| FR-25 | Driver Ruijie AP mendukung timeout adaptif dan penanganan SSH host key. | Ekstraksi konfigurasi AP berjalan stabil tanpa timeout koneksi palsu dan tanpa ketergantungan manual pada known_hosts. | Kontrak Driver; Driver Ruijie AP | TC-DRV-01, TC-DRV-03 |
| FR-26 | Sistem mengarsipkan dan memulihkan pengaturan backup perangkat per repositori S3. | Saat repositori S3 di-disconnect, pengaturan disalin ke `repository_device_setting_archives`; saat di-connect kembali, pengaturan dipulihkan otomatis. | Arsitektur Database; API bagian Storage | TC-S3-05, TC-S3-06 |
| FR-27 | Dashboard menyediakan fitur pencarian perangkat responsif seketika (Live Search). | Desktop menampilkan search bar penuh; tablet & mobile menampilkan tombol expandable search; menyaring hostname, IP, model, status, dan worker tanpa reload. | Spesifikasi UI; devices.js | TC-UI-07 |
| FR-28 | Kartu Total Devices menampilkan badge resmi Zabbix dan status sinkronisasi dinamis. | Badge Zabbix berwarna merah (#d40000); status Sync/Not-Sync menggunakan border badge dan dot yang selaras dengan kolom Status. | Spesifikasi UI; dashboard.py | TC-UI-08 |
| FR-29 | Kartu Storage Cluster Ceph Health otomatis disembunyikan untuk storage non-Ceph. | Jika repositori aktif adalah MinIO atau storage terputus, kartu Ceph Health disembunyikan agar operator tidak bingung. | Spesifikasi UI; dashboard.py | TC-UI-09 |
| FR-30 | Sistem menyediakan modal peringatan batas waktu ketidakaktifan sesi (Inactivity Timeout). | Muncul countdown peringatan 60 detik sebelum sesi ditutup otomatis jika tidak ada interaksi pengguna demi keamanan. | Spesifikasi UI; auth.js | TC-AUTH-07 |

## Non-functional requirements

| ID | Requirement | Kriteria penerimaan | Desain | Test |
|---|---|---|---|---|
| NFR-01 | File backup S3 harus menjaga kerahasiaan dan integritas. | Round-trip identik; perubahan satu bit dan kunci salah ditolak sebelum dekripsi; format mengikuti satu spesifikasi. | Enkripsi Backup S3 | TC-CRYPTO-01 sampai TC-CRYPTO-06 |
| NFR-02 | Operasi backup tidak memblokir request web sampai pengambilan selesai. | API membuat job dan mengembalikan respons penerimaan; eksekusi berlangsung di worker Celery. | TDD bagian deployment | TC-BKP-01 |
| NFR-03 | Data operasional persisten disimpan di PostgreSQL. | Restart Redis tidak menjadi mekanisme kehilangan metadata utama; database tetap menjadi sumber data persisten. | TDD dan Arsitektur Database | TC-OPS-01 |
| NFR-04 | Aplikasi gagal tertutup jika kontrak database penting tidak terpenuhi. | Startup non-test menolak tabel atau kolom kritis yang hilang. | TDD bagian startup | TC-DB-01 |
| NFR-05 | Semua timestamp operasional disimpan dengan timezone, kecuali jam harian lokal. | Kolom timestamp memakai timezone; `daily_time` menyimpan jam lokal; scheduler memakai `Asia/Jakarta`. | Arsitektur Database | TC-DB-02 |
| NFR-06 | Deployment dapat direproduksi melalui Docker Compose dan migrasi Alembic. | Migrator selesai sebelum API/worker/beat mulai; health check API tersedia. | Runbook | TC-OPS-02 sampai TC-OPS-03 |
| NFR-07 | Dokumentasi tidak boleh memuat secret atau data uji yang disamarkan sebagai hasil nyata. | Secret scan dokumentasi tidak menemukan nilai credential; UAT tetap kosong sampai diisi pelaksana. | Indeks dokumentasi | TC-DOC-01 sampai TC-DOC-02 |
| NFR-08 | UI menyediakan state loading, kosong, error, serta navigasi keyboard untuk dialog utama. | State dapat ditampilkan dan kontrol utama dapat dioperasikan melalui keyboard. | Spesifikasi UI | TC-UI-04 sampai TC-UI-06 |

## Batasan dan asumsi

- Satu repository aktif digunakan sebagai target backup baru.
- Snapshot lama tetap terkait dengan repository asalnya.
- Pengunduhan snapshot hanya tersedia untuk admin.
- Jadwal harian tidak mendukung cron bebas.
- S3 harus mendukung operasi yang dipakai aplikasi. Conditional put diperlukan untuk proteksi manifest.
- Driver dan perangkat harus menghasilkan data yang dapat divalidasi oleh kontrak driver.
- URL aplikasi pengguna adalah `https://netbackup.makuku.co.id`.
- Nilai target SLA, RPO, dan RTO menunggu keputusan pemilik proyek.

## Traceability bisnis

| Sasaran bisnis | Requirement produk |
|---|---|
| BR-01 | FR-04 sampai FR-10 |
| BR-02 | FR-09, FR-16, FR-19 |
| BR-03 | FR-13 sampai FR-15, NFR-01 |
| BR-04 | FR-11, FR-17 |
| BR-05 | FR-01, FR-02, FR-21 |
| BR-06 | FR-17 |
| BR-07 | FR-09, FR-18, FR-20 |
| BR-08 | FR-05, FR-12, NFR-06 |
| BR-09 | FR-19 |

