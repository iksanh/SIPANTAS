# -*- coding: utf-8 -*-
"""Halaman Pengaturan: identitas kantor, penyimpanan, dan daftar pengguna.

Halamannya terbuka untuk semua supaya petugas bisa mengganti kata sandinya
sendiri; yang dilihat petugas hanya kartu itu. Seluruh penyimpanannya khusus
admin.

Menambah pengguna dan mengganti kata sandi ada di rute/auth.py — keduanya
menyentuh kredensial, jadi dikumpulkan bersama masuk/keluar.
"""
from urllib.parse import quote

from flask import Blueprint, g, redirect, request

from .. import db, izin, kabar, pemeliharaan, sinkron, web

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
                                  pemeliharaan.ringkas(), _phpt(peng))


def _phpt(peng):
    """Keadaan setelan PHPT untuk kartunya. Kunci API tidak pernah dikirim
    balik ke peramban — yang ditampilkan hanya ada atau tidaknya."""
    return {
        "url": peng.get(sinkron.KUNCI_URL) or "",
        "ada_kunci": bool((peng.get(sinkron.KUNCI_API) or "").strip()),
        "url_env": sinkron.konfigurasi.ambil("SINKRON_URL", "").strip(),
        "kunci_env": bool(sinkron.konfigurasi.ambil("SINKRON_KUNCI", "").strip()),
    }


@bp.post("/pengaturan")
@izin.perlu_admin
def simpan():
    """Semua isian berawalan set_ masuk ke tabel pengaturan apa adanya —
    menambah isian di web.py tidak perlu menyentuh rute ini."""
    for nama in request.form:
        # Setelan PHPT punya rutenya sendiri (diperiksa dulu sebelum disimpan).
        if nama.startswith("set_") and not nama.startswith("set_sinkron_"):
            g.k.execute(db.upsert("pengaturan", "kunci,nilai", kunci="kunci"),
                        (nama[4:], request.form[nama]))
    g.k.commit()
    return redirect("/pengaturan?pesan=pengaturan#p-kantor", 303)


@bp.post("/pengaturan/sinkron")
@izin.perlu_admin
def simpan_sinkron():
    """Alamat dan kunci API aplikasi PHPT untuk tarik data lewat NIB.

    Kunci yang dikosongkan tidak menghapus kunci lama — isiannya memang selalu
    kosong karena kuncinya tidak pernah ditampilkan. Menghapusnya lewat
    centang tersendiri. Tombol "Simpan & uji" langsung mencoba sambungannya.
    """
    f = request.form
    tujuan = "/pengaturan#p-phpt"
    url = (f.get("url") or "").strip()
    if url:
        try:
            url = sinkron.periksa_url(url)
        except ValueError as ex:
            return redirect(kabar.ke(tujuan, "galat=" + quote(str(ex))), 303)

    def tulis(kunci, nilai):
        g.k.execute(db.upsert("pengaturan", "kunci,nilai", kunci="kunci"), (kunci, nilai))

    tulis(sinkron.KUNCI_URL, url)
    kunci = (f.get("kunci") or "").strip()
    if f.get("hapus_kunci"):
        tulis(sinkron.KUNCI_API, "")
    elif kunci:
        tulis(sinkron.KUNCI_API, kunci)
    g.k.commit()

    if f.get("aksi") != "uji":
        return redirect(kabar.ke(tujuan, "pesan=pengaturan_phpt"), 303)
    try:
        sinkron.ambil("00000", g.k)
    except sinkron.SinkronGagal as ex:
        return redirect(kabar.ke(tujuan, "galat=" + quote(
            "Tersimpan, tetapi uji sambungan gagal: " + str(ex))), 303)
    return redirect(kabar.ke(tujuan, "baik=" + quote(
        "Tersimpan. Aplikasi PHPT tersambung dan kunci API diterima.")), 303)


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
