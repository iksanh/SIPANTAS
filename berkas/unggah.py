# -*- coding: utf-8 -*-
"""Penyimpanan unggahan dokumen: file asli, teks, dan hasil pilahannya.

Yang ditulis di sini hanya tabel `unggahan` dan `unggahan_dokumen` serta file
di data/unggahan/. Tabel berkas (pihak, bidang_tanah, dokumen_pendukung, …)
tidak disentuh: usulan isian diterapkan di peramban dan baru tersimpan lewat
tombol Simpan biasa.

Di Berkas baru, berkasnya belum punya id saat file diunggah. Unggahannya
disimpan sebagai titipan bertoken, ditautkan oleh tautkan() saat Simpan, dan
dibuang bersihkan_titipan() bila tidak pernah ditautkan.
"""
import datetime as dt
import hashlib
import logging
import os
import secrets

from . import db, jalur
from .baca import ocr, pilah
from .baca.jenis import DAFTAR, PILIHAN

log = logging.getLogger(__name__)

DIR_UNGGAHAN = jalur.UNGGAHAN
UMUR_TITIPAN_HARI = 7
STATUS = ("baru", "pasti", "diabaikan", "diterapkan")
_EKSTENSI = {b"%PDF": "pdf", b"\x89PNG": "png", b"\xff\xd8": "jpg"}


def jalur_file(nama_file):
    return os.path.join(DIR_UNGGAHAN, os.path.basename(nama_file or ""))


def _ekstensi(isi):
    return next((e for awal, e in _EKSTENSI.items() if isi.startswith(awal)), "bin")


def simpan(k, nama, isi, pengguna_id, berkas_id, titipan):
    """Baca, pilah, lalu simpan satu file. GalatBaca diteruskan ke pemanggil.
    Tidak melakukan commit; pemanggil yang memutuskan."""
    bersihkan_titipan(k)
    halaman = ocr.baca(nama, isi)
    potongan = pilah.kelompokkan(halaman)
    sidik = hashlib.sha256(isi).hexdigest()
    if berkas_id:
        kembar = k.execute("SELECT 1 FROM unggahan WHERE sidik=? AND berkas_id=?",
                           (sidik, berkas_id)).fetchone()
    else:
        kembar = k.execute("SELECT 1 FROM unggahan WHERE sidik=? AND titipan=?",
                           (sidik, titipan)).fetchone()
    nama_file = f"u{berkas_id or 'T'}-{secrets.token_hex(8)}.{_ekstensi(isi)}"
    uid = db.sisip_id(k, "INSERT INTO unggahan (berkas_id,titipan,nama_asli,nama_file,sidik,"
                         "jml_halaman,pengguna_id,dibuat) VALUES (?,?,?,?,?,?,?,?)",
                      (berkas_id or None, None if berkas_id else titipan,
                       os.path.basename(nama)[:200], nama_file, sidik, len(halaman),
                       pengguna_id, db.sekarang()))
    dokumen = []
    for p in potongan:
        did = db.sisip_id(k, "INSERT INTO unggahan_dokumen (unggahan_id,hal_awal,hal_akhir,"
                             "jenis_tebakan,yakin,teks) VALUES (?,?,?,?,?,?)",
                          (uid, p.hal_awal, p.hal_akhir, p.jenis, p.yakin, p.teks))
        dokumen.append({"id": did, "hal_awal": p.hal_awal, "hal_akhir": p.hal_akhir,
                        "jenis_tebakan": p.jenis, "label": DAFTAR[p.jenis].label,
                        "yakin": p.yakin})
    os.makedirs(DIR_UNGGAHAN, exist_ok=True)
    with open(jalur_file(nama_file), "wb") as fh:      # gagal -> pemanggil rollback
        fh.write(isi)
    return {"id": uid, "nama_asli": os.path.basename(nama), "kembar": bool(kembar),
            "dokumen": dokumen}


def dokumen(k, did):
    """Satu dokumen hasil pilahan berikut data file induknya, atau None."""
    r = k.execute("SELECT d.*, u.berkas_id, u.titipan, u.pengguna_id, u.nama_file, "
                  "u.nama_asli FROM unggahan_dokumen d JOIN unggahan u ON u.id=d.unggahan_id "
                  "WHERE d.id=?", (did,)).fetchone()
    return dict(r) if r else None


def setel_jenis(k, did, jenis, status):
    if status not in ("pasti", "diabaikan"):
        raise ValueError(f"status {status!r} tidak dikenal")
    if status == "pasti" and jenis not in PILIHAN:
        raise ValueError(f"jenis {jenis!r} tidak bisa dipilih")
    k.execute("UPDATE unggahan_dokumen SET jenis=?, status=? WHERE id=?",
              (jenis if status == "pasti" else None, status, did))


def tautkan(k, titipan, berkas_id, pengguna_id):
    """Titipan milik pengguna ini -> berkas yang baru disimpan. Jumlah yang ditautkan."""
    if not titipan:
        return 0
    c = k.execute("UPDATE unggahan SET berkas_id=?, titipan=NULL "
                  "WHERE titipan=? AND pengguna_id=? AND berkas_id IS NULL",
                  (berkas_id, titipan, pengguna_id))
    return c.rowcount


def _buang(k, baris):
    for r in baris:
        k.execute("DELETE FROM unggahan_dokumen WHERE unggahan_id=?", (r["id"],))
        k.execute("DELETE FROM unggahan WHERE id=?", (r["id"],))
        try:
            os.remove(jalur_file(r["nama_file"]))
        except OSError:
            pass
    return len(baris)


def hapus_semua(k, berkas_id):
    """Dipanggil saat berkas dihapus: CASCADE membuang barisnya, tapi filenya tidak."""
    return _buang(k, k.execute("SELECT id, nama_file FROM unggahan WHERE berkas_id=?",
                               (berkas_id,)).fetchall())


def bersihkan_titipan(k, umur_hari=UMUR_TITIPAN_HARI):
    """Buang titipan yang tidak pernah ditautkan, baris maupun filenya."""
    batas = (dt.datetime.now() - dt.timedelta(days=umur_hari)).strftime("%Y-%m-%d %H:%M:%S")
    return _buang(k, k.execute("SELECT id, nama_file FROM unggahan "
                               "WHERE berkas_id IS NULL AND dibuat < ?", (batas,)).fetchall())
