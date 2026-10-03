# -*- coding: utf-8 -*-
"""Terbitkan dokumen: beri nomor, rakit DOCX, catat di arsip."""
import os
import re

from .. import db
from . import docxgen
from . import foto as foto_lapang
from . import konteks
from . import penyambung
from . import templat
from .. import util
from .. import jalur

DIR_TEMPLATE = jalur.TEMPLATE
DIR_KELUARAN = jalur.KELUARAN
DIR_FOTO = foto_lapang.DIR_FOTO

JUDUL = {"bap": "BAP", "risalah": "Risalah", "sk": "SK", "penolakan": "Penolakan"}


def _pengaturan(k):
    return {r["kunci"]: r["nilai"] for r in k.execute("SELECT kunci,nilai FROM pengaturan")}


def nomor_risalah(k, berkas_id):
    """Nomor Risalah berjalan per tahun: 12/2026"""
    d = konteks.muat(k, berkas_id)
    tgl = util.tanggal(d["risalah"].get("tanggal"))
    if not tgl:
        return None
    n = db.ambil_nomor(k, "risalah", "-", tgl.year)
    nomor = f"{n}/{tgl.year}"
    k.execute("UPDATE risalah SET nomor=? WHERE berkas_id=?", (nomor, berkas_id))
    k.commit()
    return nomor


def nomor_sk(k, berkas_id):
    """Nomor SK per jenis hak per tahun: 33/HM/BPN.75.03/XII/2026"""
    d = konteks.muat(k, berkas_id)
    tgl = util.tanggal(d["sk"].get("tanggal"))
    if not tgl:
        return None
    kode = d["jenis_hak_rekomendasi"] or d["jenis_hak_dimohon"]
    # Kode yang tercetak di nomor SK belum tentu sama dengan kode jenis haknya:
    # tanah wakaf berkode HW. Diambil dari matriks jenis hak, bukan ditebak di sini.
    r = k.execute("SELECT kode_sk FROM ref_jenis_hak WHERE kode=?", (kode,)).fetchone()
    kode_sk = (r["kode_sk"] if r and r["kode_sk"] else kode)
    p = _pengaturan(k)
    n = db.ambil_nomor(k, "sk", kode_sk, tgl.year)
    nomor = f"{n}/{kode_sk}/{p.get('kantor_kode', 'BPN')}/{util.bulan_romawi(tgl)}/{tgl.year}"
    k.execute("UPDATE sk SET nomor=? WHERE berkas_id=?", (nomor, berkas_id))
    k.commit()
    return nomor


def _kata_penyambung(k, jenis, jalur):
    """Tulis kata penyambung bila jenis dokumen ini memang memakainya.

    Gagalnya tidak membatalkan penerbitan: dokumennya sudah jadi, hanya tanpa
    kata penyambung (mis. di komputer yang tidak punya Microsoft Word).
    """
    aktif = [x.strip().lower()
             for x in (_pengaturan(k).get("kata_penyambung") or "").split(",")]
    if jenis not in aktif:
        return 0
    try:
        return penyambung.tambahkan(jalur)
    except penyambung.TidakAdaWord:
        print("  ! kata penyambung dilewati: Microsoft Word tidak ada di komputer ini")
    except Exception as ex:                                        # noqa: BLE001
        print(f"  ! kata penyambung gagal: {type(ex).__name__}: {ex}")
    return 0


def _varian(k, d):
    """Varian template untuk berkas ini, dari matriks jenis hak."""
    kode = d.get("jenis_hak_rekomendasi") or d.get("jenis_hak_dimohon")
    r = k.execute("SELECT varian_template FROM ref_jenis_hak WHERE kode=?", (kode,)).fetchone()
    return (r["varian_template"] or "") if r else ""


def _nama_file(d, jenis):
    penerima = konteks.penerima_hak(d)
    nama = re.sub(r"[^A-Za-z0-9 ]+", "", penerima.get("nama", "berkas")).strip() or "berkas"
    return f"{d['id']:04d} - {JUDUL[jenis]} - {nama}.docx"


def _kepala_lampiran(c, d):
    """Identitas berkas di bawah judul halaman lampiran foto BAP."""
    desa = " ".join(x for x in (c.get("jenis_desa"), c.get("nama_desa")) if x)
    letak = ", ".join(x for x in (desa, c.get("kecamatan") and f"Kecamatan {c['kecamatan']}")
                      if x)
    pbt = " / ".join(x for x in (c.get("nomor_pbt") and f"PBT {c['nomor_pbt']}",
                                 c.get("nib") and f"NIB {c['nib']}") if x)
    return [("Nazhir" if konteks.wakaf(d) else "Pemohon", c.get("nama_penerima", "")),
            ("Letak tanah", letak),
            ("Bidang tanah", pbt),
            ("Tanggal pemeriksaan", c.get("tgl_bap", ""))]


