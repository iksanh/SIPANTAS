# -*- coding: utf-8 -*-
"""Halaman Pengaturan: identitas kantor, penyimpanan, dan daftar pengguna.

Halamannya terbuka untuk semua supaya petugas bisa mengganti kata sandinya
sendiri; yang dilihat petugas hanya kartu itu. Seluruh penyimpanannya khusus
admin.

Menambah pengguna dan mengganti kata sandi ada di rute/auth.py — keduanya
menyentuh kredensial, jadi dikumpulkan bersama masuk/keluar.
"""
from flask import Blueprint, g, redirect, request

from .. import db, izin, kabar, pemeliharaan, web

bp = Blueprint("pengaturan", __name__)


@bp.get("/pengaturan")
def halaman():
    if not izin.admin(g.pengguna):
        # Petugas tidak perlu tahu siapa saja yang punya akun, apalagi
        # identitas kantor dan angka penyimpanan.
        return web.halaman_pengaturan(g.pengguna, {}, [], kabar.pesan())
    peng = {r["kunci"]: r["nilai"] for r in g.k.execute("SELECT * FROM pengaturan")}
    daftar = [dict(r) for r in g.k.execute("SELECT * FROM pengguna ORDER BY id")]
    return web.halaman_pengaturan(g.pengguna, peng, daftar, kabar.pesan(),
                                  pemeliharaan.ringkas())


@bp.post("/pengaturan")
@izin.perlu_admin
def simpan():
    """Semua isian berawalan set_ masuk ke tabel pengaturan apa adanya —
    menambah isian di web.py tidak perlu menyentuh rute ini."""
    for nama in request.form:
        if nama.startswith("set_"):
            g.k.execute(db.upsert("pengaturan", "kunci,nilai", kunci="kunci"),
                        (nama[4:], request.form[nama]))
    g.k.commit()
    return redirect("/pengaturan?pesan=pengaturan#p-kantor", 303)


@bp.post("/pemeliharaan")
@izin.perlu_admin
def rapikan():
    """Buang berkas yang bisa dibuat ulang, atas permintaan petugas."""
    aksi = request.form.get("aksi") or ""
    jumlah = 0
    if aksi == "pratinjau":
        jumlah, _ = pemeliharaan.bersihkan_pratinjau(maks_berkas=0, maks_mb=0)
    elif aksi == "cadangan_db":
        jumlah, _ = pemeliharaan.bersihkan_cadangan_db()
    elif aksi == "keluaran":
        try:
            hari = int(request.form.get("umur_hari") or "90")
        except ValueError:
            hari = pemeliharaan.KELUARAN_UMUR_HARI
        jumlah, _, _ = pemeliharaan.rapikan_keluaran(g.k, max(hari, 0))
    return redirect(f"/pengaturan?pesan={'bersih' if jumlah else 'bersih_kosong'}"
                    "#penyimpanan", 303)
