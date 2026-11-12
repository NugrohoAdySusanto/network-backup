# Prompt Video Canva AI: Alur & Perhitungan Enkripsi Konfigurasi Network Device ke Ceph S3

Dokumen ini dirancang sebagai **prompt siap pakai (*copy-paste*)** untuk **Canva AI** (Canva Magic Design / Canva Video Generator / Magic Write) agar menghasilkan video penjelasan teknis berbahasa Indonesia dengan **tempo santai, jelas, dan tidak terburu-buru** mengenai alur (*flow*), rumus, serta cara perhitungan enkripsi file konfigurasi perangkat jaringan ke Ceph S3 pada sistem **NetBackup**.

> [!TIP]
> **Cara Pemakaian di Canva AI:**
> 1. Untuk membuat **draf video utuh otomatis** dengan tempo lambat & mudah dipahami, salin seluruh isi **Bagian A (Master Prompt Siap Tempel)** ke Canva AI.
> 2. Untuk menyusun/mengedit video per slide agar penjelasannya lebih leluasa, gunakan **Bagian B (Detail 12 Scene Santai: ~6–7 Menit)** satu per satu.
> 3. Sumber kebenaran teknis dokumen ini diverifikasi langsung dari kode produksi ([`backup_execution_service.py`](../../backend/app/services/backup_execution_service.py), [`s3_service.py`](../../backend/app/services/s3_service.py), [`vault_crypto.py`](../../backend/app/crypto/vault_crypto.py), [`manifest_crypto.py`](../../backend/app/crypto/manifest_crypto.py), [`payload_crypto.py`](../../backend/app/crypto/payload_crypto.py), [`kdf.py`](../../backend/app/crypto/kdf.py)) serta [`enkripsi-backup-s3.md`](enkripsi-backup-s3.md) dan [`rumus-perhitungan-enkripsi-s3.md`](rumus-perhitungan-enkripsi-s3.md).

---

## BAGIAN A — Master Prompt Siap Tempel ke Canva AI (Tempo Santai & Terukur)

Salin blok teks di bawah ini langsung ke Canva AI:

