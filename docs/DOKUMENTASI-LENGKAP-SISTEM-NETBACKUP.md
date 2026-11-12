# DOKUMENTASI LENGKAP ARSITEKTUR, REKAYASA SISTEM, DAN OPERASIONAL
# NETBACKUP — CENTRALIZED NETWORK CONFIGURATION BACKUP DASHBOARD

**Versi Dokumentasi:** 2.0 (Konsolidasi Final & Tervalidasi Kode)  
**Institusi / Organisasi:** PT Lucky Mom Indonesia  
**Klasifikasi:** Dokumentasi Teknis & Naskah Tugas Akhir (TA)  
**Basis Waktu Sistem:** `Asia/Jakarta` (WIB, UTC+7)  
**URL Produksi:** `https://netbackup.makuku.co.id`  
**Status Pengujian Kode:** 116/116 Unit Tests Lulus (100% fungsionalitas inti, keamanan, audit, dan driver terverifikasi)

---

## DAFTAR ISI MASTER

1. [BAGIAN I: PERENCANAAN PROYEK & GAMBARAN UMUM (PLAN)](#bagian-i-perencanaan-proyek--gambaran-umum-plan)
   - 1.1 Latar Belakang Masalah
   - 1.2 Tujuan dan Manfaat Sistem
   - 1.3 Project Charter & Identitas Proyek
   - 1.4 Ruang Lingkup Sistem (In-Scope vs Out-of-Scope)
   - 1.5 Pernyataan Khusus Lingkup Kriptografi Tugas Akhir (TA)
   - 1.6 Stakeholder & Tata Kelola
2. [BAGIAN II: ANALISIS KEBUTUHAN SISTEM & PRODUK (REQUIREMENTS & PRODUCT)](#bagian-ii-analisis-kebutuhan-sistem--produk-requirements--product)
   - 2.1 Analisis Kebutuhan Bisnis (BRD — Business Requirements Document)
   - 2.2 Analisis Kebutuhan Produk (PRD — Product Requirements Document)
   - 2.3 Daftar Kebutuhan Fungsional Ber-ID (FR-01 s/d FR-26)
   - 2.4 Daftar Kebutuhan Non-Fungsional Ber-ID (NFR-01 s/d NFR-10)
   - 2.5 User Persona & Hak Akses Berbasis Peran (RBAC)
   - 2.6 Matriks Penelusuran Kebutuhan (Traceability Matrix)
3. [BAGIAN III: ARSITEKTUR SISTEM & DESAIN TEKNIS (ARCHITECTURE & TDD)](#bagian-iii-arsitektur-sistem--desain-teknis-architecture--tdd)
   - 3.1 Pola Arsitektur Modular Monolith
   - 3.2 Diagram Topologi Layanan & Kontainer Docker
   - 3.3 Batasan Tanggung Jawab Komponen Layanan
   - 3.4 Siklus Hidup Eksekusi Backup & Mesin Status (Job State Machine)
   - 3.5 Pola Ketahanan Eksekusi (Distributed Lock, Availability Gate, Fail-Closed)
4. [BAGIAN IV: DESAIN BASIS DATA & RELASI ERD AKTUAL (DATABASE SCHEMA)](#bagian-iv-desain-basis-data--relasi-erd-aktual-database-schema)
   - 4.1 Prinsip Desain Skema & Multi-Repository Scoping
   - 4.2 Diagram Relasi Entitas (ERD Aktual Mermaid)
   - 4.3 Spesifikasi Detail 11 Tabel Basis Data
   - 4.4 Riwayat Migrasi Alembic (001 s/d 015) & Verifikasi Kontrak Startup
5. [BAGIAN V: SPESIFIKASI KONTRAK REST API BACKEND (API CONTRACT)](#bagian-v-spesifikasi-kontrak-rest-api-backend-api-contract)
   - 5.1 Protokol Komunikasi, Sesi Server-Side & Proteksi CSRF
   - 5.2 Rincian Endpoint per Domain Layanan
   - 5.3 Taksonomi Kode Error & Format Respons Standar
6. [BAGIAN VI: EKOSISTEM DRIVER PERANGKAT JARINGAN (DRIVER CONTRACT)](#bagian-vi-ekosistem-driver-perangkat-jaringan-driver-contract)
   - 6.1 Arsitektur Adapter Driver (Base Class & Lifecycle)
   - 6.2 Driver Bawaan (MikroTik, Ruijie AP, Ruijie Switch, Sangfor NSF)
   - 6.3 Backup Worker Management (Custom Parametric CLI Driver Engine)
7. [BAGIAN VII: SPESIFIKASI KRIPTOGRAFI & KOMPRESI S3 (SINGLE SOURCE OF TRUTH)](#bagian-vii-spesifikasi-kriptografi--kompresi-s3-single-source-of-truth)
   - 7.1 Ringkasan Konseptual Alur Kriptografi
   - 7.2 Spesifikasi Parameter Kriptografi Aktual (Ground Truth)
   - 7.3 Diagram Alur Enkripsi Upload & Dekripsi Restore (Mermaid)
   - 7.4 Analisis Keamanan & Prinsip Fail-Closed (Padding Oracle & Bit-Flipping)
   - 7.5 Halaman Demonstrasi & Visualisasi Web
   - 7.6 Glosarium Istilah Kriptografi Terapan
8. [BAGIAN VIII: DESAIN ANTARMUKA & PENGALAMAN PENGGUNA (UI/UX DESIGN SYSTEM)](#bagian-viii-desain-antarmuka--pengalaman-pengguna-uiux-design-system)
   - 8.1 Filosofi Desain Anti-Slop & Kerapatan Informasi
   - 8.2 Token Desain, Palet Warna & Tipografi
   - 8.3 Aksesibilitas WCAG AA & Dukungan Navigasi Keyboard
   - 8.4 Penanganan Tata Letak Responsif (Desktop, Tablet, Mobile)
9. [BAGIAN IX: RANGKUMAN IMPLEMENTASI & DEPENDENSI (IMPLEMENTATION)](#bagian-ix-rangkuman-implementasi--dependensi-implementation)
   - 9.1 Ringkasan Tahapan Pengembangan (Checkpoint C0 s/d C21)
   - 9.2 Manajemen Dependensi Runtime & Development
10. [BAGIAN X: STRATEGI PENGUJIAN & PENJAMINAN MUTU (TESTING & QA)](#bagian-x-strategi-pengujian--penjaminan-mutu-testing--qa)
    - 10.1 Rencana Pengujian (Test Plan)
    - 10.2 Hasil Pengujian Otomatis Pytest Unit Tests
    - 10.3 Skenario Pengujian Khusus Kriptografi (Test Script)
    - 10.4 Format Berita Acara UAT (User Acceptance Testing)
11. [BAGIAN XI: PANDUAN DEPLOYMENT & RUNBOOK OPERASIONAL (OPERATIONS & RUNBOOK)](#bagian-xi-panduan-deployment--runbook-operasional-operations--runbook)
    - 11.1 Prosedur Deployment Awal & Update Rilis
    - 11.2 Konfigurasi Environment Variable (.env)
    - 11.3 Prosedur Operasional Standar (SOP) Backup & Restore
    - 11.4 Matriks Penanganan Insiden & Troubleshooting Runbook
12. [BAGIAN XII: BUKU MANUAL PENGGUNA & PERTANYAAN UMUM (USER MANUAL & FAQ)](#bagian-xii-buku-manual-pengguna--pertanyaan-umum-user-manual--faq)
    - 12.1 Panduan Langkah Pengguna Akhir Berbasis Tugas
    - 12.2 Pertanyaan yang Sering Diajukan (FAQ)

---

# BAGIAN I: PERENCANAAN PROYEK & GAMBARAN UMUM (PLAN)

## 1.1 Latar Belakang Masalah
Dalam operasional infrastruktur jaringan berskala perusahaan (*enterprise*), konfigurasi perangkat aktif seperti Router, Switch, Access Point, dan Next-Generation Firewall merupakan aset digital paling mendasar. Kegagalan operasional jaringan kerap kali terjadi bukan karena kerusakan fisik perangkat keras, melainkan akibat perubahan konfigurasi yang tidak terdokumentasi, kesalahan manusia (*human error*), atau pembaruan sistem yang gagal (*bad configuration push*).

Tantangan utama yang dihadapi meliputi:
1. **Pencadangan Manual yang Terfragmentasi:** Operator jaringan melakukan pencadangan manual melalui salin-tempel teks terminal atau pengunduhan file lokal yang tersebar di laptop teknisi tanpa repositori terpusat.
2. **Ketiadaan Versioning & Deduplikasi:** Proses backup konvensional menghasilkan ribuan duplikasi file konfigurasi yang identik, memboroskan kapasitas penyimpanan dan menyulitkan pelacakan perubahan konfigurasi antar waktu.
3. **Risiko Keamanan Data Tidak Terenkripsi (*Data at-Rest Vulnerability*):** File konfigurasi memuat informasi rahasia tingkat tinggi, termasuk *enable secret*, *community string* SNMP, preshared keys VPN, dan topologi internal. Penyimpanan plaintext pada penyimpanan awan atau object storage pihak ketiga membuka risiko kebocoran data yang fatal.
4. **Keberagaman Vendor (*Multivendor Heterogeneity*):** Setiap vendor (MikroTik, Ruijie, Sangfor, Cisco, Huawei) memiliki sintaksis CLI, protokol transport, penanganan terminal paging, dan prosedur penyimpanan yang berbeda.

## 1.2 Tujuan dan Manfaat Sistem
Sistem **NetBackup** dibangun sebagai platform otomasi terpusat untuk mengelola seluruh siklus hidup konfigurasi perangkat jaringan. Manfaat utama sistem mencakup:
- **Otomasi Terjadwal & Terisolasi:** Proses backup berjalan secara asinkron tanpa memblokir antarmuka web, terkoordinasi melalui antrean worker terdistribusi.
- **Penyimpanan Terenkripsi Mandiri (*Self-Contained Encrypted Storage*):** Seluruh file konfigurasi dikompresi dan dienkripsi sebelum ditransmisikan ke Ceph S3, menjamin keamanan tingkat tinggi tanpa ketergantungan pada keamanan fisik server penyimpanan.
- **Efisiensi Ruang Berbasis Deduplikasi:** Menerapkan deduplikasi Content-Addressable Storage (CAS) berbasis hashing ganda untuk menghindari penyimpanan objek ganda apabila konfigurasi perangkat tidak mengalami perubahan.
- **Kepatuhan Audit:** Menyediakan jejak audit permanen mengenai siapa yang mengeksekusi backup, riwayat pekerjaan, status perangkat, dan ekspor laporan berkala dalam format Excel dan PDF.

## 1.3 Project Charter & Identitas Proyek

| Atribut Proyek | Informasi Rinci |
| :--- | :--- |
| **Nama Proyek** | NetBackup — Enterprise Network Configuration Backup & Lifecycle Management |
| **Institusi Pemilik** | PT Lucky Mom Indonesia |
| **Target Operasional** | Lingkungan Jaringan Enterprise Kantor Pusat, Gudang, dan Gerai Retail |
| **Sponsor Proyek** | `[ISI: Nama Sponsor Proyek / Direktur IT]` |
| **Product Owner** | `[ISI: Nama Product Owner / Lead Network Engineer]` |
| **Project Manager** | `[ISI: Nama Project Manager]` |
| **Lead Architect & Developer**| `[ISI: Nama Penyusun / Mahasiswa Pengembang TA]` |
| **Status Rilis** | Version 2.0 (Production Hardened) |
| **Basis Domain Aktif** | `https://netbackup.makuku.co.id` |

## 1.4 Ruang Lingkup Sistem (In-Scope vs Out-of-Scope)

### Fitur Masuk Ruang Lingkup (In-Scope):
1. **Sinkronisasi Otomatis Zabbix:** Integrasi Zabbix API sebagai *Single Source of Truth* untuk penemuan host jaringan, alamat IP, model/vendor, dan status ketersediaan ICMP (*Availability Pre-Check*).
2. **Ekosistem Driver Multivendor:** Driver bawaan untuk MikroTik RouterOS, Ruijie AP, Ruijie Switch, Sangfor NSF, serta Custom Parametric Driver Builder berbasis web GUI.
3. **Manajemen Penyimpanan Ceph S3:** Pengaturan endpoint, bucket, kredensial, verifikasi sertifikat SSL CA, inisialisasi bucket, dan rotasi master password.
4. **Pipeline Kriptografi & Kompresi S3:** Kompresi zlib, derivasi PBKDF2, enkripsi terotentikasi AES-256-GCM (AEAD) dengan Additional Authenticated Data (AAD), serta pengujian integritas Fail-Closed (dengan kompatibilitas mundur untuk payload legacy).
5. **Deduplikasi & Kebijakan Retensi:** Skema GFS (*Grandfather-Father-Son*: 7 Harian, 4 Mingguan, 12 Bulanan, 3 Tahunan) serta proteksi *Latest Known Good Configuration*.
6. **Pelaporan & Notifikasi:** Ekspor laporan audit Excel (`.xlsx`) dan PDF (`.pdf`) bertanda air, serta notifikasi insiden via webhook Feishu/Lark.
7. **Kontrol Akses Berbasis Peran (RBAC):** Pemisahan hak akses antara Administrator dan Viewer dengan sesi server-side Redis dan proteksi CSRF.

### Fitur di Luar Ruang Lingkup (Out-of-Scope):
- **Push Konfigurasi Otomatis ke Perangkat:** NetBackup secara sengaja tidak melakukan *push restoration* otomatis langsung ke switch/router guna menghindari risiko terputusnya rute trafik produksi (*bricking*). Pemulihan dilakukan dengan mengunduh snapshot terverifikasi untuk diaudit sebelum diterapkan oleh network engineer.
- **Diff Konfigurasi Baris demi Baris di GUI:** Evaluasi perubahan berfokus pada deteksi perbedaan hash konten (*changed* vs *no_change*).
- **Protokol Backup Non-CLI:** Pengambilan konfigurasi melalui TFTP/FTP/SNMP write di luar koneksi SSH/Telnet CLI.

## 1.5 Pernyataan Khusus Lingkup Kriptografi Tugas Akhir (TA)
Sesuai dengan batasan formal Tugas Akhir (TA), pengujian mendalam dan pemodelan matematis kriptografi **HANYA BERLAKU PADA DUA ALUR BERIKUT**:
1. **Alur Upload / Penyimpanan ke S3:** Konfigurasi Teks Plaintext &rarr; Kompresi zlib Deflate (Level 6, Magic Marker `NBZ1`) &rarr; Derivasi Kunci PBKDF2-HMAC-SHA256 (100.000 iterasi, 32-byte) &rarr; Pengikatan AAD Header 32-byte (`NBG1` || Salt || Nonce) &rarr; Enkripsi Terotentikasi AES-256-GCM (Ciphertext + 16B GMAC Tag) &rarr; Pembungkusan Amplop Biner Mandiri &rarr; Upload ke Object Storage Ceph S3.
2. **Alur Restore / Pengambilan dari S3:** Pengunduhan Binary Envelope dari Ceph S3 &rarr; Pemeriksaan Header `NBG1` (atau fallback legacy) &rarr; Derivasi Ulang Kunci PBKDF2 dari DEK Repositori &rarr; Verifikasi Tag GMAC 128-bit & Dekripsi AES-256-GCM (*Fail-Closed Gate*) &rarr; Pemeriksaan Marker `NBZ1` & Dekompresi zlib Inflate &rarr; Restorasi Plaintext Konfigurasi Asli.

> [!IMPORTANT]
> Seluruh mekanisme kriptografi lain di luar dua alur tersebut (seperti hashing password login Argon2id, token sesi Redis, enkripsi kredensial database di kolom PostgreSQL, TLS/HTTPS, dan SSH transport encryption) dinyatakan sebagai **DEPENDENSI INFRASTRUKTUR DI LUAR SCOPE UTAMA TA**. Mekanisme-mekanisme tersebut berfungsi sebagai prasyarat operasional dan tidak menjadi objek analisis kriptografi TA.

## 1.6 Stakeholder & Tata Kelola

| Peran | Pihak Bertanggung Jawab | Tanggung Jawab Utama |
| :--- | :--- | :--- |
| **Sponsor Proyek** | `[ISI: Direksi / Kepala Divisi IT]` | Menyetujui alokasi infrastruktur server, lisensi, dan kebijakan keamanan data. |
| **Product Owner** | `[ISI: Network Operations Lead]` | Menentukan prioritas fitur, validasi integrasi perangkat jaringan, dan kriteria penerimaan. |
| **Lead Developer / Author** | `[ISI: Mahasiswa Pengembang TA]` | Merancang arsitektur perangkat lunak, mengimplementasikan modul backend/frontend, dan menulis pengujian. |
| **Tim Network Operations** | Staf NOC PT Lucky Mom Indonesia | Pengguna utama operasional, memantau riwayat backup, dan melakukan penanganan perangkat offline. |
| **Tim DevOps / SysAdmin** | Tim Infrastruktur Server | Mengelola ketersediaan kluster Ceph S3, server basis data PostgreSQL, dan gateway Nginx. |
| **Dosen Pembimbing TA** | `[ISI: Nama Dosen Pembimbing]` | Memvalidasi ketepatan implementasi algoritma kriptografi, metodologi rekayasa perangkat lunak, dan penulisan naskah. |

---

# BAGIAN II: ANALISIS KEBUTUHAN SISTEM & PRODUK (REQUIREMENTS & PRODUCT)

## 2.1 Analisis Kebutuhan Bisnis (BRD — Business Requirements Document)
1. **Pencegahan Waktu Henti (*Downtime Reduction*):** Ketika insiden kegagalan perangkat keras jaringan terjadi, teknisi harus dapat menemukan dan mengunduh konfigurasi operasional terakhir (*Latest Known Good*) dalam waktu kurang dari 2 menit.
2. **Kepatuhan Regulasi dan Kerahasiaan Data:** Arsip konfigurasi yang disimpan pada media penyimpanan terpusat tidak boleh terbaca dalam bentuk teks murni guna mematuhi standar perlindungan data internal perusahaan.
3. **Efisiensi Penggunaan Bandwidth dan Penyimpanan:** Proses backup harian terhadap puluhan hingga ratusan perangkat tidak boleh membebani trafik WAN perusahaan dan tidak boleh memboroskan kapasitas kluster Ceph S3.

## 2.2 Analisis Kebutuhan Produk (PRD — Product Requirements Document)
Sistem diwujudkan sebagai aplikasi web responsif tanpa ketergantungan *build tools* berat di sisi frontend, berkomunikasi melalui RESTful API berkeamanan tinggi dengan antrean pemrosesan tugas latar belakang.

## 2.3 Daftar Kebutuhan Fungsional Ber-ID (Functional Requirements)

| ID Kebutuhan | Nama Kebutuhan | Deskripsi Fungsional & Kriteria Penerimaan |
| :--- | :--- | :--- |
| **FR-01** | Autentikasi Pengguna & Sesi | Sistem wajib memvalidasi kredensial pengguna secara case-sensitive, menerbitkan cookie session `HttpOnly` server-side berbasis Redis, dan menyediakan token proteksi CSRF. |
| **FR-02** | Manajemen Akun Pengguna | Pengguna dengan peran Administrator dapat membuat, memperbarui, dan menonaktifkan akun pengguna lain. Pengguna tidak dapat menonaktifkan akunnya sendiri. |
| **FR-03** | Manajemen Profil & Sandi | Pengguna dapat memperbarui profil dan mengubah password akun dengan memasukkan password lama dan konfirmasi password baru. |
| **FR-04** | Sinkronisasi Perangkat Zabbix | Sistem menyinkronkan daftar host jaringan dari Zabbix Host Group secara otomatis atau manual, memetakan hostname, IP, vendor, model, dan status ketersediaan. Perangkat yang dihapus di Zabbix ditandai `source_present = false` tanpa menghapus riwayat arsip. |
| **FR-05** | Ekosistem Driver Jaringan | Sistem menyediakan driver bawaan (MikroTik, Ruijie AP, Ruijie Switch, Sangfor) dan antarmuka pembuatan Driver Parametrik Kustom berbasis CLI (SSH/Telnet, port, privilege escalation, paging bypass, regex sanitasi) lengkap dengan fitur uji koneksi *live dry-run*. |
| **FR-06** | Konfigurasi Penjadwalan | Administrator dapat mengaktifkan jadwal harian per perangkat pada slot waktu kelipatan 5 menit dan memilih kebijakan retensi (`standard_31` atau `smart_7_4_12_3`). |
| **FR-07** | Eksekusi Backup Manual | Administrator dapat memicu backup seketika melalui tombol antarmuka web, mengembalikan respons HTTP 202 Accepted dan status `QUEUED` secara instan. |
| **FR-08** | Scheduler Asinkron Otomatis | Celery Beat memeriksa jadwal jatuh tempo setiap 60 detik dan mendistribusikan tugas backup ke Celery Worker tanpa memblokir request API web. |
| **FR-09** | Mesin Status Pekerjaan (State Machine) | Pekerjaan backup bertransisi secara deterministik melalui status: `QUEUED` &rarr; `CONNECTING` &rarr; `EXTRACTING` &rarr; `VALIDATING` &rarr; `HASHING` &rarr; `UPLOADING` &rarr; `SUCCESS_CHANGED` / `SUCCESS_NO_CHANGE` / `FAILED`. |
| **FR-10** | Availability Pre-Check Gate | Sebelum melakukan koneksi SSH, worker memeriksa status Zabbix. Jika perangkat `DOWN`, pekerjaan dihentikan dengan status `SKIPPED_DEVICE_DOWN` untuk menghemat sumber daya. |
| **FR-11** | Deteksi Perubahan Konten | Sistem menormalisasi teks konfigurasi dan menghitung hash SHA-256 konten (`content_sha256`) untuk mendeteksi apakah konfigurasi berstatus `baseline`, `changed`, atau `no_change`. |
| **FR-12** | Deduplikasi Penyimpanan (CAS) | Konfigurasi yang berstatus `no_change` mengaitkan snapshot baru ke objek S3 fisik yang sudah ada (`config_objects`) tanpa melakukan upload ulang byte ke S3. |
| **FR-13** | Kompresi Data Sebelum Enkripsi | Payload konfigurasi dikompresi menggunakan zlib Deflate (Level 6) dan diawali dengan penanda magic header `b"NBZ1"`. |
| **FR-14** | Enkripsi Payload At-Rest S3 | Data terkompresi dienkripsi menggunakan AES-256-GCM (AEAD) dengan kunci 32-byte yang diturunkan dari DEK repositori via PBKDF2-HMAC-SHA256 (100.000 iterasi). |
| **FR-15** | Integritas Pesan AEAD & AAD Binding | Tag autentikasi GMAC 16-byte dihitung terintegrasi di atas ciphertext serta mengikat header 32-byte (`NBG1` + Salt + Nonce) sebagai Additional Authenticated Data (AAD). |
| **FR-16** | Verifikasi Integritas Fail-Closed | Saat pengunduhan konfigurasi, tag autentikasi GMAC diverifikasi secara matematis sebelum dekompresi. Jika tidak cocok, proses dibatalkan seketika dengan melempar `IntegrityVerificationError` tanpa memproses data terkorupsi. |
| **FR-17** | Manajemen Repositori S3 | Administrator dapat mengonfigurasi endpoint S3, nama bucket, access key, secret key, inisialisasi master password, membuka kunci (*unlock*), serta menguji koneksi modal popup. |
| **FR-18** | Rotasi Kredensial Repositori | Administrator dapat memperbarui Master Password repositori melalui mekanisme *re-wrapping* DEK pada manifest S3 tanpa mengharuskan enkripsi ulang seluruh objek snapshot lama. |
| **FR-19** | Unduh Snapshot Terverifikasi | Administrator dapat mengunduh konfigurasi asli dalam bentuk plaintext terverifikasi. Sesi Viewer ditolak untuk mengunduh snapshot. |
| **FR-20** | Eksekusi Kebijakan Retensi | Mesin pembersihan menghapus snapshot yang telah kedaluwarsa secara berkala sesuai kebijakan `standard_31` atau `smart_7_4_12_3`. |
| **FR-21** | Proteksi Latest Known Good | Snapshot terakhir yang berstatus valid/sukses tidak boleh dihapus oleh siklus retensi apa pun, menjamin ketersediaan konfigurasi pemulihan darurat. |
| **FR-22** | Notifikasi Insiden Feishu | Kegagalan backup mengirimkan kartu peringatan diagnostik interaktif ke grup Feishu/Lark secara real-time melalui webhook. |
| **FR-23** | Ekspor Laporan Audit Eksekutif | Sistem menghasilkan laporan riwayat eksekusi backup dalam format Microsoft Excel (`.xlsx`) multi-sheet dan dokumen PDF (`.pdf`) bertanda air institusi. |
| **FR-24** | Antarmuka Pengguna Responsif | Antarmuka web mendukung tema Gelap dan Terang (*Dark/Light Mode*), tata letak adaptif desktop/tablet/mobile, dan tabel dengan kolom hostname terkunci (*sticky*). |
| **FR-25** | Simulator Kriptografi Web | Halaman khusus `/crypto-animation.html` menyediakan demonstrasi animasi alur kriptografi dan laboratorium live Web Crypto API untuk keperluan pengujian dan sidang TA. |
| **FR-26** | Pemantauan Log Audit & Deteksi Ancaman Keamanan | Sistem mengumpulkan seluruh log aktivitas (`SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`) secara real-time, mendeteksi ancaman web (SQL Injection, XSS, Path Traversal, Brute-Force Login, HMAC Tampering) via Security Middleware, menyediakan dasbor analitik terfilter (KPI cards, filter waktu fleksibel, tabel interaktif, modal JSON), dan ekspor laporan resmi (Excel multi-sheet & PDF standar institusi). |

## 2.4 Daftar Kebutuhan Non-Fungsional (Non-Functional Requirements)

| ID NFR | Kategori | Spesifikasi & Batasan Kualitas |
| :--- | :--- | :--- |
| **NFR-01** | Keamanan Data | Seluruh data konfigurasi yang tersimpan di Ceph S3 wajib terenkripsi mandiri (*self-contained envelope*) menggunakan AES-256-GCM AEAD (dengan fallback terverifikasi untuk arsip snapshot legacy). Tidak ada kunci rahasia yang disimpan secara hardcoded di kode sumber. |
| **NFR-02** | Waktu Respons API | Endpoint pemicu backup manual wajib merespons dalam waktu kurang dari 500 ms (asynchronous dispatch), dan query data dashboard merespons dalam waktu kurang dari 200 ms. |
| **NFR-03** | Konkurensi & Mutex | Penguncian terdistribusi berbasis Redis (*Distributed Mutex Lock*) wajib mencegah eksekusi ganda terhadap perangkat yang sama dalam satu jendela waktu. |
| **NFR-04** | Ketersediaan Sistem | Arsitektur kontainer Docker dilengkapi mekanisme *healthcheck* otomatis pada setiap kontainer, dengan kebijakan *restart unless-stopped*. |
| **NFR-05** | Aksesibilitas Visual | Seluruh teks dan kontrol interaktif pada antarmuka web wajib memenuhi standar kontras WCAG AA (rasio kontras minimum 4.5:1 untuk teks normal dan 3:1 untuk komponen antarmuka). |
| **NFR-06** | Aksesibilitas Keyboard | Seluruh elemen tombol, modal, dropdown, dan input form dapat dioperasikan penuh menggunakan keyboard (Tab, Enter, Space, Escape) dengan indikator `:focus-visible` yang jelas. |
| **NFR-07** | Reduksi Gerak (*Reduced Motion*) | Animasi pada antarmuka dan visualizer kriptografi wajib menghormati pengaturan preferensi pengguna `prefers-reduced-motion: reduce`. |
| **NFR-08** | Integritas Basis Data | Skema basis data mematuhi kaidah integritas referensial relasional PostgreSQL dengan batasan *Check Constraints*, *Foreign Keys*, dan *Unique Indexes*. Verifikasi kontrak skema dijalankan otomatis saat startup. |
| **NFR-09** | Kompatibilitas Browser | Antarmuka web bekerja secara konsisten pada peramban modern (Google Chrome, Mozilla Firefox, Microsoft Edge, Safari) tanpa memerlukan plugin tambahan. |
| **NFR-10** | Portabilitas Infrastruktur | Seluruh dependensi aplikasi dikemas dalam berkas `docker-compose.yml` sehingga dapat dideploy secara identik pada lingkungan staging maupun produksi. |

## 2.5 User Persona & Hak Akses Berbasis Peran (RBAC)

```mermaid
graph TD
    User([Pengguna Terautentikasi]) --> CheckRole{Pemeriksaan Peran}
    
    CheckRole -->|Peran: Admin| AdminRole[Akses Administrator Penuh]
    CheckRole -->|Peran: Viewer| ViewerRole[Akses Viewer Terbatas]
    
    AdminRole --> A1[Trigger Manual Backup]
    AdminRole --> A2[Unduh Snapshot Konfigurasi]
    AdminRole --> A3[Kelola Storage S3 & Rotasi Kunci]
    AdminRole --> A4[Kelola Driver Parametrik & Dry-Run]
    AdminRole --> A5[Kelola Jadwal & Retensi]
    AdminRole --> A6[Kelola Pengguna Sistem]
    AdminRole --> A7[Ekspor Laporan Excel/PDF]
    
    ViewerRole --> V1[Lihat Dashboard & Ringkasan KPI]
    ViewerRole --> V2[Lihat Tabel Status Perangkat]
    ViewerRole --> V3[Lihat Riwayat Snapshot Read-Only]
    ViewerRole --> V4[Ekspor Laporan Audit]
    ViewerRole -.->|Ditolak HTTP 403| Blocked[Operasi Perubahan & Unduh File]
```

## 2.6 Matriks Penelusuran Kebutuhan (Traceability Matrix)

| ID Kebutuhan | Modul Implementasi | Rujukan Desain Arsitektur | ID Test Script | Status Pengujian |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01, FR-02** | `app.api.auth`, `app.api.users` | Bab 3.3, Bab 5.2 | `TC-AUTH-01`, `TC-USER-01` | Lulus (Pytest) |
| **FR-04** | `app.services.zabbix_service` | Bab 3.3, Bab 5.2 | `TC-DEV-01`, `TC-DEV-02` | Lulus (Pytest) |
| **FR-05** | `app.drivers.*`, `app.api.drivers`| Bab 6.1, Bab 6.2, Bab 6.3 | `TC-DRV-01`, `TC-DRV-02` | Lulus (Pytest) |
| **FR-06, FR-08** | `app.services.schedule_service` | Bab 3.4, Bab 5.2 | `TC-SET-01`, `TC-SCH-01` | Lulus (Pytest) |
| **FR-07, FR-09** | `app.services.backup_execution`| Bab 3.4, Bab 3.5 | `TC-BKP-01`, `TC-JOB-01` | Lulus (Pytest) |
| **FR-11, FR-12** | `app.services.backup_execution`| Bab 4.3, Bab 7.2 | `TC-CAS-01`, `TC-DEDUP-01`| Lulus (Pytest) |
| **FR-13, FR-14** | `app.crypto.payload_crypto` | Bab 7.2, Bab 7.3 | `TS-CRYPTO-01`, `TC-PAY-01` | Lulus (Pytest) |
| **FR-15, FR-16** | `app.crypto.payload_crypto` | Bab 7.2, Bab 7.4 | `TS-CRYPTO-02`, `TC-SEC-01` | Lulus (Pytest) |
| **FR-17, FR-18** | `app.services.s3_service` | Bab 5.2, Bab 7.2 | `TC-S3-01`, `TS-CRYPTO-05` | Lulus (Pytest) |
| **FR-19** | `app.api.snapshots` | Bab 5.2, Bab 7.3 | `TC-SNAP-01` | Lulus (Pytest) |
| **FR-20, FR-21** | `app.services.retention_service`| Bab 3.3, Bab 4.3 | `TC-RET-01`, `TC-RET-02` | Lulus (Pytest) |
| **FR-22** | `app.services.notification` | Bab 3.3, Bab 11.4 | `TC-NOTIF-01` | Lulus (Pytest) |
| **FR-23** | `app.services.report_service` | Bab 3.3, Bab 5.2 | `TC-REP-01` | Lulus (Pytest) |
| **FR-26** | `app.core.security_middleware`, `app.services.audit_log_service`, `app.services.audit_export_service`, `app.api.audit_logs` | Bab 4.3, Bab 5.2 | `TC-LOG-01` s/d `TC-LOG-08` | Lulus (Pytest) |

---

# BAGIAN III: ARSITEKTUR SISTEM & DESAIN TEKNIS (ARCHITECTURE & TDD)

## 3.1 Pola Arsitektur Modular Monolith
NetBackup mengadopsi pola arsitektur **Modular Monolith** berorientasi kontainer Docker. Pola ini dipilih karena memberikan isolasi domain bisnis yang sangat jelas di dalam basis kode tunggal, mempermudah pemeliharaan dan konsistensi transaksi basis data relasional, sekaligus memisahkan beban komputasi jaringan (*I/O network bound*) ke worker asinkron terpisah.

Komponen utama sistem:
1. **Frontend Presentation Layer:** Single-Page Application berbasis HTML5 semantik, Vanilla JavaScript (ES6+), dan Tailwind CSS yang disajikan langsung oleh gateway Nginx dengan nol dependensi Node.js di lingkungan produksi.
2. **API Gateway & Web Server (Nginx):** Berfungsi sebagai reverse proxy, penanganan SSL/TLS termination, kompresi aset statis, penyedia security headers, dan perutean request `/api/v1/` ke backend FastAPI.
3. **Application Control Layer (FastAPI ASGI):** Menyediakan RESTful API, validasi request berbasis skema Pydantic, proteksi CSRF, otentikasi sesi server-side, dan otorisasi RBAC.
4. **Task Broker & Memory Store (Redis 7):** Berfungsi sebagai message broker antrean Celery, penyimpanan sesi pengguna terenkripsi, dan penyedia distributed mutex lock per perangkat.
5. **Background Execution Engine (Celery Worker & Beat):** Menjalankan tugas pemanggilan CLI jaringan via Netmiko/SSH/Telnet, pemrosesan kompresi, derivasi KDF, enkripsi payload, transmisi S3, dan evaluasi jadwal retensi periodik.
6. **Relational Database (PostgreSQL 16):** Menyimpan metadata perangkat, riwayat pekerjaan, snapshot logis, konfigurasi driver, repositori penyimpanan, dan pengguna sistem.
7. **Object Storage Engine (Ceph RGW / S3):** Menyimpan objek biner payload konfigurasi yang telah terenkripsi secara mandiri (*immutable storage*).

## 3.2 Diagram Topologi Layanan & Kontainer Docker

```mermaid
flowchart TB
    Client([Klien Browser / Network Admin])

    subgraph DOCKER_INFRASTRUCTURE ["Infrastruktur Kontainer Docker (Bridge Network: backup_net)"]
        
        subgraph GATEWAY ["Reverse Proxy Gateway"]
            NGINX["network-backup-nginx-1\nNginx 1.27 Alpine (Port 80)"]
        end

        subgraph BACKEND_API ["Layanan API & Kontrol"]
            API["network-backup-api-1\nFastAPI Python 3.12 (Port 8000)\nUvicorn Worker"]
            MIGRATOR["network-backup-migrator-1\nAlembic DB Migrations\n(Run-Once at Startup)"]
        end

        subgraph STATE_QUEUE ["State & Message Broker"]
            REDIS[("network-backup-redis-1\nRedis 7 Alpine (Port 6379)\n- Session Store\n- Distributed Locks\n- Celery Broker")]
        end

        subgraph ASYNC_ENGINE ["Mesin Eksekusi Latar Belakang"]
            WORKER["network-backup-worker-1\nCelery Worker (Parallel Tasks)\nSSH / Netmiko / Crypto Engine"]
            BEAT["network-backup-beat-1\nCelery Beat Scheduler\n(Periodic Tick 60s)"]
        end

        subgraph PERSISTENT_RDBMS ["Basis Data Relasional"]
            POSTGRES[("network-backup-postgres-1\nPostgreSQL 16 Alpine\nVolume: postgres_data")]
        end
    end

    subgraph EXTERNAL_SERVICES ["Layanan & Infrastruktur Eksternal"]
        ZABBIX[("Zabbix Server API\nSingle Source of Truth\nHost Discovery & Status")]
        CEPH_S3[("Ceph RGW S3 Storage\nBucket Penyimpanan Backup\nPayload Terenkripsi")]
        DEVICES[("Perangkat Jaringan\nRouter, Switch, AP, Firewall\n(MikroTik, Ruijie, Sangfor)")]
        FEISHU[("Feishu / Lark Webhook\nNotifikasi Insiden Real-time")]
    end

    Client <-->|HTTPS :443 / HTTP :80| NGINX
    NGINX <-->|Static Files / HTML / JS| NGINX
    NGINX <-->|Proxy Pass /api/v1| API
    
    API <-->|Session Read/Write & Mutex| REDIS
    API <-->|SQLAlchemy ORM Queries| POSTGRES
    API -.->|Enqueue Manual Backup| REDIS
    
    BEAT -.->|Enqueue Scheduled Backup| REDIS
    REDIS <-->|Fetch Task Jobs| WORKER
    
    WORKER <-->|Update Job States & Snapshots| POSTGRES
    WORKER <-->|Check Device Up/Down| ZABBIX
    WORKER <-->|SSH / Telnet CLI Extraction| DEVICES
    WORKER <-->|Put / Get Encrypted Payload| CEPH_S3
    WORKER -.->|Send Failure Alerts| FEISHU
    
    MIGRATOR -.->|Apply Alembic Head| POSTGRES
```

## 3.3 Batasan Tanggung Jawab Komponen Layanan

| Nama Layanan / Kontainer | Tanggung Jawab Fungsional | Dependensi Utama |
| :--- | :--- | :--- |
| **Nginx (`network-backup-nginx-1`)** | Menyajikan file statis antarmuka web, menerapkan header keamanan HTTP, mengompresi response (Gzip), dan mem-proxy request API ke backend. | Kontainer `api` (Healthcheck OK) |
| **API (`network-backup-api-1`)** | Memvalidasi hak akses (RBAC), menangani autentikasi sesi, memvalidasi payload request Pydantic, menyediakan endpoint CRUD, dan menginisialisasi S3 storage. | `postgres` (Healthy), `redis` (Healthy), `migrator` (Completed) |
| **Worker (`network-backup-worker-1`)** | Melakukan koneksi SSH/Telnet ke perangkat target, ekstraksi teks konfigurasi, normalisasi data, kompresi zlib, derivasi KDF PBKDF2, enkripsi AES-256-GCM (AEAD), dan transmisi S3. | `postgres`, `redis`, Zabbix, Ceph S3, Perangkat Jaringan |
| **Beat (`network-backup-beat-1`)** | Mengevaluasi jadwal backup harian pada tabel `device_backup_settings` setiap menit dan memicu proses pembersihan retensi berkala. | `postgres`, `redis` |
| **Migrator (`network-backup-migrator-1`)** | Menjalankan `alembic upgrade head` secara otomatis saat siklus hidup kontainer dimulai untuk menjamin skema basis data selalu mutakhir sebelum API menerima trafik. | `postgres` (Healthy) |
| **Redis (`network-backup-redis-1`)** | Menampung antrean pesan tugas Celery, menyimpan state sesi pengguna, dan menyediakan mekanisme kunci mutex per perangkat (`lock:device:{id}`). | Volume lokal `redis_data` |
| **PostgreSQL (`network-backup-postgres-1`)** | Menyimpan seluruh model data transaksional, metadata objek, dan jejak audit eksekusi. | Volume lokal `postgres_data` |

## 3.4 Siklus Hidup Eksekusi Backup & Mesin Status (Job State Machine)
Setiap pekerjaan backup dikendalikan oleh mesin status (*finite state machine*) yang ketat dan deterministik.

```mermaid
stateDiagram-v2
    [*] --> QUEUED: Backup Dipicu (Manual / Jadwal)
    
    QUEUED --> CONNECTING: Worker Mengambil Tugas & Mengunci Mutex
    
    CONNECTING --> SKIPPED_DEVICE_DOWN: Availability Check Zabbix = DOWN
    CONNECTING --> SKIPPED_STATUS_UNKNOWN: Availability Check Zabbix = UNKNOWN
    CONNECTING --> FAILED: Koneksi SSH Timeout / Autentikasi CLI Gagal
    
    CONNECTING --> EXTRACTING: Koneksi SSH Berhasil Terbuka
    
    EXTRACTING --> FAILED: Ekstraksi Gagal / Perintah CLI Error
    EXTRACTING --> VALIDATING: Konfigurasi Berhasil Diambil
    
    VALIDATING --> FAILED: Konfigurasi Kosong / Gagal Validasi Keyword
    VALIDATING --> HASHING: Normalisasi Teks Berhasil
    
    HASHING --> UPLOADING: Hitung SHA-256 Konten (Changed / Baseline)
    HASHING --> SUCCESS_NO_CHANGE: Hash Identik dengan Snapshot Terakhir (Deduplikasi)
    
    UPLOADING --> FAILED: Kompresi, Enkripsi AES, atau Upload S3 Gagal
    UPLOADING --> SUCCESS_CHANGED: Payload Terenkripsi Berhasil Masuk S3
    
    SKIPPED_DEVICE_DOWN --> [*]: Mutex Dilepas & Catat Riwayat
    SKIPPED_STATUS_UNKNOWN --> [*]: Mutex Dilepas & Catat Riwayat
    FAILED --> [*]: Kirim Alert Feishu & Lepas Mutex
    SUCCESS_NO_CHANGE --> [*]: Catat Snapshot Baru & Lepas Mutex
    SUCCESS_CHANGED --> [*]: Catat Snapshot Baru & Lepas Mutex
```

## 3.5 Pola Ketahanan Eksekusi
1. **Penguncian Terdistribusi (*Distributed Mutex Lock*):** Sebelum worker menghubungkan sesi SSH ke perangkat, worker meminta kunci mutex ke Redis dengan key `lock:device:{device_id}` dengan masa berlaku tertentu. Jika perangkat sedang dalam proses backup, permintaan kedua langsung ditolak untuk menghindari benturan sesi CLI.
2. **Gerbang Ketersediaan Zabbix (*Availability Pre-Check Gate*):** Zabbix memantau ketersediaan perangkat setiap 30 detik via ICMP/Agent. Sebelum membuka socket SSH yang membutuhkan timeout 15-30 detik, worker menanyakan status Zabbix terlebih dahulu. Perangkat yang berstatus `DOWN` langsung ditandai `SKIPPED_DEVICE_DOWN`, memangkas waktu antrean secara dramatis.
3. **Pemberhentian Aman Saat Kegagalan (*Fail-Closed Security*):** Jika terjadi kegagalan pada tahap kompresi, derivasi kunci, atau transmisi enkripsi, sistem langsung menghentikan proses, menghapus artefak sementara di memori, dan mencatat status `FAILED`. Objek yang tidak terverifikasi keutuhannya tidak akan pernah disimpan ke basis data snapshot.

---

# BAGIAN IV: DESAIN BASIS DATA & RELASI ERD AKTUAL (DATABASE SCHEMA)

## 4.1 Prinsip Desain Skema & Multi-Repository Scoping
Skema basis data NetBackup dibangun di atas PostgreSQL 16 dengan menerapkan prinsip normalisasi bentuk ketiga (3NF) serta pemisahan repositori S3 yang ketat (*Multi-Repository Scoping*). Setiap snapshot, objek konfigurasi, dan pekerjaan backup terikat langsung ke `repository_id` aktif untuk menjamin isolasi data multi-penyimpanan.

## 4.2 Diagram Relasi Entitas (ERD Aktual Mermaid)

```mermaid
erDiagram
    USERS ||--o{ BACKUP_JOBS : "requests (requested_by)"
    USERS ||--o{ DEVICE_BACKUP_SETTINGS : "configures (updated_by)"
    USERS ||--o{ SYSTEM_AUDIT_LOGS : "acted_by (user_id)"
    
    DEVICES ||--|| DEVICE_BACKUP_SETTINGS : "has settings (device_id)"
    DEVICES ||--o{ BACKUP_JOBS : "executes on (device_id)"
    DEVICES ||--o{ CONFIG_OBJECTS : "owns physical objects (device_id)"
    DEVICES ||--o{ SNAPSHOTS : "has logical snapshots (device_id)"
    
    BACKUP_JOBS ||--o| SNAPSHOTS : "generates (backup_job_id)"
    BACKUP_JOBS }o--|| STORAGE_REPOSITORIES : "stored in (repository_id)"
    
    CONFIG_OBJECTS ||--o{ SNAPSHOTS : "referenced by (config_object_id)"
    CONFIG_OBJECTS }o--|| STORAGE_REPOSITORIES : "stored in (repository_id)"
    
    SNAPSHOTS ||--o{ SNAPSHOT_RETENTION_MARKS : "tagged with (snapshot_id)"
    SNAPSHOTS }o--|| STORAGE_REPOSITORIES : "scoped to (repository_id)"
    
    CUSTOM_DRIVERS ||--o{ DEVICES : "assigned via driver_key"
    STORAGE_REPOSITORIES ||--o{ REPOSITORY_DEVICE_SETTING_ARCHIVES : "archives settings (s3_bucket)"
    
    INTEGRATION_STATUS {
        string name PK
        string status
        text summary
        jsonb details
        timestamp last_checked_at
        timestamp last_success_at
        timestamp updated_at
    }

    USERS {
        bigint id PK
        string username UK
        string email
        string password_hash
        string role
        boolean is_active
        timestamp last_login_at
        timestamp created_at
        timestamp updated_at
    }

    DEVICES {
        bigint id PK
        string zabbix_host_id UK
        string hostname
        inet ip_address
        string vendor
        string model
        string host_group
        string availability_status
        timestamp availability_checked_at
        timestamp zabbix_last_sync_at
        boolean source_present
        timestamp created_at
        timestamp updated_at
    }

    DEVICE_BACKUP_SETTINGS {
        bigint device_id PK,FK
        string driver_key
        boolean schedule_enabled
        time daily_time
        timestamp next_run_at
        timestamp last_dispatched_at
        string retention_policy
        bigint updated_by FK
        timestamp updated_at
    }

    BACKUP_JOBS {
        uuid id PK
        bigint device_id FK
        string trigger_type
        bigint requested_by FK
        string driver_key
        uuid repository_id FK
        timestamp scheduled_for
        string celery_task_id
        string state
        string error_class
        text error_message
        text log_excerpt
        string zabbix_status_at_start
        string change_status
        bigint config_object_id FK
        smallint retry_count
        timestamp started_at
        timestamp finished_at
        integer duration_ms
        timestamp created_at
    }

    CONFIG_OBJECTS {
        bigint id PK
        bigint device_id FK
        char content_sha256
        char object_sha256
        string s3_bucket
        text s3_key
        string extension
        bigint size_bytes
        string etag
        string storage_status
        uuid repository_id FK
        timestamp uploaded_at
        timestamp verified_at
        timestamp deleted_at
        timestamp created_at
    }

    SNAPSHOTS {
        bigint id PK
        bigint device_id FK
        uuid backup_job_id FK,UK
        bigint config_object_id FK
        uuid repository_id FK
        timestamp captured_at
        string change_status
        string retention_policy_at_capture
        string display_filename
        boolean is_retained
        timestamp expired_at
        timestamp created_at
    }

    SNAPSHOT_RETENTION_MARKS {
        bigint snapshot_id PK,FK
        string mark_type PK
        timestamp marked_at
    }

    CUSTOM_DRIVERS {
        uuid id PK
        string key UK
        string label
        string vendor_hint
        string model_hint
        string transport
        integer default_port
        integer connect_timeout
        integer command_timeout
        boolean need_enable
        string enable_command
        string enable_prompt_pattern
        string disable_paging_command
        string paging_mode
        string backup_command
        string output_extension
        jsonb strip_patterns
        integer validation_min_length
        string validation_required_keyword
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    STORAGE_REPOSITORIES {
        uuid id PK
        string name
        string endpoint
        string bucket
        string access_key
        string secret_key_encrypted
        boolean secure
        boolean is_active UK
        boolean is_initialized
        string master_key_encrypted
        jsonb repo_manifest
        timestamp created_at
        timestamp updated_at
    }

    SYSTEM_AUDIT_LOGS {
        bigint id PK
        timestamp created_at
        string category
        string severity
        string event_type
        string source_ip
        string user_agent
        bigint user_id FK
        string username
        string endpoint
        text message
        jsonb details
    }

    REPOSITORY_DEVICE_SETTING_ARCHIVES {
        bigint id PK
        string s3_bucket
        string device_hostname
        string device_zabbix_id
        string driver_key
        boolean schedule_enabled
        time daily_time
        string retention_policy
        timestamp updated_at
    }
```

## 4.3 Spesifikasi Detail 12 Tabel Basis Data

### 1. Tabel `users`
Menyimpan kredensial pengguna terautentikasi dan hak akses role-based access control (RBAC).
- `id` (BigInteger, PK, Autoincrement)
- `username` (String(64), Non-Null, Unique Index `uq_users_username`)
- `email` (String(255), Nullable)
- `password_hash` (String(255), Non-Null) — Hash password menggunakan algoritma Argon2id.
- `role` (String(16), Non-Null) — Check constraint: `role IN ('admin', 'viewer')`.
- `is_active` (Boolean, Non-Null, Default: true) — Menandai status keaktifan akun.
- `last_login_at` (DateTime with timezone, Nullable) — Waktu login terakhir.
- `created_at` & `updated_at` (DateTime with timezone, Non-Null, server_default: now())

### 2. Tabel `devices`
Menyimpan inventaris perangkat jaringan yang disinkronkan secara berkala dari Zabbix API.
- `id` (BigInteger, PK, Autoincrement)
- `zabbix_host_id` (String(64), Non-Null, Unique Index `uq_devices_zabbix_host_id`)
- `hostname` (String(255), Non-Null, Indexed)
- `ip_address` (INET, Non-Null) — Tipe data native PostgreSQL untuk validasi IP.
- `vendor` & `model` (String(128), Nullable) — Dideteksi dari Zabbix Inventory.
- `host_group` (String(255), Non-Null) — Grup host Zabbix asal perangkat.
- `availability_status` (String(16), Non-Null, Default: 'unknown') — Check constraint: `IN ('up', 'down', 'unknown')`.
- `availability_checked_at` (DateTime with timezone, Nullable)
- `zabbix_last_sync_at` (DateTime with timezone, Nullable)
- `source_present` (Boolean, Non-Null, Default: true) — `true` jika host masih ada di Zabbix; `false` jika host telah dihapus di Zabbix namun riwayat backup dipertahankan.
- `created_at` & `updated_at` (DateTime with timezone, Non-Null)

### 3. Tabel `device_backup_settings`
Menyimpan konfigurasi pencadangan spesifik untuk setiap perangkat (relasi 1-to-1 dengan `devices`).
- `device_id` (BigInteger, PK, FK &rarr; `devices.id` ON DELETE RESTRICT)
- `driver_key` (String(64), Nullable) — Kunci driver jaringan yang ditugaskan.
- `schedule_enabled` (Boolean, Non-Null, Default: false)
- `daily_time` (Time without timezone, Nullable) — Check constraint: wajib kelipatan 5 menit dan detik = 0 (`minute % 5 = 0 AND second = 0`).
- `next_run_at` (DateTime with timezone, Nullable, Indexed) — Waktu pemicuan jadwal berikutnya.
- `last_dispatched_at` (DateTime with timezone, Nullable)
- `retention_policy` (String(32), Non-Null, Default: 'standard_31') — Check constraint: `IN ('standard_31', 'smart_7_4_12_3')`.
- `updated_by` (BigInteger, Nullable, FK &rarr; `users.id` ON DELETE SET NULL)
- `updated_at` (DateTime with timezone, Non-Null)

### 4. Tabel `backup_jobs`
Menyimpan catatan riwayat dan status eksekusi pekerjaan pencadangan konfigurasi.
- `id` (UUID, PK, Default: uuid4)
- `device_id` (BigInteger, Non-Null, FK &rarr; `devices.id` ON DELETE RESTRICT)
- `trigger_type` (String(16), Non-Null) — Check constraint: `IN ('manual', 'scheduled')`.
- `requested_by` (BigInteger, Nullable, FK &rarr; `users.id` ON DELETE SET NULL)
- `driver_key` (String(64), Nullable)
- `repository_id` (UUID, Nullable, FK &rarr; `storage_repositories.id` ON DELETE SET NULL, Indexed)
- `scheduled_for` (DateTime with timezone, Nullable)
- `celery_task_id` (String(64), Nullable) — ID tugas Celery worker.
- `state` (String(40), Non-Null, Default: 'QUEUED', Indexed) — Status pekerjaan.
- `error_class`, `error_message`, `log_excerpt` (Text, Nullable) — Rincian diagnostik jika terjadi kegagalan.
- `zabbix_status_at_start` (String(16), Nullable) — Status ketersediaan saat tugas dimulai.
- `change_status` (String(16), Nullable) — Check constraint: `IN ('baseline', 'changed', 'no_change')`.
- `config_object_id` (BigInteger, Nullable, FK &rarr; `config_objects.id` ON DELETE SET NULL)
- `retry_count` (SmallInteger, Non-Null, Default: 0)
- `started_at`, `finished_at` (DateTime with timezone, Nullable)
- `duration_ms` (Integer, Nullable) — Durasi total pengerjaan dalam milidetik.
- `created_at` (DateTime with timezone, Non-Null, Indexed desc)

### 5. Tabel `config_objects`
Menyimpan referensi objek fisik konfigurasi yang tersimpan di Ceph S3 (Content-Addressable Storage).
- `id` (BigInteger, PK, Autoincrement)
- `device_id` (BigInteger, Non-Null, FK &rarr; `devices.id` ON DELETE RESTRICT)
- `content_sha256` (CHAR(64), Non-Null) — Hash SHA-256 dari teks plaintext konfigurasi ternormalisasi.
- `object_sha256` (CHAR(64), Non-Null) — Hash SHA-256 dari file fisik biner terenkripsi di S3.
- `s3_bucket` (String(255), Non-Null)
- `s3_key` (Text, Non-Null) — Path objek di S3, format: `{repo_prefix}/{device_id}/{object_sha256}.{ext}`.
- `extension` (String(16), Non-Null) — Ekstensi file (`rsc`, `txt`, dll).
- `size_bytes` (BigInteger, Non-Null) — Ukuran fisik file terenkripsi di S3 dalam bytes.
- `etag` (String(255), Nullable) — ETag dari S3 response.
- `storage_status` (String(16), Non-Null, Default: 'available') — Check constraint: `IN ('available', 'deleted', 'error', 'pending_delete')`.
- `repository_id` (UUID, Nullable, FK &rarr; `storage_repositories.id` ON DELETE SET NULL, Indexed)
- `uploaded_at`, `verified_at`, `deleted_at` (DateTime with timezone, Nullable)
- `created_at` (DateTime with timezone, Non-Null)
- *Unique Constraints:* `uq_config_object_content` (`repository_id`, `device_id`, `content_sha256`) dan `uq_config_object_s3_key` (`repository_id`, `s3_bucket`, `s3_key`).

### 6. Tabel `snapshots`
Menyimpan titik waktu snapshot logis yang mereferensikan `config_objects`.
- `id` (BigInteger, PK, Autoincrement)
- `device_id` (BigInteger, Non-Null, FK &rarr; `devices.id` ON DELETE RESTRICT)
- `backup_job_id` (UUID, Non-Null, Unique FK &rarr; `backup_jobs.id` ON DELETE RESTRICT)
- `config_object_id` (BigInteger, Non-Null, FK &rarr; `config_objects.id` ON DELETE RESTRICT)
- `repository_id` (UUID, Nullable, FK &rarr; `storage_repositories.id` ON DELETE SET NULL, Indexed)
- `captured_at` (DateTime with timezone, Non-Null, Indexed desc)
- `change_status` (String(16), Non-Null) — Check constraint: `IN ('baseline', 'changed', 'no_change')`.
- `retention_policy_at_capture` (String(32), Non-Null) — Kebijakan retensi saat snapshot dibuat.
- `display_filename` (String(255), Non-Null) — Nama file yang ditampilkan ke pengguna saat download.
- `is_retained` (Boolean, Non-Null, Default: true, Indexed) — `false` jika telah kedaluwarsa.
- `expired_at` (DateTime with timezone, Nullable)
- `created_at` (DateTime with timezone, Non-Null)

### 7. Tabel `snapshot_retention_marks`
Menyimpan penanda klasifikasi retensi GFS multi-tingkat pada suatu snapshot.
- `snapshot_id` (BigInteger, PK, FK &rarr; `snapshots.id` ON DELETE CASCADE)
- `mark_type` (String(32), PK, Indexed) — Check constraint: `IN ('STANDARD_WINDOW', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY', 'LATEST_GOOD')`.
- `marked_at` (DateTime with timezone, Non-Null)

### 8. Tabel `custom_drivers`
Menyimpan definisi konfigurasi driver parametrik CLI kustom yang dibuat via web GUI.
- `id` (UUID, PK, Default: uuid4)
- `key` (String(64), Non-Null, Unique Index `ix_custom_drivers_key`)
- `label`, `vendor_hint`, `model_hint` (String(128), Non-Null)
- `transport` (String(32), Non-Null, Default: 'ssh')
- `default_port` (Integer, Non-Null, Default: 22)
- `connect_timeout` (Integer, Non-Null, Default: 15) & `command_timeout` (Integer, Non-Null, Default: 60)
- `need_enable` (Boolean, Non-Null, Default: false)
- `enable_command` (String(64), Non-Null, Default: 'enable')
- `enable_prompt_pattern` (String(64), Non-Null, Default: `[#$]`)
- `disable_paging_command` (String(128), Nullable)
- `paging_mode` (String(32), Non-Null, Default: 'none')
- `backup_command` (String(255), Non-Null, Default: 'show running-config')
- `output_extension` (String(16), Non-Null, Default: 'txt')
- `strip_patterns` (JSONB, Nullable, Default: `[]`)
- `validation_min_length` (Integer, Non-Null, Default: 30)
- `validation_required_keyword` (String(64), Nullable, Default: 'hostname')
- `is_active` (Boolean, Non-Null, Default: true, Indexed)
- `created_at` & `updated_at` (DateTime with timezone, Non-Null)

### 9. Tabel `storage_repositories`
Menyimpan konfigurasi repositori penyimpanan S3 terisolasi.
- `id` (UUID, PK, Default: uuid4)
- `name` (String(128), Non-Null)
- `endpoint` (String(255), Non-Null) — URL Ceph RGW S3.
- `bucket` (String(128), Non-Null)
- `access_key` (String(128), Non-Null)
- `secret_key_encrypted` (String(512), Non-Null) — S3 Secret Key terenkripsi.
- `secure` (Boolean, Non-Null, Default: true) — Wajib HTTPS/SSL.
- `is_active` (Boolean, Non-Null, Default: false, Unique Partial Index: hanya 1 repo aktif bersamaan).
- `is_initialized` (Boolean, Non-Null, Default: false) — Menandai keberadaan `repo_manifest.enc`.
- `master_key_encrypted` (String(512), Nullable) — Master password repositori terenkripsi.
- `repo_manifest` (JSONB, Nullable) — Cache metadata manifest.
- `created_at` & `updated_at` (DateTime with timezone, Non-Null)

### 10. Tabel `integration_status`
Menyimpan status pemeriksaan kesehatan koneksi integrasi pihak ketiga secara real-time.
- `name` (String(64), PK) — Contoh: `'zabbix'`, `'ceph'`, `'feishu'`.
- `status` (String(32), Non-Null) — Contoh: `'healthy'`, `'warning'`, `'error'`.
- `summary` (Text, Nullable)
- `details` (JSONB, Nullable)
- `last_checked_at`, `last_success_at` (DateTime with timezone, Nullable)
- `updated_at` (DateTime with timezone, Non-Null)

### 11. Tabel `system_audit_logs`
Menyimpan jejak audit sistem, pemantauan anomali, dan deteksi ancaman keamanan (*brute-force*, injeksi SQL/XSS, path traversal, dan perusakan integritas kriptografi S3).
- `id` (BigInteger, PK, Autoincrement)
- `created_at` (DateTime with timezone, Non-Null, Indexed)
- `category` (String(32), Non-Null, Indexed) — Nilai: `'STORAGE'`, `'AUTH'`, `'SECURITY'`, `'AUDIT'`, `'BACKUP_JOB'`, `'SYSTEM'`.
- `severity` (String(16), Non-Null, Indexed) — Nilai: `'INFO'`, `'WARNING'`, `'ERROR'`, `'CRITICAL'`.
- `event_type` (String(64), Non-Null, Indexed) — Contoh: `'SQLI_ATTEMPT'`, `'LOGIN_FAILED'`, `'CRYPTO_HMAC_INTEGRITY_TAMPER'`.
- `source_ip` (String(64), Nullable, Indexed) — Alamat IP klien penyerang / operator.
- `user_agent` (String(255), Nullable)
- `user_id` (BigInteger, Nullable, FK `users.id` ON DELETE SET NULL)
- `username` (String(128), Nullable)
- `endpoint` (String(255), Nullable) — URI dan metode request (misal: `'GET /api/v1/devices'`).
- `message` (Text, Non-Null) — Pesan deskripsi insiden / aktivitas yang informatif.
- `details` (JSONB, Nullable) — Payload rincian insiden, regex match, atau error trace.
- Indeks gabungan performa: `ix_audit_logs_filter (created_at DESC, category, severity)`.

### 12. Tabel `repository_device_setting_archives`
Menyimpan arsip snapshot konfigurasi backup perangkat (`driver_key`, `schedule_enabled`, `daily_time`, `retention_policy`) yang terikat pada bucket repositori S3 tertentu saat repositori diputus atau dialihkan, sehingga saat repositori dihubungkan kembali seluruh pengaturan dipulihkan secara instan tanpa kehilangan data.
- `id` (BigInteger, PK, Autoincrement)
- `s3_bucket` (String(128), Non-Null, Indexed `ix_repo_setting_archives_bucket`)
- `device_hostname` (String(255), Non-Null)
- `device_zabbix_id` (String(64), Nullable)
- `driver_key` (String(64), Nullable)
- `schedule_enabled` (Boolean, Non-Null, Default: false)
- `daily_time` (Time without timezone, Nullable)
- `retention_policy` (String(32), Non-Null, Default: 'standard_31')
- `updated_at` (DateTime with timezone, Non-Null, server_default: now())
- Unique constraint: `uq_repo_setting_archives_bucket_hostname (s3_bucket, device_hostname)`.

## 4.4 Riwayat Migrasi Alembic & Verifikasi Kontrak Startup
Evolusi skema dikelola melalui migrasi Alembic di direktori `migrations/versions/`:
- `001_initial_schema.py`: Pembuatan tabel inti `users`, `devices`, `device_backup_settings`, `backup_jobs`, `config_objects`, `snapshots`, `snapshot_retention_marks`, `integration_status`.
- `002_add_auth_tokens.py`: Penambahan token reset password.
- `003_storage_repositories.py`: Pembuatan tabel `storage_repositories`.
- `004_custom_drivers.py`: Pembuatan tabel `custom_drivers`.
- `005_repository_scoping.py`: Penambahan kolom `repository_id` pada `backup_jobs`, `config_objects`, dan `snapshots`.
- `006_smart_retention_indexes.py`: Penambahan index parsial performa retensi.
- `007_unique_active_repo.py`: Penambahan partial unique index `is_active = true` pada `storage_repositories`.
- `008_driver_paging_modes.py`: Penambahan kolom mode paging pada `custom_drivers`.
- `009_multi_repo_unique_constraints.py`: Penambahan constraint majemuk (`repository_id`, `device_id`, `content_sha256`).
- `010_storage_and_custom_drivers.py`: Pembuatan kolom `master_key_encrypted` pada `storage_repositories` dan sinkronisasi seluruh relasi foreign key.
- `011_reconcile_schema_drift.py`: Rekonsiliasi drift skema minor.
- `012_multi_repo_unique.py`: Constraint unik scoping multi-repositori.
- `013_config_object_pending_delete.py`: Status pending delete untuk manajemen siklus retensi S3.
- `014_user_email.py`: Penambahan kolom `email` pada tabel `users`.
- `015_system_audit_logs.py`: Pembuatan tabel `system_audit_logs` dan 6 indeks pencarian audit.
- `016_repo_setting_archives.py` (HEAD): Pembuatan tabel `repository_device_setting_archives` untuk pengarsipan pengaturan backup perangkat per-bucket S3.

**Verifikasi Kontrak Skema saat Startup (`verify_schema_contract`):**  
Saat kontainer `api` dijalankan, fungsi siklus hidup lifespan di `backend/app/main.py` melakukan inspeksi otomatis terhadap skema basis data PostgreSQL. Jika terdapat salah satu dari 12 tabel yang hilang atau kolom kritis (`storage_repositories.master_key_encrypted`, `backup_jobs.repository_id`) belum terpasang, proses startup akan langsung dibatalkan (*Fail-Closed*) untuk mencegah *runtime drift*.

---

# BAGIAN V: SPESIFIKASI KONTRAK REST API BACKEND (API CONTRACT)

## 5.1 Protokol Komunikasi, Sesi Server-Side & Proteksi CSRF
- **Base URL:** `/api/v1` (semua request client diarahkan via Nginx reverse proxy).
- **Format Pertukaran Data:** `application/json` (kecuali endpoint unduh file konfigurasi dan ekspor laporan yang menghasilkan binary stream).
- **Zona Waktu:** Seluruh stempel waktu (*timestamp*) berformat ISO 8601 dengan offset zona waktu eksplisit `+07:00` (`Asia/Jakarta`).
- **Autentikasi:** Berbasis sesi server-side yang disimpan di Redis. Klien menerima cookie sesi bernama `netbackup_session` bertanda `HttpOnly`, `SameSite=Lax`, dan `Path=/`.
- **Proteksi CSRF:** Seluruh request yang mengubah status data (`POST`, `PUT`, `DELETE`) wajib menyertakan header `X-CSRF-Token` yang diperoleh dari endpoint `/api/v1/auth/csrf-token`.

## 5.2 Rincian Endpoint per Domain Layanan

### 1. Domain Autentikasi (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Autentikasi nama pengguna dan password. Memvalidasi kecocokan huruf besar/kecil (case-sensitive). Menghasilkan cookie sesi.
- `POST /api/v1/auth/logout`: Menghapus sesi aktif dari Redis dan mengosongkan cookie sesi klien.
- `GET /api/v1/auth/me`: Mengembalikan profil pengguna terautentikasi (id, username, email, role, permissions).
- `GET /api/v1/auth/csrf-token`: Menghasilkan token CSRF unik yang terikat pada sesi aktif.
- `POST /api/v1/auth/change-password`: Mengubah password pengguna aktif (memerlukan password lama dan konfirmasi password baru).
- `POST /api/v1/auth/forgot-password`: Meminta tautan reset password via email. Memberikan respons status 200 netral untuk mencegah *user enumeration attack*.
- `POST /api/v1/auth/reset-password`: Mengeksekusi perubahan password menggunakan token reset valid yang belum kedaluwarsa.

### 2. Domain Dashboard & Metrik (`/api/v1/dashboard`)
- `GET /api/v1/dashboard/summary`: Mengembalikan ringkasan indikator kinerja utama (KPI): total perangkat terdaftar, target perangkat terjadwal hari ini, jumlah backup berhasil hari ini, rasio keberhasilan backup (%), flag `is_ceph_storage`, detail `active_storage` (nama, bucket, endpoint), status kluster Ceph (hanya disediakan jika storage aktif adalah Ceph), dan status sinkronisasi Zabbix terstruktur (`status`, `is_synced`, `summary`, `last_checked_at`). Seluruh metrik backup terisolasi ke repositori S3 yang sedang aktif.

### 3. Domain Manajemen Perangkat & Zabbix (`/api/v1/devices`)
- `GET /api/v1/devices`: Mengambil daftar inventaris perangkat jaringan dengan dukungan parameter pencarian (`search`), filter status ketersediaan (`availability`), pagination (`limit`, `offset`), dan sorting.
- `GET /api/v1/devices/{device_id}`: Mengambil detail lengkap spesifikasi perangkat, pengaturan backup saat ini, dan riwayat snapshot terbaru.
- `POST /api/v1/devices/sync`: Memerintahkan sinkronisasi manual ke Zabbix API untuk memperbarui daftar host dan status live ICMP. (Khusus Admin).

### 4. Domain Pengaturan Backup Perangkat (`/api/v1/backup-settings`)
- `GET /api/v1/backup-settings/{device_id}`: Mengambil konfigurasi driver yang ditugaskan, jam eksekusi harian, dan kebijakan retensi perangkat.
- `PUT /api/v1/backup-settings/{device_id}`: Memperbarui penugasan driver, mengaktifkan/menonaktifkan jadwal harian (wajib menit kelipatan 5), dan memilih skema retensi (`standard_31` atau `smart_7_4_12_3`). (Khusus Admin, memerlukan CSRF).
- `DELETE /api/v1/backup-settings/{device_id}`: Mereset pengaturan jadwal dan driver perangkat ke default tidak aktif. (Khusus Admin).

### 5. Domain Eksekusi Pekerjaan Backup (`/api/v1/backups`)
- `POST /api/v1/backups/manual`: Memicu pencadangan seketika untuk perangkat tertentu (`{"device_id": 123}`). Mengembalikan status HTTP 202 Accepted beserta ID pekerjaan UUID. Memeriksa ketersediaan mutex dan repositori aktif. (Khusus Admin).
- `GET /api/v1/backups/jobs`: Mengambil daftar riwayat seluruh pekerjaan backup dengan filter status (`QUEUED`, `RUNNING`, `SUCCESS_CHANGED`, `SUCCESS_NO_CHANGE`, `FAILED`), filter perangkat, dan rentang tanggal.
- `GET /api/v1/backups/jobs/{job_id}`: Mengambil status detail proses pekerjaan, stempel waktu per transisi status, diagnostik error, dan kutipan log execution.

### 6. Domain Snapshot & Unduh Konfigurasi (`/api/v1/snapshots` & `/api/v1/devices/{id}/snapshots`)
- `GET /api/v1/devices/{device_id}/snapshots`: Mengambil daftar titik waktu snapshot logis yang dimiliki perangkat pada repositori aktif.
- `GET /api/v1/snapshots/{snapshot_id}`: Mengambil metadata detail snapshot, status perubahan (`baseline`, `changed`, `no_change`), dan ukuran file biner di S3.
- `GET /api/v1/snapshots/{snapshot_id}/download`: **Mengunduh file konfigurasi asli.** Backend mengambil objek biner terenkripsi dari Ceph S3, memverifikasi integritas tag autentikasi GMAC/HMAC, mendekripsi payload AES-256-GCM (atau fallback legacy AES-256-CBC), mendekompresi zlib Deflate, dan mengalirkan teks konfigurasi murni ke browser sebagai attachment file. (Khusus Admin; Viewer ditolak HTTP 403).

### 7. Domain Manajemen Penyimpanan S3 (`/api/v1/storage`)
- `GET /api/v1/storage/repositories`: Mengambil daftar seluruh repositori S3 yang terdaftar (menampilkan status aktif, endpoint, bucket, dan status inisialisasi tanpa membuka kunci rahasia).
- `POST /api/v1/storage/test`: Menguji konektivitas ke endpoint S3, keberadaan bucket, dan keabsahan Access Key / Secret Key melalui operasi `head_bucket`. (Khusus Admin).
- `POST /api/v1/storage/initialize`: Menginisialisasi bucket S3 baru atau kosong dengan Master Password. Membuat berkas manifes terenkripsi `repo_manifest.enc` dan membangkitkan Data Encryption Key (DEK) 256-bit acak. (Khusus Admin).
- `POST /api/v1/storage/unlock`: Membuka kunci repositori S3 yang sudah terpasang manifes dengan memasukkan Master Password yang sesuai. Memverifikasi integritas manifes sebelum menetapkan repositori sebagai aktif. (Khusus Admin).
- `POST /api/v1/storage/repositories/{id}/activate`: Mengaktifkan salah satu repositori yang telah terbuka kuncinya sebagai repositori operasional aktif dan memulihkan arsip pengaturan perangkat yang terkait. (Khusus Admin).
- `POST /api/v1/storage/disconnect` (atau `/api/v1/storage/repositories/{id}/disconnect`): **Mendiskoneksikan Repositori S3 Aktif.** Mencadangkan seluruh pengaturan backup perangkat (`driver_key`, jadwal, retensi) ke tabel `repository_device_setting_archives` per bucket, lalu melepaskan status aktif tanpa galat. (Khusus Admin).
- `DELETE /api/v1/storage/repositories/{id}`: Menghapus data repositori dari database secara aman bila repositori berstatus non-aktif dan tidak lagi memiliki referensi snapshot aktif. (Khusus Admin).
- `POST /api/v1/repositories/{repo_id}/rotate-password`: **Rotasi Master Password Repositori.** Memverifikasi Master Password lama, membungkus ulang DEK 256-bit persisten dengan Master Password baru pada `repo_manifest.enc`, dan memperbarui kredensial tanpa merusak kemampuan dekripsi seluruh snapshot lama. (Khusus Admin).

### 8. Domain Manajemen Driver Jaringan (`/api/v1/drivers`)
- `GET /api/v1/drivers`: Mengambil daftar seluruh driver yang tersedia (gabungan driver bawaan sistem dan custom driver database aktif).
- `POST /api/v1/drivers/custom`: Mendaftarkan konfigurasi Driver Parametrik CLI baru (label, transport, port, privilege escalation, paging bypass, regex strip, keyword validasi). (Khusus Admin).
- `PUT /api/v1/drivers/custom/{key}`: Memperbarui parameter driver kustom yang sudah ada. (Khusus Admin).
- `DELETE /api/v1/drivers/custom/{key}`: Menonaktifkan driver kustom. Driver bawaan sistem diproteksi dan tidak dapat dihapus. (Khusus Admin).
- `POST /api/v1/drivers/test`: Melakukan uji ekstraksi konfigurasi secara langsung (*live dry-run test*) ke perangkat sandbox tanpa menyimpan data ke S3, berguna untuk memverifikasi regex dan prompt driver sebelum digunakan di produksi. (Khusus Admin).

### 9. Domain Pelaporan Audit Eksekutif (`/api/v1/reports`)
- `GET /api/v1/reports/export`: Menghasilkan berkas laporan audit berdasarkan filter tanggal mulai (`start_date`), tanggal selesai (`end_date`), dan format pilihan (`format=xlsx` atau `format=pdf`). Format Excel menghasilkan lembar audit log komprehensif, sedangkan format PDF menyertakan ringkasan eksekutif dan visualisasi KPI.

### 10. Domain Manajemen Pengguna (`/api/v1/users`)
- `GET /api/v1/users`: Menampilkan seluruh daftar pengguna terdaftar beserta peran dan status keaktifan. (Khusus Admin).
- `POST /api/v1/users`: Mendaftarkan akun pengguna baru dengan menetapkan username unik, email, password awal, dan peran (`admin` atau `viewer`). (Khusus Admin).
- `PUT /api/v1/users/{user_id}/deactivate`: Menonaktifkan hak akses pengguna tertentu. (Khusus Admin; dilarang menonaktifkan akun sendiri).

### 11. Domain Pemeriksaan Kesehatan Layanan (`/healthz` & `/api/v1/health/ceph`)
- `GET /healthz`: Pemeriksaan kesiapan layanan dasar backend (memeriksa konektivitas koneksi pool PostgreSQL dan ping Redis). Mengembalikan `{"status": "ok"}` dengan HTTP 200.
- `GET /api/v1/health/ceph`: Memeriksa ketersediaan kluster Ceph S3 dan status operasional penyimpanan objek.

### 12. Domain Pemantauan Log & Audit Keamanan (`/api/v1/logs`)
- `GET /api/v1/logs`: Mengambil daftar log audit dan keamanan sistem terfilter dengan parameter pencarian (`search`), kategori (`category`: `STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`), tingkat keparahan (`severity`: `INFO`, `WARNING`, `ERROR`, `CRITICAL`), rentang waktu fleksibel (`period`: `today`, `24h`, `7d`, `30d`, atau `custom` dengan `start_date` dan `end_date`), pagination (`page`, `page_size`), dan sorting kronologis terbalik. Endpoint dilengkapi mesin auto-backfill idempoten yang memastikan seluruh riwayat backup jobs, akun pengguna, repositori storage, dan pengaturan perangkat tersinkronisasi otomatis. (Khusus Admin / Viewer).
- `GET /api/v1/logs/stats`: Mengambil agregasi metrik audit secara instan: total log tersimpan, jumlah insiden keamanan, jumlah login gagal, total error sistem, serta distribusi frekuensi per kategori dan tingkat keparahan. (Khusus Admin / Viewer).
- `GET /api/v1/logs/export`: Mengekspor data log audit ke format dokumen resmi (`format=xlsx` atau `format=pdf`) dengan filter periode waktu, kategori, dan keparahan yang sama. Format Excel menghasilkan lembar multi-sheet terstruktur dengan metadata ringkasan dan pewarnaan kode baris. Format PDF menghasilkan dokumen laporan audit keamanan berstandar institusi (Landscape A4, stempel waktu ISO, nomor halaman Two-Pass `Halaman X dari Y`, watermark, tabel insiden berwarna sesuai keparahan, dan blok tanda tangan otorisasi). (Khusus Admin / Viewer).
- `GET /api/v1/logs/{log_id}`: Mengambil detail satu entri log audit secara lengkap termasuk payload JSON detail, request ID, IP address klien, user agent, dan jejak traceback error jika terjadi kegagalan sistem. (Khusus Admin / Viewer).

## 5.3 Taksonomi Kode Error & Format Respons Standar
Seluruh respons kesalahan disajikan dalam format JSON terstruktur seragam:

```json
{
  "error": {
    "code": "INTEGRITY_VERIFICATION_FAILED",
    "message": "Payload HMAC verification failed: invalid key material or corrupted ciphertext.",
    "details": null,
    "request_id": "ba61b920-4801-4de5-be58-904f3a2bbfe3"
  }
}
```

Daftar Kode Error Utama:
- `VALIDATION_ERROR` (HTTP 422): Ketidaksesuaian tipe data request payload terhadap skema Pydantic.
- `UNAUTHORIZED` (HTTP 401): Sesi tidak valid, telah kedaluwarsa, atau kredensial salah.
- `FORBIDDEN` (HTTP 403): Pengguna peran Viewer mencoba mengakses operasi Administrator.
- `CSRF_TOKEN_INVALID` (HTTP 403): Token proteksi CSRF hilang atau tidak cocok.
- `NOT_FOUND` (HTTP 404): Entitas perangkat, snapshot, atau pekerjaan tidak ditemukan.
- `CONFLICT_ACTIVE_JOB` (HTTP 409): Perangkat sedang diproses oleh tugas backup lain (kunci mutex aktif).
- `STORAGE_DISCONNECTED` (HTTP 503): Operasi backup atau download ditolak karena repositori S3 belum terbuka atau belum aktif.
- `INTEGRITY_VERIFICATION_FAILED` (HTTP 500): Verifikasi autentikasi HMAC payload S3 gagal, mengindikasikan file telah rusak atau password repositori salah.

---

# BAGIAN VI: EKOSISTEM DRIVER PERANGKAT JARINGAN (DRIVER CONTRACT)

## 6.1 Arsitektur Adapter Driver (Base Class & Lifecycle)
Ekosistem driver NetBackup dirancang menggunakan pola desain **Adapter Pattern**. Seluruh driver menginduk pada kelas abstrak `BackupDriver` di `backend/app/drivers/base.py`.

Siklus hidup eksekusi driver:
1. `validate_target(device)`: Memeriksa kelengkapan atribut perangkat (alamat IP valid, port terdefinisi).
2. `connect(credentials)`: Membuka transport koneksi (SSHv2 menggunakan pustaka Netmiko/Paramiko atau Telnet).
3. `escalate_privilege()`: Menjalankan eskalasi hak akses jika perangkat memerlukan mode `enable` atau `super`.
4. `disable_paging()`: Mengirimkan instruksi bypass paginasi layar terminal (misal: `terminal length 0`).
5. `collect_configuration()`: Mengeksekusi perintah pencadangan spesifik vendor dan menampung aliran teks output.
6. `sanitize_and_normalize(raw_text)`: Membersihkan banner selamat datang, escape code ANSI, prompt terminal, dan stempel waktu variabel agar hasil komparasi hash menjadi konsisten.
7. `validate_configuration(cleaned_text)`: Memastikan teks konfigurasi tidak kosong dan memenuhi batas panjang minimum serta memuat kata kunci wajib (misal: `hostname`).
8. `disconnect()`: Menutup socket koneksi secara rapi pada blok `finally`.

## 6.2 Driver Bawaan (Built-in Drivers)

| Kunci Driver | Perangkat Sasaran | Transport & Port | Perintah Ekstraksi | Karakteristik Khusus |
| :--- | :--- | :--- | :--- | :--- |
| `mikrotik_routeros` | MikroTik RouterOS (v6 & v7) | SSHv2 (Port 22) | `/export compact` | Menghasilkan script konfigurasi teks `.rsc` bersih, bukan file biner `.backup`. Portabel lintas arsitektur hardware. |
| `ruijie_ap` | Ruijie Wireless Access Point | SSHv2 (Port 22 / custom) | CLI extraction | Ekstraksi konfigurasi nirkabel terstruktur dengan penanganan timeout adaptif dan negosiasi key exchange legacy (`diffie-hellman-group14-sha1`, `ssh-rsa`) tanpa ketergantungan penambahan manual di `known_hosts` (teruji stabil pada AP-04 dan AP-05). |
| `ruijie_switch` | Ruijie Enterprise Campus Switch | SSHv2 (Port 22) | `show running-config` | Mengirimkan perintah `write memory` / konfirmasi save prompt terlebih dahulu sebelum ekstraksi untuk memastikan seluruh running-config tersinkronisasi. Mendukung negosiasi key exchange legacy (`diffie-hellman-group14-sha1`, `ssh-rsa`) untuk switch generasi terdahulu. |
| `sangfor_nsf` | Sangfor Next-Gen Firewall (NGAF) | SSHv2 (Port 22) | `show running-config` | Penanganan paginasi terminal khusus dan sanitasi header audit log otomatis. |

## 6.3 Backup Worker Management (Custom Parametric CLI Driver Engine)
Untuk mendukung ratusan vendor dan model perangkat jaringan lain (seperti Cisco IOS/XE, Huawei VRP, Fortinet FortiGate, HP Aruba, H3C, VyOS) tanpa perlu mengubah kode program Python, sistem menyediakan **Mesin Driver Parametrik Kustom** (`ParametricCLIDriver`).

Administrator dapat mengonfigurasi parameter berikut langsung dari antarmuka Web GUI:
- **Pilihan Protokol Transport:** SSHv2 atau Telnet (berguna untuk switch legacy di lingkungan isolated OT/ICS).
- **Nomor Port Kustom:** Mendukung port forwarding non-standar (misal port 2222 atau 2323).
- **Mode Privilege Escalation:** Pengaturan checkbox `need_enable`, teks perintah (`enable` / `super`), dan regex deteksi prompt password eskalasi (`[#$]`).
- **Paginasi Terminal Dinamis:** Teks perintah bypass layar, seperti `terminal length 0`, `screen-length 0 temporary`, atau `stty cols 1000`.
- **Ekspresi Reguler Sanitasi (*Strip Patterns*):** Daftar regex JSON untuk membuang baris dinamis yang berubah setiap detik (seperti waktu uptime, versi NTP sync, dan stempel waktu eksekusi) agar proses deduplikasi CAS berjalan optimal.
- **Validasi Integritas Teks:** Batas panjang karakter minimum (default: 30 karakter) dan kata kunci wajib (default: `hostname` atau `sysname`).

---

# BAGIAN VII: SPESIFIKASI KRIPTOGRAFI TERPADU AES-256-GCM & KOMPRESI S3 (SINGLE SOURCE OF TRUTH)

## 7.1 Ringkasan Konseptual Tiga Titik Kriptografi (Three Cryptographic Points)
NetBackup menerapkan standar kriptografi modern **AES-256-GCM (Authenticated Encryption with Associated Data / AEAD)** secara terpadu di seluruh lapisan sistem:
1. **Point 1: Database Credential Vault (`vault_crypto.py`)** — Mengenkripsi kredensial sensitif di PostgreSQL (S3 Secret Access Key dan Master Password repositori) menggunakan amplop Base64URL dengan magic marker `b"NBV1"`, salt 16-byte, nonce 12-byte, ciphertext AES-256-GCM, dan tag GMAC 16-byte dengan pengikatan AAD 32-byte.
2. **Point 2: S3 Repository Manifest Envelope (`manifest_crypto.py`)** — Membungkus Data Encryption Key (DEK) repositori di dalam file biner `repo_manifest.enc` di Ceph S3 dengan master password (KEK via PBKDF2 100k), diawali magic marker `b"NBM1"` dan tag GMAC 16-byte (payload JSON `"cipher": "AES-256-GCM"`).
3. **Point 3: Simplified At-Rest Configuration Payload (`payload_crypto.py`)** — Mengompresi teks konfigurasi dengan zlib Deflate level 6 (`b"NBZ1"`), kemudian menyandikannya langsung menggunakan **Simplified AES-256-GCM (AEAD)** dengan DEK 256-bit berkecepatan tinggi tanpa redundansi PBKDF2. Header amplop berukuran ringkas 16 byte (`b"NBG2"` + nonce 12B) diikat sebagai *Additional Authenticated Data* (AAD 16-byte); saat proses pemulihan (restore), keabsahan tag autentikasi GMAC 128-bit wajib diverifikasi secara matematis sebelum dekompresi dan operasi restore plaintext dilakukan. Untuk data/snapshot lawas, sistem menyediakan fallback terverifikasi fail-closed ke format transisi `NBG1` dan format legacy AES-256-CBC + HMAC-SHA256.

## 7.2 Spesifikasi Parameter Kriptografi Terpadu (Ground Truth)
Berdasarkan implementasi kode sumber pada [backend/app/crypto/vault_crypto.py](file:///opt/network-backup/backend/app/crypto/vault_crypto.py), [backend/app/crypto/manifest_crypto.py](file:///opt/network-backup/backend/app/crypto/manifest_crypto.py), [backend/app/crypto/payload_crypto.py](file:///opt/network-backup/backend/app/crypto/payload_crypto.py), dan [backend/app/crypto/kdf.py](file:///opt/network-backup/backend/app/crypto/kdf.py):

| Titik Kriptografi | Modul Sumber | Magic Header | Format Envelope & Penyimpanan | Kunci KDF & Standard |
| :--- | :--- | :--- | :--- | :--- |
| **Point 1: Database Vault** | `vault_crypto.py` | `b"NBV1"` (4B) | Base64URL(`[NBV1 4B] \|\| [Salt 16B] \|\| [Nonce 12B] \|\| [Ciphertext] \|\| [Tag 16B]`) di PostgreSQL | PBKDF2(APP_SECRET, 100k) -> 32B AES-GCM Key |
| **Point 2: S3 Manifest** | `manifest_crypto.py`| `b"NBM1"` (4B) | Biner `[NBM1 4B] \|\| [Salt 16B] \|\| [Nonce 12B] \|\| [Ciphertext JSON] \|\| [Tag 16B]` di S3 | PBKDF2(MasterPass, 100k) -> 32B AES-GCM Key |
| **Point 3: S3 Payload (Simplified)** | `payload_crypto.py` | `b"NBG2"` (4B) | Biner `[NBG2 4B] \|\| [Nonce 12B] \|\| [NBZ1 zlib Ciphertext] \|\| [Tag 16B]` di S3 | **Direct 256-bit DEK** (Tanpa overhead PBKDF2/Salt) |

### Rincian Parameter Kriptografi Universal:
| Parameter Teknis | Nilai Konfigurasi Aktual | Rujukan Standar Industri | Justifikasi & Perilaku Sistem |
| :--- | :--- | :--- | :--- |
| **Algoritma Simetris** | **AES-256-GCM** (Key Length: 256-bit / 32 bytes) | NIST SP 800-38D / FIPS PUB 197 | Skema Authenticated Encryption with Associated Data (AEAD) standar industri modern. |
| **Mode Operasi** | **GCM** (Galois/Counter Mode) | NIST SP 800-38D | Menggabungkan kerahasiaan (*counter mode*) dan integritas (*Galois field*) dalam satu lintasan. |
| **Ukuran Blok & Padding**| **Stream / Counter (No Padding)** | NIST SP 800-38D | Mengeliminasi kebutuhan padding PKCS#7 dan kebal total terhadap serangan Padding Oracle. |
| **Nonce Kriptografi** | **12 bytes (96-bit) CSPRNG** (`os.urandom(12)`) | Rekomendasi Standar NIST SP 800-38D | Dibangkitkan baru secara acak untuk setiap kali enkripsi, menjamin keunikan ruang IV. |
| **Key Derivation (Payload)** | **Direct 256-bit Resolution** | Standar KMS Industri | DEK repositori telah memiliki entropi 256-bit penuh, PBKDF2 redundan dieliminasi. |
| **Key Derivation (Vault & Manifest)** | **PBKDF2-HMAC-SHA256 (100k rounds)** | RFC 8018 / NIST SP 800-132 | Memperlambat brute-force kamus untuk password master dan secret aplikasi. |
| **Tag Autentikasi** | **16 bytes (128-bit) GMAC Tag** | NIST SP 800-38D | Tag integritas terotentikasi yang dihasilkan dan diverifikasi langsung oleh AESGCM engine. |
| **Associated Data (AAD Payload)** | **16 bytes:** `b"NBG2" (4B) \|\| Nonce (12B)` | NIST SP 800-38D | Mengikat header amplop secara matematis dengan ukuran ringkas 16 byte. |
| **Prinsip Keamanan** | **Fail-Closed Security Gate** | Zero-Trust Storage | Kegagalan verifikasi tag melempar `IntegrityVerificationError` seketika tanpa dekripsi. |
| **Kompatibilitas Mundur** | **Fallback Multi-Generasi Terverifikasi** | Standar Transisi v1-v2-v3 | Mendukung otomatis payload modern `NBG2`, transisi `NBG1`, dan legacy `CBC`. |

## 7.3 Diagram Alur Enkripsi Upload & Dekripsi Restore (Mermaid)

### Alur A: Upload & Enkripsi Payload ke S3 (Simplified AES-256-GCM AEAD)
```mermaid
sequenceDiagram
    autonumber
    participant DEV as Perangkat Jaringan
    participant WRK as Backup Worker (Celery)
    participant SEC as Modul Kriptografi (payload_crypto.py)
    participant S3 as Storage Ceph RGW (S3)

    DEV->>WRK: Konfigurasi Plaintext (UTF-8 / ASCII)
    WRK->>SEC: Kirim raw_bytes & DEK Repositori (256-bit)
    
    rect rgb(240, 249, 255)
        Note over SEC: Tahap 1: Kompresi Data
        SEC->>SEC: zlib.compress(raw_bytes, level=6)
        SEC->>SEC: Sisipkan Magic Marker b"NBZ1" di awal
    end
    
    rect rgb(238, 242, 255)
        Note over SEC: Tahap 2: Nonce Generation & AAD Binding
        SEC->>SEC: Bangkitkan Nonce acak 12-byte (os.urandom)
        SEC->>SEC: Susun AAD Header (16B): b"NBG2" || Nonce
    end
    
    rect rgb(240, 253, 244)
        Note over SEC: Tahap 3: Enkripsi AES-256-GCM AEAD Langsung
        SEC->>SEC: AESGCM(DEK).encrypt(Nonce, compressed_data, AAD)
        Note over SEC: Instan, hardware-accelerated (AES-NI), tanpa delay PBKDF2!
    end
    
    rect rgb(254, 252, 232)
        Note over SEC: Tahap 4: Pembungkusan Binary Envelope
        SEC->>SEC: Susun Envelope: [NBG2 4B] || [Nonce 12B] || [Ciphertext] || [Tag 16B]
    end
    
    SEC-->>WRK: Objek Biner Terenkripsi Mandiri (Binary Envelope NBG2)
    WRK->>S3: PUT Object (s3_key, Binary Payload)
    S3-->>WRK: ETag & Status Konfirmasi Upload Berhasil
```

### Alur B: Restore & Dekripsi Payload dari S3 (Simplified AES-256-GCM AEAD)
```mermaid
sequenceDiagram
    autonumber
    participant ADM as Administrator (Browser)
    participant API as FastAPI Backend
    participant SEC as Modul Kriptografi (payload_crypto.py)
    participant S3 as Storage Ceph RGW (S3)

    ADM->>API: GET /api/v1/snapshots/{id}/download
    API->>S3: GET Object (s3_key)
    S3-->>API: Stream Objek Biner Terenkripsi
    
    rect rgb(255, 241, 242)
        Note over API,SEC: Tahap 1: Validasi Format & Header Parsing
        API->>SEC: Kirim Binary Envelope & DEK Repositori
        alt Diawali Magic Marker b"NBG2" (Simplified Modern AES-256-GCM)
            SEC->>SEC: Header AAD = data[:16] (NBG2 + Nonce)
            SEC->>SEC: AESGCM(DEK).decrypt(Nonce, Ciphertext_and_Tag, AAD)
            Note over SEC: Instan tanpa KDF! Fail-Closed jika InvalidTag.
        else Format Tidak Dikenal
            Note over SEC: Fail-Closed seketika melempar DecryptionError
        end
    end
    
    rect rgb(240, 249, 255)
        Note over SEC: Tahap 2: Pemeriksaan Marker & Dekompresi zlib
        alt Buffer Diawali Magic Marker b"NBZ1"
            SEC->>SEC: zlib.decompress(decrypted[4:])
        else Format Legacy Tanpa Kompresi
            SEC->>SEC: Gunakan raw decrypted buffer
        end
    end
    
    SEC-->>API: Plaintext Konfigurasi Asli Terpulihkan
    API-->>ADM: Unduhan File Konfigurasi (Text Stream)
```
    
    SEC-->>API: Plaintext Konfigurasi Asli Terpulihkan
    API-->>ADM: Unduhan File Konfigurasi (Text Stream)
```

## 7.4 Analisis Keamanan & Prinsip Fail-Closed
1. **Mengapa Menggunakan AES-256-GCM (AEAD)?**  
   AES-256-GCM adalah standar *Authenticated Encryption with Associated Data* (AEAD) modern yang menyatukan proses penyandian kerahasiaan (*confidentiality*) dan pembuktian integritas (*authenticity*) dalam satu lintasan matematis (*single pass*). Berbeda dengan mode CBC konvensional, GCM beroperasi dengan mode counter sehingga tidak memerlukan *padding* blok PKCS#7, mengeliminasi seluruh vektor serangan manipulasi padding (*Padding Oracle Attacks* / CVE POODLE) secara permanen.
2. **Perlindungan Header via Additional Authenticated Data (AAD):**  
   Header amplop biner berukuran 32 byte (`b"NBG1"` + Salt 16B + Nonce 12B) dimasukkan ke dalam mesin AEAD sebagai *Additional Authenticated Data* (AAD). Ini membuktikan integritas header: apabila penyerang mencoba mengubah stempel versi, memanipulasi salt, atau menukar nonce, verifikasi tag GMAC akan gagal dan data ditolak seketika.
3. **Efisiensi & Akselerasi Hardware (Galois Field Multiplier):**  
   Perhitungan tag integritas GMAC berbasis perkalian Galois Field ($GF(2^{128})$) diakselerasi secara native oleh instruksi prosesor modern (Intel AES-NI/PCLMULQDQ dan ARMv8 Crypto Extensions), memberikan *throughput* pemrosesan konfigurasi yang lebih cepat dan latensi CPU yang lebih rendah dibanding menghitung HMAC-SHA256 terpisah.
4. **Mengapa Kompresi Dilakukan Sebelum Enkripsi?**  
   Algoritma enkripsi simetris modern seperti AES dirancang untuk menghasilkan ciphertext dengan tingkat keacakan (*entropy*) matematis mendekati sempurna (~7.99 bit per byte). Jika data dienkripsi terlebih dahulu, tidak ada algoritma kompresi apa pun (termasuk zlib, gzip, atau lzma) yang mampu memampatkan ukuran file tersebut. Melakukan kompresi sebelum enkripsi memungkinkan penghematan kapasitas fisik Ceph S3 hingga ~75% tanpa mengurangi keamanan ciphertext.
5. **Mengapa PBKDF2 dengan 100.000 Putaran?**  
   Sesuai rekomendasi NIST SP 800-132, algoritma fungsi penurunan kunci (*Key Derivation Function*) wajib menerapkan perulangan hashing matematis yang berat guna menaikkan biaya komputasi penyerang. Penambahan Salt acak 16 byte mengeliminasi efektivitas tabel pelangi (*Rainbow Table*), dan 100.000 iterasi SHA-256 membuat upaya *brute-force* berbasis kluster GPU atau kartu ASIC menjadi tidak layak secara ekonomi dan waktu.
6. **Prinsip Pertahanan Menutup Saat Gagal (*Fail-Closed*):**  
   Sistem tidak pernah menoleransi kegagalan integritas data. Pada saat pemulihan, jika tag autentikasi GMAC tidak cocok (misalnya akibat manipulasi 1 bit data atau kesalahan kunci), exception `IntegrityVerificationError` dilempar ke layer API untuk menghentikan pemrosesan dan mencatat insiden keamanan pada audit log tanpa mengembalikan byte mentah yang tidak terverifikasi.

## 7.5 Halaman Demonstrasi & Visualisasi Web
Aplikasi menyediakan halaman visualisasi dan simulator interaktif yang dapat diakses publik di:  
👉 **`https://netbackup.makuku.co.id/crypto-animation.html`**

Fitur halaman demonstrasi:
- **Visualisasi Bertahap (Step-by-Step Pipeline):** Memperagakan alur enkripsi upload AES-256-GCM dan alur restore secara visual dengan kontrol putar otomatis, jeda, maju, mundur, dan pemilihan kecepatan.
- **Data Buffer Inspector:** Menampilkan transformasi byte hex nyata, deteksi stempel magic `NBG1` dan `NBZ1`, rasio kompresi, dan metadata properti kriptografi.
- **Laboratorium Live Web Crypto API:** Memanfaatkan pustaka native peramban `crypto.subtle` untuk memperagakan enkripsi dan dekripsi AES-256-GCM langsung di sisi klien, lengkap dengan fitur simulasi serangan *Bit-Flipping* (memanipulasi 1 bit ciphertext atau AAD) atau penggunaan kunci yang salah guna membuktikan ketangguhan respons *Fail-Closed*.

## 7.6 Glosarium Istilah Kriptografi Terapan
- **Plaintext:** Teks asli konfigurasi perangkat jaringan yang belum disandikan dan dapat dibaca manusia.
- **Ciphertext:** Teks tersandi hasil enkripsi simetris berentropi tinggi yang tidak bermakna tanpa kunci dekripsi yang valid.
- **Cryptographic Salt:** Rangkaian 16 byte acak CSPRNG yang digabungkan ke kunci sebelum hashing KDF untuk memastikan bahwa password yang sama menghasilkan material kunci yang berbeda.
- **Nonce (Number used ONCE):** Rangkaian 12 byte (96-bit) acak pengawal cipher mode GCM untuk memastikan dua konfigurasi identik menghasilkan ciphertext yang berbeda saat diunggah berulang kali.
- **AEAD (Authenticated Encryption with Associated Data):** Skema enkripsi terpadu yang menjamin kerahasiaan (*confidentiality*) dan keabsahan data (*authenticity/integrity*) secara serentak.
- **GMAC (Galois Message Authentication Code):** Mekanisme autentikasi pesan kriptografi berbasis perkalian medan Galois $GF(2^{128})$ yang terintegrasi pada AES-GCM.
- **AAD (Additional Authenticated Data):** Data header yang tidak disandikan (terbuka), namun diikatkan ke dalam perhitungan tag autentikasi agar terlindung dari manipulasi.
- **DEK (Data Encryption Key):** Kunci simetris 256-bit acak yang digunakan langsung untuk mengenkripsi dan mendekripsi payload konfigurasi perangkat di repositori S3.
- **KEK (Key Encryption Key):** Kunci tingkat atas (Master Password repositori) yang digunakan khusus untuk membungkus (*wrap*) DEK di dalam manifes repositori.
- **Fail-Closed:** Prinsip rekayasa keamanan di mana sistem memilih membatalkan operasi secara tegas saat validasi gagal alih-alih melanjutkan pemrosesan dalam kondisi ragu-ragu.

---

# BAGIAN VIII: DESAIN ANTARMUKA & PENGALAMAN PENGGUNA (UI/UX DESIGN SYSTEM)

## 8.1 Filosofi Desain Anti-Slop & Kerapatan Informasi
Antarmuka pengguna NetBackup dirancang mengikuti prinsip **Anti-Slop** (*Human-Crafted Utility*):
- **Bebas Elemen Klise AI:** Tidak menggunakan gradien pelangi generik (ungu-ke-biru tanpa tujuan), efek kaca *glassmorphism* berlebihan di semua komponen, atau lingkaran *glowing pulse* yang mengaburkan konsentrasi operator.
- **Kerapatan Informasi Tinggi (*High Information Density*):** Layout dirancang untuk kebutuhan teknisi jaringan dan operator NOC, memaksimalkan visibilitas status perangkat, stempel waktu, dan metrik tanpa pemborosan ruang vertikal.
- **Elevasi Bertujuan (*Purposeful Elevation*):** Permukaan kartu dan tabel duduk rata (*flat clean*); bayangan (*shadow*) hanya diberikan pada jendela modal popup dan menu popover untuk menandai layer interaksi aktif.

## 8.2 Token Desain, Palet Warna & Tipografi
Sistem mendukung tema **Gelap (*Dark Mode*)** dan **Terang (*Light Mode*)** yang terdefinisi pada variabel CSS di `index.html`:

| Token Variabel CSS | Nilai Tema Terang | Nilai Tema Gelap | Fungsi Semantik |
| :--- | :--- | :--- | :--- |
| `--bg-page` | `#f5f7f8` | `#0f172a` (Slate 900) | Latar belakang dasar halaman |
| `--bg-surface` | `#ffffff` | `#1e293b` (Slate 800) | Latar belakang kontainer kartu, tabel, dan header |
| `--bg-soft` | `#edf2f5` | `#334155` (Slate 700) | Latar belakang baris hover dan tombol sekunder |
| `--ink` | `#112330` | `#f8fafc` (Slate 50) | Warna teks utama (*high-contrast*) |
| `--muted` | `#4b6171` | `#94a3b8` (Slate 400) | Warna teks sekunder (rasio kontras 5.6:1 WCAG AA) |
| `--border-line` | `#dbe4e8` | `rgba(148, 163, 184, 0.2)` | Garis pembatas sel tabel dan panel |
| `--brand-primary`| `#0284c7` (Sky 600) | `#38bdf8` (Sky 400) | Warna aksen utama tindakan sistem |
| `--success` | `#15803d` (Green 700)| `#22c55e` (Green 500) | Indikator status `UP`, `SUCCESS`, dan `HEALTH_OK` |
| `--danger` | `#b91c1c` (Red 700) | `#ef4444` (Red 500) | Indikator status `DOWN`, `FAILED`, dan `Integrity Error` |

**Tipografi Standar:**
- **Antarmuka Utama:** `Plus Jakarta Sans` dan `DM Sans` (sans-serif) — memberikan keterbacaan tinggi pada teks navigasi, label formulir, dan tabel data.
- **Data Teknis & Hex:** `Space Mono` (monospace) — digunakan pada tampilan alamat IP, kunci publik, hash SHA-256, stempel waktu, dan inspektur byte.

## 8.3 Aksesibilitas WCAG AA & Dukungan Navigasi Keyboard
- **Rasio Kontras Teruji:** Seluruh pasangan warna teks terhadap latar belakang memenuhi batas ambang WCAG AA (minimum 4.5:1 untuk teks biasa dan 3:1 untuk teks besar/kontrol).
- **Indikator Fokus Eksplisit:** Seluruh elemen interaktif (`<a>`, `<button>`, `<input>`, `<select>`) dilengkapi gaya `:focus-visible` berupa outline 2px berwarna biru langit cerah dengan offset 2px.
- **Navigasi Keyboard Penuh:** Jendela modal dan dropdown menu dapat ditutup seketika dengan menekan tombol `Escape`, dan urutan fokus `Tab` mengikuti hierarki visual secara logis.

## 8.4 Penanganan Tata Letak Responsif & Kendali Form Presisi
- **Desktop (≥ 1280px):** Menampilkan seluruh kolom tabel (Hostname, IP, Vendor, Model, Driver, Availability, Schedule, Last Backup, Retention, dan Tindakan Baris).
- **Tablet (~768px) & Mobile (~375px):** Tabel perangkat mengaktifkan mode gulir horizontal (*overflow-x: auto*) dengan kolom pertama (**HOSTNAME**) berstatus **Sticky Column** (`sticky left-0 bg-surface z-10 shadow-sm`). Saat operator menggeser tabel ke kanan pada layar kecil, identitas perangkat tetap terkunci di sisi kiri sehingga konteks data tidak hilang.
- **Pencarian Perangkat Responsif (Responsive Live Instant Search):**
  - Menggantikan badge statis "ACTIVE" di sebelah tombol *Export* dengan kontrol pencarian instan:
    - **Desktop (`≥ 1024px`):** Kolom input pencarian tampil penuh secara permanen.
    - **Tablet & Ponsel (`< 1024px`):** Tampil ringkas berupa tombol *Search* berikon kaca pembesar. Saat diklik, kolom input melebar (*expand*) dan kursor langsung terfokus (*auto-focus*).
    - Tombol *Search* memancarkan indikator dot biru menyala jika filter sedang aktif menyaring tabel. Tombol tutup (`✕`) dan tombol `Escape` menutup bar pencarian secara bersih.
    - Filter menyaring Hostname, IP, Vendor, Model, Status (`Active`/`Non-Active`), dan Driver Worker seketika tanpa me-reload halaman.
- **Kartu Total Devices & Badge Resmi Zabbix:**
  - Kartu 1 "Total Devices" menampilkan badge merek Zabbix dengan warna merah resmi (`#d40000`).
  - Di bawahnya, terdapat status sinkronisasi Zabbix dinamis (`Sync` hijau / `Not-Sync` merah) yang mengadopsi format `.status-cell-wrapper` lengkap dengan border badge dan dot indikator, identik dengan kolom **STATUS** tabel perangkat.
- **Pusat Pengaturan Driver & Deduplikasi Jadwal:**
  - Pemilihan backup driver dipusatkan secara eksklusif pada kolom *Backup Worker* pada tabel perangkat. Dropdown driver pada modal *Schedule* ditiadakan untuk mencegah benturan konfigurasi dan redundansi data.
- **Scoping Visibilitas Kartu Ceph Cluster Health:**
  - Kartu metrik "Storage Cluster (Ceph Health)" otomatis disembunyikan jika repositori penyimpanan aktif bukan Ceph (misalnya MinIO atau dalam kondisi terputus/disconnected) guna menghindari kebingungan operator.
- **Peringatan Batas Waktu Ketidakaktifan Sesi (Inactivity Timeout Countdown):**
  - Dialog modal peringatan countdown 60 detik otomatis muncul jika tidak ada aktivitas mouse/keyboard dari operator sebelum sesi ditutup demi standar keamanan data.
- **Pilihan Waktu Terkontrol (Strict 5-Minute Discrete Scheduling):** Modal konfigurasi jadwal tidak lagi menggunakan input waktu bebas, melainkan dua dropdown pasangan terstruktur: Jam (`00` s/d `23`) dan Menit diskrit (`:00`, `:05`, ..., `:55`). Hal ini menjamin bahwa seluruh konfigurasi jadwal di antarmuka sinkron secara deterministik dengan siklus pemicu Celery Beat.
- **Visualisasi Kategori Log Terstandarisasi:** Dropdown dan badge tabel pada menu *Audit & Security Logs* menampilkan kategori dengan pembeda warna semantik yang kontras: `STORAGE` (Cyan), `AUTH` (Indigo), `SECURITY` (Red), `BACKUP_JOB` (Blue), `AUDIT` (Emerald), dan `SYSTEM` (Purple).

---

# BAGIAN IX: RANGKUMAN IMPLEMENTASI & DEPENDENSI (IMPLEMENTATION)

## 9.1 Ringkasan Tahapan Pengembangan (Checkpoint C0 s/d C24)
Pengembangan sistem NetBackup diselesaikan melalui 24 tahapan rekayasa berkesinambungan:
- **C0 - C2:** Pembangunan fondasi arsitektur kontainer Docker, basis data PostgreSQL, model ORM SQLAlchemy, migrasi Alembic awal, dan otentikasi sesi server-side berbasis Redis.
- **C3 - C5:** Integrasi Zabbix Host Group API, normalisasi ICMP availability, pendaftaran driver bawaan, antrean Celery worker, dan perancangan mesin status pekerjaan (*Job State Machine*).
- **C6 - C10:** Stabilisasi driver SSH Paramiko untuk vendor MikroTik, Ruijie, dan Sangfor; penanganan bypass terminal paging, dan mekanisme penguncian terdistribusi Redis Mutex.
- **C11 - C15:** Pembangunan mesin pelaporan audit eksekutif multi-sheet Microsoft Excel (`.xlsx`) via OpenPyXL dan dokumen PDF (`.pdf`) via ReportLab.
- **C16 - C18:** Penyempurnaan alur simpan `write memory` pada switch Ruijie campus, deteksi status firewall Sangfor, dan integrasi webhook Feishu/Lark.
- **C19:** Pembangunan modul S3 Management GUI (Inisialisasi Master Password, Unlock, Connection Test Popup Modal, dan Active Repository Isolation).
- **C20:** Verifikasi rilis Version 1.0, audit stabilitas skema basis data, dan konsolidasi roadmap Version 2.0.
- **C21:** Penguatan keamanan *Zero-Trust Payload Encryption* at-rest di Ceph S3 (diupgrade ke AES-256-GCM AEAD dengan pengikatan AAD, PBKDF2 100k, Fail-Closed Security, serta fallback terverifikasi untuk arsip CBC legacy), penyematan kompresi zlib `NBZ1`, pembuatan builder Custom Parametric Driver CLI, dan peluncuran halaman simulator interaktif `/crypto-animation.html`.
- **C22 (Observabilitas & Keamanan):** Pembuatan tabel ke-11 `system_audit_logs` (Alembic 015), middleware inspeksi WAF aktif (SQLi, XSS, Path Traversal), taksonomi 6 kategori audit (`STORAGE`, `AUTH`, `SECURITY`, `AUDIT`, `BACKUP_JOB`, `SYSTEM`), mesin sinkronisasi backfill riwayat lawas otomatis, serta ekspor laporan audit resmi (Excel dan PDF 2-pass).
- **C23 (Stabilitas Lapangan & Diskrit 5-Menit):** Penegakan waktu jadwal diskrit kelipatan 5 menit pada antarmuka dan validasi backend, hardening timeout dan host key driver Ruijie AP (AP-04, AP-05), serta standarisasi 100% Bahasa Inggris di seluruh antarmuka dan log sistem.
- **C24 (Siklus Hidup S3 & Modernisasi UI/UX):** Pembuatan tabel ke-12 `repository_device_setting_archives` (Alembic 016) untuk mengarsipkan konfigurasi backup perangkat per-bucket saat repositori diputus/dialihkan, penanganan alur disconnect/delete repositori S3 yang mulus tanpa galat 500, penyelarasan visibilitas kartu Ceph Cluster Health, deduplikasi konfigurasi driver (eksklusif kolom Backup Worker), pencarian perangkat instan responsif (desktop full, tablet/mobile expandable search button), badge resmi Zabbix merah (#d40000) dengan status Sync/Not-Sync ber-border dot, perapian jejak audit Zabbix, serta modal peringatan batas waktu inaktivitas sesi.

## 9.2 Manajemen Dependensi Runtime & Development

### Dependensi Runtime (`backend/requirements.txt`):
- `fastapi`: Framework web asinkron berkinerja tinggi untuk RESTful API.
- `uvicorn[standard]`: ASGI web server produksi.
- `pydantic` & `pydantic-settings`: Validasi tipe data dan pembacaan konfigurasi environment variable.
- `sqlalchemy`: Object-Relational Mapping (ORM) basis data.
- `psycopg[binary]`: Driver konektor PostgreSQL native v3.
- `alembic`: Manajemen skema dan migrasi basis data versioning.
- `celery`: Sistem antrean tugas terdistribusi.
- `redis`: Klien memori untuk message broker dan session store.
- `netmiko`: Pustaka otomasi koneksi multi-vendor SSH/Telnet perangkat jaringan.
- `paramiko`: Pustaka protokol kriptografi SSHv2.
- `boto3` & `botocore`: Pustaka SDK AWS S3 untuk komunikasi dengan Ceph RGW.
- `cryptography`: Pustaka kriptografi primitif (AES cipher blocks, PKCS#7 padding).
- `argon2-cffi`: Hashing password akun pengguna dengan standar Argon2id.
- `httpx`: Klien HTTP asinkron untuk Zabbix API dan webhook Feishu.
- `openpyxl`: Pembuat berkas spreadsheet Microsoft Excel (`.xlsx`).
- `reportlab`: Pembuat dokumen cetak PDF (`.pdf`).

### Dependensi Pengembangan & Pengujian (`backend/requirements-dev.txt`):
- `pytest`: Framework pengujian unit otomatis.
- `pytest-cov`: Penganalisis cakupan baris kode (*code coverage*).
- `ruff`: Linter dan formatter kode Python super cepat.
- `mypy`: Pengecek tipe data statis (*static type checker*).

---

# BAGIAN X: STRATEGI PENGUJIAN & PENJAMINAN MUTU (TESTING & QA)

## 10.1 Rencana Pengujian (Test Plan)
Strategi pengujian NetBackup mencakup tiga lapisan penjaminan mutu:
1. **Pengujian Unit Otomatis (Automated Unit Testing):** Memverifikasi integritas fungsi matematis kriptografi, kontrak skema basis data, normalisasi status Zabbix, dan adapter driver secara terisolasi.
2. **Pengujian Integrasi Layanan (Service Integration Testing):** Memverifikasi komunikasi antar kontainer (FastAPI &rarr; Redis &rarr; Celery &rarr; PostgreSQL &rarr; Ceph S3).
3. **Pengujian Penerimaan Pengguna (User Acceptance Testing / UAT):** Memvalidasi pengalaman pengguna akhir di peramban web pada domain produksi `https://netbackup.makuku.co.id`.

## 10.2 Hasil Pengujian Otomatis Pytest Unit Tests
Eksekusi pengujian suite pada direktori `tests/unit/` menghasilkan **116 test lulus dari total 116 test case (100% Pass Rate)**.
- `tests/unit/test_crypto_standalone.py`: **LULUS PENUH (100%)** — Memverifikasi isolasi derivasi KDF, enkripsi payload zlib + AES-256-GCM AEAD, pengikatan AAD header `NBG1`, penolakan data korup/tampered, dan kompatibilitas mundur dekripsi format legacy CBC.
- `tests/unit/test_storage_repository.py`: **LULUS PENUH (100%)** — Memverifikasi inisialisasi bucket, validasi SSL, enkripsi kredensial, proteksi overwrite manifest, dan rotasi password master.
- `tests/unit/test_schema_contract.py`: **LULUS PENUH (100%)** — Memverifikasi integritas 11 tabel basis data dan batasan constraint.
- `tests/unit/test_driver_registry.py` & `test_custom_drivers.py`: **LULUS PENUH (100%)** — Memverifikasi adapter bawaan dan builder driver parametrik kustom.
- `tests/unit/test_security.py`: **LULUS PENUH (100%)** — Memverifikasi hashing Argon2id dan normalisasi username case-sensitive.
- `tests/unit/test_vulnerabilities_hardening.py`: **LULUS PENUH (100%)** — Memverifikasi strict SSH host key checking, proteksi mutlak retensi *Latest Known Good*, dan verifikasi TLS Ceph.
- `tests/unit/test_reports.py`: **LULUS PENUH (100%)** — Memverifikasi pembuatan laporan eksekutif XLSX dan PDF dengan normalisasi metadata.
- `tests/unit/test_audit_logs.py`: **LULUS PENUH (100%)** — Memverifikasi logging audit otomatis, agregasi statistik KPI, deteksi payload berbahaya (SQLi, XSS, Path Traversal), dan ekspor laporan audit ke Excel/PDF.

## 10.3 Skenario Pengujian Khusus Kriptografi (Test Script)

| ID Test Case | Prasyarat Pengujian | Langkah Pengujian | Hasil yang Diharapkan | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TS-CRYPTO-01** | Tersedia konfigurasi jaringan valid dan Master Password aktif. | 1. Enkripsi konfigurasi via `encrypt_payload_aes256`.<br>2. Simpan objek biner ke S3.<br>3. Unduh dan dekripsi via `decrypt_payload_aes256`. | Konfigurasi hasil dekripsi 100% identik (*bit-identical*) dengan teks asli. Magic marker `NBZ1` berhasil diekspansi. | **LULUS** |
| **TS-CRYPTO-02** | Objek biner terenkripsi valid berada di S3. | 1. Ambil berkas envelope biner.<br>2. Manipulasi 1 bit pada area ciphertext (bit-flipping attack).<br>3. Jalankan fungsi dekripsi. | Sistem langsung mendeteksi ketidakcocokan HMAC, melempar `IntegrityVerificationError`, dan membatalkan proses sebelum dekripsi AES dimulai (*Fail-Closed*). | **LULUS** |
| **TS-CRYPTO-03** | Objek biner terenkripsi valid berada di S3. | 1. Jalankan proses dekripsi dengan memasukkan password atau DEK yang salah. | Verifikasi KDF dan HMAC gagal, melempar `IntegrityVerificationError`. Plaintext tidak bocor. | **LULUS** |
| **TS-CRYPTO-04** | Data biner acak berukuran < 80 bytes. | 1. Uji dekripsi terhadap data berukuran 50 bytes (header terpotong). | Sistem langsung menolak dengan `DecryptionError` ("Payload envelope too short, minimum 80 bytes"). | **LULUS** |
| **TS-CRYPTO-05** | Repositori S3 aktif dengan puluhan snapshot lama. | 1. Jalankan rotasi password repositori via API `/rotate-password`.<br>2. Unduh snapshot yang dibuat sebelum rotasi. | Manifes repositori berhasil diperbarui dengan Master Password baru; snapshot lama tetap dapat didekripsi dengan sempurna karena DEK dipertahankan. | **LULUS** |

## 10.4 Format Berita Acara UAT (User Acceptance Testing)

```text
========================================================================================
                      BERITA ACARA USER ACCEPTANCE TESTING (UAT)
                       SISTEM NETWORK CONFIGURATION BACKUP
========================================================================================

Pada hari ini, [ISI: Hari], tanggal [ISI: Tanggal, Bulan, Tahun], bertempat di PT Lucky Mom Indonesia, telah dilaksanakan pengujian User Acceptance Testing (UAT) terhadap sistem NetBackup Versi 2.0.

Pihak Penguji:
1. Nama: [ISI: Nama Penguji / QA Engineer]        Jabatan: [ISI: Jabatan]
2. Nama: [ISI: Nama Perwakilan Klien / User]       Jabatan: [ISI: Jabatan]

Hasil Skenario Pengujian:
+----+--------------------------------------------+---------------+-------------+
| No | Skenario Pengujian                         | Hasil (Pass/Fail) | Catatan     |
+----+--------------------------------------------+---------------+-------------+
| 1  | Login Sesi & Hak Akses Admin / Viewer      | [           ] |             |
| 2  | Sinkronisasi Inventaris Perangkat Zabbix   | [           ] |             |
| 3  | Pembuatan & Uji Coba Driver Parametrik     | [           ] |             |
| 4  | Konfigurasi Jadwal Harian & Mutex Check    | [           ] |             |
| 5  | Eksekusi Pencadangan Manual & Asinkron     | [           ] |             |
| 6  | Kompresi zlib & Enkripsi AES-256 S3        | [           ] |             |
| 7  | Uji Pertahanan Integritas HMAC Fail-Closed | [           ] |             |
| 8  | Unduh Snapshot Konfigurasi Plaintext       | [           ] |             |
| 9  | Rotasi Master Password Repositori S3       | [           ] |             |
| 10 | Ekspor Laporan Audit Excel & Dokumen PDF   | [           ] |             |
| 11 | Notifikasi Kartu Peringatan Feishu         | [           ] |             |
| 12 | Navigasi Responsif Desktop, Tablet, Mobile | [           ] |             |
+----+--------------------------------------------+---------------+-------------+

Kesimpulan Pengujian:
Sistem dinyatakan [  ] DITERIMA PENUH / [  ] DITERIMA DENGAN CATATAN / [  ] DITOLAK.

Catatan Tambahan:
[ISI: Catatan pengujian jika ada]

Tanda Tangan Pihak Penguji:

      Penguji Sistem / QA,                        Perwakilan Pengguna / User,


( ____________________________ )                ( ____________________________ )
NIP:                                            NIP:
========================================================================================
```

---

# BAGIAN XI: PANDUAN DEPLOYMENT & RUNBOOK OPERASIONAL (OPERATIONS & RUNBOOK)

## 11.1 Prosedur Deployment Awal & Update Rilis

### Persyaratan Minimal Server:
- **Sistem Operasi:** Linux Ubuntu Server 22.04 LTS / Debian 12
- **Hardware:** Minimal 2 vCPU, 4 GB RAM, 20 GB Disk Space
- **Software:** Docker Engine 24+ & Docker Compose v2+
- **Jaringan:** Port 80 & 443 terbuka ke Nginx; akses rute jaringan ke Zabbix Server (port 10051/80), Ceph S3 (port 443/7480), dan perangkat jaringan (port 22/23).

### Langkah Deployment Awal:
```bash
# 1. Masuk ke direktori aplikasi
cd /opt/network-backup

# 2. Salin dan sesuaikan environment variables
cp .env.example .env
nano .env

# 3. Validasi konfigurasi Docker Compose
docker compose config

# 4. Bangun image dan jalankan seluruh kontainer di latar belakang
docker compose up -d --build

# 5. Periksa status kesiapan kontainer
docker compose ps

# 6. Pantau log migrasi database
docker compose logs -f migrator

# 7. Lakukan inisialisasi akun bootstrap admin awal (jika database baru)
docker compose run --rm api python -m app.cli.bootstrap_users
```

### Prosedur Pembaruan Rilis (*Release Update*):
```bash
# 1. Buat backup basis data PostgreSQL terlebih dahulu
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > /opt/backup-preupdate-$(date +%Y%m%d).sql

# 2. Tarik kode rilis terbaru
git checkout main
git pull origin main

# 3. Bangun ulang image dan jalankan migrator
docker compose build migrator api worker beat
docker compose up migrator

# 4. Restart layanan utama tanpa downtime lama
docker compose up -d api worker beat nginx
docker compose ps
```

## 11.2 Konfigurasi Environment Variable (.env)
Berikut adalah daftar variabel konfigurasi yang dikelola sistem (seluruh nilai rahasia disajikan dalam placeholder):

| Nama Variabel | Deskripsi & Kegunaan | Contoh Nilai Aman / Default |
| :--- | :--- | :--- |
| `APP_ENV` | Mode lingkungan aplikasi (`production` / `development` / `test`) | `production` |
| `APP_SECRET` | Kunci master enkripsi internal server (minimal 32 karakter acak) | `<APP_SECRET_RANDOM_KEY>` |
| `DATABASE_URL` | URL koneksi SQLAlchemy PostgreSQL | `postgresql+psycopg://user:pass@postgres:5432/netbackup` |
| `REDIS_URL` | URL koneksi Redis untuk Celery broker dan session store | `redis://redis:6379/0` |
| `POSTGRES_DB` | Nama basis data aplikasi di PostgreSQL | `netbackup` |
| `POSTGRES_USER` | Nama pengguna basis data | `netbackup_user` |
| `POSTGRES_PASSWORD`| Kata sandi basis data | `<POSTGRES_PASSWORD>` |
| `NGINX_PORT` | Port publik yang diekspos oleh gateway Nginx | `80` |
| `COOKIE_SECURE` | Flag cookie HTTPS (`true` di production) | `true` |
| `ZABBIX_API_URL` | URL endpoint Zabbix API JSON-RPC | `http://zabbix.internal.corp/api_jsonrpc.php` |
| `ZABBIX_API_TOKEN`| Token autentikasi Zabbix API (Read-Only) | `<ZABBIX_BEARER_TOKEN>` |
| `ZABBIX_HOST_GROUP`| Nama grup host jaringan di Zabbix | `Network Devices` |
| `FEISHU_WEBHOOK_URL`| URL Webhook grup notifikasi Feishu/Lark | `https://open.feishu.cn/open-apis/bot/v2/hook/<TOKEN>` |
| `SSH_STRICT_HOST_KEY_CHECKING` | Penegakan verifikasi fingerprint SSH host (`true` / `false`) | `false` |

## 11.3 Prosedur Operasional Standar (SOP) Backup & Restore
1. **SOP Backup Manual Harian:**
   - Masuk ke dashboard `https://netbackup.makuku.co.id`.
   - Pilih satu atau beberapa perangkat pada tabel.
   - Klik menu tindakan **Backup Now**.
   - Sistem akan memvalidasi status Zabbix, mengunci mutex perangkat, menjalankan ekstraksi, mengenkripsi payload, dan mengunggahnya ke Ceph S3.
   - Status baris akan berubah menjadi hijau dengan badge `SUCCESS_CHANGED` atau `SUCCESS_NO_CHANGE`.
2. **SOP Pemulihan Konfigurasi (*Restore Drill*):**
   - Buka menu dropdown tindakan pada baris perangkat target &rarr; pilih **View History & Snapshots**.
   - Pilih titik waktu snapshot yang diinginkan.
   - Klik tombol **Download Configuration**.
   - Backend memverifikasi otentikasi HMAC, mendekripsi payload di memori, dan mengalirkan file teks asli ke komputer operator.
   - Teknisi jaringan memverifikasi teks konfigurasi sebelum menerapkannya ke perangkat fisik.

## 11.4 Matriks Penanganan Insiden & Troubleshooting Runbook

| Gejala Gangguan | Kemungkinan Penyebab | Langkah Diagnosis | Tindakan Solusi Pemulihan |
| :--- | :--- | :--- | :--- |
| Pekerjaan backup berstatus `SKIPPED_DEVICE_DOWN`. | Perangkat tidak merespons ICMP ping pada pemantauan Zabbix. | Periksa host di dashboard Zabbix; lakukan ping manual ke IP perangkat dari server. | Pastikan perangkat aktif dan interface rute normal. Pekerjaan akan otomatis dieksekusi saat status Zabbix kembali `UP`. |
| Pekerjaan backup berstatus `FAILED` pada tahap `connecting`. | Kredensial SSH salah, port tertutup firewall, atau limit sesi SSH perangkat penuh. | Periksa log worker via `docker compose logs worker \| grep <job_id>`. | Periksa password/user SSH perangkat; bersihkan sesi menggantung di switch via `clear line`. |
| Pengunduhan snapshot gagal dengan pesan `STORAGE_DISCONNECTED`. | Repositori S3 sedang tidak aktif atau belum dibuka kuncinya setelah restart server. | Buka menu **S3 Storage Management** di dashboard web. | Masukkan Master Password repositori pada modal **Unlock Repository** untuk mengaktifkan kembali DEK. |
| Pengunduhan snapshot gagal dengan pesan `INTEGRITY_VERIFICATION_FAILED`. | File di S3 mengalami kerusakan fisik (*bit rot*) atau Master Password repositori tidak cocok. | Periksa ETag berkas di S3; pastikan repositori tidak diubah secara sepihak di luar sistem. | Gunakan snapshot valid terdekat lainnya. Uji integritas berkas cadangan melalui simulator `/crypto-animation.html`. |
| Antarmuka web menampilkan respons lambat atau tugas menumpuk di `QUEUED`. | Antrean Celery macet atau worker kehabisan slot thread konkuren. | Jalankan `docker compose top worker` dan periksa antrean Redis: `docker compose exec redis redis-cli llen celery`. | Lakukan restart worker: `docker compose restart worker`. Jika beban perangkat tinggi, naikkan concurrency worker di docker-compose. |

**Kontak Eskalasi Insiden:**  
- **Tim On-Call Jaringan:** `[ISI: Tim Jaringan Makuku - ext 4101 / kanal Lark #noc-incident]`  
- **Lead DevOps:** `[ISI: DevOps Lead - devops@makuku.co.id]`

---

# BAGIAN XII: BUKU MANUAL PENGGUNA & PERTANYAAN UMUM (USER MANUAL & FAQ)

## 12.1 Panduan Langkah Pengguna Akhir Berbasis Tugas

### 1. Masuk ke Aplikasi (Login)
- Akses alamat `https://netbackup.makuku.co.id` melalui peramban web Anda.
- Masukkan **Username** dan **Password** Anda. Perhatikan bahwa huruf besar dan huruf kecil pada username dibedakan secara ketat (*case-sensitive*).
- Centang opsi **Remember Me** jika Anda ingin sesi login bertahan lebih lama pada komputer kerja Anda.
- Klik tombol **Sign In**.

### 2. Memantau Status Perangkat Jaringan
- Pada halaman utama, perhatikan kartu ringkasan KPI di bagian atas untuk melihat kesehatan umum infrastruktur jaringan.
- Tabel perangkat menampilkan seluruh perangkat yang disinkronkan dari Zabbix:
  - Badge Hijau (`UP`): Perangkat online dan siap dicadangkan.
  - Badge Merah (`DOWN`): Perangkat offline; pencadangan akan dilewati secara aman.
  - Kolom **Last Backup Status**: Menampilkan status pencadangan terakhir (`SUCCESS`, `NO_CHANGE`, atau `FAILED`).

### 3. Mengatur Jadwal Backup Harian (Khusus Admin)
- Klik ikon roda gigi atau tombol pengaturan pada baris perangkat yang ingin diatur.
- Centang opsi **Enable Daily Schedule**.
- Pilih waktu pencadangan (jam dan menit kelipatan 5, misal `02:15` WIB).
- Pilih kebijakan retensi yang diinginkan:
  - **Standard (31 Days):** Menyimpan snapshot selama 31 hari kalender.
  - **Smart GFS Retention:** Menyimpan 7 snapshot harian, 4 mingguan, 12 bulanan, dan 3 tahunan.
- Klik tombol **Save Settings**.

### 4. Mengunduh Konfigurasi Perangkat (Khusus Admin)
- Buka menu dropdown pada perangkat &rarr; klik **View History & Snapshots**.
- Modal riwayat akan menampilkan daftar seluruh snapshot konfigurasi yang pernah diambil.
- Klik tombol **Download** pada snapshot yang diinginkan.
- Konfigurasi akan otomatis didekripsi dan diunduh ke komputer Anda dalam format teks (`.rsc` untuk MikroTik, `.txt` untuk Ruijie/Sangfor).

### 5. Mengunduh Laporan Rekapitulasi Audit
- Pada bilah navigasi atas, klik tombol **Reports**.
- Tentukan rentang tanggal pelaporan (*Start Date* dan *End Date*).
- Pilih format output yang diinginkan:
  - **Export to Excel (.xlsx):** Berisi rekapitulasi tabular lengkap seluruh eksekusi backup untuk kebutuhan analisis data.
  - **Export to PDF (.pdf):** Dokumen laporan resmi bertanda air institusi yang siap dicetak untuk pelaporan ke pimpinan.

## 12.2 Pertanyaan yang Sering Diajukan (FAQ)

**Q1: Apa itu pencadangan terenkripsi mandiri (*Self-Contained Encrypted Backup*)?**  
*Jawab:* Setiap file backup yang disimpan ke Ceph S3 telah dibungkus dengan amplop kriptografi biner yang memuat Magic Header `NBG1`, Salt acak, Nonce unik 12-byte, data tersandi AES-256-GCM, dan tag integritas GMAC 16-byte (dengan pengikatan Additional Authenticated Data). File ini tidak bergantung pada metadata eksternal dan sama sekali tidak dapat dibaca oleh pihak lain yang memiliki akses fisik ke server penyimpanan tanpa memiliki kunci Master Password repositori. File snapshot lawas berbasis AES-256-CBC juga tetap dapat dibaca secara aman melalui jalur kompatibilitas mundur.

**Q2: Mengapa sistem menolak pengunduhan konfigurasi dengan pesan "Integrity Verification Failed"?**  
*Jawab:* Ini adalah fitur perlindungan keamanan *Fail-Closed*. Pesan ini menandakan bahwa tag integritas HMAC pada file S3 tidak cocok dengan hasil perhitungan kunci, yang dapat disebabkan oleh: (1) Master Password repositori yang dimasukkan salah, atau (2) file konfigurasi di S3 telah rusak/dimanipulasi. Sistem secara tegas menolak memproses file tersebut guna melindungi keamanan infrastruktur jaringan Anda.

**Q3: Apa yang terjadi jika Master Password repositori S3 diganti (dirotasi)?**  
*Jawab:* NetBackup menggunakan model enkripsi amplop (*Envelope Encryption*). Master Password bertindak sebagai Key Encryption Key (KEK) yang membungkus Data Encryption Key (DEK). Saat Anda melakukan rotasi password di menu S3 Management, sistem hanya membungkus ulang DEK pada berkas manifes dengan password baru. Seluruh snapshot lama Anda di S3 **tetap dapat didekripsi dengan sempurna** tanpa perlu dienkripsi ulang.

**Q4: Apakah sistem dapat memulihkan konfigurasi otomatis langsung ke router/switch saat terjadi bencana jaringan?**  
*Jawab:* Sesuai rancangan batas keamanan sistem v2, NetBackup tidak melakukan *push configuration* otomatis ke perangkat secara remote untuk mencegah risiko kesalahan fatal konfigurasi yang dapat memutus akses jaringan secara total (*lockout*). File konfigurasi yang diunduh dari dashboard harus ditinjau oleh Network Engineer sebelum di-apply ke perangkat.

**Q5: Mengapa ada perangkat yang berstatus "NO_CHANGE" pada riwayat pencadangan?**  
*Jawab:* Sistem menerapkan Content-Addressable Storage (CAS) berbasis hashing SHA-256. Jika konfigurasi perangkat tidak mengalami perubahan sejak backup terakhir, sistem menandainya sebagai `NO_CHANGE`. Snapshot logis tetap dicatat untuk keperluan audit tanggal, namun sistem tidak mengunggah duplikasi file fisik baru ke S3, menghemat kapasitas penyimpanan Anda hingga 90%.

**Q6: Apa arti indikator "Sync" dan "Not-Sync" di bawah badge Zabbix pada kartu Total Devices?**  
*Jawab:* Indikator ini mencerminkan kondisi konektivitas sinkronisasi inventaris antara sistem NetBackup dan Zabbix NMS. Teks hijau bertuliskan **`Sync`** dengan border dan dot menandakan proses sinkronisasi aktif dan sehat (`status = 'OK'`). Teks merah bertuliskan **`Not-Sync`** menandakan integrasi Zabbix terputus atau mengalami kendala komunikasi.

**Q7: Bagaimana cara kerja fitur pencarian perangkat (Live Search) pada layar tablet atau ponsel?**  
*Jawab:* Pada resolusi desktop (≥ 1024px), kolom pencarian selalu terbuka penuh di samping tombol Export. Pada layar tablet dan ponsel (< 1024px), pencarian tampil ringkas berupa tombol **Search** berikon kaca pembesar untuk menghemat ruang. Saat tombol ditekan, kolom input melebar secara otomatis dan langsung memfokuskan kursor. Tombol akan memancarkan dot biru menyala jika ada filter yang sedang aktif menyaring tabel. Pengguna dapat menekan tombol `✕` atau tombol `Escape` untuk menutupnya kembali.

**Q8: Mengapa pemilihan driver backup ditiadakan dari jendela pop-up Schedule?**  
*Jawab:* Pemilihan driver backup kini dipusatkan secara eksklusif pada kolom **Backup Worker** di tabel perangkat utama untuk mencegah redundansi fungsional dan benturan konfigurasi. Jendela pop-up Schedule kini berfokus murni pada penentuan jam pencadangan harian (slot diskrit kelipatan 5 menit) dan kebijakan retensi snapshot.

**Q9: Mengapa kartu Storage Cluster (Ceph Health) terkadang hilang dari dashboard?**  
*Jawab:* Kartu metrik Ceph Cluster Health dikhususkan untuk pemantauan storage berbasis Ceph S3 (RADOS Gateway). Jika repositori S3 yang sedang aktif adalah MinIO, AWS S3, atau jika storage dalam kondisi terputus (*disconnected*), kartu tersebut otomatis disembunyikan agar operator tidak bingung dengan pembacaan status yang tidak relevan.

**Q10: Apakah konfigurasi backup perangkat akan hilang jika repositori S3 diputus (disconnect) atau diganti?**  
*Jawab:* Tidak. Sistem NetBackup memiliki mekanisme pengarsipan otomatis (`repository_device_setting_archives`). Saat repositori aktif diputus, seluruh konfigurasi driver, jadwal, dan retensi perangkat dicadangkan per bucket. Jika repositori tersebut dihubungkan kembali di kemudian hari, konfigurasi backup perangkat akan dipulihkan secara otomatis.

**Q11: Apa maksud pop-up peringatan "Sesi Akan Segera Berakhir" (Inactivity Timeout)?**  
*Jawab:* Demi kepatuhan keamanan enterprise (mencegah akses tanpa izin pada komputer kerja yang ditinggalkan), sistem memantau aktivitas interaksi pengguna. Jika tidak ada aktivitas selama periode tertentu, muncul modal hitung mundur 60 detik. Pengguna dapat mengklik "Lanjutkan Sesi" untuk memperpanjang sesi kerja, atau membiarkannya hingga sesi tertutup secara otomatis demi keamanan data.

---

*Naskah dokumentasi lengkap ini disusun secara komprehensif sebagai acuan tunggal operasional enterprise dan laporan akhir teknis Tugas Akhir (TA) NetBackup.*
