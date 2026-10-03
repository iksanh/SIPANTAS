# -*- coding: utf-8 -*-
"""Sesi masuk: satu baris di tabel `sesi`, token acak di kuki HttpOnly.

Sengaja bukan kuki bertanda tangan bawaan Flask: sesi yang tercatat di
basis data bisa dicabut dari sisi server, dan bentuknya tidak berubah sejak
versi http.server — pengguna yang sedang masuk tidak terlempar keluar saat
aplikasinya diperbarui.
"""
import datetime as dt
import os
import secrets

from . import db

NAMA_KUKI = "sesi"
# Kuki kedua, untuk yang belum masuk. Isinya token CSRF halaman masuk: tanpa
# ini, formulir masuk sendiri tidak terjaga, dan penyerang bisa memaksa korban
# masuk ke akun miliknya lalu menunggu korban mengetik data ke sana.
KUKI_TAMU = "csrf_tamu"
UMUR_JAM = 12
# Di belakang HTTPS (mis. nginx atau Caddy di depan), setel HTTPS=1 di
# lingkungan supaya kukinya ikut ditandai Secure.
LEWAT_HTTPS = os.environ.get("HTTPS", "").strip() not in ("", "0", "tidak")


def muat(k, token):
    """(pengguna, token CSRF) untuk sesi ini.

    (None, None) kalau tokennya kosong, kedaluwarsa, tidak dikenal, atau
    penggunanya sudah dinonaktifkan. Keduanya diambil dalam satu kueri karena
    dibutuhkan bersama di tiap permintaan.
    """
    if not token:
        return None, None
    r = k.execute(
        "SELECT p.*, s.csrf AS _csrf FROM sesi s JOIN pengguna p ON p.id=s.pengguna_id "
        "WHERE s.token=? AND s.kedaluwarsa > ? AND p.aktif=1",
        (token, db.sekarang())).fetchone()
    if not r:
        return None, None
    d = dict(r)
    return d, d.pop("_csrf")


def buat(k, pengguna_id):
    """Sesi baru berikut token CSRF-nya sendiri. Sekalian membuang sesi yang
    sudah lewat waktunya."""
    token = secrets.token_urlsafe(32)
    habis = (dt.datetime.now() + dt.timedelta(hours=UMUR_JAM)).strftime("%Y-%m-%d %H:%M:%S")
    k.execute("DELETE FROM sesi WHERE kedaluwarsa < ?", (db.sekarang(),))
    k.execute("INSERT INTO sesi (token,pengguna_id,kedaluwarsa,csrf) VALUES (?,?,?,?)",
              (token, pengguna_id, habis, secrets.token_urlsafe(32)))
    k.commit()
    return token


def token_baru():
    return secrets.token_urlsafe(32)


def pasang_kuki_tamu(jawaban, nilai):
    """Kuki token CSRF untuk yang belum masuk. HttpOnly: nilainya tidak perlu
    dibaca JavaScript, cukup dibandingkan di server dengan isian formulirnya."""
    jawaban.set_cookie(KUKI_TAMU, nilai, max_age=UMUR_JAM * 3600, path="/",
                       httponly=True, samesite="Lax", secure=LEWAT_HTTPS)
    return jawaban


def hapus(k, token):
    if token:
        k.execute("DELETE FROM sesi WHERE token=?", (token,))
        k.commit()


def pasang_kuki(jawaban, token):
    jawaban.set_cookie(NAMA_KUKI, token, max_age=UMUR_JAM * 3600, path="/",
                       httponly=True, samesite="Lax", secure=LEWAT_HTTPS)
    return jawaban


def hapus_kuki(jawaban):
    jawaban.delete_cookie(NAMA_KUKI, path="/")
    return jawaban
