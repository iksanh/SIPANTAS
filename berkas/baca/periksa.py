# -*- coding: utf-8 -*-
"""Pemeriksaan silang hasil baca. Hanya peringatan, tidak pernah memblokir.

NIK menyimpan tanggal lahir di digit ke-7 s.d. 12 (ddmmyy); untuk perempuan
tanggalnya ditambah 40. Salah baca OCR pada NIK atau tanggal lahir sering
ketahuan dari ketidakcocokan keduanya.
"""
import re

from ..aiw import _jenis_kelamin, _tanggal

# Huruf yang kerap terbaca OCR di tempat angka
_ANGKA = str.maketrans("OoDQIl|SB", "000011158")


def rapikan_nik(mentah):
    """'75O3O7 4512 9OOOO1' -> '7503074512900001'; bukan 16 angka -> ''."""
    nik = re.sub(r"\D", "", (mentah or "").translate(_ANGKA))
    return nik if len(nik) == 16 else ""


def nik(n, ttl="", jenis_kelamin=""):
    """Peringatan bila tanggal lahir / jenis kelamin tidak cocok dengan NIK."""
    if not re.fullmatch(r"\d{16}", n or ""):
        return [f"NIK \"{n}\" bukan 16 angka."] if n else []
    dd, mm, yy = int(n[6:8]), int(n[8:10]), n[10:12]
    perempuan = dd > 40
    if perempuan:
        dd -= 40
    hasil = []
    tgl = _tanggal(ttl or "")
    if tgl:
        y, b, d = tgl.split("-")
        if (int(d), int(b), y[2:]) != (dd, mm, yy):
            hasil.append(f"NIK {n} menunjukkan tanggal lahir {dd:02d}-{mm:02d}-..{yy}, "
                         f"tetapi tertulis {d}-{b}-{y}. Periksa salah satunya.")
    jk = _jenis_kelamin(jenis_kelamin)
    if jk and (jk == "Perempuan") != perempuan:
        hasil.append(f"NIK {n} menunjukkan jenis kelamin "
                     f"{'perempuan' if perempuan else 'laki-laki'}, tetapi tertulis {jk}.")
    return hasil
