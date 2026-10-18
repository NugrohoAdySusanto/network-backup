# Proposal Proyek NetBackup

## Ringkasan eksekutif

NetBackup diusulkan sebagai layanan internal untuk mengotomatisasi backup konfigurasi perangkat jaringan. Aplikasi menggabungkan inventaris Zabbix, eksekusi melalui worker, penyimpanan S3, riwayat snapshot, retention, pelaporan, dan antarmuka berbasis peran.

Nilai utama proyek adalah mengurangi ketergantungan pada backup manual, mempertahankan riwayat yang dapat ditelusuri, dan memastikan file yang disimpan ke S3 tidak dapat dibaca atau diubah tanpa terdeteksi. Proposal ini tidak menetapkan anggaran, tanggal, atau nama penanggung jawab tanpa data dari pemilik proyek.

## Masalah yang diselesaikan

- Backup manual sulit dijadwalkan dan diaudit.
- Konfigurasi perangkat tersebar pada banyak vendor dan format.
- File konfigurasi dapat mengandung informasi operasional sensitif.
- Penyimpanan file yang sama berulang kali memboroskan kapasitas.
- Tim membutuhkan riwayat pekerjaan, titik pemulihan, dan diagnosis kegagalan.
- Perubahan repository perlu diisolasi agar arsip tidak tercampur.

## Solusi yang diusulkan

Sistem terdiri dari antarmuka web, REST API, database metadata, antrean pekerjaan, worker backup, scheduler, integrasi Zabbix, dan penyimpanan S3. Alur utamanya:

1. Zabbix memasok inventaris dan status perangkat.
2. Administrator memilih driver, jadwal, dan retention.
3. API membuat pekerjaan dan Celery menjalankannya di background.
4. Driver mengambil, menormalisasi, dan memvalidasi konfigurasi.
5. Sistem menghitung hash untuk mendeteksi perubahan dan objek yang dapat digunakan ulang.
6. File baru dienkripsi, diunggah, diunduh ulang, lalu diverifikasi.
7. Snapshot menghubungkan perangkat, pekerjaan, repository, dan objek fisik.
8. Pengguna yang berwenang dapat melihat riwayat dan memulihkan file.

Detail produk berada di [PRD](../01-product/FEATURE-FINAL.md), sedangkan desain teknis berada di [TDD](../02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md).

## Manfaat yang diharapkan

| Area | Manfaat |
|---|---|
| Operasional | Backup manual dan terjadwal dikelola dari satu tempat |
| Audit | Setiap pekerjaan memiliki state, waktu, pemicu, hasil, dan diagnosis kegagalan |
| Penyimpanan | Konten yang tidak berubah dapat memakai objek yang telah diverifikasi |
| Pemulihan | Snapshot retained dapat diunduh dari repository yang sesuai |
| Keamanan file | Payload diverifikasi sebelum dekripsi dan tidak diunggah sebagai plaintext |
| Pengelolaan | Administrator mengelola pengguna, repository, driver, dan pengaturan perangkat |

## Batas pekerjaan

Ruang lingkup mengikuti [Project Charter](project-charter.md). Pembahasan kriptografi dibatasi pada file backup yang disimpan ke dan diambil dari S3. Mekanisme lain tetap menjadi dependensi implementasi dan tidak dianalisis sebagai bagian TA.

## Pendekatan pelaksanaan

| Tahap | Keluaran |
|---|---|
| Validasi kebutuhan | BRD, PRD, acceptance criteria, dan traceability |
| Validasi desain | TDD, arsitektur database, kontrak API, serta spesifikasi enkripsi S3 |
| Implementasi | Aplikasi dan migrasi yang mengikuti dokumen desain |
| Verifikasi | Unit test, test script, pemeriksaan link, dan pemeriksaan konsistensi dokumentasi |
| Penerimaan | UAT dengan hasil, catatan, dan tanda tangan yang diisi oleh pihak berwenang |
| Operasional | README, runbook, manual pengguna, serta prosedur rollback |

## Sumber daya

| Kebutuhan | Isian |
|---|---|
| Pengembang | `[ISI: jumlah dan nama/peran]` |
| QA/UAT | `[ISI: jumlah dan nama/peran]` |
| Infrastruktur | `[ISI: server, database, Redis, dan endpoint S3]` |
| Perangkat uji | `[ISI: jenis perangkat dan lingkungan uji]` |
| Anggaran | `[ISI: anggaran yang disetujui]` |

Nilai secret, credential, dan nama bucket sensitif tidak dicatat pada proposal.

## Rencana waktu

| Aktivitas | Mulai | Selesai | Penanggung jawab |
|---|---|---|---|
| Finalisasi kebutuhan | `[ISI]` | `[ISI]` | `[ISI]` |
| Finalisasi desain | `[ISI]` | `[ISI]` | `[ISI]` |
| Implementasi dan integrasi | `[ISI]` | `[ISI]` | `[ISI]` |
| Pengujian | `[ISI]` | `[ISI]` | `[ISI]` |
| UAT | `[ISI]` | `[ISI]` | `[ISI]` |
| Rilis | `[ISI]` | `[ISI]` | `[ISI]` |

## Estimasi biaya

`[ISI: rincian biaya tenaga kerja, infrastruktur, lisensi, dan contingency]`

## Risiko proposal

Risiko teknis dan mitigasi mengikuti Project Charter. Risiko keputusan yang masih terbuka:

- Pemilik repository dan tata kelola master password belum dicantumkan.
- Target keberhasilan backup dan waktu pemulihan belum disepakati.
- Jadwal UAT dan pihak penandatangan belum ditetapkan.
- Kapasitas penyimpanan serta pertumbuhan arsip belum dihitung.

## Kriteria penerimaan proposal

Proposal diterima jika sponsor dan pemilik produk menyetujui ruang lingkup, sumber daya, jadwal, anggaran, risiko, dan kriteria keberhasilan.

| Peran | Nama | Keputusan | Tanggal | Tanda tangan |
|---|---|---|---|---|
| Sponsor | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Pemilik produk | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Project Manager | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
