# -*- coding: utf-8 -*-
"""Teks per halaman -> jenis dokumen; halaman berurutan yang sejenis digabung.

Sengaja aturan kata kunci, bukan model: bisa dijelaskan, jalan tanpa GPU, dan
setiap salah tebak dikoreksi petugas di layar verifikasi. Koreksi itu dicatat
(unggahan_dokumen.jenis_tebakan vs jenis) untuk bahan pemilah berikutnya.
"""
import re
from dataclasses import dataclass

from .jenis import DAFTAR

AMBANG_YAKIN = 0.6       # di bawahnya layar ringkasan menandai "kurang yakin"
AMBANG_LAINNYA = 0.3     # di bawahnya dokumen dianggap "lainnya"
MIN_TEKS = 20            # karakter non-spasi
PEMISAH_HALAMAN = "\n\f\n"

_POLA = {kode: [(re.compile(p), b) for p, b in j.pola] for kode, j in DAFTAR.items()}


@dataclass
class Potongan:
    hal_awal: int
    hal_akhir: int
    jenis: str
    yakin: float
    teks: str


def _normal(teks):
    return " ".join((teks or "").lower().split())


def tebak(teks):
    """(kode jenis, yakin 0..1)."""
    if len("".join((teks or "").split())) < MIN_TEKS:
        return "tidak_terbaca", 0.0
    t = _normal(teks)
    terbaik, nilai = "lainnya", 0.0
    for kode, pola in _POLA.items():
        if not pola:
            continue
        skor = min(1.0, sum(b for p, b in pola if p.search(t)) / DAFTAR[kode].cukup)
        if skor > nilai:
            terbaik, nilai = kode, skor
    if nilai < AMBANG_LAINNYA:
        return "lainnya", round(nilai, 2)
    return terbaik, round(nilai, 2)


def kelompokkan(halaman):
    """Daftar Halaman (ocr.py) -> daftar Potongan, urut halaman."""
    hasil, yakin_kini = [], []
    for h in halaman:
        jenis, yakin = ("tidak_terbaca", 0.0) if h.gagal else tebak(h.teks)
        akhir = hasil[-1] if hasil else None
        gabung = (akhir is not None and akhir.jenis == jenis and akhir.hal_akhir == h.no - 1
                  and jenis != "tidak_terbaca" and not DAFTAR[jenis].satu_halaman)
        if gabung:
            akhir.hal_akhir = h.no
            akhir.teks += PEMISAH_HALAMAN + h.teks
            yakin_kini.append(yakin)
            akhir.yakin = round(sum(yakin_kini) / len(yakin_kini), 2)
        else:
            hasil.append(Potongan(h.no, h.no, jenis, yakin, h.teks))
            yakin_kini = [yakin]
    return hasil
