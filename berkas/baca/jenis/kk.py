# -*- coding: utf-8 -*-
"""Urai teks Kartu Keluarga.

Formulir berkas tidak punya medan Nomor KK, jadi KK dijadikan satu baris
Dokumen tambahan. Anggotanya (nama + NIK) dikembalikan hanya untuk dicocokkan
dengan daftar pihak di layar validasi; tidak diterapkan ke formulir.
"""
import re

from ..periksa import rapikan_nik

_NOMOR = re.compile(r"^\s*no(?:mor)?\.?\s*(?:kk)?\s*[:.]?\s*([\dOoIlSB ]{16,24})\s*$",
                    re.I | re.M)
_ANGGOTA = re.compile(r"^\s*\d{1,2}[.)]?\s+([A-Za-z][A-Za-z .'-]*?)\s+([\dOoIlSB]{16})\b", re.M)


def urai(teks):
    teks = teks or ""
    peringatan, dokumen = [], []
    m = _NOMOR.search(teks)
    nomor = rapikan_nik(m.group(1)) if m else ""
    if nomor:
        dokumen.append({"uraian": f"Kartu Keluarga Nomor {nomor}", "kategori": "tambahan"})
    else:
        dokumen.append({"uraian": "Kartu Keluarga", "kategori": "tambahan"})
        peringatan.append("Nomor KK tidak terbaca; lengkapi uraiannya sendiri.")
    pihak = []
    for nama, nik in _ANGGOTA.findall(teks):
        nik = rapikan_nik(nik)
        if nik:
            pihak.append({"nama": " ".join(nama.split()).upper(), "nik": nik})
    return {"isian": {}, "pihak": pihak, "dokumen": dokumen, "peringatan": peringatan}
