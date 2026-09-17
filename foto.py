# -*- coding: utf-8 -*-
"""Foto lapangan: simpan, rapikan, dan buang berkas gambarnya.

Foto diunggah dari tab "Foto lapangan" dan dilampirkan BAP di halaman
tersendiri. Berkasnya disimpan di `data/foto/`, barisnya di `foto_lapang`.

Foto ponsel biasanya berukuran besar dan berputar lewat tanda EXIF saja -
Word tidak selalu menghormati tanda itu. Kalau Pillow terpasang, foto diputar
tegak dan diperkecil sekali saat diunggah, jadi DOCX-nya tetap ringan. Tanpa
Pillow, JPEG/PNG disimpan apa adanya.
"""
import io
import os
import secrets

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_FOTO = os.path.join(DIR, "data", "foto")

MINIMAL = 4                 # foto paling sedikit sebelum BAP boleh dicetak
SISI_MAKS = 1600            # piksel sisi terpanjang setelah diperkecil
MUTU_JPEG = 85

try:
    from PIL import Image, ImageOps
except ImportError:         # pragma: no cover - Pillow tidak wajib
    Image = None


def jalur(nama_file):
    return os.path.join(DIR_FOTO, os.path.basename(nama_file or ""))


def ada(f):
    """Baris foto_lapang yang berkas gambarnya masih ada di disk."""
    return bool(f.get("nama_file")) and os.path.isfile(jalur(f["nama_file"]))


def _jenis(isi):
    if isi[:3] == b"\xff\xd8\xff":
        return "jpg"
    if isi[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return None


def _rapikan(isi):
    """(bita, ekstensi) foto yang sudah tegak dan diperkecil, atau None."""
    if Image is None:
        jenis = _jenis(isi)
        return (isi, jenis) if jenis else None
    try:
        gambar = Image.open(io.BytesIO(isi))
        gambar = ImageOps.exif_transpose(gambar)
        if gambar.mode not in ("RGB", "L"):
            latar = Image.new("RGB", gambar.size, "white")
            rgba = gambar.convert("RGBA")
            latar.paste(rgba, mask=rgba.split()[-1])
            gambar = latar
        gambar.thumbnail((SISI_MAKS, SISI_MAKS))
        keluar = io.BytesIO()
        gambar.save(keluar, "JPEG", quality=MUTU_JPEG, optimize=True)
        return keluar.getvalue(), "jpg"
    except Exception:                                              # noqa: BLE001
        return None


def simpan(k, berkas_id, nama_asli, isi, keterangan=""):
    """Simpan satu foto unggahan. Kembalikan None bila berhasil, atau pesan galat."""
    hasil = _rapikan(isi) if isi else None
    if hasil is None:
        return (f"{nama_asli}: bukan foto yang bisa dibaca. Gunakan JPG atau PNG"
                + ("" if Image else " (atau pasang Pillow supaya format lain diterima)")
                + ".")
    bita, ext = hasil
    os.makedirs(DIR_FOTO, exist_ok=True)
    nama = f"{berkas_id:04d}-{secrets.token_hex(6)}.{ext}"
    with open(jalur(nama), "wb") as fh:
        fh.write(bita)
    urut = k.execute("SELECT COALESCE(MAX(urut), -1) + 1 FROM foto_lapang WHERE berkas_id=?",
                     (berkas_id,)).fetchone()[0]
    k.execute("INSERT INTO foto_lapang (berkas_id, urut, nama_file, keterangan) "
              "VALUES (?,?,?,?)", (berkas_id, urut, nama, keterangan or None))
    return None


def _buang_berkas(nama_file):
    try:
        os.remove(jalur(nama_file))
    except OSError:
        pass


def atur(k, berkas_id, urutan, keterangan):
    """Samakan foto berkas dengan daftar di formulir.

    `urutan` = id foto sesuai urutan di layar; foto yang tidak ada di situ sudah
    dihapus petugas, jadi baris dan berkas gambarnya ikut dibuang.
    """
    lama = {r["id"]: r["nama_file"] for r in k.execute(
        "SELECT id, nama_file FROM foto_lapang WHERE berkas_id=?", (berkas_id,))}
    tetap = []
    for i, fid in enumerate(urutan):
        if fid in lama and fid not in tetap:
            tetap.append(fid)
            ket = keterangan[i] if i < len(keterangan) else ""
            k.execute("UPDATE foto_lapang SET urut=?, keterangan=? WHERE id=?",
                      (len(tetap) - 1, ket or None, fid))
    for fid, nama in lama.items():
        if fid not in tetap:
            k.execute("DELETE FROM foto_lapang WHERE id=?", (fid,))
            _buang_berkas(nama)


def hapus_semua(k, berkas_id):
    """Buang berkas gambar milik satu berkas - dipanggil sebelum berkasnya dihapus."""
    for r in k.execute("SELECT nama_file FROM foto_lapang WHERE berkas_id=?", (berkas_id,)):
        _buang_berkas(r["nama_file"])
    k.execute("DELETE FROM foto_lapang WHERE berkas_id=?", (berkas_id,))
