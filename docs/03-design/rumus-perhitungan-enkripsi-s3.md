# Rumus dan Perhitungan Kriptografi Enkripsi Konfigurasi ke S3 Storage

Dokumen ini merinci seluruh rumus matematis, derivasi kunci, fungsi hash, operasi cipher blok/stream, dan perhitungan ukuran byte yang dieksekusi pada alur enkripsi hingga pemulihan (*restore*) file konfigurasi perangkat jaringan ke Ceph S3 storage.

> [!NOTE]
> Spesifikasi arsitektur, diagram alur sistem, dan tata letak amplop kanonis berada pada [Spesifikasi Enkripsi Backup S3](enkripsi-backup-s3.md).

---

## Pemetaan Rumus ke Kode Sumber

| Tahap | Komponen / Modul | Operasi Matematis Utama |
| :--- | :--- | :--- |
| **1. Hash Integritas & Deduplikasi** | `backend/app/services/backup_execution_service.py` | `SHA-256` pada plaintext mentah dan ter-normalisasi |
| **2. Pembukaan KEK (Vault & Manifest)** | `backend/app/crypto/kdf.py`, `vault_crypto.py`, `manifest_crypto.py` | `PBKDF2-HMAC-SHA256` ($100\,000$ putaran) + `AES-256-GCM` |
| **3. Resolusi Direct-DEK** | `backend/app/crypto/payload_crypto.py` (`_resolve_symmetric_key`) | Pemetaan langsung 32-byte / 64-hex atau `SHA-256` tunggal |
| **4. Kompresi Payload** | `backend/app/crypto/payload_crypto.py` | Penanda `NBZ1` + `zlib` DEFLATE level 6 |
| **5. Enkripsi & Autentikasi AEAD** | `backend/app/crypto/payload_crypto.py` (`AESGCM`) | `AES-256-GCM` (`GCTR` + `GHASH` di $GF(2^{128})$ + Tag GMAC) |
| **6. Kalkulasi Ukuran Amplop & Verifikasi** | `backend/app/crypto/payload_crypto.py`, `api/snapshots.py` | Ukuran total byte `NBG2`, verifikasi tag, dan perbandingan `SHA-256` |

---

## 1. Perhitungan Hash Integritas & Deduplikasi (Pre-Enkripsi)

Sumber: `backend/app/services/backup_execution_service.py`

$$\text{object\_sha256} = \text{Hex}\Big(\text{SHA-256}\big(\text{raw\_bytes}\big)\Big)$$

$$\text{content\_sha256} = \text{Hex}\Big(\text{SHA-256}\big(\text{UTF8}(\text{normalize\_config}(\text{collected.text}))\big)\Big)$$

### Keterangan Simbol & Konstanta
- $\text{collected.text}$ & $\text{raw\_bytes}$: teks konfigurasi mentah dari driver dan representasi byte-nya ($\text{collected.text.encode(encoding)}$).
- $\text{normalize\_config}(\cdot)$: fungsi pembersihan teks dinamis per vendor (misalnya timestamp/uptime agar perubahan non-konfigurasi tidak memicu snapshot baru).
- $\text{SHA-256}(\cdot)$: fungsi hash kriptografis $256\text{-bit}$ ($32\text{ byte}$).
- $\text{Hex}(\cdot)$: representasi heksadesimal sepanjang $64\text{ karakter}$.
- $|\text{object\_sha256}| = |\text{content\_sha256}| = 64\text{ karakter} \ (32\text{ byte biner})$.

---

## 2. Perhitungan Derivasi Kunci KEK (`PBKDF2-HMAC-SHA256`)

Sumber: `backend/app/crypto/kdf.py`, `backend/app/crypto/vault_crypto.py`, `backend/app/crypto/manifest_crypto.py`, `backend/app/services/s3_service.py`

Tahap ini dijalankan untuk mendekripsi `master_key_encrypted` dari PostgreSQL (`NBV1`) serta mendekripsi `repo_manifest.enc` dari Ceph S3 (`NBM1`) guna memperoleh DEK (*Data Encryption Key*).

### 2.1 Rumus PBKDF2-HMAC-SHA256 (`derive_key_aes256_gcm`)

$$K_{\text{derived}} = \text{PBKDF2-HMAC-SHA256}(P,\ S,\ c,\ dklen)$$

$$K_{\text{derived}} = U_1 \oplus U_2 \oplus \dots \oplus U_c$$

$$U_1 = \text{HMAC-SHA256}\big(P,\ S \parallel \text{INT\_32\_BE}(1)\big)$$

$$U_i = \text{HMAC-SHA256}\big(P,\ U_{i-1}\big), \qquad 2 \le i \le c$$

### 2.2 Rumus Internal HMAC-SHA256

