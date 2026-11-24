# app.py
import hmac
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session)

from db import get_db, init_db

app = Flask(__name__)

# --- Konfigurasi (atur lewat environment variable di production) ---
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
PUSTAKAWAN_PASSWORD = os.environ.get('PUSTAKAWAN_PASSWORD', 'pustakawan123')
if 'PUSTAKAWAN_PASSWORD' not in os.environ:
    print("PERINGATAN: PUSTAKAWAN_PASSWORD belum diset, memakai password default. "
          "Ganti sebelum dipakai sungguhan!")

# Pastikan database terinisiasi saat pertama kali jalan
init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('pustakawan'):
            flash('Silakan login sebagai pustakawan dulu.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- Publik
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/katalog')
def katalog():
    q = request.args.get('q', '').strip()
    db = get_db()

    if q:
        like = f'%{q}%'
        buku_list = db.execute(
            'SELECT * FROM buku WHERE judul LIKE ? OR penulis LIKE ? ORDER BY judul',
            (like, like)).fetchall()
    else:
        buku_list = db.execute('SELECT * FROM buku ORDER BY judul').fetchall()

    # Peminjaman yang masih aktif beserta judul bukunya
    riwayat_list = db.execute('''
        SELECT peminjaman.*, buku.judul
        FROM peminjaman
        JOIN buku ON peminjaman.buku_id = buku.id
        WHERE peminjaman.status = 'Dipinjam'
        ORDER BY peminjaman.id DESC
    ''').fetchall()
    db.close()

    return render_template('katalog.html', buku_list=buku_list,
                           riwayat_list=riwayat_list, q=q)


@app.route('/pinjam/<int:buku_id>', methods=['POST'])
def pinjam(buku_id):
    peminjam = request.form.get('peminjam', '').strip()
    tanggal_pinjam = datetime.now().strftime('%Y-%m-%d %H:%M')

    if not peminjam:
        flash('Nama peminjam wajib diisi.', 'error')
        return redirect(url_for('katalog'))
    if len(peminjam) > 100:
        flash('Nama peminjam maksimal 100 karakter.', 'error')
        return redirect(url_for('katalog'))

    db = get_db()
    # Kurangi stok secara atomik: hanya berhasil jika stok masih > 0
    cur = db.execute('UPDATE buku SET stok = stok - 1 WHERE id = ? AND stok > 0', (buku_id,))
    if cur.rowcount == 1:
        db.execute('INSERT INTO peminjaman (buku_id, peminjam, tanggal_pinjam) VALUES (?, ?, ?)',
                   (buku_id, peminjam, tanggal_pinjam))
        db.commit()
        flash(f'Buku berhasil dipinjam oleh {peminjam}.', 'success')
    else:
        flash('Buku tidak ditemukan atau stok sudah habis.', 'error')
    db.close()

    return redirect(url_for('katalog'))


# ------------------------------------------------------------ Autentikasi
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if hmac.compare_digest(password.encode(), PUSTAKAWAN_PASSWORD.encode()):
            session['pustakawan'] = True
            flash('Login berhasil.', 'success')
            return redirect(url_for('pustakawan'))
        flash('Password salah.', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('pustakawan', None)
    flash('Kamu sudah logout.', 'success')
    return redirect(url_for('index'))


# ------------------------------------------------------------- Pustakawan
@app.route('/pustakawan')
@login_required
def pustakawan():
    db = get_db()
    buku_list = db.execute('SELECT * FROM buku ORDER BY judul').fetchall()
    aktif_list = db.execute('''
        SELECT peminjaman.*, buku.judul
        FROM peminjaman
        JOIN buku ON peminjaman.buku_id = buku.id
        WHERE peminjaman.status = 'Dipinjam'
        ORDER BY peminjaman.id DESC
    ''').fetchall()
    selesai_list = db.execute('''
        SELECT peminjaman.*, buku.judul
        FROM peminjaman
        JOIN buku ON peminjaman.buku_id = buku.id
        WHERE peminjaman.status = 'Dikembalikan'
        ORDER BY peminjaman.id DESC
        LIMIT 20
    ''').fetchall()
    db.close()
    return render_template('pustakawan.html', buku_list=buku_list,
                           aktif_list=aktif_list, selesai_list=selesai_list)


@app.route('/tambah_buku', methods=['POST'])
@login_required
def tambah_buku():
    judul = request.form.get('judul', '').strip()
    penulis = request.form.get('penulis', '').strip()
    stok = request.form.get('stok', '').strip()

    if not (judul and penulis and stok):
        flash('Judul, penulis, dan stok wajib diisi.', 'error')
        return redirect(url_for('pustakawan'))

    try:
        stok = int(stok)
    except ValueError:
        flash('Stok harus berupa angka.', 'error')
        return redirect(url_for('pustakawan'))
    if stok < 0:
        flash('Stok tidak boleh negatif.', 'error')
        return redirect(url_for('pustakawan'))

    db = get_db()
    db.execute('INSERT INTO buku (judul, penulis, stok) VALUES (?, ?, ?)',
               (judul, penulis, stok))
    db.commit()
    db.close()
    flash(f'Buku "{judul}" berhasil ditambahkan.', 'success')
    return redirect(url_for('pustakawan'))


@app.route('/kembali/<int:peminjaman_id>', methods=['POST'])
@login_required
def kembali(peminjaman_id):
    tanggal_kembali = datetime.now().strftime('%Y-%m-%d %H:%M')
    db = get_db()
    pinjaman = db.execute(
        "SELECT buku_id FROM peminjaman WHERE id = ? AND status = 'Dipinjam'",
        (peminjaman_id,)).fetchone()

    if pinjaman:
        db.execute("UPDATE peminjaman SET status = 'Dikembalikan', tanggal_kembali = ? WHERE id = ?",
                   (tanggal_kembali, peminjaman_id))
        db.execute('UPDATE buku SET stok = stok + 1 WHERE id = ?', (pinjaman['buku_id'],))
        db.commit()
        flash('Buku sudah dikembalikan, stok bertambah.', 'success')
    else:
        flash('Data peminjaman tidak ditemukan atau sudah dikembalikan.', 'error')
    db.close()
    return redirect(url_for('pustakawan'))


@app.route('/hapus_buku/<int:buku_id>', methods=['POST'])
@login_required
def hapus_buku(buku_id):
    db = get_db()
    aktif = db.execute(
        "SELECT COUNT(*) FROM peminjaman WHERE buku_id = ? AND status = 'Dipinjam'",
        (buku_id,)).fetchone()[0]

    if aktif:
        flash(f'Buku tidak bisa dihapus: masih ada {aktif} peminjaman aktif.', 'error')
    else:
        # Hapus riwayat lama buku ini dulu agar tidak melanggar foreign key
        db.execute('DELETE FROM peminjaman WHERE buku_id = ?', (buku_id,))
        db.execute('DELETE FROM buku WHERE id = ?', (buku_id,))
        db.commit()
        flash('Buku berhasil dihapus.', 'success')
    db.close()
    return redirect(url_for('pustakawan'))


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '1') == '1')