def rakit(k, berkas_id, jenis):
    """Rakit DOCX-nya saja: tanpa nomor baru, tanpa catatan arsip.

    Dipakai `terbitkan()` dan dipakai lagi kalau dokumen lama diminta padahal
    berkasnya sudah dibuang dari folder keluaran untuk menghemat tempat.
    Kembalikan (jalur, konteks, isi berkas).
    """
    c, d = konteks.bangun(k, berkas_id)
    if c is None:
        raise ValueError("Berkas tidak ditemukan")

    # Tata naskah mana yang dipakai ditentukan jenis haknya: wakaf punya Risalah dan
    # SK sendiri. Varian yang belum punya berkasnya jatuh kembali ke template baku.
    template = os.path.join(DIR_TEMPLATE, f"{templat.kunci(jenis, _varian(k, d))}.docx")
    if not os.path.exists(template):
        raise FileNotFoundError(
            f"Template {jenis}.docx belum ada. Jalankan: python siapkan_template.py")

    foto, kepala = [], []
    if jenis == "bap":
        foto = [(foto_lapang.jalur(f["nama_file"]), f.get("keterangan") or "")
                for f in d["foto"] if f["ada"]]
        kepala = _kepala_lampiran(c, d)

    tujuan = os.path.join(DIR_KELUARAN, _nama_file(d, jenis))
    docxgen.render(template, c, tujuan, foto=foto, kepala_lampiran=kepala)
    _kata_penyambung(k, jenis, tujuan)
    return tujuan, c, d


def rakit_ulang(k, nama_file):
    """Buat kembali dokumen yang berkasnya sudah tidak ada di folder keluaran.

    Dipakai supaya folder keluaran boleh dirapikan tanpa membuat tautan unduh dan
    pratinjau dokumen lama jadi mati. Kembalikan jalurnya, atau None kalau dokumen
    itu tidak tercatat pernah dicetak - berarti tidak diketahui asalnya.
    """
    r = k.execute("SELECT berkas_id, jenis_dokumen FROM dokumen_terbit WHERE nama_file=? "
                  "ORDER BY id DESC LIMIT 1", (nama_file,)).fetchone()
    if not r:
        return None
    tujuan, _, _ = rakit(k, r["berkas_id"], r["jenis_dokumen"])
    return tujuan


def terbitkan(k, berkas_id, jenis, pengguna_id=None):
    """Rakit satu dokumen, beri nomor, catat di arsip. Kembalikan jalur berkas hasil."""
    if jenis == "risalah":
        d0 = konteks.muat(k, berkas_id)
        if not util.tanggal(d0["risalah"].get("tanggal")):
            raise ValueError("Tanggal Risalah belum diisi, sehingga nomornya belum bisa "
                             "diberikan. Isi di tab “Sidang & dokumen terbit”.")
        if not (d0["risalah"].get("nomor") or "").strip():
            nomor_risalah(k, berkas_id)
    if jenis == "sk":
        d0 = konteks.muat(k, berkas_id)
        if not util.tanggal(d0["sk"].get("tanggal")):
            raise ValueError("Tanggal SK belum diisi, sehingga nomornya belum bisa diberikan. "
                             "Isi di tab “Sidang & dokumen terbit”.")
        if not (d0["sk"].get("nomor") or "").strip():
            nomor_sk(k, berkas_id)

    tujuan, c, d = rakit(k, berkas_id, jenis)
    nama_file = os.path.basename(tujuan)

    nomor = {"risalah": c["nomor_risalah"], "sk": c["nomor_sk"]}.get(jenis, "")
    k.execute("INSERT INTO dokumen_terbit (berkas_id,jenis_dokumen,nomor,nama_file,dicetak_oleh) "
              "VALUES (?,?,?,?,?)", (berkas_id, jenis, nomor, nama_file, pengguna_id))
    k.commit()
    return tujuan


def terbitkan_semua(k, berkas_id, pengguna_id=None):
    hasil = []
    d = konteks.muat(k, berkas_id)
    urutan = ["bap", "risalah"]
    if (d["risalah"].get("kesimpulan") or "dikabulkan") == "dikabulkan":
        urutan.append("sk")
    for j in urutan:
        try:
            hasil.append((j, terbitkan(k, berkas_id, j, pengguna_id), None))
        except Exception as e:                                   # noqa: BLE001
            hasil.append((j, None, str(e)))
    return hasil
