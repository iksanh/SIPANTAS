# -*- coding: utf-8 -*-
"""Cetakan loket: formulir Daftar Kelengkapan dan surat pengembalian berkas.

Keduanya dirakit dari pradaftar, bukan dari berkas, dan **tidak disimpan** ke
folder keluaran/ maupun dicatat di `dokumen_terbit`. Alasannya sama dengan
alasan folder keluaran boleh dirapikan: cetakan ini bisa dibuat ulang persis
kapan saja dari pradaftarnya, jadi menyimpannya cuma menumpuk berkas. Yang
perlu ditelusuri — siapa yang memeriksa dan kapan — sudah ada di baris
pradaftarnya sendiri.

Yang dilihat petugas adalah **pratinjau PDF**, bukan unduhan: formulir loket
dibaca sebentar lalu dicetak, tidak disunting. Karena itu DOCX-nya ditaruh di
folder `pratinjau/` bersama PDF hasil konversinya — dua-duanya singgahan yang
selalu bisa dibuat ulang, dan dipangkas sendiri oleh pemeliharaan.py.

Singgahannya tidak perlu dicatat di mana pun: waktu ubah DOCX-nya disetel ke
waktu ubah pradaftarnya (atau waktu ubah template, mana yang lebih baru), jadi
perbandingan mtime yang sudah dipakai pdf.ke_pdf() otomatis mengenali kapan
PDF-nya basi. Cetakan yang datanya tidak berubah langsung tampil.

Perakitannya tetap lewat docxgen dan template biasa, jadi tata naskahnya bisa
diubah lewat menu Template seperti BAP, Risalah, dan SK.
"""
import datetime as dt
import os
import re

from .. import pradaftar, util
from . import docxgen, pdf, templat

# Satu spasi em per tingkat. Indentasi dibawa di dalam teksnya karena tabel
# formulirnya cuma punya satu kolom uraian — sama seperti aslinya, yang juga
# menjorokkan anak butir di dalam sel yang sama.
JOROK = " "

CENTANG = "✓"


def _letak(d):
    bagian = [d.get("desa") and f"{d.get('jenis_desa') or 'Desa'} {d['desa']}",
              d.get("kecamatan") and f"Kecamatan {d['kecamatan']}",
              d.get("letak_lain")]
    return ", ".join(x for x in bagian if x) or "-"


def _baris_butir(pohon):
    """Pohon butir jadi baris tabel, urut seperti formulirnya.

    Penanda tingkat 0 masuk kolom No.; huruf anak butir ikut menempel di depan
    uraiannya — persis susunan lampirannya, yang juga menaruh a/b/c di dalam
    sel uraian, bukan di kolom nomor.
    """
    hasil = []
    for n in pradaftar.ratakan(pohon):
        tingkat = n["tingkat"]
        awalan = f"{n['penanda']}. " if (tingkat and n["penanda"]) else ""
        nama = n["nama"]
        if n["isian_bebas"]:
            # Titik-titik pada formulir aslinya: diisi yang diketik petugas,
            # atau dibiarkan sebagai titik-titik supaya bisa ditulis tangan.
            nama += (" " + "; ".join(n["uraian_daftar"]) if n["uraian_daftar"]
                     else " ……")
        elif n["uraian_daftar"]:
            # Butir biasa yang boleh lebih dari satu surat: rinciannya ikut
            # tercetak di belakang bunyi butir, di dalam sel yang sama.
            nama += ": " + "; ".join(n["uraian_daftar"])
        # Baris kepala kelompok tidak dicentang: pada formulirnya yang memikul
        # centang adalah butirnya, dan kepala kelompok cuma menaungi. Butir yang
        # tidak berlaku dikosongkan dua-duanya, sesuai catatan "coret yang tidak
        # perlu" pada formulirnya.
        dicentang = n["sifat"] != "judul" and n["berlaku"]
        # Surat yang perlu koreksi memang ada, jadi dicentang di kolom Ada.
        # Formulir resminya tidak punya kolom ketiga; catatannya ditaruh di
        # belakang bunyi butir, di dalam sel uraian yang sama.
        ada = n["ada"] in (pradaftar.ADA, pradaftar.KOREKSI)
        if dicentang and n["ada"] == pradaftar.KOREKSI:
            nama += (f" (perlu koreksi: {n['catatan_jawab']})"
                     if n["catatan_jawab"] else " (perlu koreksi)")
        hasil.append({
            "penanda": n["penanda"] if tingkat == 0 else "",
            "nama": JOROK * tingkat + awalan + nama,
            "ada": CENTANG if (dicentang and ada) else "",
            "tidak": CENTANG if (dicentang and not ada) else "",
        })
    return hasil


