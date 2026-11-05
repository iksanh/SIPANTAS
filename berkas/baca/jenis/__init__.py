# -*- coding: utf-8 -*-
"""Daftar jenis dokumen yang dikenali unggah dokumen, beserta pola pengenalnya.

Pola dicocokkan dengan teks yang sudah dinormalkan (huruf kecil, spasi dan
baris baru dirapatkan jadi satu spasi). Tiap pola berbobot; tingkat yakin =
jumlah bobot yang cocok dibagi `cukup`, paling tinggi 1. Judul dokumen diberi
bobot besar karena paling bisa dipercaya, ciri lain menambah keyakinan.

Menambah jenis baru: tambahkan satu Jenis di DAFTAR, lalu pengurainya di
berkas/baca/jenis/<kode>.py dan sambungannya di ekstrak.py.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Jenis:
    kode: str
    label: str
    pola: list = field(default_factory=list)   # [(regex, bobot)]
    satu_halaman: bool = False                  # tidak digabung dengan halaman sejenis
    cukup: float = 4.0                          # bobot untuk yakin penuh


DAFTAR = {j.kode: j for j in [
    Jenis("ktp", "KTP", [
        (r"\bnik\b", 2), (r"\bprovinsi\b", 1), (r"berlaku hingga", 2),
        (r"gol\.? ?darah", 1), (r"status perkawinan", 1), (r"kewarganegaraan", 1),
        (r"tempat ?/? ?tgl\.? lahir", 1), (r"kartu tanda penduduk", 2),
    ], satu_halaman=True, cukup=6),
    Jenis("kk", "Kartu Keluarga", [
        (r"kartu keluarga", 3), (r"kepala keluarga", 2), (r"\bno\.? ?:? ?\d{16}\b", 1),
        (r"nama lengkap", 1), (r"hubungan dalam keluarga", 1),
    ]),
    Jenis("sppf", "Surat Pernyataan Penguasaan Fisik", [
        (r"penguasaan fisik", 3), (r"bidang tanah", 1), (r"surat pernyataan", 1),
        (r"\bbatas", 1), (r"\butara\b", 1),
    ]),
    Jenis("aiw", "Akta Ikrar Wakaf", [
        (r"akta (?:pengganti )?(?:akta )?ikrar wakaf", 4), (r"\bwakif\b", 1),
        (r"\bna[zd]h?ir\b", 1), (r"\bppaiw\b", 1), (r"\bwt\.\s?\d", 1),
    ]),
    Jenis("pbt", "Peta Bidang Tanah", [
        (r"peta bidang tanah", 3), (r"\bnib\b", 2), (r"\bluas\b", 1),
        (r"badan pertanahan nasional", 1),
    ]),
    Jenis("lainnya", "Dokumen lain"),
    Jenis("tidak_terbaca", "Tidak terbaca"),
]}

# Jenis yang boleh dipilih petugas (Bukan -> "Ini adalah: ...")
PILIHAN = [k for k in DAFTAR if k != "tidak_terbaca"]