$$\text{HMAC-SHA256}(K,\ m) = \text{SHA-256}\Big((K' \oplus \text{opad}) \parallel \text{SHA-256}\big((K' \oplus \text{ipad}) \parallel m\big)\Big)$$

### 2.3 Kompleksitas Komputasi & Header AAD Vault/Manifest

$$N_{\text{SHA-256}} = 2 \times c = 2 \times 100\,000 = 200\,000\text{ operasi hash}$$

$$\text{AAD}_{\text{NBV1}} = \texttt{"NBV1"} \parallel S_{16\text{B}} \parallel N_{12\text{B}}, \qquad |\text{AAD}_{\text{NBV1}}| = 4 + 16 + 12 = 32\text{ byte}$$

$$\text{AAD}_{\text{NBM1}} = \texttt{"NBM1"} \parallel S_{16\text{B}} \parallel N_{12\text{B}}, \qquad |\text{AAD}_{\text{NBM1}}| = 4 + 16 + 12 = 32\text{ byte}$$

### Keterangan Simbol & Konstanta
- $P$: `APP_SECRET` pada Vault (`NBV1`) atau `master_password` pada Manifest (`NBM1`).
- $S$: `salt` CSPRNG sepanjang $16\text{ byte}$ ($128\text{ bit}$).
- $c = 100\,000$: jumlah iterasi *key stretching* (RFC 8018 / NIST SP 800-132).
- $dklen = 32\text{ byte}$ ($256\text{ bit}$).
- $\oplus$: operasi XOR bitwise; $\parallel$: operasi penyambungan byte (*concatenation*).
- $\text{INT\_32\_BE}(1)$: bilangan bulat $1$ dalam big-endian $4\text{ byte}$ (`0x00000001`).
- $\text{ipad} = \text{0x36}$ diulang $64\text{ byte}$; $\text{opad} = \text{0x5c}$ diulang $64\text{ byte}$; $K'$ adalah kunci $P$ berukuran blok $64\text{ byte}$.
- Hasil DEK di-cache pada `self._cached_dek` di `S3Service` sehingga $200\,000$ operasi SHA-256 tidak diulang pada setiap file payload.

---

## 3. Perhitungan Resolusi Kunci Payload (*Direct-DEK*)

Sumber: `backend/app/crypto/payload_crypto.py` (`_resolve_symmetric_key`)

Pada level payload S3 (`NBG2`), iterasi PBKDF2 dihilangkan sepenuhnya ($0$ iterasi). DEK repositori dipetakan langsung menjadi kunci simetris $256\text{-bit}$:

$$K_{\text{DEK}} = \begin{cases} k, & \text{jika } k \in \text{bytes} \land |k| = 32\text{ byte} \\ \text{bytes.fromhex}(k), & \text{jika } k \in \text{str} \land |k| = 64\text{ karakter hex valid} \\ \text{SHA-256}\big(\text{UTF8}(k)\big), & \text{jika } k \text{ berupa string/bytes lain (1x hash tunggal)} \end{cases}$$

### Keterangan Simbol & Konstanta
- Pada manifest standar (`manifest_crypto.py`), DEK dibuat dengan `secrets.token_hex(32)` $\implies |k| = 64\text{ karakter hex} \implies |K_{\text{DEK}}| = 32\text{ byte} \ (256\text{ bit})$.
- Ruang pencarian kunci (*keyspace*): $2^{256} \approx 1{,}158 \times 10^{77}$ kemungkinan kunci.

---

## 4. Perhitungan Kompresi Payload (`NBZ1` + DEFLATE)

Sumber: `backend/app/crypto/payload_crypto.py` (`encrypt_payload_aes256`)

Plaintext dikompresi sebelum enkripsi dengan `zlib.compress(raw_bytes, level=6)` lalu diawali magic header $4\text{ byte}$ `b"NBZ1"`:

$$M_{\text{comp}} = \texttt{"NBZ1"} \parallel \text{DEFLATE}_{L=6}\big(\text{raw\_bytes}\big)$$

$$|M_{\text{comp}}| = 4 + \big|\text{DEFLATE}_{L=6}(\text{raw\_bytes})\big|\text{ byte}$$

Rasio penghematan ukuran (*compression ratio*):

$$R_{\text{comp}} = \frac{|M_{\text{comp}}|}{|\text{raw\_bytes}|} \times 100\%$$

### Keterangan Simbol & Konstanta
- $\texttt{"NBZ1"}$: magic bytes $4\text{ byte}$ penanda payload hasil kompresi zlib.
- $\text{DEFLATE}_{L=6}(\cdot)$: stream terkompresi RFC 1950/1951 (LZ77 + Huffman + header zlib $2\text{ byte}$ + checksum Adler-32 $4\text{ byte}$).

---

## 5. Perhitungan Internal Enkripsi & Autentikasi `AES-256-GCM` (AEAD)

