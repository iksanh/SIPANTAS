# -*- coding: utf-8 -*-
"""Urai teks Peta Bidang Tanah (PBT) menjadi isian tab Bidang tanah.

Teksnya hasil OCR/lapisan teks PDF yang dibaca app.js di peramban, sama
seperti aiw.py. Jawabannya berbentuk sama dengan sinkron.olah(): isian yang
namanya persis nama medan formulir, ditambah peringatan. Yang tidak terbaca
tidak dikirim, supaya isian yang sudah diketik petugas tidak dikosongkan.
"""
import re

from .aiw import BATAS_TEKS, _tanggal  # noqa: F401  (BATAS_TEKS dipakai rute)
from .sinkron import _polos, luas

_ARAH = ("utara", "timur", "selatan", "barat")


def _baris_label(teks, pola):
    """Nilai sesudah label pertama yang cocok di awal baris, atau ''."""
    m = re.search(rf"^\s*(?:{pola})\s*[:.]?\s*(.+)$", teks, re.I | re.M)
    return _bersih(m.group(1)) if m else ""


def _bersih(v):
    return re.sub(r"\s+", " ", v or "").strip(" :;,-").strip()


def _angka_luas(v):
    """'1.349' -> 1349.0, '349,6' -> 349.6, '1.349,5' -> 1349.5."""
    v = (v or "").strip().rstrip(".,")
    if not v:
        return None
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", v):
        v = v.replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def cocok_desa(daftar, nama_desa, nama_kec):
    """Desa di daftar referensi (dict id, kecamatan_id, nama, kecamatan) yang
    namanya sama; bila kembar, kecamatannya harus cocok juga. Tidak menebak."""
    nd, nk = _polos(nama_desa), _polos(nama_kec)
    if not nd:
        return None
    calon = [d for d in daftar if _polos(d["nama"]) == nd]
    if nk:
        sekec = [d for d in calon if _polos(d.get("kecamatan")) == nk]
        if sekec:
            calon = sekec
    return calon[0] if len(calon) == 1 else None


def urai(teks, daftar_desa):
    teks = (teks or "")[:BATAS_TEKS]
    isian, peringatan = {}, []

    m = re.search(r"\bno(?:mor)?\.?\s*(?:peta\s+bidang(?:\s+tanah)?|pbt)?\s*[:.]?\s*"
                  r"(\d[\d.]*\s*/\s*\d{4})\b", teks, re.I)
    if m:
        isian["nomor_pbt"] = re.sub(r"\s+", "", m.group(1))

    tgl = _baris_label(teks, r"tanggal(?!\s+lahir)|tgl\.?")
    isian["tanggal_pbt"] = _tanggal(tgl) if tgl else ""

    nib = _baris_label(teks, r"n\.?\s*i\.?\s*b\.?|nomor\s+identifikasi\s+bidang(?:\s+tanah)?")
    m = re.match(r"[\dOoIl.\s]+", nib)
    if m:
        nib = re.sub(r"\s+", "", m.group(0).translate(str.maketrans("OoIl", "0011"))).strip(".")
        if re.search(r"\d", nib):
            isian["nib"] = nib

    m = re.search(r"^\s*luas(?:\s+(?:tanah|bidang|hasil\s+ukur))?\s*[:.]?\s*([\d.,]+)",
                  teks, re.I | re.M)
    if m:
        isian["luas_pbt"] = luas(_angka_luas(m.group(1)), "Luas", peringatan)

    for arah in _ARAH:
        isian[f"batas_{arah}"] = _baris_label(teks, rf"(?:batas\s+|sebelah\s+)?{arah}")

    isian["penggunaan_sekarang"] = _baris_label(teks, r"penggunaan(?:\s+tanah)?")

    desa = _baris_label(teks, r"desa\s*/\s*kel(?:urahan)?\.?|kel(?:urahan)?\.?\s*/\s*desa|"
                              r"desa|kelurahan")
    kec = _baris_label(teks, r"kecamatan|kec\.")
    if desa:
        d = cocok_desa(daftar_desa, desa, kec)
        if d:
            isian["desa_id"], isian["kecamatan"] = d["id"], d["kecamatan_id"]
        else:
            peringatan.append(f"Desa «{desa}»{' Kecamatan ' + kec if kec else ''} tidak "
                              "ditemukan pasti di daftar wilayah — pilih desanya sendiri.")

    isian = {k: v for k, v in isian.items() if v not in (None, "")}
    if not isian:
        peringatan.append("Tidak ada isian PBT yang terbaca. Coba foto/scan yang lebih "
                          "jelas, atau halaman lain.")
    return {"isian": isian, "peringatan": peringatan}