```text
Buatkan video edukasi teknis animasi modern (rasio 16:9, durasi 6–7 menit, 12 Scene) dalam BAHASA INDONESIA berjudul:
"Alur & Cara Menghitung Enkripsi Konfigurasi Perangkat Jaringan ke Ceph S3 (AES-256-GCM AEAD)"

ATURAN TEMPO, PACING, & KETERBACAAN (WAJIB DIPATUHI):
- Jangan terburu-buru. Buat durasi tiap scene minimal 25–40 detik agar audiens punya cukup waktu membaca rumus dan angka.
- Kecepatan voiceover: tenang, artikulatif, dan santai (~120 kata per menit).
- Berikan jeda hening 1,5–2 detik setelah menyebut setiap rumus atau angka penting sebelum masuk ke langkah berikutnya.
- Animasi teks & rumus: tampilkan BARIS DEMI BARIS secara bertahap mengikuti suara narator (jangan memunculkan seluruh rumus sekaligus dalam satu layar penuh).
- Transisi antar scene: gunakan transisi halus (Dissolve / Slide lembut 0,7 detik), hindari potongan cepat atau efek kilat berlebihan.

Gaya Visual & Desain:
- Tema: Dark Tech / Cybersecurity Explainer (latar biru dongker gelap #0A0F18 dan kartu panel #111A28).
- Warna aksen: Biru Cyan (#38BDF8) untuk alur data/kunci, Hijau Emerald (#10B981) untuk kompresi/validasi lulus, Kuning Amber (#F59E0B) untuk rumus/tag, dan Merah Rose (#F43F5E) untuk error Fail-Closed.
- Tipografi: Judul bold bersih (Plus Jakarta Sans / Sans-serif) dan font monospace (Space Mono / Consolas) berukuran besar untuk setiap rumus matematika, ukuran byte, serta blok data.

Struktur Materi Video (12 Scene — Santai & Bertahap):
1. Intro & Masalah Keamanan (25 detik): Mengapa config router/switch (IP, VLAN, password, SNMP) tidak boleh disimpan plaintext di S3. Kenalkan arsitektur 3 Titik AES-256-GCM AEAD: Vault DB ("NBV1") -> Manifest S3 ("NBM1") -> Payload S3 ("NBG2").
2. Flow End-to-End Backup ke S3 (30 detik): Tampilkan satu per satu 6 langkah: Driver CLI -> Backup Service (SHA-256) -> Vault DB (NBV1) -> Manifest S3 (NBM1) -> Payload Crypto (NBG2) -> Upload HTTPS ke Ceph S3.
3. Rumus 1 — Hash SHA-256 Pre-Enkripsi (30 detik):
   - object_sha256 = Hex(SHA-256(raw_bytes)) -> cek keutuhan biner saat restore
   - content_sha256 = Hex(SHA-256(UTF8(normalize_config(collected.text)))) -> cek deduplikasi
   - Panjang output = 256 bit = 32 byte = 64 karakter heksadesimal.
4. Rumus 2 — Pembukaan KEK via PBKDF2-HMAC-SHA256 (35 detik):
   - Proses 2 tingkat: (a) APP_SECRET membuka Master Password di Vault ("NBV1"), lalu (b) Master Password membuka DEK 256-bit di Manifest ("NBM1").
   - Rumus: K_derived = PBKDF2-HMAC-SHA256(P, Salt_16B, c = 100.000, dklen = 32B) = U_1 ⊕ U_2 ⊕ ... ⊕ U_100.000
   - Total komputasi (kunci ≤ 64B) = 2 × 100.000 = 200.000 pemanggilan SHA-256; AAD = 32 byte.
   - DEK disimpan sementara di memori (_cached_dek) agar tidak dihitung ulang tiap file.
5. Rumus 3 & 4 — Direct-DEK & Kompresi NBZ1 (30 detik):
   - Level Payload memakai Direct-DEK: K_DEK = bytes.fromhex(dek_64hex) = 32 byte (256-bit), 0 putaran PBKDF2, ruang kunci 2^256.
   - Kompresi: M_comp = b"NBZ1" || DEFLATE_L6(raw_bytes); |M_comp| = 4 + |DEFLATE_L6(raw_bytes)| byte; Rasio = (|M_comp| / |raw_bytes|) × 100%.
6. Rumus 5A — Inisialisasi AES-256-GCM (35 detik):
   - Nonce N = CSPRNG(12B = 96 bit); Header AAD A = b"NBG2" || N (16B = 128 bit)
   - Counter awal J0 = N || 0x00000001; Subkey Hash H = AES_K_DEK(0^128).
7. Rumus 5B — Enkripsi Stream Counter Mode GCTR (35 detik):
   - Jumlah blok n = ceil(|M_comp| / 16) tanpa padding PKCS#7
   - Counter ke-i: CB_i = inc32^i(J0)
   - C_i = P_i ⊕ AES_K_DEK(CB_i) dan blok akhir parsial memakai MSB(|P_n*|), sehingga |C| = |M_comp|.
8. Rumus 5C — Autentikasi GHASH GF(2^128) & Tag GMAC 16B (35 detik):
   - Susunan input: X_input = A || C || 0^u || [|A|_bit]_64 || [|C|_bit]_64 (m = 1 + n + 1 blok)
   - Iterasi: Y_i = (Y_{i-1} ⊕ X_i) · H mod (x^128 + x^7 + x^2 + x + 1)
   - Tag GMAC: T = MSB_128(Y_m ⊕ AES_K_DEK(J0)) = 16 byte (128 bit).
9. Rumus 6 — Susunan & Ukuran Total Amplop S3 NBG2 (30 detik):
   - Format pita byte: [NBG2 4B] || [Nonce 12B] || [Ciphertext C] || [Tag GMAC 16B]
   - Overhead tetap = 4 (NBG2) + 12 (Nonce) + 4 (NBZ1) + 16 (Tag) = 36 byte
   - Total Ukuran di S3 = 36 + |DEFLATE_L6(raw_bytes)| byte (batas cek header minimum = 32 byte).
10. Studi Kasus Bagian 1 — Hitung Kompresi & Blok GCTR untuk File 10.240 Byte (40 detik):
    - Input |raw_bytes| = 10.240 B -> hasil DEFLATE = 2.560 B
    - Langkah 1: |M_comp| = 4 + 2.560 = 2.564 B (Rasio 25,04%)
    - Langkah 2: n = ceil(2.564 / 16) = 161 blok (160 blok × 16B + 1 blok akhir 4B).
11. Studi Kasus Bagian 2 — Hitung Blok GHASH & Ukuran Akhir di S3 (40 detik):
    - Langkah 3: Pad nol sementara u = (161 × 16) - 2.564 = 12 B (96 bit); m = 1 (AAD) + 161 (Ciphertext) + 1 (Length) = 163 blok
    - Langkah 4: Ukuran akhir di Ceph S3 = 36 + 2.560 = 2.596 B (4B NBG2 + 12B Nonce + 2.564B Ciphertext + 16B Tag GMAC).
12. Alur Restore & Pertahanan Fail-Closed (40 detik):
    - Tampilkan 4 gerbang validasi wajib saat restore: (1) ≥ 32B & "NBG2", (2) T_hitung == T_S3, (3) GCTR decrypt + dekompresi "NBZ1", (4) SHA-256 == object_sha256 di DB.
    - Simulasi visual: ubah 1 bit di Ciphertext atau Nonce/AAD -> Tag GMAC gagal (InvalidTag / IntegrityVerificationError) -> akses ditolak seketika (Fail-Closed).

Gunakan voiceover Bahasa Indonesia yang tenang, ramah edukasi, dan beri jeda antar poin.
```