Sumber: `backend/app/crypto/payload_crypto.py` (`AESGCM`, standar NIST SP 800-38D)

### 5.1 Pembentukan Nonce, AAD, Counter Awal ($J_0$), dan Hash Subkey ($H$)

$$N = \text{os.urandom}(12), \qquad |N| = 12\text{ byte} = 96\text{ bit}$$

$$A = \text{AAD}_{\text{NBG2}} = \texttt{"NBG2"} \parallel N, \qquad |A| = 4 + 12 = 16\text{ byte} = 128\text{ bit}$$

$$J_0 = N \parallel \text{0x00000001}, \qquad |J_0| = 96 + 32 = 128\text{ bit}$$

$$H = E_{K_{\text{DEK}}}\big(0^{128}\big)$$

### 5.2 Perhitungan Ciphertext via Mode Counter ($\text{GCTR}$ — Kerahasiaan)

Plaintext terkompresi $P = M_{\text{comp}}$ dipecah menjadi $n$ blok $128\text{-bit}$ ($16\text{ byte}$), dengan $n = \lceil |P| / 16 \rceil$:

$$\text{inc}_{32}(X) = \text{MSB}_{96}(X) \parallel \Big(\big(\text{int}(\text{LSB}_{32}(X)) + 1\big) \bmod 2^{32}\Big)$$

$$CB_i = \text{inc}_{32}^{i}(J_0), \qquad i = 1, 2, \dots, n$$

$$C_i = P_i \oplus E_{K_{\text{DEK}}}(CB_i), \qquad i = 1, 2, \dots, n - 1$$

$$C_n^* = P_n^* \oplus \text{MSB}_{|P_n^*|}\Big(E_{K_{\text{DEK}}}(CB_n)\Big)$$

$$C = C_1 \parallel C_2 \parallel \dots \parallel C_n^*, \qquad |C| = |M_{\text{comp}}|$$

### 5.3 Perhitungan Autentikasi $\text{GHASH}$ pada Galois Field $GF(2^{128})$

Input autentikasi disusun dari $A$ dan $C$ dengan padding nol sementara di memori agar kelipatan $128\text{ bit}$ ($16\text{ byte}$):

$$v = 128 \cdot \lceil |A|_{\text{bit}} / 128 \rceil - |A|_{\text{bit}} = 0\text{ bit} \quad (\text{karena } |A|_{\text{bit}} = 128)$$

$$u = 128 \cdot \lceil |C|_{\text{bit}} / 128 \rceil - |C|_{\text{bit}}$$

$$X_{\text{input}} = A \parallel C \parallel 0^u \parallel \big[|A|_{\text{bit}}\big]_{64} \parallel \big[|C|_{\text{bit}}\big]_{64}$$

Pecah $X_{\text{input}}$ menjadi $m$ blok $128\text{-bit}$ ($X_1, X_2, \dots, X_m$), dengan $m = 1 + \lceil |C| / 16 \rceil + 1$:

$$Y_0 = 0^{128}$$

$$Y_i = (Y_{i-1} \oplus X_i) \bullet H, \qquad i = 1, 2, \dots, m$$

$$\text{GHASH}_H(A, C) = Y_m$$

Operator perkalian polinomial $\bullet$ dihitung dalam medan hingga $GF(2^{128})$ modulo polinomial irreduksibel:

$$R(x) = x^{128} + x^7 + x^2 + x + 1$$

### 5.4 Finalisasi Tag Autentikasi GMAC

$$T = \text{MSB}_{128}\Big(\text{GHASH}_H(A, C) \oplus E_{K_{\text{DEK}}}(J_0)\Big), \qquad |T| = 16\text{ byte} = 128\text{ bit}$$

### Keterangan Simbol & Konstanta
- $E_{K_{\text{DEK}}}(\cdot)$: enkripsi satu blok $128\text{-bit}$ menggunakan AES-256 ($14\text{ putaran}$).
- $\text{MSB}_s(X)$ / $\text{LSB}_s(X)$: mengambil $s$ bit paling kiri / paling kanan dari nilai $X$.
- $P_n^*$ dan $C_n^*$: blok terakhir plaintext dan ciphertext berpanjang $1 \le b \le 128\text{ bit}$ tanpa padding PKCS#7.
- $[|A|_{\text{bit}}]_{64}$: panjang bit AAD dalam integer big-endian $64\text{-bit}$ ($128 = \texttt{0x0000000000000080}$).
- $[|C|_{\text{bit}}]_{64}$: panjang bit ciphertext dalam integer big-endian $64\text{-bit}$ ($8 \cdot |C|$).

---

## 6. Perhitungan Ukuran Amplop S3 (`NBG2`) & Persamaan Verifikasi Restore

