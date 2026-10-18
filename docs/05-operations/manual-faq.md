# Buku Manual dan FAQ NetBackup

## Untuk siapa

Panduan ini ditujukan kepada admin dan viewer aplikasi. Admin dapat menjalankan operasi dan mengubah konfigurasi. Viewer hanya dapat melihat data yang tersedia.

URL aplikasi: `https://netbackup.makuku.co.id`

Kontak bantuan: [ISI: service desk atau kanal dukungan]

## Masuk dan keluar

### Login

1. Buka URL aplikasi.
2. Masukkan username dan password.
3. Pilih opsi remember session hanya pada perangkat kerja yang dikelola organisasi.
4. Pilih Sign In.

Jika login gagal, periksa penulisan username/password. Jangan mengirim password melalui tiket dukungan.

### Logout

Buka menu akun lalu pilih Logout. Tutup browser bila komputer dipakai bersama.

### Lupa password

1. Pilih Forgot Password.
2. Masukkan email akun.
3. Buka tautan reset yang dikirim ke email.
4. Buat password baru dan konfirmasi nilainya.

Respons aplikasi tetap sama untuk email terdaftar maupun tidak. Hubungi admin bila email tidak diterima setelah memeriksa folder spam dan masa tunggu wajar.

## Membaca dashboard

Dashboard menampilkan ringkasan perangkat, hasil backup, dan storage, lalu tabel perangkat.

| Informasi | Arti |
|---|---|
| Availability | Status terakhir dari Zabbix: up, down, atau unknown |
| Backup state | Tahap atau hasil job terakhir |
| Change status | Baseline, changed, atau no change |
| Driver | Implementasi yang mengambil konfigurasi perangkat |
| Schedule | Jadwal harian perangkat |
| Repository | Storage yang terkait dengan backup/snapshot |

Status `changed` bukan kegagalan. Status itu menyatakan konfigurasi normal berbeda dari snapshot sebelumnya.

## Menyinkronkan perangkat

Khusus admin:

1. Pilih Sync Zabbix.
2. Tunggu notifikasi bahwa task diterima.
3. Refresh daftar setelah task selesai.

Perangkat yang hilang dari Zabbix tidak langsung dihapus. Aplikasi menandainya tidak lagi present agar histori tetap tersedia.

## Mengatur backup perangkat

Khusus admin:

1. Pilih perangkat.
2. Pilih driver yang sesuai.
3. Aktifkan jadwal bila diperlukan.
4. Pilih waktu pada slot lima menit.
5. Pilih retention policy.
6. Simpan.

Satu slot waktu aktif tidak dapat dipakai dua perangkat. Jika ditolak, pilih slot lain. Jangan memilih driver hanya berdasarkan nama vendor tanpa memastikan model/perintahnya sesuai.

## Menjalankan backup manual

Khusus admin:

1. Pastikan repository aktif.
2. Pastikan driver perangkat sudah disimpan.
3. Pilih Backup Now pada baris perangkat.
4. Buka histori untuk memantau job.

API hanya menerima job lalu worker menjalankannya. Status tidak langsung sukses setelah tombol dipilih.

Hasil umum:

| Hasil | Arti |
|---|---|
| `SUCCESS_CHANGED` | Konfigurasi valid dan berbeda dari sebelumnya |
| `SUCCESS_NO_CHANGE` | Konfigurasi sama dan object lama sudah diverifikasi |
| `SKIPPED_DEVICE_DOWN` | Zabbix menyatakan perangkat down |
| `SKIPPED_STATUS_UNKNOWN` | Availability belum cukup meyakinkan |
| `FAILED` | Salah satu tahap gagal; lihat failure stage dan code |

## Melihat histori dan snapshot

Pilih perangkat, lalu buka histori backup untuk melihat job. Buka Backup Archives untuk melihat snapshot yang masih retained.

Job adalah catatan eksekusi. Snapshot adalah titik pemulihan logis. Beberapa snapshot `no_change` dapat menunjuk file fisik S3 yang sama.

## Mengunduh hasil restore

Khusus admin:

1. Buka Backup Archives perangkat.
2. Cari snapshot retained.
3. Pastikan repository asal aktif.
4. Pilih Download.
5. Simpan file pada lokasi yang disetujui organisasi.

Backend memverifikasi object sebelum mengirim file. Download bukan restore otomatis ke perangkat. Review file dan ikuti prosedur perubahan jaringan sebelum menerapkannya secara manual.

## Mengelola repository S3

Khusus admin.

### Repository baru

1. Buka S3 Storage Management.
2. Isi data koneksi.
3. Jalankan Test Connection.
4. Pilih Initialize.
5. Buat dan simpan password master sesuai kebijakan organisasi.

