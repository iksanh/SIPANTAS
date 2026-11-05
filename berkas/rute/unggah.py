# -*- coding: utf-8 -*-
"""Unggah dokumen: unggah & pilah, gambar halaman, setel jenis, ekstrak.

Semua rute di sini hanya menulis tabel unggahan/unggahan_dokumen. Usulan
isian dikirim sebagai JSON; penerapannya di app.js, penyimpanannya lewat
tombol Simpan biasa.

Hak akses mengikuti berkasnya: unggahan yang tertaut ke berkas hanya untuk
yang boleh mengubah berkas itu; titipan (Berkas baru yang belum disimpan)
hanya untuk pengunggahnya sendiri dan admin. Unggahan berisi NIK dan foto
KTP, jadi titipan orang lain dijawab 404, bukan 403.
"""
from flask import Blueprint, Response, abort, g, jsonify, request

from .. import izin, unggah
from ..baca import ekstrak, ocr
from ..util import ke_int

bp = Blueprint("unggah", __name__)


# Rute ini dipanggil fetch() dari app.js. Penangan 403 aplikasi mengalihkan POST
# ke halaman asal (303), yang bagi fetch berarti HTML, bukan jawaban. Di sini
# jawabannya tetap JSON dengan kode aslinya.
@bp.errorhandler(403)
def _tak_berwenang(_galat):
    return jsonify({"galat": "Anda tidak berwenang mengubah berkas ini."}), 403


@bp.errorhandler(404)
def _tak_ada(_galat):
    return jsonify({"galat": "Unggahan tidak ditemukan."}), 404


def _pastikan(d):
    """Dokumen yang boleh disentuh pengguna ini; selain itu 404/403."""
    if d is None:
        abort(404)
    if d["berkas_id"]:
        izin.pastikan_ubah(g.k, d["berkas_id"])
    elif d["pengguna_id"] != g.pengguna["id"] and not izin.admin(g.pengguna):
        abort(404)
    return d


@bp.post("/unggah")
def unggah_file():
    if not ocr.TERSEDIA:
        return jsonify({"galat": ocr.PESAN_PASANG}), 503
    berkas = request.files.get("berkas")
    bid = ke_int(request.form.get("berkas_id"))
    titipan = (request.form.get("titipan") or "").strip()[:64]
    if berkas is None or not berkas.filename or not (bid or titipan):
        return jsonify({"galat": "File atau tujuan unggahan tidak ada."}), 400
    if bid:
        izin.pastikan_ubah(g.k, bid)
    try:
        hasil = unggah.simpan(g.k, berkas.filename, berkas.read(), g.pengguna["id"],
                              bid, None if bid else titipan)
    except ocr.GalatBaca as e:
        g.k.rollback()
        return jsonify({"galat": str(e)}), 400
    g.k.commit()
    return jsonify(hasil)


@bp.get("/unggah/dok/<int:did>/gambar")
def gambar(did):
    d = _pastikan(unggah.dokumen(g.k, did))
    no = ke_int(request.args.get("hal")) or d["hal_awal"]
    try:
        with open(unggah.jalur_file(d["nama_file"]), "rb") as fh:
            png = ocr.gambar(d["nama_asli"], fh.read(), no)
    except (OSError, ocr.GalatBaca):
        abort(404)
    return Response(png, mimetype="image/png",
                    headers={"Cache-Control": "private, max-age=600"})


@bp.post("/unggah/dok/<int:did>/jenis")
def setel_jenis(did):
    _pastikan(unggah.dokumen(g.k, did))
    try:
        unggah.setel_jenis(g.k, did, request.form.get("jenis") or None,
                           request.form.get("status", ""))
    except ValueError as e:
        return jsonify({"galat": str(e)}), 400
    g.k.commit()
    return jsonify({"ok": True})


@bp.get("/unggah/dok/<int:did>/ekstrak")
def ekstrak_dok(did):
    d = _pastikan(unggah.dokumen(g.k, did))
    if d["status"] != "pasti":
        return jsonify({"galat": "Jenis dokumen belum dipastikan."}), 409
    return jsonify(ekstrak.jalankan(d["jenis"], d["teks"], g.k))
