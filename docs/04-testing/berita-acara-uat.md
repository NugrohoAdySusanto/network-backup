# Template Berita Acara User Acceptance Test

Dokumen ini adalah template. Semua field wajib diisi oleh pelaksana yang berwenang setelah pengujian dilakukan. Jangan menandai hasil sebelum tersedia bukti eksekusi.

## Identitas pelaksanaan

| Field | Nilai |
|---|---|
| Nama proyek | NetBackup |
| Environment | [ISI: nama environment UAT] |
| URL | [ISI: URL environment UAT] |
| Branch/tag/commit | [ISI: referensi versi yang diuji] |
| Tanggal mulai | [ISI: tanggal dan timezone] |
| Tanggal selesai | [ISI: tanggal dan timezone] |
| Koordinator UAT | [ISI: nama dan peran] |
| Perwakilan pengguna | [ISI: nama dan peran] |
| Data uji | [ISI: deskripsi data sintetis] |

## Ruang lingkup

[ISI: modul, requirement, dan batas pengujian]

## Prasyarat dan dependency

| Item | Status | Catatan |
|---|---|---|
| Stack aplikasi tersedia | [ISI] | [ISI] |
| Migration database sesuai versi | [ISI] | [ISI] |
| Integrasi sandbox tersedia | [ISI] | [ISI] |
| Akun admin dan viewer uji tersedia | [ISI] | [ISI] |
| Backup/rollback environment dikonfirmasi | [ISI] | [ISI] |

## Hasil skenario

Gunakan status `Lulus`, `Gagal`, `Blocked`, atau `Belum Diuji` setelah skenario dijalankan.

| No. | Test ID | Skenario | Status | Bukti | Catatan/defect |
|---:|---|---|---|---|---|
| 1 | [ISI: TC-...] | [ISI] | [ISI] | [ISI: link/lokasi bukti] | [ISI] |
| 2 | [ISI: TC-...] | [ISI] | [ISI] | [ISI: link/lokasi bukti] | [ISI] |
| 3 | [ISI: TC-...] | [ISI] | [ISI] | [ISI: link/lokasi bukti] | [ISI] |

Tambahkan baris sesuai jumlah skenario yang dieksekusi. Daftar skenario sumber berada di [Test Script](test-script.md).

## Defect dan tindak lanjut

| Defect ID | Ringkasan | Severity | Pemilik | Target | Status |
|---|---|---|---|---|---|
| [ISI] | [ISI] | [ISI] | [ISI] | [ISI] | [ISI] |

## Pengecualian

[ISI: skenario yang tidak dijalankan, alasan, risiko, dan persetujuan]

## Kesimpulan

| Keputusan | Pilih setelah review |
|---|---|
| Diterima | [ISI] |
| Diterima dengan catatan | [ISI] |
| Ditolak | [ISI] |

Ringkasan keputusan:

[ISI: alasan keputusan dan syarat tindak lanjut]

## Persetujuan

| Peran | Nama | Keputusan | Tanggal | Tanda tangan/referensi persetujuan |
|---|---|---|---|---|
| Product Owner/Perwakilan bisnis | [ISI] | [ISI] | [ISI] | [ISI] |
| Project Manager | [ISI] | [ISI] | [ISI] | [ISI] |
| QA Lead | [ISI] | [ISI] | [ISI] | [ISI] |
| Technical Lead | [ISI] | [ISI] | [ISI] | [ISI] |
