# Frontend NetBackup

Frontend NetBackup adalah dashboard statis tanpa proses build Node. Nginx menyajikan `index.html`, CSS, dan modul JavaScript, lalu mem-proxy request `/api/` dan `/healthz` ke FastAPI.

## Entry point

- `index.html`: dashboard utama dan seluruh dialog operasional.
- `crypto-animation.html`: visualisasi edukasi alur payload S3, bukan control produksi.
- `css/app.css`: style tambahan.

## Modul JavaScript

| File | Fungsi |
|---|---|
| `js/api.js` | Request API same-origin, CSRF, dan normalisasi error |
| `js/auth.js` | Login, logout, dan pemulihan session |
| `js/devices.js` | Daftar perangkat, ringkasan, sync, backup, dan setting |
| `js/backups.js` | Histori serta detail job |
| `js/archives.js` | Snapshot dan download |
| `js/schedules.js` | Jadwal dan retention perangkat |
| `js/storage.js` | Pengelolaan repository |
| `js/reports.js` | Export XLSX/PDF |
| `js/users.js` | Preferensi dan user admin |
| `js/workers.js` | Driver bawaan/kustom dan test driver |
| `js/theme.js` | Light/dark preference |

## Menjalankan

Frontend normal dijalankan melalui stack lengkap:

```bash
docker compose up -d --build
```

Port lokal default:

```text
http://localhost:8080
```

URL deployment yang didokumentasikan:

```text
https://netbackup.makuku.co.id
```

Membuka file langsung melalui `file://` tidak mendukung alur session/API dan bukan cara pengujian yang valid.

## Kontrak autentikasi

- Browser menerima cookie session HttpOnly dari backend.
- Token CSRF diperoleh dari respons login atau `/api/v1/auth/me` dan dikirim oleh `js/api.js` pada operasi perubahan.
- Tidak ada endpoint `/api/v1/auth/csrf-token` terpisah.
- Jika session invalid, frontend kembali ke dialog login.
- UI menyembunyikan action admin dari viewer, tetapi backend tetap melakukan pemeriksaan final.

## Aturan perubahan

1. Gunakan wrapper `api.js`; jangan memanggil dependency eksternal secara langsung.
2. Escape data tidak dipercaya sebelum disisipkan ke HTML.
3. Sediakan state loading, empty, error, disabled, dan success.
4. Pertahankan fokus keyboard, label dialog/form, dan kontras light/dark.
5. Uji viewport ponsel, tablet, dan desktop.
6. Selaraskan perubahan route dengan [Kontrak API](../docs/02-architecture/API-CONTRACT-v1.0.md).
7. Selaraskan workflow dengan [Spesifikasi UI](../docs/01-product/DESIGN-FINAL.md) dan [Test Script](../docs/04-testing/test-script.md).

## Visualisasi kriptografi

`crypto-animation.html` memakai Web Crypto API untuk demonstrasi primitive di browser, sedangkan tahap kompresinya adalah transformasi ilustratif dan bukan implementasi produksi. Rujukan teknis yang mengikat adalah [Spesifikasi Enkripsi Backup S3](../docs/03-design/enkripsi-backup-s3.md).
