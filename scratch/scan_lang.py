import os
import re

distinctive_id = [
    'berhasil', 'gagal', 'simpan', 'hapus', 'ubah', 'tambah', 'batal', 'tutup',
    'unduh', 'masuk', 'keluar', 'kata sandi', 'perangkat', 'pengguna', 'repositori',
    'pekerjaan', 'peringatan', 'riwayat', 'catatan', 'koneksi', 'apakah', 'silakan',
    'mohon', 'pilih', 'harap', 'kembali', 'hanya', 'tidak', 'sudah', 'belum',
    'dihapus', 'ditambahkan', 'diperbarui', 'sekarang'
]

pattern = re.compile(r'\b(' + '|'.join(distinctive_id) + r')\b', re.IGNORECASE)

# Check frontend
files_to_check = ['/opt/network-backup/frontend/index.html']
for f in os.listdir('/opt/network-backup/frontend/js'):
    if f.endswith('.js'):
        files_to_check.append(os.path.join('/opt/network-backup/frontend/js', f))

print("=== Scanning Frontend ===")
for path in files_to_check:
    with open(path, 'r', encoding='utf-8') as fp:
        for line_no, line in enumerate(fp, 1):
            m = pattern.search(line)
            if m:
                print(f"{os.path.basename(path)}:{line_no} [{m.group(0)}]: {line.strip()[:100]}")

# Check backend api & services messages
print("\n=== Scanning Backend API & Services ===")
backend_files = []
for root, dirs, files in os.walk('/opt/network-backup/backend/app'):
    for f in files:
        if f.endswith('.py'):
            backend_files.append(os.path.join(root, f))

for path in backend_files:
    with open(path, 'r', encoding='utf-8') as fp:
        for line_no, line in enumerate(fp, 1):
            m = pattern.search(line)
            if m:
                rel = os.path.relpath(path, '/opt/network-backup/backend/app')
                print(f"{rel}:{line_no} [{m.group(0)}]: {line.strip()[:100]}")
