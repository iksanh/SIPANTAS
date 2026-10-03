# -*- coding: utf-8 -*-
"""Perkakas bersama untuk uji acuan.

Cara kerjanya: sekali waktu, hasil yang sekarang dianggap benar direkam ke
folder `uji/emas/`. Sesudah itu setiap perubahan kode dibandingkan dengan
rekaman tersebut. Kalau berbeda, ujinya gagal dan selisihnya ditampilkan
baris per baris.

Gunanya: merapikan `konteks.py` dan `docxgen.py` tanpa diam-diam mengubah isi
dokumen. Terbilang, luas berhuruf, penomoran a/i/romawi, kalimat otomatis, dan
frasa akta terlalu banyak untuk diperiksa manual setiap kali kode disentuh.

Dua lapis yang diuji:

  konteks   `konteks.bangun()` untuk SEMUA berkas. Cepat (milidetik per berkas),
            jadi dijalankan penuh. Ini yang paling teliti: selisihnya langsung
            menunjuk nama penanda yang berubah.
  dokumen   Teks DOCX hasil rakitan, hanya untuk sekumpulan berkas contoh.
            Lambat (beberapa detik per dokumen), jadi dipilihkan yang bentuknya
            berbeda-beda saja.

Basis datanya tidak pernah disentuh: yang dipakai selalu salinan sementara.
"""
import contextlib
import difflib
import json
import os
import shutil
import sqlite3
import tempfile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from berkas import db
from berkas.dokumen import konteks, terbitkan

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_EMAS = os.path.join(DIR, "emas")

JENIS_DOKUMEN = ("bap", "risalah", "sk")

# Berapa banyak berkas contoh yang dipakai untuk uji dokumen. Yang dipilih
# adalah berkas dengan bentuk berbeda-beda (lihat berkas_contoh).
MAKS_CONTOH = 8


# ----------------------------------------------------------- basis data
@contextlib.contextmanager
def sambung_salinan():
    """Sambungan ke SALINAN basis data, di folder sementara.

    Basis data asli tidak pernah dibuka untuk ditulis oleh uji. Salinannya
    dibuang lagi setelah selesai, jadi uji boleh menulis sesukanya tanpa
    merusak data kerja.
    """
    if not os.path.exists(db.BERKAS_DB):
        raise FileNotFoundError(
            f"Basis data tidak ada di {db.BERKAS_DB}. "
            "Jalankan aplikasinya sekali dulu supaya basis datanya terbentuk.")

    sarang = tempfile.mkdtemp(prefix="uji_berkas_")
    try:
        tujuan = os.path.join(sarang, "berkas.db")
        asal = sqlite3.connect(db.BERKAS_DB)
        salinan = sqlite3.connect(tujuan)
        try:
            with salinan:
                asal.backup(salinan)          # aman walau aplikasinya sedang jalan
        finally:
            asal.close()
            salinan.close()

        k = sqlite3.connect(tujuan, timeout=15)
        k.row_factory = sqlite3.Row
        k.execute("PRAGMA foreign_keys = ON")
        try:
            yield k
        finally:
            k.close()
    finally:
        shutil.rmtree(sarang, ignore_errors=True)


def semua_berkas(k):
    """Id setiap berkas, urut."""
    return [r[0] for r in k.execute("SELECT id FROM berkas ORDER BY id")]


def _bentuk(k, berkas_id):
    """Sidik jari kasar bentuk sebuah berkas.

    Dua berkas dengan sidik jari sama akan melewati cabang kode yang sama di
    docxgen - beda isinya saja. Untuk uji dokumen yang mahal, satu wakil per
    bentuk sudah cukup.
    """
    r = k.execute("SELECT jenis_hak_dimohon, jenis_kegiatan, asal_tanah, kewenangan "
                  "FROM berkas WHERE id=?", (berkas_id,)).fetchone()
    if not r:
        return None
    peran = tuple(sorted(x[0] for x in k.execute(
        "SELECT DISTINCT peran FROM pihak WHERE berkas_id=?", (berkas_id,))))

    def n(tabel):
        return k.execute(f"SELECT COUNT(*) FROM {tabel} WHERE berkas_id=?",
                         (berkas_id,)).fetchone()[0]

    # Jumlah barisnya dibulatkan ke kelompok nol / satu / banyak: hanya itu yang
    # membedakan jalur pengulangan di template, selebihnya cuma beda isi.
    return (r["jenis_hak_dimohon"], r["jenis_kegiatan"], r["asal_tanah"], r["kewenangan"],
            peran,
            min(n("riwayat_perolehan"), 2),
            min(n("dokumen_pendukung"), 2),
            min(n("hak_asal"), 2),
            min(n("foto_lapang"), 2),
            min(n("pendapat_anggota"), 2))