---

## BAGIAN B — Panduan Detail 12 Scene (Pacing Santai: ~6 Menit 45 Detik)

Gunakan bagian ini untuk menyusun tiap slide di Canva secara presisi agar ritme penyampaian nyaman diikuti audiens.

---

### Scene 1 — Pembuka: Mengapa Backup Harus Dienkripsi? (0:00 – 0:25 | 25 detik)
- **Aturan Visual:** Munculkan teks dan 3 kartu titik kriptografi satu per satu setiap ~5 detik.
- **Judul Layar:** `Mengamankan Konfigurasi Jaringan Sebelum Masuk Ceph S3`
- **Teks Layar:**
  - Data sensitif di config: IP Address, VLAN, SNMP Community, Password/Secret.
  - Solusi NetBackup — **3 Titik AES-256-GCM (AEAD)**:
    1. `Database Vault (NBV1)` — mengamankan kredensial di PostgreSQL
    2. `Repository Manifest (NBM1)` — membungkus DEK di Ceph S3
    3. `At-Rest Payload (NBG2)` — mengamankan file konfigurasi di Ceph S3
- **Narasi (Voiceover — santai ~120 kpm):**
  > "File konfigurasi router dan switch menyimpan informasi penting seperti topologi IP, VLAN, hingga kata sandi akses. *(jeda 1,5 dtk)* Agar tetap aman saat disimpan di Ceph S3, sistem NetBackup melindungi data lewat arsitektur tiga titik berbasis AES-256-GCM AEAD."

---

### Scene 2 — Peta Alur Lengkap (*Flow*) Backup ke Ceph S3 (0:25 – 0:55 | 30 detik)
- **Aturan Visual:** Flowchart horizontal 6 langkah; nyalakan highlight langkah 1 ke 6 satu per satu mengikuti kalimat narator.
- **Judul Layar:** `Alur End-to-End Enkripsi File Konfigurasi ke Ceph S3`
- **Langkah di Layar:**
  1. `Driver CLI` &rarr; Ambil konfigurasi (`collected.text` / `raw_bytes`)
  2. `Backup Service` &rarr; Hitung `object_sha256` & `content_sha256`
  3. `Vault DB (NBV1)` &rarr; Dekripsi `Master Password`
  4. `Manifest S3 (NBM1)` &rarr; Verifikasi & buka `DEK 256-bit`
  5. `Payload Crypto (NBG2)` &rarr; Kompresi `NBZ1` + Enkripsi `AES-256-GCM`
  6. `Ceph RGW S3` &rarr; Upload objek biner via HTTPS/TLS
- **Narasi (Voiceover):**
  > "Mari kita lihat alur lengkapnya secara berurutan. *(jeda 1 dtk)* Pertama, driver mengambil teks konfigurasi dari perangkat. Kedua, sistem menghitung hash SHA-256. *(jeda 1 dtk)* Ketiga dan keempat, master password dibuka dari Vault untuk mengambil kunci DEK 256-bit dari Manifest. *(jeda 1 dtk)* Terakhir, file dikompresi, dienkripsi, lalu dikirim ke Ceph S3."

---

