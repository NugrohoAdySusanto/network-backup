# Test Script NetBackup

## Tujuan

Dokumen ini mendefinisikan skenario verifikasi untuk requirement pada [PRD](../01-product/FEATURE-FINAL.md). Kolom hasil sengaja tidak disediakan di sini; hasil eksekusi dicatat pada test report terpisah atau [Berita Acara UAT](berita-acara-uat.md).

## Aturan eksekusi

- Gunakan environment uji yang terisolasi dan data sintetis.
- Jangan memakai credential, bucket, alamat perangkat, atau email production.
- Simpan request ID dan job ID sebagai bukti tanpa menyalin secret atau isi konfigurasi sensitif.
- Bersihkan data uji sesuai kebijakan environment setelah pengujian.
- Untuk test yang mengubah byte envelope, gunakan object atau fixture uji, bukan arsip production.
- Status hanya boleh diisi setelah langkah benar-benar dijalankan.

## Prasyarat umum

| ID | Prasyarat |
|---|---|
| PRE-01 | Stack PostgreSQL, Redis, migrator, API, worker, beat, dan Nginx dapat dijalankan. |
| PRE-02 | Database uji berada pada migration head `015_system_audit_logs`. |
| PRE-03 | Tersedia akun admin dan viewer sintetis. |
| PRE-04 | Tersedia stub atau sandbox Zabbix, S3-compatible storage, perangkat/driver, webhook, dan SMTP sesuai test. |
| PRE-05 | Clock dan timezone environment uji dikendalikan atau dapat diobservasi. |

## Autentikasi dan pengguna

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-AUTH-01 | FR-01 | Akun aktif | Login dengan kredensial valid, lalu panggil `/auth/me`. | Login `200`, cookie session dipasang, dan profil aktif dikembalikan tanpa secret. |
| TC-AUTH-02 | FR-01 | Akun aktif | Login dengan password salah. | Request ditolak dan session tidak dibuat. |
| TC-AUTH-03 | FR-01 | Session aktif | Logout dengan CSRF valid, lalu panggil `/auth/me`. | Logout `204`; session lama tidak dapat dipakai. |
| TC-AUTH-04 | FR-03 | Session aktif | Ubah password dengan konfirmasi berbeda, lalu ulangi dengan data valid. | Konfirmasi berbeda ditolak; perubahan valid berhasil dan session user dicabut. |
| TC-AUTH-05 | FR-03 | Email terdaftar dan email acak | Kirim forgot-password untuk kedua alamat. | Keduanya memberi respons netral yang tidak mengungkap keberadaan akun. |
| TC-AUTH-06 | FR-03 | Token reset valid, expired, dan acak | Coba reset untuk setiap token dan uji konfirmasi password. | Hanya token valid dengan konfirmasi cocok yang berhasil; token tidak dapat dipakai ulang. |
| TC-USER-01 | FR-02 | Admin login | Buat user admin/viewer, coba username duplikat dan role tidak didukung. | User valid dibuat; duplikat dan role lain ditolak. |
| TC-USER-02 | FR-02 | Viewer login | Panggil list, create, dan deactivate user. | Seluruh endpoint admin ditolak `403`. |
| TC-USER-03 | FR-02 | Admin dan target user aktif | Nonaktifkan target, coba login target, lalu coba nonaktifkan diri sendiri. | Target tidak dapat login; histori tetap ada; self-deactivation ditolak. |

## Perangkat dan driver

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-DEV-01 | FR-04 | Stub Zabbix berisi host baru dan lama | Jalankan sync, ubah atribut host, lalu sync ulang. | Perangkat dibuat lalu diperbarui berdasarkan `zabbix_host_id` tanpa duplikasi. |
| TC-DEV-02 | FR-04 | Perangkat pernah tersinkron | Hilangkan host dari stub dan jalankan sync. | Record tidak dihapus dan berubah menjadi `source_present=false`. |
| TC-DEV-03 | FR-04 | Dataset lebih besar dari satu halaman | Uji filter status, pencarian, limit, offset, dan detail. | Item dan total konsisten dengan filter; detail ID tidak ada memberi `404`. |
| TC-DRV-01 | FR-05 | Database uji | Ambil registry. | Empat driver bawaan aktif muncul dengan key unik; mock tidak muncul di production. |
| TC-DRV-02 | FR-05 | Admin login | Buat lalu ubah driver parametrik dengan payload valid dan tidak valid. | Definisi valid tersedia di registry; validasi field menolak payload salah. |
| TC-DRV-03 | FR-05 | Admin dan target sandbox | Jalankan endpoint test driver untuk hasil valid serta kegagalan koneksi/validasi. | Hasil sesuai taxonomy driver dan tidak membocorkan credential/output sensitif. |
| TC-DRV-04 | FR-05 | Driver kustom dan bawaan ada | Hapus driver kustom, lalu coba path kustom pada key bawaan. | Driver kustom tidak lagi aktif; driver bawaan tidak terhapus. |

