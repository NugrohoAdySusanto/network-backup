# Desain UI NetBackup

## Implementasi saat ini

Antarmuka utama adalah single-page dashboard pada `frontend/index.html`, dilayani Nginx tanpa proses build frontend. Styling memakai CSS lokal, Tailwind CDN, DM Sans, dan Space Mono. JavaScript per domain memanggil REST API same-origin melalui `frontend/js/api.js`.

Dokumen ini menjelaskan UI yang sudah ada, bukan mockup target.

## Struktur layar

```text
Login dialog
  -> Header dan action menu
  -> Ringkasan infrastruktur
  -> Tabel perangkat
  -> Dialog kontekstual
       - riwayat backup
       - arsip dan download
       - pengaturan jadwal (dropdown jam & menit diskrit kelipatan 5)
       - audit & security logs (tabel audit trail, filter 6 kategori, export XLSX/PDF)
       - preferensi dan pengguna
       - export laporan
       - storage S3
       - worker dan driver
       - modal peringatan batas waktu ketidakaktifan sesi (inactivity countdown 60s)
```

Dashboard mempertahankan fokus pada satu tabel perangkat. Workflow sekunder memakai dialog agar operator tidak kehilangan konteks filter dan baris perangkat.

## Modul frontend

| File | Tanggung jawab |
|---|---|
| `frontend/js/api.js` | Wrapper fetch, cookie session, CSRF, dan error API |
| `frontend/js/auth.js` | Login, logout, pemulihan session, dan timeout detektor inaktivitas (60s countdown) |
| `frontend/js/devices.js` | Tabel perangkat, live search responsif, ringkasan KPI, sync Zabbix, backup manual, dan penyimpanan pengaturan |
| `frontend/js/backups.js` | Histori dan detail backup |
| `frontend/js/archives.js` | Daftar snapshot dan download hasil restore |
| `frontend/js/schedules.js` | Pengaturan jadwal harian dan retention (tanpa duplikasi driver) |
| `frontend/js/storage.js` | Test, init, unlock, activate, disconnect, delete, dan rotasi repository |
| `frontend/js/reports.js` | Filter dan export laporan |
| `frontend/js/audit_logs.js` | Pemantauan audit terpusat, filter kategori (6 tipe), severity badge, pagination, dan export Excel/PDF |
| `frontend/js/users.js` | Preferensi serta administrasi user |
| `frontend/js/workers.js` | Driver bawaan/kustom dan test driver |
| `frontend/js/theme.js` | Preferensi light/dark |

## Hierarki visual

- Header memuat identitas produk, action operasional, user, dan theme toggle.
- Tiga kartu ringkasan menampilkan jumlah perangkat (dengan badge Zabbix merah dan status Sync/Not-Sync ber-border dot), hasil backup, dan status storage (Ceph Health disembunyikan otomatis jika storage non-Ceph).
- Toolbar tabel perangkat memiliki Live Search responsif (Search bar penuh pada desktop `lg:`, dan tombol Expandable Search ber-dot aktif pada tablet/mobile `< lg:`) menggantikan tag statis lama di samping Export.
- Kolom "Backup Worker" pada tabel menjadi satu-satunya tempat pemilihan driver backup untuk mencegah redundansi konfigurasi pada modal Schedule.
- Tabel perangkat adalah pusat operasi dan mendukung scroll horizontal pada viewport sempit.
- Status memakai teks, ikon, dan warna. Warna bukan satu-satunya pembeda.
- Space Mono dipakai untuk IP, timestamp, hash, filename, dan nilai teknis.
- Feedback aksi tampil dekat konteks atau melalui toast yang bisa dibaca.

## Token warna aktual

Token berasal dari CSS variable pada `frontend/index.html`.

| Fungsi | Light | Dark |
|---|---|---|
| Latar halaman | `#f5f7f8` | `#0b1319` |
| Surface | `#ffffff` | `#132029` |
| Teks utama | `#112330` | `#f1f5f9` |
| Teks redup | `#4b6171` | `#94a3b8` |
| Border | `#dbe4e8` | `#243846` |
| Accent | `#0f3d56` | `#38bdf8` |
| Success | `#15803d` | `#22c55e` |
| Danger | `#b91c1c` | `#f87171` |
| Warning | `#b45309` | `#fbbf24` |

