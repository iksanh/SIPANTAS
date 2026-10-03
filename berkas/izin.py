# -*- coding: utf-8 -*-
"""Siapa boleh berbuat apa.

Dua peran saja, disimpan di kolom `pengguna.peran`:

    admin     seluruh aplikasi
    petugas   berkas miliknya sendiri, dan membaca data referensi

Kepemilikan berkas ada di kolom `berkas.dibuat_oleh`. Berkas hasil impor
Excel kolomnya NULL — tidak ada yang mengetiknya lewat aplikasi ini. Arsip
itu dibiarkan terlihat semua orang supaya pekerjaan yang sedang berjalan
tidak terputus, tetapi hanya admin yang boleh mengubahnya: tidak ada cara
memastikan siapa yang berhak atas berkas yang pemiliknya tidak tercatat.

Aturan di sini dipakai dua kali untuk tiap halaman — sekali oleh rute untuk
menolak permintaan, sekali oleh web.py untuk menyembunyikan tombolnya.
Menyembunyikan tombol saja tidak menjaga apa pun; penolakan di rute itulah
penjaganya.
"""
from functools import wraps

from flask import abort, g

ADMIN = "admin"
PETUGAS = "petugas"

NAMA_PERAN = {ADMIN: "Administrator", PETUGAS: "Petugas"}
PILIHAN_PERAN = [(PETUGAS, "Petugas"), (ADMIN, "Administrator")]


def admin(pengguna):
    return bool(pengguna) and pengguna.get("peran") == ADMIN


def boleh_lihat(pengguna, dibuat_oleh):
    """Admin melihat semua. Petugas melihat miliknya dan arsip tanpa pemilik."""
    if admin(pengguna):
        return True
    return dibuat_oleh is None or dibuat_oleh == pengguna["id"]


def boleh_ubah(pengguna, dibuat_oleh):
    """Arsip tanpa pemilik hanya boleh disentuh admin — lihat catatan di atas."""
    if admin(pengguna):
        return True
    return dibuat_oleh is not None and dibuat_oleh == pengguna["id"]


def saringan_daftar(pengguna):
    """(potongan WHERE, parameter) untuk daftar berkas. Kosong berarti semua."""
    if admin(pengguna):
        return "", ()
    return "WHERE b.dibuat_oleh IS NULL OR b.dibuat_oleh = ?", (pengguna["id"],)


def pemilik_berkas(k, berkas_id):
    """Isi kolom dibuat_oleh, atau False kalau berkasnya tidak ada.

    None berarti berkas ada tetapi tanpa pemilik, jadi tidak bisa dibedakan
    dari "tidak ada" lewat nilai kembaliannya sendiri.
    """
    r = k.execute("SELECT dibuat_oleh FROM berkas WHERE id=?", (berkas_id,)).fetchone()
    return False if r is None else r["dibuat_oleh"]


# ------------------------------------------------------------------ penjaga
def perlu_admin(f):
    """Rute yang hanya boleh disentuh admin."""
    @wraps(f)
    def bungkus(*a, **b):
        if not admin(g.pengguna):
            abort(403)
        return f(*a, **b)
    return bungkus


def pastikan_lihat(k, berkas_id):
    """Hentikan permintaan kalau berkas ini bukan haknya untuk dilihat.
    Kembalikan pemiliknya supaya pemanggil tidak perlu bertanya dua kali."""
    pemilik = pemilik_berkas(k, berkas_id)
    if pemilik is False:
        abort(404)
    if not boleh_lihat(g.pengguna, pemilik):
        abort(403)
    return pemilik


def pastikan_ubah(k, berkas_id):
    """Sama, untuk permintaan yang menulis."""
    pemilik = pastikan_lihat(k, berkas_id)
    if not boleh_ubah(g.pengguna, pemilik):
        abort(403)
    return pemilik