## Pengaturan dan scheduler

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-SET-01 | FR-06 | Admin dan perangkat aktif | Simpan driver, retention, serta jadwal pada menit kelipatan lima. | Setting tersimpan dan `next_run_at` dihitung. |
| TC-SET-02 | FR-06 | Admin login | Simpan menit bukan kelipatan lima, retention asing, atau jadwal aktif tanpa driver. | Setiap kombinasi invalid ditolak tanpa perubahan parsial. |
| TC-SET-03 | FR-06 | Dua perangkat | Aktifkan slot waktu sama pada keduanya. | Setting kedua ditolak oleh aturan unik slot aktif. |
| TC-SET-04 | FR-06 | Viewer login | Coba update dan delete setting. | Kedua operasi ditolak `403`. |
| TC-SCH-01 | FR-08 | Setting jatuh tempo dan memenuhi syarat | Jalankan dispatch scheduler. | Satu job scheduled dibuat, di-enqueue, dan jadwal berikutnya diperbarui. |
| TC-SCH-02 | FR-08 | Setting disabled, tanpa driver, perangkat tidak present, atau belum jatuh tempo | Jalankan dispatch. | Tidak ada job yang dibuat untuk record yang tidak memenuhi syarat. |
| TC-SCH-03 | FR-08 | Queue stub gagal | Dispatch setting jatuh tempo. | Job tercatat `FAILED` dengan stage/code aman dan jadwal tidak menghasilkan job aktif yatim. |

## Job dan pipeline backup

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-BKP-01 | FR-07, NFR-02 | Admin, perangkat siap | Panggil backup manual dan ukur waktu respons tanpa menunggu koleksi. | API mengembalikan `202` dengan job `QUEUED`; pekerjaan berjalan di worker. |
| TC-BKP-02 | FR-07 | Perangkat tanpa driver atau repository aktif | Panggil backup manual. | Request ditolak dengan code domain yang sesuai dan tidak membuat job runnable. |
| TC-BKP-03 | FR-07 | Sudah ada job aktif perangkat yang sama | Panggil backup manual lagi. | Job aktif ganda ditolak. |
| TC-BKP-04 | FR-10 | Zabbix menyatakan perangkat down | Jalankan job. | Job berakhir `SKIPPED_DEVICE_DOWN` tanpa koleksi/upload. |
| TC-BKP-05 | FR-10 | Zabbix menyatakan unknown | Jalankan job. | Job berakhir `SKIPPED_STATUS_UNKNOWN` tanpa koleksi/upload. |
| TC-BKP-06 | FR-10 | Driver menghasilkan konfigurasi invalid | Jalankan job. | Job gagal pada validasi sebelum PUT S3. |
| TC-BKP-07 | FR-10 | Driver dan S3 berhasil | Jalankan backup konten baru. | Tahap berjalan berurutan; PUT diikuti GET, verifikasi, pemeriksaan hash, snapshot, dan terminal sukses. |
| TC-BKP-08 | FR-10 | S3 stub gagal pada PUT atau GET verifikasi | Jalankan backup untuk masing-masing failure point. | Job gagal pada stage storage/verifikasi, tidak membuat snapshot sukses, dan pesan tidak memuat secret. |
| TC-JOB-01 | FR-09 | Job pada tiap state aktif | Coba seluruh transisi yang diizinkan. | Transisi valid berhasil dan timestamp/attempt diperbarui sesuai service. |
| TC-JOB-02 | FR-09 | Job terminal dan pasangan state invalid | Coba memindahkan terminal atau melompati state. | Transisi ditolak dan state lama bertahan. |
| TC-JOB-03 | FR-09 | Job aktif berumur lebih dari satu jam tanpa lease | Jalankan watchdog; sertakan kontrol job dengan lease. | Job tanpa lease menjadi `FAILED`; job dengan lease tidak diubah. |