### Scene 3 — Tahap 1: Cara Menghitung Hash Integritas `SHA-256` (0:55 – 1:25 | 30 detik)
- **Aturan Visual:** Tampilkan baris rumus ke-1 dulu (tahan 10 detik), lalu munculkan baris rumus ke-2 dan ukuran outputnya.
- **Judul Layar:** `Tahap 1: Menghitung Hash Integritas & Deduplikasi (SHA-256)`
- **Rumus di Layar (Monospace):**
  ```text
  raw_bytes      = collected.text.encode(encoding)
  object_sha256  = Hex( SHA-256( raw_bytes ) )
  content_sha256 = Hex( SHA-256( UTF8( normalize_config(collected.text) ) ) )

  Panjang Digest = 256 bit = 32 byte = 64 karakter heksadesimal
  ```
- **Narasi (Voiceover):**
  > "Sebelum enkripsi dimulai, sistem menghitung dua sidik jari SHA-256 sepanjang 32 byte atau 64 karakter hex. *(jeda 1,5 dtk)* Object SHA-256 dihitung dari byte mentah untuk memeriksa keutuhan file saat di-restore nanti. *(jeda 1,5 dtk)* Sedangkan Content SHA-256 dihitung setelah teks dinormalisasi agar backup identik tidak disimpan berulang."

---

### Scene 4 — Tahap 2: Cara Menghitung KDF `PBKDF2-HMAC-SHA256` (1:25 – 2:00 | 35 detik)
- **Aturan Visual:** Tunjukkan alur 2 langkah `APP_SECRET -> Vault (NBV1) -> Master Password -> Manifest (NBM1) -> DEK 256-bit`, lalu munculkan rumus PBKDF2 bertahap.
- **Judul Layar:** `Tahap 2: Pembukaan DEK via PBKDF2-HMAC-SHA256 (Vault & Manifest)`
- **Rumus di Layar (Monospace):**
  ```text
  Alur Kunci:
    Vault (NBV1)    : APP_SECRET       --[PBKDF2]--> Master Password
    Manifest (NBM1) : Master Password  --[PBKDF2]--> DEK 256-bit

  Rumus KDF (derive_key_aes256_gcm):
    K_derived = PBKDF2-HMAC-SHA256(P, Salt_16B, c = 100.000, dklen = 32B)
    K_derived = U_1 ⊕ U_2 ⊕ ... ⊕ U_100.000

  Beban Komputasi (kunci ≤ 64B) = 2 × 100.000 = 200.000 operasi SHA-256
  Header AAD (NBV1 & NBM1)      = Magic(4B) || Salt(16B) || Nonce(12B) = 32 Byte
  ```
- **Narasi (Voiceover):**
  > "Untuk membuka kunci enkripsi utama atau DEK, sistem bekerja dalam dua tingkat: Vault memakai APP_SECRET untuk membuka Master Password, lalu Master Password membuka Manifest di S3. *(jeda 1,5 dtk)* Keduanya menggunakan PBKDF2-HMAC-SHA256 sebanyak seratus ribu putaran—sekitar dua ratus ribu operasi SHA-256—untuk memperlambat serangan brute-force. *(jeda 1,5 dtk)* Setelah terbuka, DEK di-cache di memori pada `_cached_dek` agar proses ini tidak perlu diulang pada setiap file."

---

### Scene 5 — Tahap 3: `Direct-DEK` & Kompresi `NBZ1` (2:00 – 2:30 | 30 detik)
- **Aturan Visual:** Bagi layar jadi panel kiri (*Resolusi Kunci*) dan kanan (*Kompresi NBZ1*); tampilkan animasi ukuran teks menyusut saat melewati `DEFLATE Level 6`.
- **Judul Layar:** `Tahap 3: Resolusi Direct-DEK (0 Putaran KDF) & Kompresi NBZ1`
- **Rumus di Layar (Monospace):**
  ```text
  1. Resolusi Kunci Payload (Direct-DEK — payload_crypto.py):
     K_DEK = bytes.fromhex(dek_64hex)  -->  32 Byte (256-bit), 0 putaran PBKDF2
     Ruang Kunci = 2^256 ≈ 1,158 × 10^77 kombinasi

  2. Kompresi Sebelum Enkripsi:
     M_comp   = b"NBZ1" || DEFLATE_L6(raw_bytes)
     |M_comp| = 4 + |DEFLATE_L6(raw_bytes)| byte
     R_comp   = (|M_comp| / |raw_bytes|) × 100%
  ```
