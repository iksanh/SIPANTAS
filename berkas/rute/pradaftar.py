# -*- coding: utf-8 -*-
"""Halaman pradaftar: pemeriksaan kelengkapan berkas di loket.

Sama bentuknya dengan rute/berkas.py — daftar, formulir, lalu satu tindakan
yang mengunci. Bedanya yang mengunci di sini bukan pencetakan melainkan
`terima`: sesudah itu berkasnya sudah terbit dan pradaftarnya jadi baca-saja.

Penyimpanannya ada di pradaftar.py, pemeriksaan kelengkapannya juga di sana.
Yang di sini cuma urutan langkah dan penjagaan izinnya.
"""
import os
import urllib.parse as up

from flask import Blueprint, Response, abort, g, redirect, request

from .. import izin, kabar, pradaftar, referensi, web
from ..dokumen import kelengkapan, pdf

bp = Blueprint("pradaftar", __name__)


def _pemilik(pid):
    """Hentikan permintaan kalau pradaftar ini bukan haknya untuk dilihat.

    Aturannya sama persis dengan berkas (izin.py): admin melihat semuanya,
    petugas melihat miliknya sendiri. Tidak ada padanan "arsip impor" di sini —
    pradaftar selalu diketik lewat aplikasi ini, jadi selalu ada pemiliknya.
    """
    r = g.k.execute("SELECT dibuat_oleh FROM pradaftar WHERE id=?", (pid,)).fetchone()
    if r is None:
        abort(404)
    if not izin.boleh_lihat(g.pengguna, r["dibuat_oleh"]):
        abort(403)
    return r["dibuat_oleh"]


def _boleh_ubah(pid, pemilik, status):
    """Yang sudah diterima atau dibatalkan tidak bisa disunting lagi, siapa pun
    yang membukanya — berkasnya sudah terbit dan isinya jadi riwayat."""
    return (izin.boleh_ubah(g.pengguna, pemilik)
            and status not in pradaftar.STATUS_KUNCI)


# ------------------------------------------------------------------ halaman
@bp.get("/pradaftar")
def daftar():
    baris, ringkas = pradaftar.daftar(g.k, g.pengguna)
    return web.halaman_pradaftar(g.pengguna, baris, ringkas, kabar.pesan())


@bp.get("/pradaftar/baru")
def formulir_kosong():
    return web.halaman_pradaftar_form(g.pengguna, None, referensi.semua(g.k),
                                      kabar.pesan())


@bp.get("/pradaftar/<int:pid>")
def satu(pid):
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    if not d:
        return redirect("/pradaftar", 303)
    return web.halaman_pradaftar_form(
        g.pengguna, d, referensi.semua(g.k), kabar.pesan(),
        boleh_ubah=_boleh_ubah(pid, pemilik, d["status"]))


# ------------------------------------------------------------------- simpan
@bp.post("/pradaftar/baru")
def buat():
    pid = pradaftar.simpan(g.k, request.form, None, g.pengguna["id"])
    # Langsung ke tab Kelengkapan: itulah yang sebenarnya dikerjakan petugas
    # loket, dan daftarnya baru bisa muncul setelah jenis haknya tersimpan.
    return redirect(f"/pradaftar/{pid}?pesan=pradaftar_dibuat#q-periksa", 303)


@bp.post("/pradaftar/<int:pid>")
def simpan(pid):
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    if not _boleh_ubah(pid, pemilik, d["status"]):
        abort(403)
    pradaftar.simpan(g.k, request.form, pid, g.pengguna["id"])
    # Tombol "Layar penuh" di tab Kelengkapan menyimpan dulu, baru pindah —
    # centangan yang belum tersimpan tidak boleh hilang karena pindah halaman.
    if request.form.get("lanjut") == "periksa":
        return redirect(f"/pradaftar/{pid}/periksa", 303)
    return redirect(f"/pradaftar/{pid}?pesan=tersimpan", 303)