## Deduplikasi, snapshot, dan retention

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-DED-01 | FR-11 | Belum ada snapshot perangkat | Backup konfigurasi valid. | Snapshot pertama `baseline`, config object baru dibuat. |
| TC-DED-02 | FR-11 | Baseline ada | Backup konfigurasi normalized yang berbeda. | Snapshot `changed` dan object baru dibuat. |
| TC-DED-03 | FR-11 | Object sebelumnya ada | Backup konten sama dengan object valid, lalu ulangi saat object hilang/korup. | Object valid dipakai ulang sebagai `no_change`; object gagal restore tidak dipakai dan diganti sesuai pipeline. |
| TC-SNP-01 | FR-15 | Snapshot retained pada repository aktif | Download sebagai admin, lalu coba viewer, snapshot expired, dan repository salah. | Admin menerima file terverifikasi; kondisi lain ditolak sesuai akses/state. |
| TC-SNP-02 | FR-16 | Job sukses dan gagal | Selesaikan kedua job. | Job sukses punya maksimal satu snapshot; job gagal tidak membuat snapshot sukses. |
| TC-SNP-03 | FR-16 | Snapshot dari dua repository | Ambil detail dan list berdasarkan perangkat. | Repository dan config object terkait benar, tanpa pencampuran scope. |
| TC-SNP-04 | FR-16 | Dataset snapshot dengan retained/expired dan nama berbeda | Uji filter, search, limit, dan offset. | Hasil dan total mengikuti parameter implementasi. |
| TC-RET-01 | FR-17 | Dataset melewati batas dua policy | Jalankan evaluasi `dry_run=true`. | Ringkasan keputusan tersedia dan tidak ada row/object berubah. |
| TC-RET-02 | FR-17 | Snapshot terbaru berada di luar tier lain | Jalankan retention nyata. | Snapshot latest good tetap retained dan memiliki mark yang benar. |
| TC-RET-03 | FR-17 | Object tidak lagi direferensikan snapshot retained | Jalankan retention nyata. | Object menjadi `pending_delete`; belum langsung dihapus dari S3. |
| TC-RET-04 | FR-17 | Object pending melewati grace period dan kontrol masih direferensikan | Jalankan purge. | Hanya object tanpa referensi yang dihapus dan ditandai `deleted`; kontrol bertahan. |

## Storage repository

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-S3-01 | FR-12 | Endpoint S3 valid dan invalid | Jalankan test connection pada keduanya. | Koneksi valid berhasil; kegagalan jaringan/auth ditampilkan aman tanpa secret. |
| TC-S3-02 | FR-12 | Bucket kosong dari manifest | Init repository. | Manifest dibuat dan diverifikasi melalui restore drill; record initialized tersimpan. |
| TC-S3-03 | FR-12 | Bucket sudah memiliki manifest | Jalankan init lagi. | Overwrite tanpa otorisasi ditolak dan manifest lama tidak berubah. |
| TC-S3-04 | FR-12 | Manifest existing dan password benar/salah | Jalankan unlock untuk keduanya. | Password benar memasang repository; password salah gagal tertutup. |
| TC-S3-05 | FR-12 | Dua repository initialized | Aktifkan bergantian dan disconnect. | Hanya satu aktif; disconnect menghasilkan tidak ada repository aktif tanpa menghapus histori. |
| TC-S3-06 | FR-12 | Repository kosong dan repository yang masih direferensikan | Delete keduanya. | Repository yang aman dihapus; repository berreferensi ditolak sesuai aturan service. |

## Kriptografi payload S3

| ID | Requirement | Vektor | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-CRYPTO-01 | FR-14, NFR-01 | Empty bytes, teks kecil, byte non-UTF-8, dan file besar sesuai batas environment | Encrypt lalu decrypt setiap vektor dengan DEK yang sama. | Hasil byte-identik dan envelope mengikuti spesifikasi kanonis. |
| TC-CRYPTO-02 | FR-14, NFR-01 | Plaintext dengan marker unik | Jalankan `put_config_object` dan inspeksi body PUT stub. | Body adalah envelope, bukan plaintext; marker plaintext tidak tampak langsung pada object. |
| TC-CRYPTO-03 | FR-14 | Repository tanpa credential/manifest valid dan crypto stub gagal | Coba upload untuk tiap kondisi. | Upload dihentikan dengan `S3ServiceError`; tidak ada PUT plaintext sebagai fallback. |
| TC-CRYPTO-04 | FR-15, NFR-01 | Envelope valid lalu satu bit salt, IV, MAC, atau ciphertext diubah | Decrypt setiap variasi sambil spy operasi AES. | `IntegrityVerificationError` terjadi dan decryptor AES tidak dipanggil. |
| TC-CRYPTO-05 | FR-15, NFR-01 | Envelope valid dan DEK salah | Coba decrypt. | Verifikasi HMAC gagal sebelum dekripsi dan tidak ada plaintext dikembalikan. |
| TC-CRYPTO-06 | FR-15, NFR-01 | Byte kosong, envelope di bawah panjang minimum kanonis, padding rusak dengan MAC valid pada fixture, `NBZ1` dengan zlib rusak, dan plaintext legacy terverifikasi tanpa marker | Jalankan restore setiap vektor. | Empty/truncated ditolak; padding/zlib rusak memberi `DecryptionError`; payload legacy valid dikembalikan tanpa dekompresi. |
| TC-CRYPTO-07 | FR-13 | Repository berisi payload sebelum rotasi | Rotasi dengan password lama benar, periksa DEK manifest lama/baru, lalu restore payload lama; ulangi dengan password salah dan conflict ETag. | DEK tetap sama dan restore berhasil; password salah/conflict tidak merusak manifest lama. |