- **Narasi (Voiceover):**
  > "Masuk ke tahap enkripsi payload, kunci DEK sepanjang 64 karakter hex langsung diubah menjadi 32 byte tanpa putaran PBKDF2 lagi. Ini mempercepat CPU sambil tetap mempertahankan kekuatan 2 pangkat 256. *(jeda 1,5 dtk)* Berikutnya, teks konfigurasi dikompresi dengan zlib level 6 dan diberi awalan penanda NBZ1 sepanjang 4 byte agar ukuran data jauh lebih ramping sebelum disandikan."

---

### Scene 6 — Tahap 4A: Inisialisasi `AES-256-GCM` & Header `AAD 16B` (2:30 – 3:05 | 35 detik)
- **Aturan Visual:** Munculkan 4 kotak variabel (`N`, `A`, `J0`, `H`) satu per satu dari atas ke bawah dengan jeda 2 detik tiap kotak.
- **Judul Layar:** `Tahap 4A: Pembentukan Nonce, Header AAD 16B, J0 & Subkey H`
- **Rumus di Layar (Monospace):**
  ```text
  1) Nonce Acak CSPRNG :  N  = os.urandom(12)       [12 Byte = 96 bit]
  2) Header AAD        :  A  = b"NBG2" || N         [4 + 12 = 16 Byte = 128 bit]
  3) Counter Awal GCM  :  J0 = N || 0x00000001      [96 + 32 = 128 bit]
  4) Hash Subkey GHASH :  H  = AES_K_DEK(0^128)     [Blok nol dienkripsi AES-256]
  ```
- **Narasi (Voiceover):**
  > "Kini mesin AES-256-GCM menyiapkan empat nilai awal. *(jeda 1 dtk)* Pertama, membangkitkan Nonce acak 12 byte agar setiap hasil enkripsi selalu unik. Kedua, menggabungkan magic marker NBG2 dan Nonce menjadi Header AAD 16 byte. *(jeda 1,5 dtk)* Ketiga, membentuk counter awal J0 untuk penutup tag, dan keempat menghitung subkey H dengan mengenkripsi blok nol menggunakan DEK."

---

### Scene 7 — Tahap 4B: Cara Menghitung Enkripsi Stream `GCTR` (3:05 – 3:40 | 35 detik)
- **Aturan Visual:** Animasi blok `M_comp` dipecah per 16 byte, lalu blok `CB_1, CB_2, ...` di-AES-kan dan di-XOR (`⊕`) dengan blok plaintext menjadi `C_1, C_2, ...`.
- **Judul Layar:** `Tahap 4B: Enkripsi Counter Mode (GCTR) Tanpa Padding`
- **Rumus di Layar (Monospace):**
  ```text
  Jumlah Blok Counter:
    n = ⌈ |M_comp| / 16 ⌉   (pembulatan ke atas per 16 byte / 128 bit)

  Counter & Enkripsi per Blok:
    CB_i = inc32^i(J0),     untuk i = 1, 2, ..., n
    C_i  = P_i ⊕ AES_K_DEK(CB_i)
    C_n* = P_n* ⊕ MSB_{|P_n*|}( AES_K_DEK(CB_n) )   [bila blok akhir < 16B]

  Ukuran Ciphertext = |C| = |M_comp|   (0 byte padding PKCS#7!)
  ```
- **Narasi (Voiceover):**
  > "Untuk mengenkripsi data, mode counter GCTR membagi data terkompresi menjadi n blok berukuran masing-masing 16 byte. *(jeda 1,5 dtk)* Setiap blok counter dinaikkan nilainya, dienkripsi dengan AES-256, lalu di-XOR dengan blok data asli. *(jeda 1,5 dtk)* Karena berupa cipher stream, blok terakhir yang kurang dari 16 byte tidak perlu ditambah padding PKCS7—sehingga ukuran ciphertext persis sama dengan inputnya."

---

### Scene 8 — Tahap 4C: Cara Menghitung Autentikasi `GHASH` & `Tag GMAC` (3:40 – 4:15 | 35 detik)
- **Aturan Visual:** Tunjukkan rantai perkalian `Y_0 -> Y_1 -> ... -> Y_m` dan blok akhir `⊕ AES(J0)` menghasilkan `Tag GMAC 16B`.
- **Judul Layar:** `Tahap 4C: Perhitungan Integritas GHASH pada GF(2^128) & Tag GMAC`
- **Rumus di Layar (Monospace):**
  ```text
  Susunan Input Autentikasi (kelipatan 16 byte di memori):
    X_input = A || C || 0^u || [|A|_bit]_64 || [|C|_bit]_64
    Jumlah Blok GHASH: m = 1 (AAD) + n (Ciphertext) + 1 (Length) = n + 2 blok

  Iterasi Galois Field GF(2^128):
    Y_0 = 0^128
    Y_i = (Y_{i-1} ⊕ X_i) · H   mod (x^128 + x^7 + x^2 + x + 1)

  Finalisasi Tag Autentikasi GMAC (16 Byte):
    T = MSB_128( Y_m ⊕ AES_K_DEK(J0) )
  ```