@bp.get("/pradaftar/<int:pid>/periksa")
def periksa(pid):
    """Daftar kelengkapan selebar layar, tanpa menu samping dan tab lain."""
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    return web.halaman_periksa(g.pengguna, d, kabar.pesan(),
                               boleh_ubah=_boleh_ubah(pid, pemilik, d["status"]))


@bp.post("/pradaftar/<int:pid>/periksa")
def simpan_periksa(pid):
    """Simpan centangan saja; data pemohon tidak ikut di formulir ini."""
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    if not _boleh_ubah(pid, pemilik, d["status"]):
        abort(403)
    pradaftar.simpan_jawab(g.k, request.form, pid)
    if request.form.get("lanjut") == "kembali":
        return redirect(f"/pradaftar/{pid}?pesan=tersimpan#q-periksa", 303)
    return redirect(f"/pradaftar/{pid}/periksa?pesan=tersimpan", 303)


@bp.post("/pradaftar/<int:pid>/hapus")
@izin.perlu_admin
def hapus(pid):
    """Hanya admin. Pradaftar yang sudah jadi berkas tidak ikut menghapus
    berkasnya — yang hilang cuma catatan loketnya."""
    g.k.execute("DELETE FROM pradaftar WHERE id=?", (pid,))
    g.k.commit()
    return redirect("/pradaftar?pesan=pradaftar_hapus", 303)


# ------------------------------------------------------------- terima loket
@bp.post("/pradaftar/<int:pid>/terima")
def terima(pid):
    """Naikkan jadi berkas. Sekali berhasil tidak bisa diulang."""
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    if not _boleh_ubah(pid, pemilik, d["status"]):
        abort(403)
    alasan = (request.form.get("alasan_terima") or request.form.get("alasan") or "").strip()
    bid, galat = pradaftar.terima(g.k, pid, g.pengguna["id"], alasan)
    if galat:
        return redirect(f"/pradaftar/{pid}?galat={up.quote(galat)}#q-putusan", 303)
    pesan = up.quote(f"Berkas {bid:04d} dibuat dari pradaftar {d['nomor']}. "
                     "Lanjutkan pengisiannya di sini.")
    return redirect(f"/berkas/{bid}?baik={pesan}", 303)


@bp.post("/pradaftar/<int:pid>/status")
def status(pid):
    """Tandai dikembalikan atau batal, tanpa menyentuh isinya."""
    pemilik = _pemilik(pid)
    d = pradaftar.muat(g.k, pid)
    if not _boleh_ubah(pid, pemilik, d["status"]):
        abort(403)
    baru = request.form.get("status") or ""
    if baru not in [x for x, _ in pradaftar.STATUS]:
        abort(400)
    pradaftar.ubah_status(g.k, pid, baru)
    return redirect(f"/pradaftar/{pid}?pesan=tersimpan#q-putusan", 303)


# -------------------------------------------------------------------- cetak
# Cetakan loket tidak lewat folder keluaran/ dan tidak dicatat di
# dokumen_terbit: isinya bisa dirakit ulang persis dari pradaftarnya kapan saja
# (lihat dokumen/kelengkapan.py). Karena itu alamatnya berkunci pradaftar dan
# jenis cetakannya, bukan nama berkas seperti dokumen Panitia A.
#
# Yang sudah diterima di loket pun tetap boleh dicetak — formulirnya justru
# dibutuhkan sebagai lampiran arsip berkas — jadi yang dipakai di sini
# `_pemilik`, bukan `_boleh_ubah`.
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _lampiran(isi, tipe, nama, sikap="attachment", kepala=None):
    h = {"Content-Type": tipe,
         "Content-Disposition": f"{sikap}; filename*=UTF-8''" + up.quote(nama)}
    h.update(kepala or {})
    return Response(isi, 200, h)


