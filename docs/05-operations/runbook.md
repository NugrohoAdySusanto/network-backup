# Runbook NetBackup

## Tujuan

Runbook ini dipakai untuk deployment, health check, rollback, operasi backup/restore S3, dan penanganan insiden. Jalankan perintah dari root repository kecuali dinyatakan lain.

Kontak insiden: [ISI: tim, kanal, dan jadwal on-call]

## Batas kewenangan

- Deployment dan rollback dilakukan oleh personel yang memiliki akses host dan persetujuan perubahan.
- Jangan menghapus volume, bucket, object, repository, atau row database saat diagnosis awal.
- Jangan menjalankan downgrade migration tanpa meninjau dampak data dan kompatibilitas kode.
- Jangan menyalin credential atau isi konfigurasi perangkat ke tiket, chat, atau log tambahan.
- Restore produk berarti mengunduh file snapshot terverifikasi. Aplikasi tidak mendorong konfigurasi kembali ke perangkat.

## Pemeriksaan sebelum deployment

1. Pastikan worktree atau artefak release menunjuk commit yang disetujui.
2. Review migration baru dari revision produksi sampai `head`.
3. Pastikan `.env`, `known_hosts`, dan CA S3 tersedia pada host target tanpa masuk Git.
4. Pastikan kapasitas disk untuk image, volume PostgreSQL, dan Redis cukup.
5. Buat backup database sebelum perubahan schema.
6. Konfirmasi window perubahan dan rencana rollback.

Backup database:

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > netbackup-predeploy.sql
```

Validasi bahwa file tidak kosong dan simpan sesuai kebijakan backup organisasi. File dump dapat memuat data sensitif dan tidak boleh di-commit.

## Deployment

### Deployment awal

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs migrator
```

Isi `.env` sebelum `docker compose config`. Service `migrator` harus keluar dengan status sukses. API, worker, dan beat tidak boleh dianggap siap bila migrator gagal.

Jika akun awal dibutuhkan:

```bash
docker compose run --rm api python -m app.cli.bootstrap_users
```

### Pembaruan release

```bash
docker compose build migrator api worker beat
docker compose up migrator
docker compose up -d api worker beat nginx
docker compose ps
```

Periksa log migrator sebelum menaikkan service aplikasi. Compose juga memiliki dependency startup, tetapi pengecekan operator tetap diperlukan untuk release production.

## Verifikasi setelah deployment

```bash
curl --fail https://netbackup.makuku.co.id/healthz
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
docker compose logs --tail=100 beat
```

Verifikasi fungsional minimum:

1. Login dengan akun uji yang diizinkan.
2. Buka dashboard dan daftar perangkat.
3. Periksa status repository aktif.
4. Periksa Ceph health melalui UI/API terautentikasi.
5. Jalankan backup pada perangkat uji yang disetujui.
6. Pastikan job mencapai state terminal dan snapshot dapat diunduh.

Jangan memakai keberhasilan `/healthz` sebagai bukti seluruh dependency sehat. Endpoint itu hanya liveness proses API.

## Rollback aplikasi

Rollback dipilih bila release baru gagal dan perbaikan cepat tidak aman. Tentukan release lama yang sudah disetujui:

```bash
NETBACKUP_RELEASE_REF="ISI_REFERENSI_RELEASE"
git switch --detach "$NETBACKUP_RELEASE_REF"
docker compose build api worker beat
docker compose up -d api worker beat nginx
docker compose ps
```

Ganti nilai placeholder sebelum menjalankan. Jika release baru sudah menerapkan migration, pastikan kode lama kompatibel dengan schema baru. Pendekatan utama adalah rollback kode yang forward-compatible.

### Pemulihan database dari dump

Pemulihan database adalah tindakan berdampak tinggi. Lakukan hanya pada target yang sudah diverifikasi, setelah API, worker, dan beat dihentikan, serta setelah perubahan pascadeployment diperhitungkan.

```bash
docker compose stop api worker beat
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < netbackup-predeploy.sql
docker compose up -d migrator api worker beat nginx
```

