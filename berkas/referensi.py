# -*- coding: utf-8 -*-
"""Pembacaan data referensi: jenis hak, klausa, wilayah, dan susunan Panitia A.

Hanya kueri — tidak tahu-menahu soal HTTP maupun HTML. Dipakai dua pihak:
rute/referensi.py untuk halamannya sendiri, dan rute/berkas.py untuk mengisi
pilihan pada formulir berkas.
"""
from . import pradaftar, wilayah
from .util import ke_int


def semua(k):
    """Seluruh data referensi, untuk mengisi pilihan pada formulir berkas."""
    return {
        "jenis_hak": [dict(r) for r in k.execute(
            "SELECT * FROM ref_jenis_hak WHERE aktif=1 ORDER BY urut")],
        "kecamatan": [dict(r) for r in k.execute("SELECT * FROM ref_kecamatan ORDER BY nama")],
        "desa": [dict(r) for r in k.execute(
            "SELECT d.*, c.nama AS kecamatan FROM ref_desa d "
            "JOIN ref_kecamatan c ON c.id=d.kecamatan_id ORDER BY c.nama, d.nama")],
        "panitia": [panitia(k, r) for r in k.execute(
            "SELECT * FROM ref_panitia ORDER BY tanggal_sk DESC")],
        "klausa": [dict(r) for r in k.execute("SELECT * FROM ref_klausa ORDER BY slot, id")],
        "syarat": [dict(r) for r in k.execute(
            "SELECT * FROM ref_dokumen_syarat WHERE wajib=1 ORDER BY urut")],
    }


def panitia(k, r):
    d = dict(r)
    d["anggota"] = [dict(a) for a in k.execute(
        "SELECT * FROM ref_panitia_anggota WHERE panitia_id=? ORDER BY urut, id", (r["id"],))]
    return d


def ringkas(k):
    """Angka tiap bagian + kepala tiap SK panitia — cukup untuk merakit kartu
    yang masih tertutup. Isi tabelnya baru dibaca bagian() saat dibuka."""
    hitung = lambda q: k.execute(q).fetchone()[0]
    return {
        "jenis_hak": hitung("SELECT COUNT(*) FROM ref_jenis_hak WHERE aktif=1"),
        "klausa": hitung("SELECT COUNT(*) FROM ref_klausa"),
        "kecamatan": hitung("SELECT COUNT(*) FROM ref_kecamatan"),
        "desa": hitung("SELECT COUNT(*) FROM ref_desa"),
        "desa_kosong": hitung("SELECT COUNT(*) FROM ref_desa "
                              "WHERE nama_pejabat IS NULL OR nama_pejabat=''"),
        # yang dijabat penjabat/pelaksana tugas — bukan kepala desa definitif
        "desa_pj": hitung("SELECT COUNT(*) FROM ref_desa "
                          "WHERE nama_pejabat IS NOT NULL AND nama_pejabat <> '' "
                          "AND jabatan_pejabat NOT IN ('Kepala Desa','Lurah')"),
        "kurang": wilayah.bandingkan(k),
        "kelengkapan": pradaftar.daftar_formulir(k),
        "catatan_koreksi": hitung("SELECT COUNT(*) FROM ref_catatan_koreksi WHERE aktif=1"),
        "panitia": [dict(r) for r in k.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM ref_panitia_anggota a "
            "WHERE a.panitia_id=p.id) AS jml_anggota "
            "FROM ref_panitia p ORDER BY p.tanggal_sk DESC, p.id DESC")],
    }


