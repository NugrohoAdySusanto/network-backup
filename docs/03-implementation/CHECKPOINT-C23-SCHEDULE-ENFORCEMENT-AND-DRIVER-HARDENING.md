# CHECKPOINT C23: Strict 5-Minute Discrete Scheduling & Ruijie AP Driver Hardening

## 1. Tujuan dan Ruang Lingkup
Checkpoint ini mencakup penyempurnaan stabilitas operasional driver jaringan lapangan serta sinkronisasi penjadwalan periodik:
1. **Penegakan Penjadwalan Diskrit Kelipatan 5 Menit:** Menyelaraskan frekuensi eksekusi Celery Beat (tick 60s) dengan pilihan waktu pengguna, memastikan waktu backup perangkat hanya dapat dipilih dan disimpan pada kelipatan 5 menit (misal: `01:00`, `01:05`, `01:10`, ..., `01:55`).
2. **Hardening Driver Ruijie Wireless AP:** Mengatasi isu koneksi SSH timeout dan negosiasi key exchange pada perangkat Ruijie AP (seperti AP-04 dan AP-05) tanpa memerlukan penambahan manual `ssh-rsa` pada berkas `known_hosts`.
3. **Standarisasi Bahasa Inggris Penuh (Full English Localization):** Mengaudit seluruh antarmuka web, modal dialog, formulir, dan pesan log agar 100% konsisten menggunakan Bahasa Inggris formal.

---

## 2. Rincian Teknis Implementasi

### A. Penjadwalan 5 Menit Diskrit
- **Antarmuka Web (`frontend/index.html` & `frontend/js/schedules.js`):**
  - Menggantikan input teks waktu bebas (`<input type="time">`) dengan dua dropdown terkontrol:
    - Dropdown Jam: `00` s/d `23`.
    - Dropdown Menit: `:00`, `:05`, `:10`, `:15`, `:20`, `:25`, `:30`, `:35`, `:40`, `:45`, `:50`, `:55`.
  - Mencegah inkonsistensi di mana pengguna memilih menit sembarang (misal: 14:03) tetapi sistem hanya memicu job pada kelipatan 5 menit.
- **Validasi Backend (`backend/app/api/backup_settings.py`):**
  - Memvalidasi bahwa komponen menit pada `daily_time` bernilai modulo 5 (`minute % 5 == 0`).
  - Menolak input menit tidak valid dengan kode kesalahan `VALIDATION_ERROR` (HTTP 422).

### B. Hardening Driver Ruijie AP
- **Berkas:** `backend/app/drivers/ruijie_ap.py`.
- Mengonfigurasi parameter SSH Paramiko/Netmiko:
  - Penambahan fallback algoritma key exchange dan host key legacy (`ssh-rsa`, `diffie-hellman-group14-sha1`) untuk AP lawas.
  - Penyesuaian `banner_timeout`, `auth_timeout`, dan `blocking_timeout` agar toleran terhadap latensi jaringan nirkabel kantor cabang.
  - Penanganan bypass verifikasi host key secara terkontrol saat mode strict checking dimatikan.
  - Verifikasi lapangan sukses pada pengujian backup AP-04 (`10.11.1.233:22345`) dan AP-05 (`10.11.1.229:22345`).

### C. Standarisasi Bahasa Inggris Penuh
- Menghapus seluruh kata atau kalimat Bahasa Indonesia pada antarmuka pengguna (`frontend/index.html`, `frontend/js/`), dialog modal jadwal, dialog driver builder, dialog storage manager, dan pesan error REST API.
- Menjamin konsistensi istilah teknis global (misal: *Backup Now*, *Schedule*, *Retention Policy*, *Storage Repositories*, *Audit & Security Logs*).

---

## 3. Hasil Verifikasi Lapangan & Status
- Seluruh pengujian backup manual dan terjadwal pada Ruijie AP berjalan sukses dengan status `SUCCESS_CHANGED` atau `SUCCESS_NO_CHANGE`.
- Penjadwalan 5 menit beroperasi sinkron antara tampilan dashboard dan antrean Celery Beat.