## Health, laporan, dan notifikasi

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-HLT-01 | FR-18 | API hidup tanpa session | Panggil `/healthz` dan `/api/v1/healthz`. | Keduanya `200` tanpa autentikasi dan hanya menyatakan liveness. |
| TC-HLT-02 | FR-18 | User login dan data job/perangkat | Panggil dashboard summary. | Angka mengikuti query data dan hak akses endpoint. |
| TC-HLT-03 | FR-18 | Ceph health success, warning, dan failure stub | Panggil endpoint health Ceph. | Status/summary dinormalisasi dan kegagalan tidak membocorkan credential. |
| TC-RPT-01 | FR-19 | Dataset lintas tanggal/status/perangkat | Export XLSX dengan filter. | Workbook hanya memuat record yang cocok dan media type/nama file benar. |
| TC-RPT-02 | FR-19 | Dataset laporan | Export PDF. | PDF valid, media type/nama file benar, dan konten mengikuti filter. |
| TC-RPT-03 | FR-19 | User login | Minta format yang tidak didukung dan rentang tanggal invalid. | Request ditolak tanpa file parsial. |
| TC-NTF-01 | FR-20 | Webhook stub sukses | Selesaikan job pada terminal state yang dikonfigurasi. | Satu notifikasi aman dikirim dengan referensi job tanpa secret/config. |
| TC-NTF-02 | FR-20 | Webhook timeout/error | Selesaikan job sukses atau gagal. | Error notifikasi tercatat, tetapi terminal state utama tidak berubah. |

## Audit dan Security Logs

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-LOG-01 | FR-22 | Database sesi audit | Buat record log berbagai kategori (`SECURITY`, `AUDIT`, `BACKUP_JOB`, `STORAGE`, `AUTH`), lalu jalankan filter kategori, severity, search text, dan ID. | Query mengembalikan jumlah record dan item yang tepat sesuai parameter filter. |
| TC-LOG-02 | FR-22 | Dataset log dengan berbagai severity | Panggil perhitungan statistik audit `AuditLogService.get_stats`. | Metrik `total_logs`, `security_incidents`, `failed_logins`, `system_errors`, serta breakdown kategori dan severity terhitung akurat. |
| TC-LOG-03 | FR-23 | Dataset log terfilter | Ekspor data log ke format Excel (.xlsx). | Menghasilkan binary workbook valid, lembar summary ber-styling, dan data tabular lengkap dengan pewarnaan severity. |
| TC-LOG-04 | FR-23 | Dataset log terfilter | Ekspor data log ke format PDF (.pdf). | Menghasilkan dokumen PDF 2-pass landscape A4 valid ber-watermark, kartu KPI, nomor halaman dinamis, dan lembar verifikasi otorisasi. |
| TC-LOG-05 | FR-22 | Security middleware aktif | Kirim HTTP request dengan payload SQL injection (misal: `' OR 1=1`, `UNION SELECT`). | Request langsung diblokir `400/403` dan event `SQLI_ATTEMPT` tercatat di `system_audit_logs` dengan severity `CRITICAL`. |
| TC-LOG-06 | FR-22 | Security middleware aktif | Kirim HTTP request dengan payload Cross-Site Scripting (misal: `<script>`, `javascript:`). | Request diblokir dan event `XSS_ATTEMPT` tercatat di `system_audit_logs` dengan severity `CRITICAL`. |
| TC-LOG-07 | FR-22 | Security middleware aktif | Kirim HTTP request dengan payload path traversal (`../`, `..\\`). | Request diblokir dan event `PATH_TRAVERSAL_ATTEMPT` tercatat di `system_audit_logs` dengan severity `CRITICAL`. |
| TC-LOG-08 | FR-22 | Security middleware aktif | Kirim HTTP request normal tanpa karakter eksploitasi. | Request diteruskan ke downstream handler secara transparan tanpa interupsi. |