def bagian(k, kunci):
    """Data satu bagian referensi saja, untuk potongan /referensi/bagian/<kunci>."""
    if kunci == "jenis_hak":
        return [dict(r) for r in k.execute(
            "SELECT * FROM ref_jenis_hak WHERE aktif=1 ORDER BY urut")]
    if kunci == "klausa":
        return [dict(r) for r in k.execute("SELECT * FROM ref_klausa ORDER BY slot, id")]
    if kunci == "desa":
        return daftar_desa(k)
    if kunci == "kecamatan":
        return [dict(r) for r in k.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM ref_desa d WHERE d.kecamatan_id=c.id) AS jml_desa "
            "FROM ref_kecamatan c ORDER BY c.nama")]
    if kunci == "kemendagri":
        return wilayah.bandingkan(k)
    if kunci.startswith("kelengkapan-"):
        fid = ke_int(kunci[12:])
        r = k.execute("SELECT * FROM ref_kelengkapan WHERE id=?", (fid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["butir"] = pradaftar.ratakan(pradaftar.butir_formulir(k, fid))
        return d
    if kunci.startswith("panitia-"):
        r = k.execute("SELECT * FROM ref_panitia WHERE id=?", (ke_int(kunci[8:]),)).fetchone()
        return panitia(k, r) if r else None
    if kunci == "catatan_koreksi":
        return catatan_koreksi(k)
    return None


def catatan_koreksi(k):
    """Daftar catatan koreksi baku, berikut pilihan butir yang bisa dituju.

    Butir yang ditawarkan hanya yang dicentang di loket — kepala kelompok tidak
    pernah perlu koreksi sendiri. Labelnya membawa penanda induknya ("2.a")
    supaya "a. KTP Pemohon" tidak tertukar dengan huruf a di grup lain.
    """
    baris = [dict(r) for r in k.execute(
        "SELECT * FROM ref_catatan_koreksi ORDER BY (butir_id IS NOT NULL), "
        "butir_id, urut, id")]
    butir, penanda = [], {}
    for r in k.execute(
            "SELECT b.id, b.induk_id, b.penanda, b.nama, b.sifat, f.kode "
            "FROM ref_kelengkapan_butir b JOIN ref_kelengkapan f ON f.id=b.kelengkapan_id "
            "WHERE b.aktif=1 "
            "ORDER BY f.urut, f.id, b.urut, b.id"):
        induk = penanda.get(r["induk_id"], "")
        sendiri = ".".join(x for x in (induk, r["penanda"]) if x)
        penanda[r["id"]] = sendiri
        if r["sifat"] != "judul":
            label = f'{r["kode"]} · {sendiri + " " if sendiri else ""}{r["nama"]}'
            butir.append((r["id"], label if len(label) <= 90 else label[:87] + "…"))
    return {"baris": baris, "butir": butir}


def daftar_desa(k):
    """Semua desa beserta riwayat pejabatnya, dalam tiga kueri saja.

    Riwayatnya ikut supaya tiap baris tabel bisa langsung menawarkan pilihan
    siapa yang menjabat sekarang, tanpa satu kueri per desa. Daftar kecamatan
    ikut dikirim untuk formulir "tambah desa" di bawah tabelnya.
    """
    baris = [dict(r) for r in k.execute(
        "SELECT d.*, c.nama AS kecamatan FROM ref_desa d "
        "JOIN ref_kecamatan c ON c.id=d.kecamatan_id ORDER BY c.nama, d.nama")]
    per_desa = {}
    for p in k.execute("SELECT * FROM ref_desa_pejabat "
                       "ORDER BY desa_id, aktif DESC, COALESCE(mulai,'') DESC, id DESC"):
        per_desa.setdefault(p["desa_id"], []).append(dict(p))
    for d in baris:
        d["pejabat"] = per_desa.get(d["id"], [])
    return {"baris": baris,
            "kecamatan": [(r["id"], r["nama"]) for r in
                          k.execute("SELECT id, nama FROM ref_kecamatan ORDER BY nama")]}


def satu_desa(k, desa_id):
    """Satu desa lengkap dengan kecamatan dan riwayat pejabatnya."""
    r = k.execute("SELECT d.*, c.nama AS kecamatan FROM ref_desa d "
                  "JOIN ref_kecamatan c ON c.id=d.kecamatan_id WHERE d.id=?",
                  (desa_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["pejabat"] = wilayah.riwayat(k, desa_id)
    d["dipakai"] = k.execute("SELECT COUNT(*) FROM bidang_tanah WHERE desa_id=?",
                             (desa_id,)).fetchone()[0]
    return d


def daftar_kecamatan(k):
    """Pasangan (id, nama) untuk pilihan kecamatan pada formulir desa."""
    return [(r["id"], r["nama"]) for r in
            k.execute("SELECT id, nama FROM ref_kecamatan ORDER BY nama")]
