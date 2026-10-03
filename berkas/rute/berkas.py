# -*- coding: utf-8 -*-
"""Daftar berkas, formulir berkas, dan pencetakan dokumen.

Halaman terbesar aplikasi ini: satu formulir delapan tab yang menulis ke
sebelas tabel sekaligus. Penulisannya ada di formulir.py, pemeriksaannya di
dokumen/konteks.py, perakitan dokumennya di dokumen/terbitkan.py. Yang di
sini hanya urutan langkahnya.
"""
import urllib.parse as up

from flask import Blueprint, g, redirect, request

from .. import formulir, izin, kabar, referensi, web
from ..dokumen import foto, konteks, terbitkan
from ..util import ke_int

bp = Blueprint("berkas", __name__)


# ------------------------------------------------------------------ halaman
@bp.get("/")
@bp.get("/berkas")
def daftar():
    """Saringan dan halamannya dibawa lewat query string (?hak=WAKAF&hal=2),
    supaya alamatnya bisa disimpan, dibagikan, dan tombol Kembali tetap jalan."""
    baris, ringkas = formulir.daftar(g.k, g.pengguna)
    a = request.args
    saringan = {"q": a.get("q", "").strip(), "hak": a.get("hak", ""),
                "status": a.get("status", ""), "kegiatan": a.get("kegiatan", ""),
                "kec": a.get("kec", "")}
    tersaring = formulir.saring(baris, saringan["q"], saringan["hak"], saringan["status"],
                                saringan["kegiatan"], saringan["kec"])
    per = ke_int(a.get("per"))
    saringan["per"] = per if per in web.PER_HALAMAN else web.PER_BAWAAN
    saringan["hal"] = max(1, ke_int(a.get("hal")) or 1)
    return web.halaman_daftar(g.k, g.pengguna, baris, ringkas, kabar.pesan(),
                              tersaring, saringan)


@bp.get("/berkas/baru")
def formulir_kosong():
    return web.halaman_form(g.k, g.pengguna, None, referensi.semua(g.k),
                            pesan=kabar.pesan())


@bp.get("/berkas/<int:bid>")
def satu(bid):
    return _halaman_satu(bid)


def _halaman_satu(bid, terbit_hasil=None):
    """Formulir satu berkas. terbit_hasil diisi sesudah menekan Cetak, supaya
    hasil cetakannya tampil di tab Cetak tanpa perlu pengalihan kedua."""
    pemilik = izin.pastikan_lihat(g.k, bid)
    d = konteks.muat(g.k, bid)
    if not d:
        return redirect("/berkas", 303)
    d["_terbit"] = formulir.terbit(g.k, bid)
    return web.halaman_form(g.k, g.pengguna, d, referensi.semua(g.k),
                            konteks.periksa(g.k, bid), terbit_hasil, kabar.pesan(),
                            boleh_ubah=izin.boleh_ubah(g.pengguna, pemilik))


# ------------------------------------------------------------------- simpan
@bp.post("/berkas/baru")
def buat():
    bid = formulir.simpan(g.k, request.form, None, g.pengguna["id"])
    return redirect(_simpan_foto(bid, "dibuat"), 303)


@bp.post("/berkas/<int:bid>")
def simpan(bid):
    izin.pastikan_ubah(g.k, bid)
    formulir.simpan(g.k, request.form, bid, g.pengguna["id"])
    return redirect(_simpan_foto(bid, "tersimpan"), 303)


def _simpan_foto(bid, pesan):
    """Susun ulang/hapus foto yang ada, lalu simpan unggahan baru.
    Kembalikan alamat tujuan sesudah menyimpan."""
    f = request.form
    if f.get("foto_ada") == "1":
        foto.atur(g.k, bid,
                  [x for x in (ke_int(v) for v in f.getlist("foto_id")) if x],
                  [x.strip() for x in f.getlist("foto_ket")])
    gagal, n = [], 0
    for unggahan in request.files.getlist("foto_baru"):
        if not unggahan.filename:
            continue
        galat = foto.simpan(g.k, bid, unggahan.filename, unggahan.read())
        if galat:
            gagal.append(galat)
        else:
            n += 1
    g.k.commit()
    if gagal:
        teks = f"{len(gagal)} foto tidak tersimpan. " + " ".join(gagal)
        return f"/berkas/{bid}?galat={up.quote(teks)}#p-foto"
    if n:
        return f"/berkas/{bid}?baik={up.quote(f'Tersimpan, dengan {n} foto baru.')}#p-foto"
    return f"/berkas/{bid}?pesan={pesan}"


@bp.post("/berkas/<int:bid>/hapus")
@izin.perlu_admin
def hapus(bid):
    """Hanya admin. Menghapus berkas ikut membuang foto lapangan dan seluruh
    barisnya di sebelas tabel — tidak ada tong sampah."""
    foto.hapus_semua(g.k, bid)
    g.k.execute("DELETE FROM berkas WHERE id=?", (bid,))
    g.k.commit()
    return redirect("/berkas?pesan=dihapus", 303)


# -------------------------------------------------------------------- cetak
@bp.post("/berkas/<int:bid>/cetak")
def cetak(bid):
    """Dokumen hanya boleh terbit kalau pemeriksaannya bersih dari galat —
    nomor yang telanjur keluar tidak bisa ditarik kembali."""
    izin.pastikan_ubah(g.k, bid)
    if any(t == "galat" for t, _ in konteks.periksa(g.k, bid)):
        return redirect(f"/berkas/{bid}?pesan=galat_cetak", 303)
    jenis = request.form.get("jenis") or "semua"
    if jenis == "semua":
        hasil = terbitkan.terbitkan_semua(g.k, bid, g.pengguna["id"])
    else:
        try:
            hasil = [(jenis, terbitkan.terbitkan(g.k, bid, jenis, g.pengguna["id"]), None)]
        except Exception as ex:                                       # noqa: BLE001
            hasil = [(jenis, None, str(ex))]
    return _halaman_satu(bid, hasil)
