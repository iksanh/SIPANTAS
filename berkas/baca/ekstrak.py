# -*- coding: utf-8 -*-
"""Jenis + teks -> usulan isian. Satu pintu untuk semua pengurai.

Untuk AIW dan PBT keluaran pengurai lama diteruskan apa adanya, supaya
app.js memakai pratinjau dan penerapan yang sudah ada.
"""
from .. import aiw, pbt, referensi
from .jenis import kk, ktp, lainnya, sppf

_URAI = {"ktp": ktp.urai, "kk": kk.urai, "sppf": sppf.urai, "lainnya": lainnya.urai}


def jalankan(jenis, teks, k):
    if jenis == "aiw":
        hasil = aiw.urai(teks)
    elif jenis == "pbt":
        hasil = pbt.urai(teks, referensi.daftar_desa_ocr(k))
    elif jenis in _URAI:
        hasil = _URAI[jenis](teks)
    else:
        raise ValueError(f"jenis {jenis!r} tidak bisa diekstrak")
    return {"jenis": jenis, "hasil": hasil}