Jangan memakai prosedur ini bila dump akan menimpa transaksi valid yang harus dipertahankan. Untuk production, ikuti juga prosedur restore PostgreSQL organisasi.

## Operasi repository S3

### Test dan inisialisasi

1. Login sebagai admin.
2. Buka S3 Storage Management.
3. Isi endpoint, bucket, access key, secret key, serta opsi secure.
4. Jalankan Test Connection.
5. Untuk bucket baru, pilih Initialize dan buat password master.
6. Pastikan restore drill manifest berhasil sebelum repository dianggap initialized.

Init menolak bucket yang sudah memiliki `repo_manifest.enc`. Untuk repository existing, gunakan Unlock, bukan Initialize.

### Mengaktifkan atau memutus repository

- Activate menjadikan satu repository target backup baru.
- Disconnect membuat tidak ada repository aktif tanpa menghapus histori.
- Snapshot tetap terikat pada repository asal.
- Jangan menghapus repository yang masih direferensikan data.

### Rotasi password master

1. Pastikan repository dapat diakses dan manifest memiliki metadata ETag/version yang diperlukan.
2. Pilih Rotate Password.
3. Masukkan password master saat ini dan password baru.
4. Tunggu verifikasi manifest baru selesai.
5. Download satu snapshot lama sebagai restore regression check.

Rotasi mempertahankan DEK repository. Jangan menghapus password lama dari penyimpanan operasional sampai verifikasi selesai dan kebijakan organisasi mengizinkan.

## Menjalankan backup S3

1. Pastikan perangkat `source_present=true` dan availability memenuhi kebijakan.
2. Pastikan driver sudah dipilih.
3. Pastikan repository yang benar aktif.
4. Pilih Backup Now sebagai admin.
5. Catat job ID dan pantau state.
6. Pada sukses, buka histori/snapshot dan periksa repository serta change status.

Untuk jadwal, aktifkan schedule, pilih slot lima menit yang belum dipakai, dan periksa `next_run_at`.

## Restore dari S3

1. Login sebagai admin.
2. Pastikan repository asal snapshot sedang aktif dan dapat dijangkau.
3. Buka perangkat, lalu Backup Archives.
4. Pilih snapshot retained.
5. Download file.
6. Pastikan nama file dan isi sesuai perangkat/timestamp yang dipilih.

Backend mengambil object S3, memverifikasi integritas, mendekripsi, memproses format kompresi, lalu memeriksa hash plaintext sebelum mengirim file. Jika salah satu tahap gagal, jangan memakai object mentah dari bucket sebagai pengganti hasil restore.

## Retention

Dry-run melalui API/UI admin harus dilakukan sebelum eksekusi manual nyata pada insiden atau perubahan policy. Alur normal:

1. Evaluasi snapshot dan retention marks.
2. Pertahankan latest known good.
3. Tandai object tanpa referensi retained sebagai `pending_delete`.
4. Tunggu grace period.
5. Purge memeriksa ulang referensi dengan row lock sebelum menghapus object S3.

Jangan menghapus object langsung dari bucket untuk memperbaiki ketidaksesuaian retention.

## Health dan observabilitas

| Area | Pemeriksaan | Indikator masalah |
|---|---|---|
| API | `curl --fail https://netbackup.makuku.co.id/healthz` | Non-2xx, timeout |
| Container | `docker compose ps` | Restart loop, unhealthy, migrator gagal |
| API log | `docker compose logs --tail=200 api` | Startup schema mismatch, dependency error |
| Worker | `docker compose logs --tail=200 worker` | Task crash, lock/lease, driver, S3 error |
| Scheduler | `docker compose logs --tail=200 beat` | Dispatch/retention tidak terjadwal |
| PostgreSQL | Health container dan query aplikasi | Connection atau migration mismatch |
| Redis | Health container | Queue/session/lock gagal |
| S3 | Test connection dan repository status | Bucket/auth/network/manifest gagal |
| Zabbix | Sync dan integration status | Token, group, atau network gagal |

Log tidak boleh memuat secret. Jika ditemukan, batasi akses log, rotasi credential terkait, dan eskalasi sebagai insiden keamanan.