### Repository existing

Gunakan Unlock dengan koneksi dan password yang benar. Jangan memilih Initialize jika bucket sudah memiliki manifest.

### Mengganti repository aktif

Pilih Activate pada repository tujuan. Hanya satu repository aktif. Histori repository lain tidak dihapus, tetapi download snapshot memerlukan repository asal yang sesuai.

### Memutus storage

Disconnect menonaktifkan target aktif tanpa menghapus repository atau histori.

### Rotasi password master

Pilih Rotate Password, masukkan password saat ini dan password baru, lalu tunggu verifikasi. Sesudahnya, uji download satu snapshot lama. Detail penanganan kegagalan berada di [Runbook](runbook.md).

## Mengelola driver kustom

Khusus admin:

1. Buka Backup Worker Management.
2. Buat definisi driver dengan key yang stabil.
3. Isi perintah backup, paging, timeout, ekstensi, pola normalisasi, dan validasi.
4. Jalankan test pada perangkat sandbox.
5. Simpan hanya jika hasil valid.

Hasil test dapat berisi data sensitif. Jangan menyalinnya ke tiket atau dokumen umum.

## Export laporan

1. Buka Export Report.
2. Pilih format XLSX atau PDF.
3. Isi rentang tanggal dan filter opsional.
4. Unduh file.

Pastikan rentang waktu dan filter tercantum dalam konteks laporan saat file dibagikan.

## Mengelola pengguna

Khusus admin:

- Buat user dengan role `admin` atau `viewer`.
- Isi email bila user memerlukan reset password.
- Deactivate user yang tidak lagi membutuhkan akses.
- Admin tidak dapat menonaktifkan dirinya sendiri melalui endpoint ini.

## FAQ

### Apa itu backup terenkripsi?

File konfigurasi diubah menjadi object yang tidak dapat dibaca langsung sebelum dikirim ke S3. Saat download, backend memverifikasi bahwa object tidak berubah lalu memulihkan file aslinya. Detail teknis berada di [Spesifikasi Enkripsi Backup S3](../03-design/enkripsi-backup-s3.md).

### Mengapa backup tidak langsung selesai?

Backup berjalan di Celery worker. Setelah API menerima request, job berpindah melalui beberapa state sampai sukses, skip, retry, atau gagal.

### Mengapa perangkat tidak dapat di-backup?

Penyebab umum adalah driver belum dipilih, repository tidak aktif, ada job aktif lain, perangkat tidak present, atau availability down/unknown. Lihat pesan aman pada histori job.

### Apakah `no_change` berarti tidak ada snapshot?

Tidak. Sistem dapat membuat snapshot logis baru yang menunjuk object lama setelah object tersebut berhasil dipulihkan dan diverifikasi.

### Mengapa saya tidak melihat tombol Backup atau Download?

Akun viewer tidak memiliki operasi admin. Pada akun admin, tombol juga dapat nonaktif bila resource belum siap, misalnya storage disconnected.

### Mengapa snapshot lama tidak bisa diunduh setelah pindah repository?

Snapshot tetap terikat pada repository asal. Aktifkan dan buka repository yang sesuai, lalu coba lagi. Jangan memindahkan relasi langsung di database.

### Apa arti integrity verification failed?

Object, material kunci, atau data yang dibaca tidak cocok dengan tag integritas. Jangan mencoba membuka byte mentah atau melewati validasi. Catat request/job/snapshot ID dan hubungi tim dukungan.

### Bagaimana jika lupa password?

Untuk password login, gunakan Forgot Password bila email dan SMTP tersedia atau hubungi admin. Untuk password master repository, aplikasi tidak memiliki recovery otomatis. Hubungi pemilik credential organisasi; jangan menginisialisasi ulang bucket existing karena dapat memutus akses dan merusak referensi manifest.

### Apakah rotasi password mengenkripsi ulang semua backup?

Tidak. Rotasi membungkus ulang manifest sambil mempertahankan DEK repository, sehingga backup lama tetap dapat dipulihkan bila rotasi berhasil.

### Apakah aplikasi mengembalikan konfigurasi ke perangkat?

Tidak. Restore menghasilkan file download yang sudah diverifikasi. Penerapan kembali ke perangkat mengikuti prosedur perubahan jaringan terpisah.

### Mengapa retention tidak langsung menghapus object?

Penghapusan memakai dua tahap. Object ditandai `pending_delete`, menunggu grace period, lalu diperiksa ulang sebelum purge.

### Di mana melaporkan masalah?

Hubungi [ISI: service desk atau kanal insiden]. Sertakan waktu, timezone, request ID/job ID, state, dan error code. Jangan sertakan password, token, cookie, secret key, atau file konfigurasi.
