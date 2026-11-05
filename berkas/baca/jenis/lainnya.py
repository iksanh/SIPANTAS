# -*- coding: utf-8 -*-
"""Dokumen yang tidak dikenali -> usulan satu baris Dokumen tambahan.

Uraiannya dari judul surat (baris yang diawali SURAT, AKTA, BERITA ACARA, …)
ditambah nomornya bila terbaca. Bila judul tidak ketemu, baris pertama dipakai
dan petugas diingatkan untuk memeriksanya.
"""
import re

_JUDUL = re.compile(r"^\s*((?:surat|akta|berita\s+acara|keterangan|pernyataan|kuitansi|"
                    r"kwitansi|sertipikat|sertifikat|keputusan|izin|rekomendasi)\b.*)$",
                    re.I | re.M)
_NOMOR = re.compile(r"^\s*nomor\s*[:.]?\s*(\S+)", re.I | re.M)
_KECIL = {"dan", "atau", "di", "ke", "dari", "yang", "untuk", "tentang"}


def _judul(v):
    kata = " ".join(v.split()).lower().split()
    return " ".join(k if (i and k in _KECIL) else k.capitalize() for i, k in enumerate(kata))


def urai(teks):
    teks = teks or ""
    peringatan = []
    m = _JUDUL.search(teks)
    if m:
        judul = _judul(m.group(1))
    else:
        pertama = next((b for b in teks.splitlines() if b.strip()), "Dokumen")
        judul = _judul(pertama)[:120]
        peringatan.append("Judul dokumen tidak dikenali; periksa uraiannya.")
    n = _NOMOR.search(teks)
    uraian = f"{judul} Nomor {n.group(1)}" if n else judul
    return {"isian": {}, "pihak": [], "dokumen": [{"uraian": uraian, "kategori": "tambahan"}],
            "peringatan": peringatan}