def konteks(k, d):
    """Nilai tiap penanda untuk kedua template."""
    p = {r["kunci"]: r["nilai"] for r in k.execute("SELECT kunci,nilai FROM pengaturan")}
    return {
        "nomor": d.get("nomor") or "",
        "tanggal": util.tanggal_panjang(d.get("tanggal")) or "",
        "judul_formulir": d.get("judul_formulir") or "Daftar Kelengkapan Persyaratan",
        "dasar_formulir": d.get("dasar_formulir") or "",
        "nama_hak": d.get("nama_hak") or d.get("jenis_hak") or "",
        "pemohon": d.get("pemohon_nama") or "",
        "pemohon_nik": d.get("pemohon_nik") or "-",
        "pemohon_alamat": d.get("pemohon_alamat") or "-",
        "kuasa": d.get("kuasa_nama") or "",
        "letak": _letak(d),
        # Anak kalimat utuh, bukan cuma nilainya: letak tanah boleh belum
        # diketahui saat berkas dikembalikan, dan "yang terletak di -" janggal
        # dibaca pemohon. Penanda bersyarat tidak bisa dipakai karena yang
        # hilang cuma sepotong kalimat, bukan paragrafnya.
        "letak_frasa": (f" yang terletak di {_letak(d)}"
                        if _letak(d) != "-" else ""),
        "luas": (f"{util.format_angka(d['luas_surat'])} m²"
                 if d.get("luas_surat") else "-"),
        "nomor_pbt": d.get("nomor_pbt") or "-",
        "catatan": d.get("catatan") or "",
        "kota": p.get("kantor_kota", ""),
        "kantor": p.get("kantor_nama", ""),
        "petugas": d.get("_petugas") or "",
        "butir": _baris_butir(d["pohon"]),
        "kurang": [{"nama": _sebut(x)} for x in d["kurang"]],
        "koreksi": [{"nama": _sebut(x), "catatan": x["catatan_jawab"] or "-"}
                    for x in d.get("koreksi", [])],
        # Tabel surat pengembalian: yang belum dibawa dan yang sudah dibawa tapi
        # harus diperbaiki, dalam SATU daftar dengan kolom keterangan. Dua tabel
        # terpisah akan menyisakan tabel berkepala tanpa isi bila salah satunya
        # kosong — docxgen hanya membuang tabel yang tak bersisa satu baris pun.
        "dikembalikan": (
            [{"nama": _sebut(x), "keterangan": "Belum ada"} for x in d["kurang"]]
            + [{"nama": _sebut(x),
                "keterangan": ("Perlu diperbaiki: " + x["catatan_jawab"]
                               if x["catatan_jawab"] else "Perlu diperbaiki")}
               for x in d.get("koreksi", [])]),
    }


def _sebut(n):
    return (f"{n['penanda']}. " if n["penanda"] else "") + n["nama"]


# jenis cetakan -> (kunci template, judul di layar)
JENIS = {"kelengkapan": "checklist", "pengembalian": "pengembalian"}
JUDUL = {"kelengkapan": "Daftar Kelengkapan Persyaratan",
         "pengembalian": "Surat Pengembalian Berkas"}


def nama_file(d, jenis):
    bersih = re.sub(r"[^A-Za-z0-9 ]+", "", d.get("pemohon_nama") or "").strip() or "pemohon"
    nomor = (d.get("nomor") or f"PD-{d['id']:04d}").replace("/", "-")
    judul = "Kelengkapan" if jenis == "kelengkapan" else "Pengembalian"
    return f"{nomor} - {judul} - {bersih}.docx"


def _waktu(teks):
    """'YYYY-MM-DD HH:MM:SS' jadi detik epoch. Yang tak terbaca dianggap 0."""
    try:
        return dt.datetime.strptime(teks, "%Y-%m-%d %H:%M:%S").timestamp()
    except (TypeError, ValueError):
        return 0.0


def rakit(k, pid, jenis, petugas=""):
    """Rakit satu cetakan loket ke folder pratinjau/. Kembalikan (jalur, d).

    Waktu ubah berkasnya disetel mengikuti datanya, bukan waktu perakitan —
    itulah yang membuat singgahan PDF-nya bisa dipakai ulang tanpa perlu
    mencatat apa pun di basis data.
    """
    if jenis not in JENIS:
        raise ValueError(f"Jenis cetakan tidak dikenal: {jenis}")
    d = pradaftar.muat(k, pid)
    if not d:
        raise ValueError("Pradaftar tidak ditemukan")
    if jenis == "pengembalian" and d["lengkap"]:
        raise ValueError("Kelengkapannya sudah terpenuhi, jadi tidak ada surat "
                         "pengembalian yang perlu dibuat.")
    d["_petugas"] = petugas

    berkas = templat.kunci_kelengkapan(JENIS[jenis], d.get("varian_template") or "")
    template = os.path.join(templat.DIR_TEMPLATE, f"{berkas}.docx")
    if not os.path.exists(template):
        raise FileNotFoundError(
            f"Template {berkas}.docx belum ada. Jalankan: "
            "python -m berkas.perkakas.siapkan_checklist")

    os.makedirs(pdf.DIR_PRATINJAU, exist_ok=True)
    tujuan = os.path.join(pdf.DIR_PRATINJAU, nama_file(d, jenis))
    # Dirakit ke nama sementara lalu dipindahkan: berkas yang sama bisa sedang
    # dibaca Word untuk permintaan lain, dan os.replace() menggantinya sekaligus
    # alih-alih membiarkannya sempat terbaca setengah jadi.
    sementara = tujuan + ".tmp.docx"
    docxgen.render(template, konteks(k, d), sementara)
    # Nama petugas ikut tercetak tetapi bukan bagian data pradaftarnya, jadi
    # tidak boleh ikut menentukan umur singgahan — kalau ikut, cetakan yang
    # sama oleh dua petugas akan dikonversi dua kali tanpa alasan.
    cap = max(_waktu(d.get("diubah")), _waktu(d.get("dibuat")),
              os.path.getmtime(template))
    if cap:
        os.utime(sementara, (cap, cap))
    os.replace(sementara, tujuan)
    return tujuan, d