## Troubleshooting

| Gejala | Kemungkinan penyebab | Tindakan aman |
|---|---|---|
| API tidak start setelah deploy | Migration gagal atau schema kritis hilang | Periksa log migrator/API; jangan bypass schema check; perbaiki migration atau rollback release. |
| Login berulang kembali ke dialog | Cookie secure/origin salah, Redis/session bermasalah | Periksa `APP_BASE_URL`, `COOKIE_SECURE`, reverse proxy, dan Redis tanpa menyalin cookie. |
| Perangkat tidak muncul | Sync Zabbix gagal, group salah, atau perangkat ditandai tidak present | Periksa integration log dan jalankan sync admin; validasi group ID. |
| Backup tetap queued | Worker mati atau broker tidak tersedia | Periksa `docker compose ps`, log worker, dan Redis. |
| Backup di-skip | Availability down/unknown atau perangkat tidak present | Verifikasi Zabbix dan konektivitas; jangan paksa dengan mengubah database. |
| Driver gagal validasi | Output kosong, command/paging salah, atau keyword/minimum length tidak cocok | Jalankan test driver pada target uji; koreksi definisi tanpa mencatat output sensitif. |
| Upload S3 gagal | Repository tidak aktif, manifest/credential gagal, network, bucket, atau permission | Jalankan Test Connection, periksa repository/manifest dan log request ID. |
| `IntegrityVerificationError` | Kunci salah, salt/IV/MAC/ciphertext berubah, atau object korup | Hentikan restore, pertahankan object untuk investigasi, uji snapshot lain, dan eskalasi. Jangan bypass HMAC. |
| Envelope terlalu pendek/kosong | Object terpotong atau key menunjuk object salah | Bandingkan metadata object dan database; pulihkan dari versi/replikasi storage bila tersedia. |
| Object S3 tidak ditemukan | Object terhapus di luar aplikasi, bucket/key salah, atau repository asal tidak aktif | Verifikasi repository asal, bucket, key metadata, dan versioning storage; jangan membuat row pengganti manual. |
| Dekompresi `NBZ1` gagal | Plaintext terdekripsi tetapi stream zlib rusak | Perlakukan sebagai korup; jangan hapus marker atau mengembalikan byte parsial. |
| Password master ditolak | Password salah atau manifest tidak sesuai repository | Verifikasi repository/bucket dan sumber password; jangan init ulang bucket existing. |
| Backup lama gagal setelah rotasi | Rotasi/manifest salah, repository asal tidak aktif, atau objek legacy | Hentikan rotasi lanjutan, periksa metadata manifest, uji rollback manifest sesuai prosedur service, dan eskalasi. |
| Snapshot tidak bisa diunduh | Expired, object bukan `available`, repository asal tidak aktif, atau hash gagal | Periksa state snapshot/object/repository; jangan ubah status langsung di database. |
| Retention tidak purge | Grace period belum lewat atau object masih direferensikan | Periksa mark, `pending_delete`, waktu, dan referensi; biarkan pemeriksaan ulang service bekerja. |
| Notifikasi gagal tetapi backup sukses | Webhook tidak tersedia | Perbaiki integrasi; jangan ubah hasil backup utama. |

## Pengumpulan bukti insiden

Kumpulkan hanya:

- waktu dan timezone;
- commit/release;
- request ID, job ID, snapshot ID, dan repository ID;
- state, failure stage, dan error code aman;
- status container dan potongan log yang sudah disanitasi;
- perubahan terbaru yang relevan.

Jangan mengumpulkan password, token, secret key, cookie session, DEK, file konfigurasi perangkat, atau body envelope ke kanal umum.

## Penutupan insiden

1. Konfirmasi health dan satu alur backup/restore pada target uji.
2. Dokumentasikan akar masalah dan perubahan pemulihan.
3. Buat test regression jika defect ada pada kode.
4. Perbarui runbook bila tindakan baru terbukti diperlukan.
5. Catat pemilik tindak lanjut: [ISI: nama/peran atau sistem ticketing].
