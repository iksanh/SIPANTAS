# -*- coding: utf-8 -*-
"""Pemeliharaan penyimpanan: hitung isi folder, buang yang bisa dibuat ulang.

Tiga jenis berkas menumpuk sendiri sejalan dengan pemakaian:

  `pratinjau/`         PDF hasil konversi - murni singgahan, selalu bisa dibuat lagi
                       dari DOCX-nya. Dipangkas otomatis setiap kali PDF baru dibuat.
                       Cetakan loket menaruh DOCX sumbernya di sini juga, karena
                       yang itu pun singgahan - lihat dokumen/kelengkapan.py.
  `keluaran/`          DOCX yang sudah dicetak. Bisa dirakit ulang dari basis data,
                       tetapi hanya kalau tidak pernah disunting tangan di Word -
                       karena itu pemangkasannya tidak pernah otomatis, harus ditekan
                       sendiri dari halaman Pengaturan, dan berkas yang berubah
                       sesudah dicetak selalu dilewati.
  `data/*.bak-*`       salinan basis data sebelum perbaikan massal. Yang lama dibuang,
                       beberapa yang terbaru disimpan.

Yang tidak pernah disentuh: `data/berkas.db` dan `templates/` (termasuk cadangannya,
yang sudah dibatasi sendiri oleh templat.py).
"""
import os
import time
from . import jalur

DIR_KELUARAN = jalur.KELUARAN
DIR_PRATINJAU = jalur.PRATINJAU
DIR_DATA = jalur.DATA
DIR_TEMPLATE = jalur.TEMPLATE

PRATINJAU_MAKS_BERKAS = 40           # PDF yang disimpan; selebihnya dibuat lagi saat dibuka
PRATINJAU_MAKS_MB = 100
CADANGAN_DB_SIMPAN = 3
KELUARAN_UMUR_HARI = 90              # bawaan tombol "Rapikan keluaran"
JEDA_SUNTING = 300                   # detik; selisih wajar antara dicetak dan mtime berkas


def _isi(folder, saring=None):
    """[(jalur, bita, waktu), ...] isi satu folder, terbaru lebih dulu."""
    if not os.path.isdir(folder):
        return []
    hasil = []
    for nama in os.listdir(folder):
        jalur = os.path.join(folder, nama)
        if not os.path.isfile(jalur) or (saring and not saring(nama)):
            continue
        st = os.stat(jalur)
        hasil.append((jalur, st.st_size, st.st_mtime))
    return sorted(hasil, key=lambda x: x[2], reverse=True)


def _buang(daftar):
    jumlah = bita = 0
    for jalur, ukuran, _ in daftar:
        try:
            os.remove(jalur)
        except OSError:
            continue
        jumlah += 1
        bita += ukuran
    return jumlah, bita


def ukuran(folder, saring=None):
    isi = _isi(folder, saring)
    return len(isi), sum(x[1] for x in isi)


def _bak(nama):
    return nama.startswith("berkas.db.bak-")


def ringkas():
    """Isi tiap folder untuk ditampilkan di halaman Pengaturan."""
    n_kel, b_kel = ukuran(DIR_KELUARAN)
    n_pra, b_pra = ukuran(DIR_PRATINJAU)
    n_bak, b_bak = ukuran(DIR_DATA, _bak)
    n_cad, b_cad = ukuran(os.path.join(DIR_TEMPLATE, "cadangan"))
    return [
        {"nama": "Dokumen tercetak", "folder": "keluaran/", "jumlah": n_kel, "bita": b_kel,
         "catatan": "DOCX hasil cetak. Bisa dirakit ulang dari basis data selama tidak "
                    "disunting tangan."},
        {"nama": "Singgahan pratinjau", "folder": "pratinjau/", "jumlah": n_pra, "bita": b_pra,
         "catatan": f"PDF pratinjau. Dipangkas sendiri di {PRATINJAU_MAKS_BERKAS} berkas "
                    f"terakhir atau {PRATINJAU_MAKS_MB} MB."},
        {"nama": "Cadangan basis data", "folder": "data/berkas.db.bak-*", "jumlah": n_bak,
         "bita": b_bak, "catatan": f"Salinan sebelum perbaikan massal. Disimpan "
                                   f"{CADANGAN_DB_SIMPAN} yang terbaru."},
        {"nama": "Cadangan template", "folder": "templates/cadangan/", "jumlah": n_cad,
         "bita": b_cad, "catatan": "Versi template sebelumnya, sudah dibatasi 15 versi."},
    ]


