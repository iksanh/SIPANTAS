# -*- coding: utf-8 -*-
"""Baca riwayat perolehan tanah dari tulisan yang sudah ada riwayatnya.

Di surat pernyataan, riwayat tanah ada di poin 3 (berhenti sebelum poin 4) dan
tiap mata rantainya diawali tanda "-". Satu butir "-" menjadi satu baris
Riwayat perolehan. Tidak menulis apa pun ke basis data: hasilnya dipratinjau
dan diterapkan app.js, penyimpanannya lewat Simpan biasa.
"""
import re

from .sinkron import riwayat as _rapikan

BATAS_TEKS = 20000

_MINUS = "-–—•"          # - – — • (OCR sering membaca "-" jadi en/em dash)


def _poin(nomor, teks, mulai=0):
    """Letak penanda poin "<nomor>." / "<nomor>)": utamakan yang di awal baris,
    selebihnya yang berdiri sendiri di tengah paragraf."""
    for pola in (rf"^[ \t]*{nomor}[ \t]*[.)]", rf"(?:^|(?<=\s)){nomor}[ \t]*[.)](?=\s)"):
        m = re.compile(pola, re.M).search(teks, mulai)
        if m:
            return m
    return None


def _butir(bagian):
    """Pecah bagian poin 3 per tanda "-". Kalimat pembuka sebelum "-" pertama
    dibuang; baris lanjutan tanpa "-" disambung ke butir sebelumnya."""
    baris = bagian.split("\n")
    awal = re.compile(rf"^\s*[{_MINUS}]\s*")
    if any(awal.match(b) for b in baris):
        hasil, kini = [], None
        for b in baris:
            if awal.match(b):
                kini = [awal.sub("", b)]
                hasil.append(kini)
            elif kini is not None:
                kini.append(b)
        return [" ".join(x) for x in hasil]
    # Satu paragraf: "-" pemisah harus diapit spasi supaya "Al-Amin" dan
    # "12-05-1990" tidak ikut terpecah.
    pecah = re.split(rf"\s[{_MINUS}]\s", " " + bagian + " ")
    return pecah[1:] if len(pecah) > 1 else None


def urai(teks):
    """Tulisan -> {"riwayat": [butir, ...], "peringatan": [...]}"""
    teks = (teks or "").replace("\r\n", "\n").replace("\r", "\n")[:BATAS_TEKS]
    peringatan = []
    if not teks.strip():
        return {"riwayat": [], "peringatan": ["Tulisannya kosong."]}

    m3 = _poin(3, teks)
    if m3:
        m4 = _poin(4, teks, m3.end())
        bagian = teks[m3.end():m4.start() if m4 else len(teks)]
    else:
        bagian = teks
        peringatan.append("Penanda poin 3 tidak ditemukan; seluruh tulisan dibaca.")

    butir = _butir(bagian)
    if butir is None:
        butir = [bagian]
        peringatan.append('Tidak ada tanda "-" di poin 3; isinya dijadikan satu baris.')
    hasil = _rapikan(butir)
    if not hasil:
        peringatan.append("Tidak ada riwayat yang terbaca.")
    return {"riwayat": hasil, "peringatan": peringatan}