def berkas_contoh(k, maks=MAKS_CONTOH):
    """Berkas yang dipakai untuk uji dokumen: satu wakil per bentuk.

    Dihitung dari isi basis data, bukan daftar id yang ditulis tangan - jadi
    kalau nanti ada jenis berkas baru, wakilnya ikut terpilih sendiri.
    """
    terpilih, sudah = [], set()
    for berkas_id in semua_berkas(k):
        b = _bentuk(k, berkas_id)
        if b is None or b in sudah:
            continue
        sudah.add(b)
        terpilih.append(berkas_id)
        if len(terpilih) >= maks:
            break
    return terpilih


# ------------------------------------------------------------- konteks
def _json(nilai):
    """JSON yang urutannya tetap, supaya dua rekaman bisa dibandingkan."""
    return json.dumps(nilai, ensure_ascii=False, indent=2, sort_keys=True,
                      default=str) + "\n"


def potret_konteks(k, berkas_id):
    """Rekaman satu berkas: nilai setiap penanda, berikut hasil pemeriksaannya.

    Dua-duanya berasal dari konteks.py dan dua-duanya ikut berubah kalau modul
    itu dirapikan, jadi direkam bersama. `periksa` masuk karena di situlah
    aturan kelengkapan berkas tinggal - bagian yang paling mudah rusak
    diam-diam saat kode disusun ulang.

    Kembalikan None kalau berkasnya tidak ada.
    """
    c, _ = konteks.bangun(k, berkas_id)
    if c is None:
        return None
    return _json({"konteks": c, "periksa": konteks.periksa(k, berkas_id)})


# ------------------------------------------------------------- dokumen
def _blok(el, induk):
    """Paragraf dan tabel yang jadi anak langsung `el`, urut sesuai dokumen.

    python-docx menyediakan `.paragraphs` dan `.tables` terpisah, sehingga
    urutan aslinya hilang. Untuk uji acuan urutan itu justru penting.
    """
    for anak in el.iterchildren():
        if anak.tag == qn("w:p"):
            yield Paragraph(anak, induk)
        elif anak.tag == qn("w:tbl"):
            yield Table(anak, induk)


def _isi_sel(sel):
    """Seluruh isi satu sel tabel jadi satu baris."""
    potong = []
    for b in _blok(sel._tc, sel):
        potong.append(b.text.strip() if isinstance(b, Paragraph) else "[tabel bersarang]")
    return " / ".join(x for x in potong if x)


def _tulis(el, induk, keluar):
    for b in _blok(el, induk):
        if isinstance(b, Paragraph):
            keluar.append(b.text.rstrip())
            continue
        keluar.append("[tabel]")
        for baris in b.rows:
            keluar.append("| " + " | ".join(_isi_sel(s) for s in baris.cells) + " |")
        keluar.append("[/tabel]")


def teks_docx(jalur):
    """Isi DOCX jadi teks datar yang enak dibandingkan.

    Tidak dibandingkan bita per bita: DOCX itu zip berisi stempel waktu dan id
    acak, jadi dua berkas yang isinya sama persis pun tidak pernah identik.
    Yang dibandingkan teksnya, berikut urutan dan struktur tabelnya.

    Baris kosong sengaja DIPERTAHANKAN - justru di situ dulu muncul baris ";"
    menggantung dan ekor kosong yang sudah dibereskan docxgen.
    """
    dok = Document(jalur)
    keluar = []
    _tulis(dok.element.body, dok, keluar)
    return "\n".join(keluar).rstrip() + "\n"


def rakit_teks(k, berkas_id, jenis):
    """Rakit satu dokumen ke folder sementara, kembalikan teksnya.

    Folder `keluaran/` yang dipakai sehari-hari tidak ikut terisi berkas uji:
    `terbitkan.DIR_KELUARAN` dialihkan sebentar, lalu dikembalikan lagi.
    """
    sarang = tempfile.mkdtemp(prefix="uji_keluaran_")
    asli = terbitkan.DIR_KELUARAN
    terbitkan.DIR_KELUARAN = sarang
    try:
        jalur, _, _ = terbitkan.rakit(k, berkas_id, jenis)
        return teks_docx(jalur)
    finally:
        terbitkan.DIR_KELUARAN = asli
        shutil.rmtree(sarang, ignore_errors=True)


# ---------------------------------------------------------------- emas
def jalur_emas(jenis, nama):
    return os.path.join(DIR_EMAS, jenis, nama)


def tulis_emas(jenis, nama, teks):
    tujuan = jalur_emas(jenis, nama)
    os.makedirs(os.path.dirname(tujuan), exist_ok=True)
    with open(tujuan, "w", encoding="utf-8", newline="\n") as f:
        f.write(teks)
    return tujuan


def baca_emas(jenis, nama):
    """Isi rekaman acuan, atau None kalau belum pernah direkam."""
    try:
        with open(jalur_emas(jenis, nama), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def beda(acuan, sekarang, nama):
    """Selisih dua teks, siap ditempel ke pesan kegagalan."""
    return "".join(difflib.unified_diff(
        acuan.splitlines(keepends=True), sekarang.splitlines(keepends=True),
        fromfile=f"acuan/{nama}", tofile=f"sekarang/{nama}", n=2))
