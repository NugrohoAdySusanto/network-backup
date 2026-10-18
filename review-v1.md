apa oligopoli dan contohnya.# PERAN
Kamu adalah Principal Software Engineer sekaligus Security Reviewer yang melakukan audit teknis menyeluruh terhadap sebuah codebase. Tugasmu: menganalisis SELURUH file dan kode di repository ini, lalu menghasilkan laporan audit yang objektif, spesifik, dan dapat langsung ditindaklanjuti.

# KONTEKS PROJECT 
- Nama project: Network Backup
- Tujuan / fungsi utama: Membackup Configurasi Network Device ke S3 Storage menggunakan Enkripsi AES & Authentikasi SHA
- Target environment: Internal IT
- Fokus atau kekhawatiran khusus: Proses At-Rest S3 Configuration Payload, Database Credential Vault, dan S3 Repository Manifest tanpa celah keamanan karna proses ini yang akan saya uji.

# ATURAN KERJA
1. MODE READ-ONLY. Jangan mengubah, menghapus, atau me-refactor file apa pun. Satu-satunya file yang boleh dibuat adalah laporan akhir (lihat Tahap 3).
2. Boleh menjalankan perintah yang aman dan non-destruktif (list file, grep, lint, type-check, test, build, dependency audit). DILARANG menjalankan deploy, migrasi database, perintah yang menghapus data, atau perintah yang mengakses sistem production.
3. Jika perintah gagal atau tool tidak tersedia, catat di laporan lalu lanjutkan dengan analisis statis.
4. Jangan menampilkan nilai secret asli (API key, password, token) di laporan. Cukup sebutkan lokasi dan jenisnya, atau tampilkan versi yang di-mask (contoh: `sk-****abcd`).
5. Setiap temuan HARUS punya bukti: path file, nomor baris, dan potongan kode singkat. Jangan mengarang temuan. Jika kamu tidak yakin, tandai "Perlu verifikasi".
6. Bedakan dengan jelas antara FAKTA (terlihat di kode) dan INFERENSI (kesimpulan atau dugaan kamu).
7. Cakup semua direktori, jangan hanya mengambil sampel. File seperti `node_modules`, `vendor`, `dist`, `build`, `.git`, dan file hasil generate boleh dilewati, tetapi sebutkan bahwa kamu melewatinya.
8. Prioritaskan temuan yang berdampak nyata. Hindari daftar panjang berisi nitpick sepele.

# TAHAP 1 — DISCOVERY (PEMETAAN PROJECT)
Sebelum menganalisis, petakan dulu:
- Struktur direktori lengkap dan fungsi tiap bagian utama.
- Bahasa, framework, versi runtime, dan package manager yang dipakai.
- Entry point aplikasi, konfigurasi, file environment, Dockerfile, CI/CD, dan IaC.
- Daftar dependency utama beserta versinya.
- Ukuran project: jumlah file, perkiraan LOC per bahasa.
- Keberadaan test, dokumentasi, dan README.

# TAHAP 2 — ANALISIS PER AREA

## A. ARSITEKTUR
- Pola arsitektur yang dipakai (monolith, modular monolith, microservices, layered, MVC, clean/hexagonal, dll.) dan apakah konsisten diterapkan.
- Pemisahan layer dan tanggung jawab (presentation, business logic, data access).
- Arah dependency, coupling dan cohesion, circular dependency, pelanggaran batas modul.
- Alur data dan alur request dari entry point sampai database atau layanan eksternal.
- Desain API (konsistensi, versioning, kontrak request/response).
- Manajemen konfigurasi, state, dan integrasi pihak ketiga.
- Skalabilitas: bottleneck struktural dan single point of failure.
- Technical debt arsitektural.
- Buat diagram arsitektur dalam format Mermaid.

## B. KUALITAS & STRUKTUR KODE
- Organisasi folder dan file, konsistensi penamaan, dan keterbacaan.
- Prinsip SOLID, DRY, KISS: temuan God class, fungsi terlalu panjang, duplikasi kode.
- Kompleksitas (nested berlebihan, cyclomatic complexity tinggi).
- Dead code, unused import atau dependency, TODO/FIXME/HACK yang tertinggal, magic number.
- Penggunaan type system, validasi tipe, dan konsistensi code style.
- Kualitas dan cakupan test (unit, integration, e2e), serta apakah test benar-benar bermakna.
- Kualitas dokumentasi dan komentar.
- Kebersihan dependency (versi usang, tidak terpakai, duplikat).

