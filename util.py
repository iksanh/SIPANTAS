# -*- coding: utf-8 -*-
"""Nilai turunan: hari, bulan, terbilang, luas, selisih.

Semua yang bisa dihitung dihitung di sini, tidak pernah disimpan di basis data.
Ini yang menutup temuan T-05 (satu tanggal disimpan lima kali) dan T-06
(luas disimpan sebagai kalimat).
"""
import datetime as _dt
import re

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jum'at", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_ROMAWI = ["I", "II", "III", "IV", "V", "VI",
                "VII", "VIII", "IX", "X", "XI", "XII"]

_SATUAN = ["", "satu", "dua", "tiga", "empat", "lima",
           "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]


def terbilang(n):
    """Angka bulat -> kata bahasa Indonesia. terbilang(1373) -> 'seribu tiga ratus tujuh puluh tiga'"""
    n = int(n)
    if n < 0:
        return "minus " + terbilang(-n)
    if n < 12:
        return _SATUAN[n] if n else "nol"
    if n < 20:
        return terbilang(n - 10) + " belas"
    if n < 100:
        return terbilang(n // 10) + " puluh" + ((" " + terbilang(n % 10)) if n % 10 else "")
    if n < 200:
        return "seratus" + ((" " + terbilang(n - 100)) if n - 100 else "")
    if n < 1000:
        return terbilang(n // 100) + " ratus" + ((" " + terbilang(n % 100)) if n % 100 else "")
    if n < 2000:
        return "seribu" + ((" " + terbilang(n - 1000)) if n - 1000 else "")
    if n < 1_000_000:
        return terbilang(n // 1000) + " ribu" + ((" " + terbilang(n % 1000)) if n % 1000 else "")
    if n < 1_000_000_000:
        return terbilang(n // 1_000_000) + " juta" + ((" " + terbilang(n % 1_000_000)) if n % 1_000_000 else "")
    return terbilang(n // 1_000_000_000) + " miliar" + (
        (" " + terbilang(n % 1_000_000_000)) if n % 1_000_000_000 else "")


def tanggal(s):
    """'2025-02-06' atau date -> date. Kosong -> None."""
    if not s:
        return None
    if isinstance(s, _dt.date):
        return s
    s = str(s).strip()
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def format_angka(n):
    """1373 -> '1.373'  (pemisah ribuan gaya Indonesia)"""
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        return ""
    return f"{n:,}".replace(",", ".")


def luas_teks(m2):
    """600 -> '600 m² (enam ratus meter persegi)'"""
    if m2 in (None, "", 0):
        return ""
    n = int(round(float(m2)))
    return f"{format_angka(n)} m² ({terbilang(n)} meter persegi)"


def luas_kira(m2):
    """Luas menurut surat tanah selalu perkiraan, jadi ditulis dengan tanda kira-kira.
    450 -> '± 450 m² (kurang lebih empat ratus lima puluh meter persegi)'"""
    if m2 in (None, "", 0):
        return ""
    n = int(round(float(m2)))
    return f"± {format_angka(n)} m² (kurang lebih {terbilang(n)} meter persegi)"


def tanggal_panjang(d):
    """date -> '06 Februari 2025'"""
    d = tanggal(d)
    return f"{d.day:02d} {BULAN[d.month - 1]} {d.year}" if d else ""


def tanggal_pendek(d):
    d = tanggal(d)
    return d.strftime("%d/%m/%Y") if d else ""


def nama_hari(d):
    d = tanggal(d)
    return HARI[d.weekday()] if d else ""


def nama_bulan(d):
    d = tanggal(d)
    return BULAN[d.month - 1] if d else ""


def hari_terbilang(d):
    d = tanggal(d)
    return terbilang(d.day) if d else ""


def tahun_terbilang(d):
    d = tanggal(d)
    return terbilang(d.year) if d else ""


def bulan_romawi(d):
    d = tanggal(d)
    return BULAN_ROMAWI[d.month - 1] if d else ""


def sapaan(jenis_kelamin):
    jk = (jenis_kelamin or "").strip().lower()
    if jk.startswith("p"):
        return "Sdri."
    if jk.startswith("l"):
        return "Sdr."
    return "Sdr./Sdri."


def hari_kerja_antara(mulai, selesai):
    """Jumlah hari kerja (Senin-Jumat) dari `mulai` sampai `selesai`.
    Dipakai untuk tenggat 14 hari kerja Panitia A (Pasal 136 Permen 18/2021).
    Hari libur nasional tidak diperhitungkan."""
    a, b = tanggal(mulai), tanggal(selesai)
    if not a or not b or b < a:
        return None
    n, d = 0, a
    while d < b:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def bersihkan(s):
    """Rapikan teks dari Excel: spasi ganda, karakter m2 yang rusak, spasi tepi."""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("�", "²").replace("m2", "m²").replace("m²²", "m²")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def angka_dari_teks(s):
    """Ambil angka luas pertama dari teks Excel lama.
    '± 1.289 m² (seribu ...)' -> 1289 ;  '600 m²' -> 600"""
    if s is None:
        return None
    s = str(s)
    m = re.search(r"(\d[\d.,]*)\s*m", s)
    if not m:
        m = re.search(r"(\d[\d.,]*)", s)
    if not m:
        return None
    t = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(t)
    except ValueError:
        return None
