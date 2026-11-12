# Project Charter NetBackup

## Ringkasan eksekutif

NetBackup adalah aplikasi internal untuk mengambil konfigurasi perangkat jaringan, menyimpan riwayat backup di penyimpanan S3 yang kompatibel, dan menyediakan pemulihan file melalui antarmuka web. Proses backup berjalan di worker terpisah agar permintaan web tidak tertahan oleh koneksi ke perangkat atau operasi penyimpanan.

File konfigurasi dapat memuat informasi sensitif. Karena itu, aplikasi mengenkripsi file sebelum mengirimkannya ke S3 dan memverifikasi keutuhannya sebelum memulihkan file. Penjelasan teknis berada di [Spesifikasi Enkripsi Backup S3](../03-design/enkripsi-backup-s3.md).

Dokumen ini menetapkan tujuan, batas proyek, deliverable, risiko, dan kriteria keberhasilan. Data organisasi yang belum tersedia ditandai dengan `[ISI: ...]`.

## Identitas proyek

| Atribut | Nilai |
|---|---|
| Nama proyek | NetBackup |
| Organisasi | PT Lucky Mom Indonesia |
| Sponsor | `[ISI: nama sponsor proyek]` |
| Pemilik produk | `[ISI: nama pemilik produk]` |
| Project Manager | `[ISI: nama Project Manager]` |
| Tanggal mulai | `[ISI: tanggal mulai]` |
| Target selesai | `[ISI: target selesai]` |
| Status | `[ISI: status proyek yang disetujui]` |

## Latar belakang

Konfigurasi perangkat jaringan perlu dicadangkan secara konsisten agar tim dapat mengambil file terakhir yang masih tersedia saat terjadi kesalahan konfigurasi, pergantian perangkat, atau kebutuhan audit. Proses manual menyulitkan penjadwalan, penelusuran hasil, deduplikasi, dan pengendalian akses.

NetBackup memusatkan inventaris perangkat, pengaturan jadwal, eksekusi backup, riwayat pekerjaan, snapshot, kebijakan retention, dan penyimpanan S3 dalam satu aplikasi.

## Tujuan

1. Mengambil konfigurasi dari perangkat yang terdaftar melalui driver yang sesuai.
2. Menjalankan backup manual dan terjadwal melalui antrean worker.
3. Menyimpan objek backup ke repository S3 aktif setelah enkripsi dan pemeriksaan integritas.
4. Menyediakan riwayat pekerjaan dan snapshot yang dapat ditelusuri.
5. Mengurangi upload berulang melalui deteksi perubahan dan deduplikasi.
6. Memberi administrator sarana untuk mengelola repository, driver, pengguna, dan pengaturan backup.
7. Memberi viewer akses baca tanpa kewenangan mengubah konfigurasi.

## Ruang lingkup

### Termasuk

- Sinkronisasi inventaris dan status perangkat dari Zabbix.
- Driver bawaan dan driver parametrik untuk pengambilan konfigurasi.
- Backup manual dan harian.
- Antrean Celery, penguncian per perangkat, retry, dan pemantauan pekerjaan terbengkalai.
- Normalisasi, hash konten, deduplikasi, dan snapshot.
- Repository S3 yang dapat diinisialisasi, dibuka, diaktifkan, diputus, dirotasi password-nya, atau dihapus jika memenuhi aturan aplikasi.
- Enkripsi file backup sebelum upload dan verifikasi sebelum restore.
- Retention `standard_31` dan `smart_7_4_12_3`.
- Ekspor laporan XLSX dan PDF.
- Notifikasi kegagalan melalui integrasi yang dikonfigurasi.
- Antarmuka web untuk admin dan viewer.

### Di luar scope

Detail kriptografi login, session, transport HTTPS, SSH, dan penyimpanan secret aplikasi tidak dibahas dalam proyek TA ini. Komponen tersebut hanya diperlakukan sebagai dependensi aplikasi.

## Stakeholder