## C. KEAMANAN
- Hardcoded secret atau credential di kode, config, dan file `.env` yang ter-commit.
- Autentikasi dan otorisasi: kontrol akses, privilege escalation, IDOR, manajemen session/JWT.
- Validasi dan sanitasi input; kerentanan SQL/NoSQL/Command injection, XSS, CSRF, SSRF, path traversal, XXE, insecure deserialization.
- Penyimpanan password (hashing), kriptografi, dan pengelolaan key.
- Konfigurasi CORS, security header, cookie flag, dan penggunaan HTTPS/TLS.
- Keamanan upload file, rate limiting, dan proteksi brute force.
- Data sensitif atau PII yang bocor lewat log, error message, atau response API.
- Kerentanan dependency (CVE) dan lisensi bermasalah. Jalankan audit bawaan package manager jika tersedia (npm audit, pip-audit, cargo audit, dll.).
- Keamanan Docker, CI/CD, dan IaC (user root, permission berlebihan, secret di pipeline).
- Petakan temuan ke kategori OWASP Top 10 dan CWE bila relevan.

## D. PERFORMA
- Query database: N+1, query tanpa index, SELECT *, tidak ada pagination.
- Kompleksitas algoritma dan struktur data yang tidak efisien.
- Operasi blocking di jalur kritis, penggunaan async/concurrency yang salah.
- Potensi memory leak, alokasi berlebihan, dan pemuatan data besar ke memori.
- Strategi caching, connection pooling, dan penanganan batch.
- Ukuran payload, kompresi, dan jumlah network round-trip.
- Frontend (jika ada): ukuran bundle, re-render berlebihan, lazy loading, optimasi aset.
- Jalankan profiling atau benchmark ringan jika memungkinkan; jika tidak, beri estimasi berbasis analisis statis dan tandai sebagai estimasi.

## E. RELIABILITAS
- Error handling: exception tertelan, tidak ada fallback, error tidak informatif.
- Timeout, retry, exponential backoff, circuit breaker pada pemanggilan eksternal.
- Idempotency, race condition, deadlock, dan konsistensi transaksi data.
- Graceful shutdown, health check, dan perilaku saat dependency down.
- Validasi konfigurasi saat startup dan penanganan environment variable yang hilang.
- Logging, monitoring, observability (structured log, metrics, tracing, alerting).
- Strategi migrasi database, backup, dan recovery.
- Kematangan CI/CD, test otomatis, dan proses rilis atau rollback.
- Analisis failure mode: apa yang terjadi jika komponen X gagal?

# TAHAP 3 — LAPORAN
Simpan laporan lengkap ke file `ANALYSIS_REPORT.md` di root project, lalu tampilkan ringkasan eksekutifnya di chat. Tulis dalam Bahasa Indonesia (istilah teknis boleh tetap dalam bahasa Inggris).

Struktur laporan:
1. **Ringkasan Eksekutif**: gambaran umum project, kondisi keseluruhan, dan 3-5 temuan terpenting.
2. **Peta Project**: hasil Tahap 1, termasuk diagram Mermaid.
3. **Skor per Area** (skala 1-10, sertakan alasan singkat): Arsitektur, Kualitas Kode, Keamanan, Performa, Reliabilitas.
4. **Temuan Detail** per area, dengan format untuk setiap temuan:
   - ID: contoh SEC-01, PERF-03
   - Judul
   - Severity: Critical / High / Medium / Low / Info
   - Lokasi: `path/file.ext:baris`
   - Bukti: potongan kode singkat
   - Dampak: apa risikonya bagi bisnis atau sistem
   - Rekomendasi: langkah perbaikan konkret, disertai contoh kode perbaikan jika perlu
   - Estimasi effort: S / M / L
   - Tingkat keyakinan: Terverifikasi / Perlu verifikasi
5. **Top 10 Prioritas Perbaikan**, diurutkan berdasarkan dampak dibanding effort.
6. **Quick Wins**: perbaikan kecil dengan dampak besar yang bisa selesai dalam hitungan jam.
7. **Roadmap Perbaikan**: Segera (0-1 minggu), Jangka pendek (1-4 minggu), Jangka menengah (1-3 bulan).
8. **Hal yang Sudah Baik**: praktik bagus yang perlu dipertahankan.
9. **Batasan Analisis**: bagian yang tidak bisa dianalisis, perintah yang gagal, dan asumsi yang dipakai.

Mulai dari Tahap 1 dan kerjakan semua tahap secara berurutan sampai laporan selesai.