## UI dan aksesibilitas

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-UI-01 | FR-21 | Login admin | Periksa seluruh action operasional utama. | Control admin tersedia sesuai state resource. |
| TC-UI-02 | FR-21 | Login viewer | Periksa dashboard dan dialog. | Control perubahan tersembunyi/nonaktif, sedangkan fungsi baca tetap tersedia. |
| TC-UI-03 | FR-21 | Session viewer | Kirim request admin langsung tanpa UI. | Backend menolak `403`; UI bukan satu-satunya enforcement. |
| TC-UI-04 | NFR-08 | API dapat ditunda, dikosongkan, dan digagalkan | Buka perangkat, snapshot, dan dialog utama pada tiap kondisi. | Loading, empty, error, dan retry tampil tanpa layout rusak. |
| TC-UI-05 | NFR-08 | Browser desktop | Navigasi seluruh dialog dengan Tab, Shift+Tab, Enter, dan Escape. | Fokus terperangkap saat dialog aktif, label terbaca, dan fokus kembali ke pemicu. |
| TC-UI-06 | NFR-08 | Viewport ponsel, tablet, desktop; light/dark | Uji tabel, form, dialog, status, dan target sentuh. | Tidak ada overflow halaman yang menghalangi aksi; tabel dapat di-scroll; status tidak bergantung pada warna saja. |

## Database, deployment, dan dokumentasi

| ID | Requirement | Prasyarat khusus | Langkah ringkas | Hasil yang diharapkan |
|---|---|---|---|---|
| TC-OPS-01 | NFR-03 | Metadata dibuat, Redis berisi data sementara | Restart/flush Redis uji tanpa menghapus PostgreSQL, lalu pulihkan service. | Metadata user, perangkat, job, object, dan snapshot tetap ada; session/queue sementara dapat hilang sesuai fungsi Redis. |
| TC-OPS-02 | NFR-06 | Volume database baru | Jalankan `docker compose up -d --build`. | Migrator mencapai head sebelum API/worker/beat healthy/running. |
| TC-OPS-03 | NFR-06 | Stack berjalan | Periksa health, restart API/worker/beat, dan jalankan prosedur rollback pada environment uji. | Health pulih, data persisten bertahan, dan langkah rollback dapat dijalankan tanpa merusak volume. |
| TC-DB-01 | NFR-04 | Database uji dengan tabel/kolom kritis sengaja hilang | Mulai API pada mode non-test untuk tiap variasi. | Startup ditolak dengan pesan schema mismatch yang tidak memuat credential. |
| TC-DB-02 | NFR-05 | Database hasil migration head | Inspeksi tipe kolom timestamp/daily time dan uji scheduler sekitar pergantian hari Jakarta. | Timestamp operasional timezone-aware; `daily_time` lokal; perhitungan jadwal sesuai `Asia/Jakarta`. |
| TC-DOC-01 | NFR-07 | Worktree dokumentasi | Jalankan secret scan terhadap file tracked dan review contoh konfigurasi. | Tidak ada nilai credential nyata; seluruh nilai sensitif memakai placeholder. |
| TC-DOC-02 | NFR-07 | Paket dokumen | Periksa UAT, link, ID requirement/test, Mermaid, command, dan endpoint terhadap source. | UAT belum berisi hasil; link/ID konsisten; tidak ada klaim lulus tanpa eksekusi. |

## Traceability requirement ke test

Matriks utama berada di kolom Test pada [PRD](../01-product/FEATURE-FINAL.md). Setiap ID yang disebut PRD muncul pada dokumen ini. Satu test dapat membuktikan lebih dari satu requirement, seperti `TC-BKP-01` untuk FR-07 dan NFR-02.

## Referensi automated test yang tersedia

| Area | File |
|---|---|
| Primitive dan payload crypto | `tests/unit/test_crypto_standalone.py` |
| Repository, manifest, upload, dan restore | `tests/unit/test_storage_repository.py` |
| Hardening dan rotasi | `tests/unit/test_review_hardening_items.py` |
| Audit logging, WAF threat inspection & export | `tests/unit/test_audit_logs.py` |
| Domain lain | File lain di `tests/unit/` dan `tests/integration/` bila tersedia |

Keberadaan file test tidak berarti seluruh test sudah lulus. Status hanya dilaporkan dari eksekusi pada commit dan environment yang disebutkan.
