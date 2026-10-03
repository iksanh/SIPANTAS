# -*- coding: utf-8 -*-
"""Mengeluarkan berkas: DOCX yang sudah dicetak, foto lapangan, dan PDF.

Dokumen di folder keluaran/ boleh saja sudah dirapikan pemeliharaan. Kalau
yang diminta sudah tidak ada, dokumennya dirakit ulang dari basis data —
isinya tetap sama karena nomor dan tanggalnya sudah tercatat saat terbit.
"""
import mimetypes
import os
import sys
import urllib.parse as up

from flask import Blueprint, Response, abort, g, request

from .. import izin, web
from ..dokumen import foto, pdf, terbitkan

bp = Blueprint("unduhan", __name__)

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _teks(isi, kode):
    return isi, kode, {"Content-Type": "text/plain; charset=utf-8"}


def _lampiran(isi, tipe, nama, sikap="attachment", kepala=None):
    h = {"Content-Type": tipe,
         "Content-Disposition": f"{sikap}; filename*=UTF-8''" + up.quote(nama)}
    h.update(kepala or {})
    return Response(isi, 200, h)


def _pastikan_boleh(nama):
    """Berkas asal dokumen ini, setelah dipastikan boleh dilihat.

    Dokumen yang tidak tercatat di dokumen_terbit tidak bisa ditelusuri
    pemiliknya, jadi hanya admin yang boleh mengambilnya.
    """
    r = g.k.execute("SELECT berkas_id FROM dokumen_terbit WHERE nama_file=? "
                    "ORDER BY id DESC LIMIT 1", (nama,)).fetchone()
    if r is None:
        if not izin.admin(g.pengguna):
            abort(403)
        return None
    izin.pastikan_lihat(g.k, r["berkas_id"])
    return r["berkas_id"]


def _pastikan_ada(nama):
    """Jalur dokumen di folder keluaran; dirakit ulang dulu kalau sudah dirapikan."""
    penuh = os.path.join(terbitkan.DIR_KELUARAN, nama)
    if os.path.isfile(penuh):
        return penuh
    try:
        return terbitkan.rakit_ulang(g.k, nama)
    except Exception as ex:                                           # noqa: BLE001
        sys.stderr.write(f"  ! gagal merakit ulang {nama}: {ex}\n")
        return None


@bp.get("/unduh/<path:nama>")
def unduh(nama):
    nama = os.path.basename(nama)
    _pastikan_boleh(nama)
    penuh = _pastikan_ada(nama)
    if not penuh or not os.path.isfile(penuh):
        return _teks("berkas tidak ditemukan", 404)
    with open(penuh, "rb") as fh:
        return _lampiran(fh.read(), DOCX, nama)


@bp.get("/foto/<int:fid>")
def lihat_foto(fid):
    r = g.k.execute("SELECT nama_file, berkas_id FROM foto_lapang WHERE id=?",
                    (fid,)).fetchone()
    if r is not None:
        izin.pastikan_lihat(g.k, r["berkas_id"])
    penuh = foto.jalur(r["nama_file"]) if r else ""
    if not penuh or not os.path.isfile(penuh):
        return _teks("foto tidak ditemukan", 404)
    tipe = mimetypes.guess_type(penuh)[0] or "application/octet-stream"
    with open(penuh, "rb") as fh:
        return Response(fh.read(), 200, {"Content-Type": tipe,
                                         "Cache-Control": "private, max-age=86400"})


@bp.get("/pratinjau/<path:nama>")
def pratinjau(nama):
    nama = os.path.basename(nama)
    _pastikan_boleh(nama)
    penuh = _pastikan_ada(nama) or ""
    bid, judul = _pemilik(nama)
    if not penuh or not os.path.isfile(penuh):
        return web.halaman_pratinjau(
            g.pengguna, nama, bid, judul,
            galat="Dokumennya belum pernah dicetak, jadi belum ada yang bisa "
                  "ditampilkan."), 404
    mesin = pdf.mesin_tersedia()
    if not mesin:
        return web.halaman_pratinjau(
            g.pengguna, nama, bid, judul,
            galat="Pratinjau PDF memerlukan Microsoft Word atau LibreOffice di komputer "
                  "ini. Keduanya tidak ditemukan.")
    if request.args.get("segarkan"):
        # Buang PDF singgahannya supaya halamannya merakit ulang dari DOCX terbaru.
        jalur_pdf = os.path.join(pdf.DIR_PRATINJAU, os.path.splitext(nama)[0] + ".pdf")
        if os.path.exists(jalur_pdf):
            try:
                os.remove(jalur_pdf)
            except OSError:
                pass
    return web.halaman_pratinjau(g.pengguna, nama, bid, judul, mesin)


def _pemilik(nama):
    """Berkas asal dokumen ini dan nama penerima haknya, untuk judul pratinjau."""
    r = g.k.execute("SELECT berkas_id FROM dokumen_terbit WHERE nama_file=? "
                    "ORDER BY id DESC LIMIT 1", (nama,)).fetchone()
    if not r:
        return None, ""
    p = g.k.execute("SELECT nama FROM pihak WHERE berkas_id=? AND peran IN "
                    "('penerima_hak','pemohon') ORDER BY urut LIMIT 1",
                    (r["berkas_id"],)).fetchone()
    return r["berkas_id"], (p["nama"] if p else "")


@bp.get("/pdf/<path:nama>")
def ke_pdf(nama):
    nama = os.path.basename(nama)
    _pastikan_boleh(nama)
    penuh = _pastikan_ada(nama)
    if not penuh or not os.path.isfile(penuh):
        return _teks("dokumen tidak ditemukan", 404)
    try:
        jalur_pdf = pdf.ke_pdf(penuh, paksa=bool(request.args.get("segarkan")))
    except pdf.TidakAdaMesin as ex:
        return _teks(str(ex), 501)
    except Exception as ex:                                           # noqa: BLE001
        return _teks(f"Gagal membuat PDF: {ex}", 500)
    with open(jalur_pdf, "rb") as fh:
        isi = fh.read()
    sikap = "attachment" if request.args.get("unduh") else "inline"
    return _lampiran(isi, "application/pdf", os.path.basename(jalur_pdf), sikap,
                     {"Cache-Control": "no-cache"})
