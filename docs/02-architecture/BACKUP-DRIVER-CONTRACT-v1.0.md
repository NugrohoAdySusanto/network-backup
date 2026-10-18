# Kontrak Backup Driver

## Tujuan dan batas

Backup driver menyatukan perbedaan perintah perangkat di belakang kontrak yang dipakai `BackupExecutionService`. Driver mengambil konfigurasi, menormalisasi hasil, memvalidasinya, lalu mengembalikan data ke pipeline. Driver tidak mengelola database, antrean, S3, enkripsi, snapshot, retention, notifikasi, atau API.

Pengambilan konfigurasi bergantung pada koneksi CLI jarak jauh yang disediakan backend; rincian keamanan transport tersebut berada di luar scope dokumen ini.

## Interface wajib

Source kebenaran berada di `backend/app/drivers/base.py`.

```python
class BackupDriver(ABC):
    metadata: DriverMetadata

    def connect(self, context: DeviceConnectionContext) -> None: ...
    def collect_config(self) -> CollectedConfig: ...
    def normalize_config(self, collected: CollectedConfig) -> str: ...
    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None: ...
    def cleanup(self) -> None: ...
```

`cleanup()` harus aman dipanggil pada blok `finally`, termasuk ketika `connect()` atau `collect_config()` gagal.

## Metadata

Setiap driver memiliki `DriverMetadata` yang tidak berubah selama instance berjalan.

| Field | Makna |
|---|---|
| `key` | Identitas stabil yang disimpan di pengaturan dan job |
| `label` | Nama untuk UI |
| `transport` | Jenis transport deklaratif |
| `implementation` | Nama implementasi driver |
| `output_extension` | Ekstensi file tanpa titik |
| `vendor_hint` | Petunjuk vendor opsional |
| `model_hint` | Petunjuk model opsional |

`vendor_hint` dan `model_hint` tidak boleh dipakai untuk memilih driver otomatis. Penetapan driver dilakukan secara eksplisit melalui pengaturan perangkat.

## Context koneksi

`DeviceConnectionContext` berisi:

| Field | Tipe |
|---|---|
| `device_id` | integer |
| `hostname` | string |
| `host` | string |
| `port` | integer |
| `username` | string |
| `password` | string |
| `connect_timeout` | integer |
| `command_timeout` | integer |
| `enable_password` | string atau `None` |

Driver menerima context dari service dan tidak membaca `.env` atau database. Implementasi `repr` context menyamarkan password. Driver juga tidak boleh memasukkan password, enable password, atau isi konfigurasi ke log dan exception.

## Hasil koleksi

`CollectedConfig` memuat:

| Field | Tipe | Default |
|---|---|---|
| `text` | string | Wajib |
| `extension` | string | Wajib |
| `encoding` | string | `utf-8` |
| `filename` | string atau `None` | `None` |

`text` harus berisi keluaran perangkat asli. Driver tidak boleh menambahkan timestamp aplikasi, job ID, hash, status, atau metadata S3 ke isi konfigurasi karena nilai tersebut akan merusak change detection.

## Driver registry

`backend/app/drivers/registry.py` mendaftarkan driver bawaan berikut:

| Key | Implementasi |
|---|---|
| `sangfor-nsf` | `SangforNSFDriver` |
| `mikrotik-routeros` | `MikrotikRouterOSDriver` |
| `ruijie-switch` | `RuijieSwitchDriver` |
| `ruijie-ap` | `RuijieAPDriver` |

Driver mock hanya didaftarkan jika `ENABLE_MOCK_DRIVER=true` dan environment bukan production.

Registry juga membaca driver kustom aktif dari tabel `custom_drivers` dan membuat `ParametricCLIDriver`. Key driver bawaan tidak boleh diduplikasi.

## Driver kustom

Driver kustom menyimpan parameter koneksi, perintah paging, perintah backup, ekstensi output, pola pembersihan, panjang minimum, dan keyword validasi. `strip_patterns` adalah daftar pola yang diaplikasikan oleh normalizer. Perubahan definisi driver tidak mengubah `driver_key` yang sudah dicatat pada job lama.

API pengelolaan dan test driver berada di [Kontrak REST API](API-CONTRACT-v1.0.md). Schema database berada di [Arsitektur Database](DATABASE-SCHEMA-ERD-v1.0.md).

## Normalisasi

Normalisasi bertujuan membuat hash konten stabil tanpa mengubah data mentah yang disimpan sebagai artefak. Implementasi dapat membuang prompt, banner, timestamp dinamis, atau baris noise yang memang diketahui untuk perangkat terkait.

Aturan:

- hasil normalisasi wajib deterministik untuk input yang sama;
- urutan baris konfigurasi tidak boleh diubah sembarangan;
- secret pada konfigurasi tidak boleh ditulis ke log;
- driver mengembalikan error jika proses normalisasi tidak dapat dipercaya;
- hash raw dan hash normalized dihitung oleh service, bukan driver.

## Validasi

Validasi minimal memastikan output tidak kosong dan memiliki struktur yang diharapkan driver. Driver kustom memakai `validation_min_length` dan `validation_required_keyword` bila dikonfigurasi. Validasi tidak boleh menyatakan sukses hanya karena koneksi berhasil.

## Taxonomy error

| Exception | Code | Retryable |
|---|---|---|
| `DriverConfigurationError` | `DRIVER_CONFIGURATION_ERROR` | Tidak |
| `DriverNotFoundError` | `DRIVER_NOT_FOUND` | Tidak |
| `DriverNotImplementedError` | `DRIVER_NOT_IMPLEMENTED` | Tidak |
| `DriverConnectionError` | Lihat konstanta pada source | Ya |
| `DriverAuthenticationError` | `AUTHENTICATION_FAILED` | Tidak |
| `DriverConnectionTimeoutError` | `CONNECTION_TIMEOUT` | Ya |
| `DriverCommandTimeoutError` | `COMMAND_TIMEOUT` | Ya |
| `DriverCollectionError` | `COMMAND_FAILED` | Tidak |
| `DriverNormalizationError` | `NORMALIZATION_FAILED` | Tidak |
| `DriverValidationError` | `INVALID_CONFIG` | Tidak |

Retry akhir tetap ditentukan oleh backup service dan batas `max_attempts` job.

## Checklist implementasi driver baru

1. Pilih key stabil dan ekstensi aman.
2. Implementasikan seluruh method `BackupDriver`.
3. Pastikan cleanup idempotent.
4. Sanitasi exception dan log.
5. Tambahkan unit test untuk metadata, koneksi gagal, koleksi, normalisasi, validasi, dan cleanup.
6. Daftarkan class di registry atau buat record driver kustom.
7. Uji melalui endpoint driver test pada environment non-production.
8. Perbarui dokumentasi dan traceability bila perilaku pipeline berubah.