# ------------------------------------------------------------------ pangkas
def bersihkan_pratinjau(maks_berkas=PRATINJAU_MAKS_BERKAS, maks_mb=PRATINJAU_MAKS_MB):
    """Sisakan PDF yang terbaru saja. Yang dibuang dibuat lagi saat dokumennya dibuka.

    Cetakan loket menaruh DOCX sumbernya di folder yang sama (lihat
    dokumen/kelengkapan.py), jadi DOCX yang PDF-nya sudah dibuang ikut dibuang:
    keduanya satu kesatuan singgahan, dan yang tertinggal sendirian tidak ada
    gunanya selain memakan tempat.
    """
    isi = _isi(DIR_PRATINJAU, lambda n: n.lower().endswith(".pdf"))
    batas_bita = maks_mb * 1024 * 1024
    simpan, terpakai = [], 0
    for baris in isi:
        terpakai += baris[1]
        if len(simpan) < maks_berkas and terpakai <= batas_bita:
            simpan.append(baris)
    buang = [x for x in isi if x not in simpan]
    tinggal = {os.path.splitext(os.path.basename(x[0]))[0] for x in simpan}
    buang += [x for x in _isi(DIR_PRATINJAU, lambda n: n.lower().endswith(".docx"))
              if os.path.splitext(os.path.basename(x[0]))[0] not in tinggal]
    return _buang(buang)


def bersihkan_cadangan_db(simpan=CADANGAN_DB_SIMPAN):
    return _buang(_isi(DIR_DATA, _bak)[simpan:])


def rapikan_keluaran(k, umur_hari=KELUARAN_UMUR_HARI):
    """Buang DOCX lama yang masih bisa dirakit ulang dari basis data.

    Dilewati bila: dokumennya belum tercatat di `dokumen_terbit` (berarti tidak
    tahu cara membuatnya lagi), berkasnya sudah dihapus dari basis data, atau
    berkasnya berubah sesudah dicetak - tanda ada suntingan tangan di Word yang
    tidak boleh hilang.
    """
    batas = time.time() - umur_hari * 86400
    catatan = {}
    for r in k.execute("SELECT d.nama_file, d.berkas_id, MAX(d.dicetak_pada) AS pada "
                       "FROM dokumen_terbit d JOIN berkas b ON b.id = d.berkas_id "
                       "GROUP BY d.nama_file, d.berkas_id"):
        catatan[r["nama_file"]] = r["pada"]

    buang, dilewati = [], 0
    for jalur, bita, waktu in _isi(DIR_KELUARAN):
        nama = os.path.basename(jalur)
        if waktu > batas:
            continue
        pada = catatan.get(nama)
        if not pada:                                   # tidak tercatat, tidak tahu asalnya
            dilewati += 1
            continue
        try:
            dicetak = time.mktime(time.strptime(pada, "%Y-%m-%d %H:%M:%S"))
        except (ValueError, TypeError):
            dilewati += 1
            continue
        if waktu > dicetak + JEDA_SUNTING:             # disunting sesudah dicetak
            dilewati += 1
            continue
        buang.append((jalur, bita, waktu))
    jumlah, bita = _buang(buang)
    return jumlah, bita, dilewati


def teks_ukuran(bita):
    if bita < 1024:
        return f"{bita} B"
    if bita < 1024 * 1024:
        return f"{bita / 1024:.0f} KB"
    return f"{bita / 1024 / 1024:.1f} MB"


if __name__ == "__main__":
    for baris in ringkas():
        print(f"  {baris['nama']:<22} {baris['jumlah']:>4} berkas  "
              f"{teks_ukuran(baris['bita']):>9}  {baris['folder']}")
