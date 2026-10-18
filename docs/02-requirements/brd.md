# Business Requirements Document NetBackup

## Tujuan dokumen

BRD ini menjelaskan kebutuhan bisnis NetBackup tanpa menetapkan detail implementasi. Spesifikasi perilaku produk berada di [PRD](prd.md).

## Ringkasan kebutuhan bisnis

Tim infrastruktur memerlukan proses backup konfigurasi perangkat yang terpusat, terjadwal, dapat diaudit, dan dapat dipulihkan. Sistem harus menggunakan inventaris perangkat yang sudah dikelola di Zabbix, menyimpan file backup pada repository S3 yang dipilih administrator, dan membatasi tindakan perubahan kepada pengguna dengan peran admin.

## Sasaran bisnis

| ID | Sasaran |
|---|---|
| BR-01 | Mengurangi ketergantungan pada backup konfigurasi manual. |
| BR-02 | Menyediakan riwayat pekerjaan dan snapshot yang dapat ditelusuri per perangkat. |
| BR-03 | Menjaga kerahasiaan dan integritas file backup yang disimpan pada S3. |
| BR-04 | Menghindari penyimpanan objek berulang ketika konfigurasi tidak berubah. |
| BR-05 | Memisahkan kewenangan operasional admin dari akses baca viewer. |
| BR-06 | Menyediakan kebijakan penyimpanan dan penghapusan arsip yang dapat dijalankan otomatis. |
| BR-07 | Menyediakan informasi kegagalan yang cukup untuk dukungan operasional. |
| BR-08 | Mendukung repository dan driver tanpa menanam konfigurasi lingkungan ke source code. |
| BR-09 | Menyediakan laporan yang dapat diekspor untuk kebutuhan audit internal. |

## Proses bisnis target

1. Sistem menyinkronkan perangkat dari grup jaringan yang dikonfigurasi di Zabbix.
2. Admin memilih driver, jadwal harian, dan kebijakan retention untuk perangkat.
3. Backup berjalan karena permintaan admin atau jadwal.
4. Sistem memeriksa status perangkat sebelum membuka koneksi pengambilan konfigurasi.
5. Worker mengambil, menormalisasi, memvalidasi, dan menghitung hash konfigurasi.
6. Jika konten belum tersimpan, sistem mengenkripsi file dan mengunggahnya ke repository S3 aktif.
7. Sistem mengunduh dan memverifikasi objek sebelum pekerjaan dinyatakan berhasil.
8. Sistem membuat snapshot sebagai titik pemulihan logis.
9. Admin dapat mengunduh snapshot yang masih retained dari repository yang sesuai.
10. Scheduler menjalankan retention dan pembersihan objek yang sudah melewati grace period.

## Pemangku kepentingan

| Kelompok | Kebutuhan |
|---|---|
| Tim infrastruktur jaringan | Backup dapat dijalankan dan file dapat dipulihkan saat diperlukan. |
| Administrator aplikasi | Dapat mengelola pengguna, driver, repository, jadwal, dan retention. |
| Viewer | Dapat memantau perangkat dan riwayat tanpa mengubah konfigurasi. |
| Tim DevOps/Support | Dapat melakukan deployment, health check, diagnosis, rollback, dan eskalasi. |
| Manajemen/klien | Mendapat ringkasan hasil dan bukti penerimaan yang dapat ditelusuri. |

Nama pemangku kepentingan: `[ISI: nama dan peran yang disetujui]`.

## Kebutuhan bisnis

| ID | Kebutuhan | Nilai bisnis | Prioritas |
|---|---|---|---|
| BRQ-01 | Inventaris perangkat harus berasal dari sumber yang dikelola tim jaringan. | Mengurangi input manual dan perbedaan data. | Wajib |
| BRQ-02 | Backup manual dan terjadwal harus memakai pipeline hasil yang sama. | Menjaga konsistensi operasional. | Wajib |
| BRQ-03 | Setiap pekerjaan harus memiliki status dan alasan kegagalan. | Mempercepat diagnosis dan audit. | Wajib |
| BRQ-04 | File backup baru harus disimpan secara terenkripsi pada S3. | Mengurangi risiko pembacaan file langsung dari storage. | Wajib |
| BRQ-05 | File yang rusak atau menggunakan kunci yang tidak sesuai harus ditolak saat restore. | Mencegah penggunaan hasil yang tidak dapat dipercaya. | Wajib |
| BRQ-06 | Konten yang tidak berubah harus memakai ulang objek yang telah diverifikasi. | Mengurangi penggunaan storage dan upload. | Wajib |
| BRQ-07 | Snapshot dan objek harus mengikuti kebijakan retention. | Mengendalikan pertumbuhan arsip. | Wajib |
| BRQ-08 | Data antar repository harus dapat dibedakan. | Mencegah arsip tercampur. | Wajib |
| BRQ-09 | Admin dan viewer harus memiliki kemampuan berbeda. | Mengurangi perubahan yang tidak berwenang. | Wajib |
| BRQ-10 | Sistem harus menghasilkan ekspor XLSX atau PDF. | Mendukung audit dan pelaporan. | Penting |
| BRQ-11 | Sistem harus memberi notifikasi pada kegagalan terminal bila integrasi tersedia. | Mempercepat respons insiden. | Penting |
| BRQ-12 | Deployment harus dapat dibuat ulang dari source dan konfigurasi placeholder. | Mengurangi drift lingkungan. | Wajib |

## Batasan dan asumsi

- Aplikasi digunakan sebagai layanan internal.
- Zabbix, database, Redis, endpoint S3, dan perangkat target dikelola di luar aplikasi.
- Hanya satu repository dapat berstatus aktif pada satu waktu.
- Jadwal otomatis memakai slot lima menit dan timezone aplikasi `Asia/Jakarta`.
- Restore pada produk saat ini berbentuk pengunduhan file konfigurasi, bukan penerapan konfigurasi kembali ke perangkat.
- Kualitas akses jaringan dan dukungan perintah perangkat berada di luar kendali aplikasi.
- Target kapasitas, RPO, RTO, dan SLA: `[ISI: nilai yang disetujui]`.

## Ukuran keberhasilan

| Ukuran | Target |
|---|---|
| Persentase backup berhasil | `[ISI: target]` |
| Waktu maksimum restore file | `[ISI: target]` |
| Batas pekerjaan terbengkalai | `[ISI: target]` |
| Masa simpan yang disetujui | `[ISI: target sesuai kebijakan]` |
| Jumlah temuan UAT terbuka saat rilis | `[ISI: target]` |

## Persetujuan

| Peran | Nama | Tanggal | Keputusan |
|---|---|---|---|
| Pemilik bisnis | `[ISI]` | `[ISI]` | `[ISI]` |
| Pemilik produk | `[ISI]` | `[ISI]` | `[ISI]` |
| Project Manager | `[ISI]` | `[ISI]` | `[ISI]` |