| Peran | Nama | Kepentingan |
|---|---|---|
| Sponsor | `[ISI: nama]` | Pendanaan dan keputusan tingkat proyek |
| Pemilik produk | `[ISI: nama]` | Prioritas dan penerimaan fitur |
| Project Manager | `[ISI: nama]` | Jadwal, risiko, dan koordinasi |
| Tim infrastruktur jaringan | `[ISI: nama/tim]` | Pengguna operasional dan pemilik perangkat |
| Tim DevOps | `[ISI: nama/tim]` | Deployment, monitoring, dan pemulihan layanan |
| Tim QA/UAT | `[ISI: nama/tim]` | Verifikasi dan penerimaan |
| Pengembang | `[ISI: nama]` | Implementasi dan pemeliharaan |

## Deliverable

1. Aplikasi NetBackup yang dapat dijalankan melalui Docker Compose.
2. Backend FastAPI, worker dan scheduler Celery, PostgreSQL, Redis, serta Nginx.
3. Antarmuka web untuk operasi yang didefinisikan dalam PRD.
4. Migrasi database sampai revision `016_repo_setting_archives`.
5. Dokumentasi pada indeks `docs/README.md`.
6. Test otomatis yang tersimpan di `tests/unit/`.
7. Test script dan template berita acara UAT.

## Milestone

| Milestone | Target | Status |
|---|---|---|
| Persetujuan kebutuhan | `[ISI: tanggal]` | `[ISI: status]` |
| Validasi desain dan database | `[ISI: tanggal]` | `[ISI: status]` |
| Penyelesaian implementasi | `[ISI: tanggal]` | `[ISI: status]` |
| Pengujian sistem | `[ISI: tanggal]` | `[ISI: status]` |
| UAT | `[ISI: tanggal]` | `[ISI: status]` |
| Rilis | `[ISI: tanggal]` | `[ISI: status]` |

## Risiko dan mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Repository atau kredensial S3 tidak tersedia | Backup dan restore gagal | Health check, error terkontrol, runbook, dan larangan menandai pekerjaan sukses sebelum verifikasi |
| Password repository hilang atau tidak dapat dibuka | Repository tidak dapat digunakan | Pengelolaan password oleh pemilik yang berwenang dan prosedur rotasi yang mempertahankan DEK |
| Objek S3 rusak atau berubah | Restore ditolak | Verifikasi tag integritas GMAC (AEAD AES-256-GCM) sebelum dekompresi dan pemeriksaan hash plaintext |
| Perangkat tidak dapat dijangkau | Backup tertunda atau dilewati | Pre-check Zabbix, retry, timeout, dan notifikasi |
| Migrasi database tidak sinkron dengan model | Aplikasi gagal mulai atau menghasilkan error data | Migrator satu kali dan verifikasi kontrak skema saat startup |
| Worker berhenti saat pekerjaan aktif | Pekerjaan tertinggal pada state aktif | Lease/heartbeat dan stale-job watchdog |
| Data uji atau hasil UAT dianggap sebagai fakta produksi | Keputusan keliru | Biarkan kolom hasil kosong sampai pengujian benar-benar dilakukan |

## Kriteria keberhasilan

- Requirement prioritas wajib lulus test yang terkait.
- Backup yang berhasil dapat diunduh kembali dan identik secara byte dengan file asal.
- Payload yang diubah satu bit ditolak sebelum proses dekripsi.
- Pengguna tanpa hak admin tidak dapat menjalankan operasi tulis yang dibatasi.
- Deployment baru dapat menjalankan migrasi dan health check sesuai runbook.
- UAT disetujui oleh `[ISI: pihak yang berwenang]`.
- Target operasional tambahan: `[ISI: target keberhasilan backup, waktu pemulihan, dan batas kegagalan]`.

## Persetujuan

| Peran | Nama | Tanggal | Tanda tangan |
|---|---|---|---|
| Sponsor | `[ISI: nama]` | `[ISI: tanggal]` | `[ISI: tanda tangan]` |
| Pemilik produk | `[ISI: nama]` | `[ISI: tanggal]` | `[ISI: tanda tangan]` |
| Project Manager | `[ISI: nama]` | `[ISI: tanggal]` | `[ISI: tanda tangan]` |