- **Narasi (Voiceover):**
  > "Secara paralel, sistem menghitung bukti keaslian data bernama tag GMAC. *(jeda 1 dtk)* Header AAD, ciphertext, padding nol sementara di memori, dan informasi panjang bit disusun menjadi total n plus 2 blok. *(jeda 1,5 dtk)* Seluruh blok dikalikan berantai dengan subkey H dalam medan Galois GF dua pangkat 128, lalu di-XOR dengan enkripsi counter J0 untuk menghasilkan Tag GMAC sepanjang 16 byte."

---

### Scene 9 — Tahap 5: Susunan & Rumus Ukuran Amplop S3 (`NBG2`) (4:15 – 4:45 | 30 detik)
- **Aturan Visual:** Pita byte horizontal berwarna dengan label ukuran jelas di bawah tiap segmen; munculkan rumus penjumlahan `4 + 12 + 4 + 16 = 36 Byte`.
- **Judul Layar:** `Susunan Final & Rumus Ukuran File di Ceph S3 (NBG2)`
- **Rumus di Layar (Monospace):**
  ```text
  Envelope_S3 = [NBG2 4B] || [Nonce 12B] || [Ciphertext C] || [Tag GMAC 16B]

  Overhead Tetap = 4 (NBG2) + 12 (Nonce) + 4 (NBZ1) + 16 (GMAC) = 36 Byte
  |Envelope_S3|  = 36 + |DEFLATE_L6(raw_bytes)| Byte

  Batas Minimum Validasi Header Dekripsi = 4 + 12 + 0 + 16 = 32 Byte
  ```
- **Narasi (Voiceover):**
  > "Keempat bagian kemudian digabung menjadi amplop biner NBG2 dan dikirim ke Ceph S3 lewat HTTPS. *(jeda 1,5 dtk)* Jika dijumlahkan, seluruh overhead tetap dari magic NBG2, nonce, penanda kompresi NBZ1, dan tag GMAC hanya 36 byte saja di luar data hasil kompresi."

---

### Scene 10 — Studi Kasus (Bagian 1): Hitung Kompresi & Blok `GCTR` (4:45 – 5:25 | 40 detik)
- **Aturan Visual:** Tampilkan langkah 1 dan langkah 2 saja agar huruf besar dan audiens mudah menghitung bersama.
- **Judul Layar:** `Contoh Hitungan Nyata (1/2): File Router 10.240 Byte`
- **Hitungan di Layar (Monospace — muncul bertahap):**
  ```text
  Diketahui:
    Ukuran File Asli      |raw_bytes|       = 10.240 Byte (10 KiB)
    Setelah Kompresi      |DEFLATE_L6(raw)| =  2.560 Byte

  Langkah 1 — Hitung Payload Terkompresi (NBZ1):
    |M_comp| = 4 + 2.560 = 2.564 Byte
    Rasio    = (2.564 / 10.240) × 100% = 25,04%

  Langkah 2 — Hitung Jumlah Blok Counter (GCTR):
    n = ⌈ 2.564 / 16 ⌉ = 161 blok
      ↳ 2.564 ÷ 16 = 160 sisa 4
      ↳ 160 blok penuh (16B) + 1 blok akhir (4B), tanpa padding!
  ```
- **Narasi (Voiceover):**
  > "Sekarang mari kita praktikkan perhitungannya langkah demi langkah. *(jeda 1 dtk)* Misalkan file konfigurasi router berukuran 10.240 byte, lalu setelah dikompresi zlib menjadi 2.560 byte. *(jeda 1,5 dtk)* Langkah pertama, tambahkan 4 byte penanda NBZ1 sehingga payload menjadi 2.564 byte, atau hemat sekitar 75 persen. *(jeda 2 dtk)* Langkah kedua, bagi 2.564 dengan 16 byte per blok, hasilnya 160 sisa 4. Maka dibutuhkan tepat 161 blok GCTR."

