# db.py
import os
import sqlite3

# Path absolut, jadi database selalu ketemu walau app dijalankan dari folder lain
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'library.db')


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    db = get_db()
    # Tabel Buku
    db.execute('''
        CREATE TABLE IF NOT EXISTS buku (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul TEXT NOT NULL,
            penulis TEXT NOT NULL,
            stok INTEGER NOT NULL CHECK (stok >= 0)
        )
    ''')
    # Tabel Peminjaman
    db.execute('''
        CREATE TABLE IF NOT EXISTS peminjaman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buku_id INTEGER,
            peminjam TEXT NOT NULL,
            tanggal_pinjam TEXT NOT NULL,
            tanggal_kembali TEXT,
            status TEXT DEFAULT 'Dipinjam',
            FOREIGN KEY (buku_id) REFERENCES buku (id)
        )
    ''')

    # Migrasi untuk library.db lama yang belum punya kolom tanggal_kembali
    kolom = [row['name'] for row in db.execute('PRAGMA table_info(peminjaman)')]
    if 'tanggal_kembali' not in kolom:
        db.execute('ALTER TABLE peminjaman ADD COLUMN tanggal_kembali TEXT')

    db.commit()
    db.close()


if __name__ == '__main__':
    init_db()
    print("Database SQLite berhasil diinisialisasi!")