Sumber: `backend/app/crypto/payload_crypto.py`, `backend/app/api/snapshots.py`

### 6.1 Susunan & Ukuran Total Amplop S3

$$\text{Envelope}_{\text{S3}} = \underbrace{\texttt{"NBG2"}}_{4\text{ byte}} \parallel \underbrace{N}_{12\text{ byte}} \parallel \underbrace{C}_{|M_{\text{comp}}|\text{ byte}} \parallel \underbrace{T}_{16\text{ byte}}$$

$$\text{Overhead}_{\text{NBG2}} = 4\text{ (Magic NBG2)} + 12\text{ (Nonce)} + 4\text{ (Magic NBZ1)} + 16\text{ (GMAC Tag)} = 36\text{ byte}$$

$$\big|\text{Envelope}_{\text{S3}}\big| = 36 + \big|\text{DEFLATE}_{L=6}(\text{raw\_bytes})\big|\text{ byte}$$

$$\big|\text{Envelope}_{\text{S3}}\big|_{\min\text{ (validasi header)}} = 4 + 12 + 0 + 16 = 32\text{ byte}$$

### 6.2 Persamaan Validasi *Fail-Closed* Saat Restore / Download

Saat file diunduh dari S3, proses dekripsi **hanya** mengembalikan plaintext jika keempat kondisi berikut terpenuhi seluruhnya:

$$\text{Validasi Header:} \quad \big|\text{Envelope}_{\text{S3}}\big| \ge 32 \ \land \ \text{Envelope}_{\text{S3}}[0:4] = \texttt{"NBG2"}$$

$$\text{Validasi GMAC:} \quad T_{\text{hitung}} = \text{MSB}_{128}\Big(\text{GHASH}_H(A_{\text{S3}}, C_{\text{S3}}) \oplus E_{K_{\text{DEK}}}(J_0)\Big) \stackrel{?}{=} T_{\text{S3}}$$

$$\text{Dekripsi Counter:} \quad M_{\text{dec}} = \text{GCTR}_{K_{\text{DEK}}}\big(\text{inc}_{32}(J_0),\ C_{\text{S3}}\big)$$

$$\text{Dekompresi & Hash:} \quad \text{SHA-256}\Big(\text{DEFLATE}^{-1}\big(M_{\text{dec}}[4:]\big)\Big) \stackrel{?}{=} \text{object\_sha256}_{\text{DB}}$$

Apabila $T_{\text{hitung}} \neq T_{\text{S3}}$ meskipun hanya berbeda $1\text{ bit}$ (pada AAD, nonce, ciphertext, maupun tag), sistem melempar `IntegrityVerificationError` dan menghentikan proses (*fail-closed*).

---

## 7. Contoh Simulasi Perhitungan Nyata

Misalkan file konfigurasi router sebelum enkripsi memiliki ukuran:

$$|\text{raw\_bytes}| = 10\,240\text{ byte} \quad (10\text{ KiB})$$

1. **Kompresi (`NBZ1` + DEFLATE level 6)** — misalkan termampatkan menjadi $2\,560\text{ byte}$:

   $$|M_{\text{comp}}| = 4 + 2\,560 = 2\,564\text{ byte}, \qquad R_{\text{comp}} = \frac{2\,564}{10\,240} \times 100\% \approx 25{,}04\%$$

2. **Jumlah Blok Counter AES-256-GCM ($\text{GCTR}$)**:

   $$n = \left\lceil \frac{2\,564}{16} \right\rceil = 161\text{ blok} \quad \big(160\text{ blok penuh } 16\text{ B} + 1\text{ blok akhir } 4\text{ B}\big)$$

3. **Jumlah Blok Perkalian $\text{GHASH}$**:

   $$|A| = 16\text{ B} \implies 1\text{ blok}, \qquad |C| = 2\,564\text{ B} \implies u = (161 \times 16 - 2\,564) \times 8 = 96\text{ bit} \ (12\text{ B})$$

   $$m = 1\text{ (AAD)} + 161\text{ (Ciphertext + pad)} + 1\text{ (Length Block)} = 163\text{ blok}$$

4. **Ukuran Akhir File Terenkripsi di Ceph S3**:

   $$\big|\text{Envelope}_{\text{S3}}\big| = 4 + 12 + 2\,564 + 16 = 36 + 2\,560 = 2\,596\text{ byte}$$

---

## Referensi & Pengujian Terkait

- Dokumen induk arsitektur: [Spesifikasi Enkripsi Backup S3](enkripsi-backup-s3.md)
- Simulator visual Web Crypto API: [crypto-animation.html](../../frontend/crypto-animation.html)
- Pengujian unit verifikasi roundtrip, AAD, tag GMAC, dan *fail-closed*: [test_crypto_standalone.py](../../tests/unit/test_crypto_standalone.py)