## Hak akses pada UI

| Aksi | Admin | Viewer |
|---|---:|---:|
| Melihat dashboard, perangkat, job, snapshot, dan health | Ya | Ya |
| Menjalankan backup dan sync | Ya | Tidak |
| Mengubah driver, jadwal, dan retention | Ya | Tidak |
| Mengelola repository | Ya | Tidak |
| Mengunduh konfigurasi hasil restore | Ya | Tidak |
| Mengelola pengguna | Ya | Tidak |
| Export laporan | Ya | Ya |

UI harus menonaktifkan atau menyembunyikan action yang tidak diizinkan, tetapi backend tetap menjadi penegak akses final.

## State penting

Setiap area data wajib menyediakan state berikut:

| State | Perilaku |
|---|---|
| Loading | Indikator terlihat dan control pemicu tidak menggandakan request |
| Empty | Menjelaskan bahwa data belum ada atau filter tidak menemukan hasil |
| Error | Menampilkan pesan aman dan opsi retry bila masuk akal |
| Disabled | Memakai atribut native dan alasan yang dapat dipahami |
| Success | Konfirmasi ringkas, lalu refresh data yang terpengaruh |
| Session expired | Kembali ke login tanpa menampilkan data sensitif lama |

Storage disconnected harus dibedakan dari storage error. Perangkat down juga harus dibedakan dari job backup gagal.

## Responsivitas

- Layout kartu berubah dari satu kolom ke dua lalu tiga kolom.
- Tabel tetap berupa tabel dan memakai container horizontal scroll.
- Dialog dibatasi tinggi viewport dan bagian isi dapat di-scroll.
- Target sentuh action utama minimal 44 x 44 CSS pixel pada perangkat sentuh.
- Teks teknis panjang seperti hash dan key objek boleh wrap atau dipotong dengan nilai lengkap tersedia secara aksesibel.

## Aksesibilitas

- Semua dialog memakai `role="dialog"`, `aria-modal="true"`, dan label judul.
- Fokus masuk ke dialog saat dibuka dan kembali ke pemicu saat ditutup.
- Escape menutup dialog jika tidak ada operasi kritis yang sedang diproses.
- Tabel scrollable dapat menerima fokus keyboard.
- Label form terhubung dengan control.
- Pesan dinamis penting memakai live region yang sesuai.
- Kontras light dan dark harus diverifikasi saat token berubah.

## Integrasi API

Frontend tidak berkomunikasi langsung dengan PostgreSQL, Redis, S3, Zabbix, Ceph Manager, atau perangkat. Semua operasi melewati endpoint pada [Kontrak REST API](../02-architecture/API-CONTRACT-v1.0.md).

CSRF token disimpan oleh modul API untuk dikirim pada operasi perubahan. Cookie session tidak dibaca JavaScript. Error ditampilkan dari pesan aman API dan tidak boleh menyisipkan HTML yang tidak dipercaya.

## Visualisasi kriptografi

`frontend/crypto-animation.html` adalah materi penjelasan terpisah untuk alur upload terenkripsi dan restore dari S3. Halaman tersebut bukan control operasional dan simulatornya bukan implementasi produksi. Sumber teknis kanonis tetap [Spesifikasi Enkripsi Backup S3](../03-design/enkripsi-backup-s3.md).

## Kriteria perubahan UI

1. Workflow admin dan viewer tetap sesuai kontrak akses.
2. Request menggunakan wrapper API dan header CSRF yang berlaku.
3. Loading, empty, error, disabled, dan success state diuji.
4. Keyboard, fokus dialog, dan screen-reader label tidak mengalami regresi.
5. Layout diuji pada lebar ponsel, tablet, dan desktop.
6. Tidak ada data demo, credential, atau hasil test fiktif pada mode production.
7. Perubahan endpoint diselaraskan dengan API contract dan test script.
