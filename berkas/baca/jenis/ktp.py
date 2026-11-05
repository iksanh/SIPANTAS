# -*- coding: utf-8 -*-
"""Urai teks KTP -> satu pihak (nama, NIK, TTL, jenis kelamin, pekerjaan, alamat).

Teks KTP berpola "Label : nilai" per baris. Label yang tidak terbaca
dibiarkan kosong; tidak ada yang ditebak.
"""
import re

from ..periksa import nik as periksa_nik, rapikan_nik
from ...aiw import _jenis_kelamin

_LABEL = {
    "nik": r"n\s*i\s*k",
    "nama": r"nama",
    "ttl": r"tempat\s*/?\s*tgl\.?\s*lahir|tempat\s*/?\s*tanggal\s*lahir",
    "jenis_kelamin": r"jenis\s*kelamin",
    "alamat": r"alamat",
    "rt_rw": r"rt\s*/\s*rw",
    "desa": r"kel\s*/\s*desa|desa\s*/\s*kel(?:urahan)?",
    "kecamatan": r"kecamatan",
    "pekerjaan": r"pekerjaan",
}
_POLA = {k: re.compile(rf"^\s*(?:{p})\b\s*[:;.]?\s*(.*)$", re.I) for k, p in _LABEL.items()}
_ROMAWI = re.compile(r"^[IVX]+$")


def _judul(v):
    """'DUSUN II' -> 'Dusun II': huruf awal besar, angka romawi tetap."""
    return " ".join(k if _ROMAWI.match(k) else "/".join(x.capitalize() for x in k.split("/"))
                    for k in v.split())


def _nilai(teks):
    hasil = {}
    for baris in teks.splitlines():
        for kol, pola in _POLA.items():
            if kol in hasil:
                continue
            m = pola.match(baris)
            if m:
                hasil[kol] = m.group(1).strip(" :;-")
                break
    return hasil


def _ttl(v):
    m = re.match(r"\s*([^,\d]+?)\s*,?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{1,2}\s+\w+\s+\d{4})", v)
    if not m:
        return ""
    return f"{_judul(m.group(1))}, {m.group(2).replace('/', '-').replace('.', '-')}"


def urai(teks):
    n = _nilai(teks or "")
    peringatan = []
    nik_mentah = n.get("nik", "")
    nik = rapikan_nik(nik_mentah)
    if nik_mentah and not nik:
        peringatan.append(f"NIK terbaca \"{nik_mentah}\" — bukan 16 angka, jadi dikosongkan.")
    jk_mentah = re.split(r"gol", n.get("jenis_kelamin", ""), flags=re.I)[0]
    alamat = [_judul(n["alamat"])] if n.get("alamat") else []
    m = re.match(r"\s*(\d{1,3})\s*/\s*(\d{1,3})", n.get("rt_rw", ""))
    if m:
        alamat.append(f"RT {m.group(1)}/RW {m.group(2)}")
    if n.get("desa"):
        alamat.append(_judul(n["desa"]))
    if n.get("kecamatan"):
        alamat.append("Kec. " + _judul(n["kecamatan"]))
    pihak = {
        "nama": " ".join(n.get("nama", "").split()).upper(),
        "nik": nik,
        "ttl": _ttl(n.get("ttl", "")),
        "jenis_kelamin": _jenis_kelamin(jk_mentah),
        "pekerjaan": _judul(n.get("pekerjaan", "")),
        "alamat": ", ".join(alamat),
    }
    peringatan += periksa_nik(nik, pihak["ttl"], pihak["jenis_kelamin"])
    return {"isian": {}, "pihak": [pihak], "dokumen": [], "peringatan": peringatan}
