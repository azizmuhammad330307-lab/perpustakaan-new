# PustakaHijau

Aplikasi perpustakaan sederhana (Flask + SQLite + Tailwind CSS).

## Menjalankan

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Buka http://127.0.0.1:5000

## Konfigurasi (environment variable)

| Variable | Fungsi | Default |
|---|---|---|
| `PUSTAKAWAN_PASSWORD` | Password login Panel Pustakawan | `pustakawan123` (ganti!) |
| `SECRET_KEY` | Kunci session Flask | acak tiap start |
| `FLASK_DEBUG` | `1` / `0` untuk mode debug | `1` |

Contoh (Windows PowerShell):

```powershell
$env:PUSTAKAWAN_PASSWORD = "passwordku"
$env:SECRET_KEY = "string-acak-panjang"
python app.py
```

## Fitur

- Katalog buku + pencarian judul/penulis
- Peminjaman buku (stok berkurang otomatis)
- Panel pustakawan (login): tambah buku, hapus buku, tandai pengembalian, riwayat