---

### Scene 11 — Studi Kasus (Bagian 2): Hitung Blok `GHASH` & Total S3 (5:25 – 6:05 | 40 detik)
- **Aturan Visual:** Lanjutkan dari angka `161 blok` di Scene 10; tampilkan langkah 3 dan 4 dengan sorotan warna pada angka akhir `2.596 Byte`.
- **Judul Layar:** `Contoh Hitungan Nyata (2/2): Blok GHASH & Total Ukuran di S3`
- **Hitungan di Layar (Monospace — muncul bertahap):**
  ```text
  Langkah 3 — Hitung Blok Perkalian GHASH:
    Ukuran tergenapkan = 161 blok × 16 Byte = 2.576 Byte
    Padding nol sementara u = 2.576 - 2.564 = 12 Byte (96 bit)
    Total Blok GHASH m = 1 (AAD 16B) + 161 (Ciphertext) + 1 (Length Block)
                       = 163 blok perkalian GF(2^128)

  Langkah 4 — Hitung Ukuran Akhir File di Ceph S3:
    |Envelope_S3| = 4 (NBG2) + 12 (Nonce) + 2.564 (C) + 16 (GMAC Tag)
                  = 36 + 2.560 = 2.596 Byte
  ```
- **Narasi (Voiceover):**
  > "Kita lanjut ke langkah ketiga untuk menghitung blok autentikasi GHASH. *(jeda 1 dtk)* Karena blok terakhir berisi 4 byte, di memori ditambahkan 12 byte nol sementara agar genap 161 blok penuh, ditambah 1 blok AAD di awal dan 1 blok panjang bit di akhir—total menjadi 163 blok perkalian. *(jeda 2 dtk)* Langkah keempat, jumlahkan seluruh komponen: 4 byte header, 12 byte nonce, 2.564 byte ciphertext, dan 16 byte tag GMAC. Ukuran akhir yang tersimpan aman di Ceph S3 adalah 2.596 byte."

---

### Scene 12 — Alur Restore, Prinsip *Fail-Closed* & Penutup (6:05 – 6:45 | 40 detik)
- **Aturan Visual:** Layar terbelah 2 kolom: Kiri hijau (*Restore Valid*), Kanan merah (*Simulasi Manipulasi 1 Bit -> Ditolak*).
- **Judul Layar:** `Verifikasi Restore & Keamanan Fail-Closed`
- **Teks & Rumus Validasi di Layar (Monospace):**
  ```text
  4 Syarat Wajib Saat Restore / Download:
    1. |Data| ≥ 32 Byte dan Data[0:4] == b"NBG2"   (gagal -> DecryptionError)
    2. T_hitung == T_S3                            (gagal -> IntegrityVerificationError)
    3. Dekripsi GCTR + Dekompresi b"NBZ1"
    4. SHA-256(Plaintext) == object_sha256_DB
  ```
- **Narasi (Voiceover):**
  > "Saat administrator memulihkan atau mengunduh konfigurasi, sistem melakukan empat pemeriksaan ketat. *(jeda 1 dtk)* Header harus berawalan NBG2 minimal 32 byte, tag GMAC yang dihitung ulang harus seratus persen cocok, stream NBZ1 harus bisa didekompresi, dan hash SHA-256 harus sama dengan catatan database. *(jeda 1,5 dtk)* Jika ada manipulasi sekecil apa pun—bahkan hanya 1 bit pada ciphertext atau header—verifikasi tag gagal dan proses langsung dihentikan secara fail-closed demi menjaga keamanan jaringan Anda."

---

## BAGIAN C — Prompt Opsional untuk Membuat Aset Visual Tambahan di Canva Media

Jika ingin menghasilkan ilustrasi/diagram terpisah di fitur **Canva Text-to-Image / Magic Media** untuk latar slide:
- **Background Hero & Intro:**
  > `Dark futuristic network operations center background, glowing cyan and emerald fiber optic data streams flowing into a secure cryptographic vault shield, minimal dark navy #0A0F18 aesthetic, clean vector tech illustration, no random text`
- **Ilustrasi Blok Amplop Biner:**
  > `Clean technical isometric diagram of an encrypted data packet block floating on dark slate background #111A28, segmented glowing bars in cyan, emerald, amber, and purple light, minimalist cybersecurity infographic style, no gibberish text`
