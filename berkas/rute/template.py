# -*- coding: utf-8 -*-
"""Halaman Template: unduh, ganti, dan kembalikan template DOCX.

Modul yang dipakai bernama `templat` (tanpa 'e'); nama berkas ini mengikuti
alamat halamannya, /template.

Sesudah template diganti, sekali perakitan percobaan langsung dijalankan.
Template yang penandanya rusak lebih baik ketahuan sekarang daripada saat
seseorang menekan Cetak.
"""
import os
import urllib.parse as up

from flask import Blueprint, Response, g, redirect, request

from .. import izin, kabar, web
from ..dokumen import konteks, templat

bp = Blueprint("template", __name__, url_prefix="/template")


@bp.before_request
@izin.perlu_admin
def _khusus_admin():
    """Mengganti template berarti mengubah bentuk semua dokumen yang dicetak
    sesudahnya — seluruh halaman ini milik admin, membaca sekalipun."""

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _galat(teks):
    return redirect("/template?galat=" + up.quote(teks), 303)


def _teks(isi, kode):
    return isi, kode, {"Content-Type": "text/plain; charset=utf-8"}


# ------------------------------------------------------------------ halaman
@bp.get("")
def halaman():
    terbuka = {}
    for b in kabar.buka():
        isi = web.bagian_template(g.k, b)
        if isi:
            terbuka[b] = isi
    return web.halaman_template(g.k, g.pengguna, kabar.pesan(), terbuka)


@bp.get("/bagian/<kunci>")
def bagian(kunci):
    isi = web.bagian_template(g.k, kunci)
    if not isi:
        return _teks("bagian tidak dikenal", 404)
    return isi, 200, {"X-Potongan": "1"}


@bp.get("/unduh/<jenis>")
def unduh(jenis):
    jenis = os.path.basename(jenis).replace(".docx", "")
    if jenis not in templat.JENIS:
        return _teks("template tidak dikenal", 404)
    p = templat.jalur(jenis)
    if not os.path.isfile(p):
        return _teks("template belum ada", 404)
    with open(p, "rb") as fh:
        isi = fh.read()
    return Response(isi, 200, {
        "Content-Type": DOCX,
        "Content-Disposition": "attachment; filename*=UTF-8''" +
                               up.quote("template-" + templat.JENIS[jenis][1]),
    })


# ------------------------------------------------------------------- ubah
def _sesudah_ubah(jenis, pesan):
    """Rakit sekali dengan konteks contoh. Template yang penandanya rusak
    ketahuan di sini, bukan saat dokumennya dibutuhkan."""
    galat = templat.uji_rakit(jenis, konteks.konteks_contoh(g.k)[0])
    if galat:
        return _galat("Template tersimpan, tetapi percobaan merakitnya gagal: " + galat +
                      " — periksa penandanya, atau kembalikan dari cadangan.")
    return redirect("/template?pesan=" + pesan, 303)


@bp.post("/unggah")
def unggah():
    jenis = request.form.get("jenis") or ""
    if jenis not in templat.JENIS:
        return _galat("Jenis template tidak dikenal.")
    berkas = request.files.get("berkas")
    if not berkas or not berkas.filename:
        return _galat("Belum ada berkas yang dipilih.")
    try:
        templat.simpan(jenis, berkas.read(), berkas.filename)
    except templat.Ditolak as ex:
        return _galat(str(ex))
    return _sesudah_ubah(jenis, "template")


@bp.post("/pulihkan")
def pulihkan():
    jenis = request.form.get("jenis") or ""
    if jenis not in templat.JENIS:
        return _galat("Jenis template tidak dikenal.")
    try:
        templat.pulihkan(jenis, request.form.get("nama") or "")
    except templat.Ditolak as ex:
        return _galat(str(ex))
    return _sesudah_ubah(jenis, "template_pulih")
