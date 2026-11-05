# -*- coding: utf-8 -*-
"""Urai Surat Pernyataan Penguasaan Fisik Bidang Tanah (SPPF).

Mengisi slot dokumen baku SPPF (baku_sppf) serta batas dan luas surat di tab
Bidang tanah. Isian SPPF sering tulisan tangan: yang tidak terbaca (label
tanpa nilai) tidak dikirim, jadi isian petugas tidak dikosongkan.
"""
import re

from ...aiw import BULAN
from ...pbt import _angka_luas, _bersih


def _baris_label(teks, pola):
    """Nilai sesudah label di baris yang sama. Berbeda dengan pbt._baris_label,
    label tanpa nilai ("Utara : ") tidak mengambil baris berikutnya."""
    m = re.search(rf"^[ \t]*(?:{pola})[ \t]*[:.]?[ \t]*(\S[^\n]*)$", teks, re.I | re.M)
    return _bersih(m.group(1)) if m else ""

_ARAH = ("utara", "timur", "selatan", "barat")
_TGL = re.compile(r"\b(\d{1,2}\s+(?:" + "|".join(BULAN) + r")\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\b",
                  re.I)
JUDUL = "Surat Pernyataan Penguasaan Fisik Bidang Tanah"


def urai(teks):
    teks = teks or ""
    isian, peringatan = {}, []
    for arah in _ARAH:
        v = _baris_label(teks, rf"(?:batas\s+|sebelah\s+)?{arah}")
        if v:
            isian[f"batas_{arah}"] = v
    # Tanda "±" sering terbaca OCR sebagai huruf acak: beri ruang beberapa
    # karakter bukan-angka di antara label dan angkanya.
    m = re.search(r"^[ \t]*luas(?:[ \t]+tanah)?[ \t]*[:.]?[^\d\n]{0,6}?([\d][\d.,]*)", teks, re.I | re.M)
    luas = _angka_luas(m.group(1)) if m else None
    if luas:
        isian["luas_surat"] = str(round(luas))
    tanggal = [t for t in _TGL.findall(teks)]
    if tanggal:
        tgl = " ".join(w.capitalize() if not w.isdigit() else w for w in tanggal[-1].split())
        isian["baku_sppf"] = f"{JUDUL} tanggal {tgl}"
    else:
        isian["baku_sppf"] = JUDUL
        peringatan.append("Tanggal surat tidak terbaca; lengkapi uraian SPPF sendiri.")
    return {"isian": isian, "pihak": [], "dokumen": [], "peringatan": peringatan}