def _tautan(pid, jenis):
    """Alamat yang dipakai halaman pratinjau untuk cetakan loket ini."""
    dasar = f"/pradaftar/{pid}"
    return {"kembali": f"{dasar}#q-putusan", "label_kembali": "Kembali ke pradaftar",
            "pdf": f"{dasar}/pdf/{jenis}", "pdf_unduh": f"{dasar}/pdf/{jenis}?unduh=1",
            "docx": f"{dasar}/docx/{jenis}",
            "segarkan": f"{dasar}/pratinjau/{jenis}?segarkan=1",
            "menu": "/pradaftar"}


def _rakit(pid, jenis):
    """(jalur DOCX, pradaftar, galat). Galat dikembalikan, bukan dilempar —
    pemanggilnya memilih sendiri mau halaman atau teks biasa."""
    try:
        jalur, d = kelengkapan.rakit(g.k, pid, jenis, g.pengguna["nama"])
        return jalur, d, None
    except Exception as ex:                                        # noqa: BLE001
        return None, None, str(ex)


@bp.get("/pradaftar/<int:pid>/pratinjau/<jenis>")
def pratinjau(pid, jenis):
    """Halaman pratinjau: PDF-nya tampil di dalam bingkai, siap dicetak."""
    _pemilik(pid)
    jalur, d, galat = _rakit(pid, jenis)
    judul = kelengkapan.JUDUL.get(jenis, jenis)
    if galat:
        return web.halaman_pratinjau(g.pengguna, judul, galat=galat,
                                     tautan=_tautan(pid, jenis)), 400
    nama = os.path.basename(jalur)
    mesin = pdf.mesin_tersedia()
    if not mesin:
        return web.halaman_pratinjau(
            g.pengguna, nama, judul_berkas=d["pemohon_nama"],
            galat="Pratinjau PDF memerlukan Microsoft Word atau LibreOffice di "
                  "komputer ini. Keduanya tidak ditemukan.",
            tautan=_tautan(pid, jenis))
    if request.args.get("segarkan"):
        _buang_pdf(jalur)
    return web.halaman_pratinjau(g.pengguna, nama, judul_berkas=d["pemohon_nama"],
                                 mesin=mesin, tautan=_tautan(pid, jenis))


def _buang_pdf(jalur_docx):
    """Buang PDF singgahannya supaya dikonversi ulang dari DOCX terbaru."""
    p = os.path.splitext(jalur_docx)[0] + ".pdf"
    if os.path.exists(p):
        try:
            os.remove(p)
        except OSError:
            pass


@bp.get("/pradaftar/<int:pid>/pdf/<jenis>")
def ke_pdf(pid, jenis):
    """PDF-nya sendiri: ditampilkan di dalam bingkai, atau diunduh dengan ?unduh=1."""
    _pemilik(pid)
    jalur, _, galat = _rakit(pid, jenis)
    if galat:
        return galat, 400, {"Content-Type": "text/plain; charset=utf-8"}
    try:
        jalur_pdf = pdf.ke_pdf(jalur, paksa=bool(request.args.get("segarkan")))
    except pdf.TidakAdaMesin as ex:
        return str(ex), 501, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as ex:                                        # noqa: BLE001
        return (f"Gagal membuat PDF: {ex}", 500,
                {"Content-Type": "text/plain; charset=utf-8"})
    with open(jalur_pdf, "rb") as fh:
        isi = fh.read()
    sikap = "attachment" if request.args.get("unduh") else "inline"
    return _lampiran(isi, "application/pdf", os.path.basename(jalur_pdf), sikap,
                     {"Cache-Control": "no-cache"})


@bp.get("/pradaftar/<int:pid>/docx/<jenis>")
def ke_docx(pid, jenis):
    """Naskah Word-nya, untuk yang perlu menyuntingnya sebelum ditandatangani."""
    _pemilik(pid)
    jalur, _, galat = _rakit(pid, jenis)
    if galat:
        return galat, 400, {"Content-Type": "text/plain; charset=utf-8"}
    with open(jalur, "rb") as fh:
        return _lampiran(fh.read(), DOCX, os.path.basename(jalur))
