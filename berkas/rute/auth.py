# -*- coding: utf-8 -*-
"""Masuk, keluar, dan pengelolaan pengguna.

Halamannya dirakit web.py; yang di sini hanya penanganan permintaannya.

Kata sandi disimpan sebagai PBKDF2-SHA256 200.000 putaran (lihat db.py), dan
sesinya satu baris di tabel `sesi` — bukan kuki bertanda tangan, supaya bisa
dicabut dari sisi server.
"""
from flask import Blueprint, g, redirect, request

from .. import db, izin, sesi, web
from ..util import ke_int

bp = Blueprint("auth", __name__)


@bp.get("/masuk")
def halaman_masuk():
    if g.pengguna:
        return redirect("/berkas", 303)
    return web.halaman_masuk()


@bp.post("/masuk")
def masuk():
    un = (request.form.get("username") or "").strip()
    sandi = request.form.get("sandi") or ""
    r = g.k.execute("SELECT * FROM pengguna WHERE username=? AND aktif=1", (un,)).fetchone()
    if not r or not db.cek_sandi(sandi, r["sandi_hash"]):
        return web.halaman_masuk("Nama pengguna atau kata sandi salah."), 401
    return sesi.pasang_kuki(redirect("/berkas", 303), sesi.buat(g.k, r["id"]))


@bp.get("/keluar")
def keluar():
    sesi.hapus(g.k, request.cookies.get(sesi.NAMA_KUKI))
    return sesi.hapus_kuki(redirect("/masuk", 303))


@bp.post("/sandi")
def ubah_sandi():
    lama = request.form.get("lama") or ""
    baru = request.form.get("baru") or ""
    r = g.k.execute("SELECT sandi_hash FROM pengguna WHERE id=?",
                    (g.pengguna["id"],)).fetchone()
    if not baru or not db.cek_sandi(lama, r["sandi_hash"]):
        return redirect("/pengaturan?pesan=sandi_salah#p-pengguna", 303)
    g.k.execute("UPDATE pengguna SET sandi_hash=? WHERE id=?",
                (db.hash_sandi(baru), g.pengguna["id"]))
    g.k.commit()
    return redirect("/pengaturan?pesan=sandi#p-pengguna", 303)


@bp.post("/pengguna/peran")
@izin.perlu_admin
def ubah_peran():
    """Naik/turunkan peran seorang pengguna.

    Admin tidak boleh menurunkan dirinya sendiri: kalau itu admin terakhir,
    tidak akan ada lagi yang bisa menaikkan siapa pun, dan aplikasinya
    terkunci tanpa jalan masuk selain menyunting basis datanya langsung.
    """
    uid = ke_int(request.form.get("id"))
    peran = request.form.get("peran")
    if not uid or peran not in izin.NAMA_PERAN:
        return redirect("/pengaturan?pesan=peran_salah#p-pengguna", 303)
    if uid == g.pengguna["id"] and peran != izin.ADMIN:
        return redirect("/pengaturan?pesan=peran_sendiri#p-pengguna", 303)
    g.k.execute("UPDATE pengguna SET peran=? WHERE id=?", (peran, uid))
    g.k.commit()
    return redirect("/pengaturan?pesan=peran#p-pengguna", 303)


@bp.post("/pengguna")
@izin.perlu_admin
def tambah_pengguna():
    nama = (request.form.get("nama") or "").strip()
    un = (request.form.get("username") or "").strip()
    sandi = request.form.get("sandi") or ""
    # Apa pun yang dikirim, peran yang tidak dikenal jatuh ke petugas —
    # wewenang tidak boleh bisa dinaikkan lewat isian formulir yang dikarang.
    peran = request.form.get("peran")
    peran = peran if peran in izin.NAMA_PERAN else izin.PETUGAS
    if not (nama and un and sandi):
        return redirect("/pengaturan", 303)
    if g.k.execute("SELECT 1 FROM pengguna WHERE username=?", (un,)).fetchone():
        return redirect("/pengaturan?pesan=pengguna_ada#p-pengguna", 303)
    g.k.execute("INSERT INTO pengguna (nama,username,sandi_hash,peran) VALUES (?,?,?,?)",
                (nama, un, db.hash_sandi(sandi), peran))
    g.k.commit()
    return redirect("/pengaturan?pesan=pengguna#p-pengguna", 303)
