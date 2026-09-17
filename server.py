# -*- coding: utf-8 -*-
"""Server web sederhana - hanya pustaka bawaan Python.

    python server.py            lalu buka http://localhost:8000

Pengguna awal: admin / admin123  (ganti lewat menu Pengaturan)
"""
import datetime as dt
import html
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import urllib.parse as up
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import db
import foto
import konteks
import pdf
import pemeliharaan
import templat
import terbitkan
import util
import web
import wilayah

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_STATIS = os.path.join(DIR, "static")
UMUR_SESI_JAM = 12
# Di belakang HTTPS (mis. nginx di server), setel ALAMAT dan HTTPS=1 di lingkungan
# supaya kuki sesinya ikut ditandai Secure.
LEWAT_HTTPS = os.environ.get("HTTPS", "").strip() not in ("", "0", "tidak")
MAKS_UNGGAH = 120 * 1024 * 1024       # batas kasar badan permintaan unggahan (foto ponsel)

PESAN = {
    "tersimpan": ("baik", "<b>Tersimpan.</b> Perubahan sudah masuk ke basis data."),
    "dibuat": ("baik", "<b>Berkas dibuat.</b> Lengkapi tab berikutnya, lalu simpan lagi."),
    "dihapus": ("baik", "<b>Berkas dihapus.</b>"),
    "sandi": ("baik", "<b>Kata sandi diubah.</b>"),
    "sandi_salah": ("galat", "<b>Kata sandi lama salah.</b>"),
    "pengguna": ("baik", "<b>Pengguna ditambahkan.</b>"),
    "pengguna_ada": ("galat", "<b>Username sudah dipakai.</b>"),
    "pengaturan": ("baik", "<b>Pengaturan disimpan.</b>"),
    "referensi": ("baik", "<b>Data referensi diperbarui.</b>"),
    "kecamatan": ("baik", "<b>Kecamatan disimpan.</b>"),
    "kecamatan_ada": ("galat", "<b>Nama kecamatan itu sudah ada.</b>"),
    "kecamatan_hapus": ("baik", "<b>Kecamatan dihapus.</b>"),
    "kecamatan_isi": ("galat", "<b>Tidak bisa dihapus.</b> Masih ada desa/kelurahan di "
                               "kecamatan ini. Pindahkan atau hapus desanya dulu."),
    "desa": ("baik", "<b>Desa/kelurahan disimpan.</b>"),
    "desa_ada": ("galat", "<b>Nama itu sudah ada</b> di kecamatan yang sama."),
    "desa_hapus": ("baik", "<b>Desa/kelurahan dihapus.</b>"),
    "desa_dipakai": ("galat", "<b>Tidak bisa dihapus.</b> Letak tanah pada berkas yang sudah "
                              "ada masih menunjuk ke sini."),
    "pejabat": ("baik", "<b>Kepala desa/lurah disimpan.</b>"),
    "pejabat_aktif": ("baik", "<b>Pejabat yang menjabat diganti.</b> Dokumen yang dicetak "
                              "setelah ini memakai nama yang baru."),
    "pejabat_hapus": ("baik", "<b>Pejabat dihapus dari riwayat.</b>"),
    "wilayah_selaras": ("baik", "<b>Daftar Kemendagri dimuat.</b>"),
    "wilayah_lengkap": ("baik", "<b>Sudah lengkap.</b> Semua kecamatan dan desa menurut "
                                "Kemendagri sudah ada."),
    "panitia": ("baik", "<b>Susunan Panitia A disimpan.</b>"),
    "panitia_hapus": ("baik", "<b>Susunan Panitia A dihapus.</b>"),
    "panitia_dipakai": ("galat", "<b>Tidak bisa dihapus.</b> Susunan ini masih dipakai "
                                 "berkas yang sudah ada. Hapus dulu rujukannya, atau biarkan "
                                 "sebagai arsip."),
    "panitia_salin": ("baik", "<b>Susunan disalin.</b> Ubah nomor SK dan anggotanya "
                              "seperlunya."),
    "anggota": ("baik", "<b>Anggota panitia disimpan.</b>"),
    "anggota_hapus": ("baik", "<b>Anggota panitia dihapus.</b>"),
    "template": ("baik", "<b>Template diganti.</b> Yang lama tersimpan sebagai cadangan."),
    "template_pulih": ("baik", "<b>Template dikembalikan</b> dari cadangan."),
    "galat_cetak": ("galat", "<b>Dokumen tidak bisa dicetak</b> karena masih ada kesalahan."),
    "bersih": ("baik", "<b>Penyimpanan dirapikan.</b>"),
    "bersih_kosong": ("baik", "<b>Tidak ada yang perlu dibuang.</b> Penyimpanannya "
                              "sudah rapi."),
}


# --------------------------------------------------------------- referensi
def muat_referensi(k):
    return {
        "jenis_hak": [dict(r) for r in k.execute(
            "SELECT * FROM ref_jenis_hak WHERE aktif=1 ORDER BY urut")],
        "kecamatan": [dict(r) for r in k.execute("SELECT * FROM ref_kecamatan ORDER BY nama")],
        "desa": [dict(r) for r in k.execute(
            "SELECT d.*, c.nama AS kecamatan FROM ref_desa d "
            "JOIN ref_kecamatan c ON c.id=d.kecamatan_id ORDER BY c.nama, d.nama")],
        "panitia": [_panitia(k, r) for r in k.execute(
            "SELECT * FROM ref_panitia ORDER BY tanggal_sk DESC")],
        "klausa": [dict(r) for r in k.execute("SELECT * FROM ref_klausa ORDER BY slot, id")],
        "syarat": [dict(r) for r in k.execute(
            "SELECT * FROM ref_dokumen_syarat WHERE wajib=1 ORDER BY urut")],
    }


def _panitia(k, r):
    d = dict(r)
    d["anggota"] = [dict(a) for a in k.execute(
        "SELECT * FROM ref_panitia_anggota WHERE panitia_id=? ORDER BY urut, id", (r["id"],))]
    return d


def ringkas_referensi(k):
    """Angka tiap bagian + kepala tiap SK panitia — cukup untuk merakit kartu
    yang masih tertutup. Isi tabelnya baru dibaca muat_bagian() saat dibuka."""
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
        "panitia": [dict(r) for r in k.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM ref_panitia_anggota a "
            "WHERE a.panitia_id=p.id) AS jml_anggota "
            "FROM ref_panitia p ORDER BY p.tanggal_sk DESC, p.id DESC")],
    }


def muat_bagian(k, kunci):
    """Data satu bagian referensi saja, untuk potongan /referensi/bagian/<kunci>."""
    if kunci == "jenis_hak":
        return [dict(r) for r in k.execute(
            "SELECT * FROM ref_jenis_hak WHERE aktif=1 ORDER BY urut")]
    if kunci == "klausa":
        return [dict(r) for r in k.execute("SELECT * FROM ref_klausa ORDER BY slot, id")]
    if kunci == "desa":
        return _daftar_desa(k)
    if kunci == "kecamatan":
        return [dict(r) for r in k.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM ref_desa d WHERE d.kecamatan_id=c.id) AS jml_desa "
            "FROM ref_kecamatan c ORDER BY c.nama")]
    if kunci == "kemendagri":
        return wilayah.bandingkan(k)
    if kunci.startswith("panitia-"):
        r = k.execute("SELECT * FROM ref_panitia WHERE id=?", (_i(kunci[8:]),)).fetchone()
        return _panitia(k, r) if r else None
    return None


def _daftar_desa(k):
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


def _satu_desa(k, desa_id):
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


# ------------------------------------------------------------------ simpan
def _n(v):
    """Teks kosong -> None, supaya kolom tetap bersih."""
    v = (v or "").strip()
    return v or None


def _i(v):
    v = (v or "").strip()
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def simpan_berkas(k, f, berkas_id=None, pengguna_id=None):
    """Tulis seluruh isi formulir. f = dict nama -> daftar nilai."""
    satu = lambda n, d="": (f.get(n) or [d])[0].strip()
    banyak = lambda n: [x.strip() for x in f.get(n, [])]
    c = k.cursor()

    kolom = (satu("nomor_berkas") or None, satu("tanggal_permohonan") or None,
             satu("jenis_hak_dimohon") or "HM", satu("jenis_hak_rekomendasi") or None,
             satu("jenis_kegiatan") or "baru", satu("asal_tanah") or "tanah_negara",
             satu("kewenangan") or "kantah", satu("status") or "draf",
             satu("catatan") or None)
    if berkas_id:
        c.execute("UPDATE berkas SET nomor_berkas=?, tanggal_permohonan=?, jenis_hak_dimohon=?, "
                  "jenis_hak_rekomendasi=?, jenis_kegiatan=?, asal_tanah=?, kewenangan=?, "
                  "status=?, catatan=?, diubah=datetime('now','localtime') WHERE id=?",
                  kolom + (berkas_id,))
    else:
        c.execute("INSERT INTO berkas (nomor_berkas,tanggal_permohonan,jenis_hak_dimohon,"
                  "jenis_hak_rekomendasi,jenis_kegiatan,asal_tanah,kewenangan,status,catatan,"
                  "dibuat_oleh) VALUES (?,?,?,?,?,?,?,?,?,?)", kolom + (pengguna_id,))
        berkas_id = c.lastrowid

    # ---- pihak: ditulis ulang seluruhnya
    c.execute("DELETE FROM pihak WHERE berkas_id=?", (berkas_id,))
    if satu("penerima_nama"):
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,ttl,jenis_kelamin,"
                  "alamat,pekerjaan,urut) VALUES (?,'penerima_hak',?,?,?,?,?,?,?,0)",
                  (berkas_id, satu("penerima_jenis_subjek") or "perorangan",
                   satu("penerima_nama"), _n(satu("penerima_nik")), _n(satu("penerima_ttl")),
                   _n(satu("penerima_jenis_kelamin")), _n(satu("penerima_alamat")),
                   _n(satu("penerima_pekerjaan"))))
        pihak_id = c.lastrowid
        if satu("penerima_jenis_subjek") == "badan_hukum" or satu("bh_akta_nomor"):
            c.execute("INSERT OR REPLACE INTO pihak_badan_hukum (pihak_id,bentuk,kedudukan,"
                      "akta_nomor,akta_tanggal,notaris,pengesahan_nomor,pengesahan_tanggal,"
                      "npwp,nib,wakil_nama,wakil_jabatan) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (pihak_id, _n(satu("bh_bentuk")), _n(satu("bh_kedudukan")),
                       _n(satu("bh_akta_nomor")), _n(satu("bh_akta_tanggal")),
                       _n(satu("bh_notaris")), _n(satu("bh_pengesahan_nomor")),
                       _n(satu("bh_pengesahan_tanggal")), _n(satu("bh_npwp")),
                       _n(satu("bh_nib")), _n(satu("bh_wakil_nama")),
                       _n(satu("bh_wakil_jabatan"))))
    if satu("kuasa_nama"):
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,urut) "
                  "VALUES (?,'kuasa','perorangan',?,?,1)",
                  (berkas_id, satu("kuasa_nama"), _n(satu("kuasa_nik"))))
    # Pihak lain dibawa lengkap dengan identitasnya: Nazhir kedua dan seterusnya
    # dicetak Risalah wakaf per orang, jadi NIK/TTL/pekerjaannya diisi di barisnya.
    lain = (banyak("lain_peran"), banyak("lain_nama"), banyak("lain_nik"),
            banyak("lain_ttl"), banyak("lain_pekerjaan"), banyak("lain_alamat"))
    for i, nama in enumerate(lain[1]):
        if not nama:
            continue
        ambil = lambda kol: lain[kol][i] if i < len(lain[kol]) else ""
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,ttl,pekerjaan,"
                  "alamat,urut) VALUES (?,?,'perorangan',?,?,?,?,?,?)",
                  (berkas_id, ambil(0) or "saksi", nama, _n(ambil(2)), _n(ambil(3)),
                   _n(ambil(4)), _n(ambil(5)), 2 + i))

    # ---- bidang tanah
    kes = satu("kesesuaian_lain") or satu("kesesuaian")
    c.execute("INSERT OR REPLACE INTO bidang_tanah (berkas_id,desa_id,nomor_pbt,tanggal_pbt,nib,"
              "luas_pbt,luas_surat,batas_utara,batas_timur,batas_selatan,batas_barat,"
              "penggunaan_sekarang,rencana_penggunaan,rtrw,kesesuaian,tanggal_peta_analisis,"
              "uraian_penguasaan_fisik,uraian_selisih_luas) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (berkas_id, _i(satu("desa_id")), _n(satu("nomor_pbt")), _n(satu("tanggal_pbt")),
               _n(satu("nib")), _i(satu("luas_pbt")), _i(satu("luas_surat")),
               _n(satu("batas_utara")), _n(satu("batas_timur")), _n(satu("batas_selatan")),
               _n(satu("batas_barat")), _n(satu("penggunaan_sekarang")),
               _n(satu("rencana_penggunaan")), _n(satu("rtrw")), _n(kes),
               _n(satu("tanggal_peta_analisis")),
               _n(satu("uraian_penguasaan_fisik")), _n(satu("uraian_selisih_luas"))))

    # ---- riwayat
    c.execute("DELETE FROM riwayat_perolehan WHERE berkas_id=?", (berkas_id,))
    uraian, bukti = banyak("riwayat_uraian"), banyak("riwayat_bukti")
    n = 0
    for i, u in enumerate(uraian):
        if u:
            c.execute("INSERT INTO riwayat_perolehan (berkas_id,urut,uraian,dokumen_bukti) "
                      "VALUES (?,?,?,?)",
                      (berkas_id, n, u, bukti[i] if i < len(bukti) else None))
            n += 1

    # ---- hak asal
    if satu("asal_sertipikat") or satu("asal_nomor_sk"):
        c.execute("INSERT OR REPLACE INTO hak_asal (berkas_id,jenis_hak_lama,nomor_sertipikat,"
                  "nomor_sk,tanggal_sk,tanggal_berakhir,luas) VALUES (?,?,?,?,?,?,?)",
                  (berkas_id, _n(satu("asal_jenis_hak")), _n(satu("asal_sertipikat")),
                   _n(satu("asal_nomor_sk")), _n(satu("asal_tanggal_sk")),
                   _n(satu("asal_tanggal_berakhir")), _i(satu("asal_luas"))))
    else:
        c.execute("DELETE FROM hak_asal WHERE berkas_id=?", (berkas_id,))

    # ---- dokumen pendukung: slot baku dulu (urutannya tetap), baru sisanya
    c.execute("DELETE FROM dokumen_pendukung WHERE berkas_id=?", (berkas_id,))
    n = 0
    for kategori, _, _, _ in db.dokumen_baku(satu("jenis_hak_dimohon")):
        u = satu("baku_" + kategori)
        # Akta Ikrar Wakaf dan Pengesahan Nazhir diisi per unsur; uraiannya boleh kosong
        # (disusun konteks.py), jenis akta saja belum berarti suratnya ada
        rincian = {x: _n(satu(f"baku_{x}_{kategori}"))
                   for x, _, _ in db.RINCIAN_BAKU.get(kategori, [])}
        if u or any(v for x, v in rincian.items() if x != "jenis"):
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian,"
                      "jenis,nomor,tanggal,pejabat,wilayah_pejabat) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (berkas_id, n, kategori, u or "", satu("baku_asli_" + kategori) or "",
                       *(rincian.get(x) for x in db.KOLOM_RINCIAN)))
            n += 1
    du, dk, dg = banyak("dokumen_uraian"), banyak("dokumen_keaslian"), banyak("dokumen_kategori")
    for i, u in enumerate(du):
        if u:
            kategori = (dg[i] if i < len(dg) else "") or "tambahan"
            if kategori in db.KATEGORI_BAKU:      # slot baku hanya diisi lewat isiannya sendiri
                kategori = "tambahan"
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian) "
                      "VALUES (?,?,?,?,?)",
                      (berkas_id, n, kategori, u, dk[i] if i < len(dk) else ""))
            n += 1

    # ---- pemeriksaan
    c.execute("INSERT OR REPLACE INTO pemeriksaan (berkas_id,tanggal_surat_tugas,tanggal_bap,"
              "panitia_id,keberatan) VALUES (?,?,?,?,?)",
              (berkas_id, _n(satu("tanggal_surat_tugas")), _n(satu("tanggal_bap")),
               _i(satu("panitia_id")), _n(satu("keberatan"))))

    # ---- pendapat anggota
    c.execute("DELETE FROM pendapat_anggota WHERE berkas_id=?", (berkas_id,))
    pn, pp, pa = banyak("pendapat_nama"), banyak("pendapat_peran"), banyak("pendapat_alasan")
    ps, pt, pw = banyak("pendapat_setuju"), banyak("pendapat_ttd"), banyak("pendapat_diwakili")
    n = 0
    for i, nama in enumerate(pn):
        if nama:
            c.execute("INSERT INTO pendapat_anggota (berkas_id,urut,nama,peran,setuju,alasan,"
                      "menandatangani,diwakili_oleh) VALUES (?,?,?,?,?,?,?,?)",
                      (berkas_id, n, nama, pp[i] if i < len(pp) else None,
                       1 if (ps[i] if i < len(ps) else "1") == "1" else 0,
                       pa[i] if i < len(pa) else None,
                       1 if (pt[i] if i < len(pt) else "1") == "1" else 0,
                       _n(pw[i]) if i < len(pw) else None))
            n += 1

    # ---- risalah & sk
    c.execute("INSERT OR REPLACE INTO risalah (berkas_id,nomor,tanggal,kesimpulan,"
              "jangka_waktu_tahun,alasan) VALUES (?,?,?,?,?,?)",
              (berkas_id, _n(satu("risalah_nomor")), _n(satu("risalah_tanggal")),
               satu("risalah_kesimpulan") or "dikabulkan", _i(satu("risalah_jangka")),
               _n(satu("risalah_alasan"))))
    c.execute("INSERT OR REPLACE INTO sk (berkas_id,nomor,tanggal,pejabat_nama,pejabat_nip,"
              "validasi_pph,uang_pemasukan) VALUES (?,?,?,?,?,?,?)",
              (berkas_id, _n(satu("sk_nomor")), _n(satu("sk_tanggal")),
               _n(satu("sk_pejabat_nama")), _n(satu("sk_pejabat_nip")),
               _n(satu("sk_validasi_pph")), _i(satu("sk_uang"))))
    k.commit()
    return berkas_id


# ------------------------------------------------------------------ handler
class Penangan(BaseHTTPRequestHandler):
    server_version = "BerkasPanitiaA/1.0"

    # ---------- utilitas ----------
    def _potongan(self, isi):
        """Potongan kartu lipat, ditandai supaya app.js tak salah menelan halaman lain."""
        if not isi:
            return self._kirim("bagian tidak dikenal", 404, "text/plain; charset=utf-8")
        return self._kirim(isi, kepala={"X-Potongan": "1"})

    def _kirim(self, isi, kode=200, tipe="text/html; charset=utf-8", kepala=None):
        if isinstance(isi, str):
            isi = isi.encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(isi)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for n, v in (kepala or {}).items():
            self.send_header(n, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(isi)

    def _alih(self, ke):
        self.send_response(303)
        self.send_header("Location", ke)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _kuki(self):
        mentah = self.headers.get("Cookie", "")
        hasil = {}
        for bagian in mentah.split(";"):
            if "=" in bagian:
                n, v = bagian.split("=", 1)
                hasil[n.strip()] = v.strip()
        return hasil

    def _pengguna(self, k):
        token = self._kuki().get("sesi")
        if not token:
            return None
        r = k.execute(
            "SELECT p.* FROM sesi s JOIN pengguna p ON p.id=s.pengguna_id "
            "WHERE s.token=? AND s.kedaluwarsa > datetime('now','localtime') AND p.aktif=1",
            (token,)).fetchone()
        return dict(r) if r else None

    def _form(self):
        """Isian formulir. Berkas yang diunggah masuk ke self.berkas_unggah (yang
        pertama per nama) dan self.berkas_banyak (semuanya, untuk <input multiple>)."""
        self.berkas_unggah = {}
        self.berkas_banyak = {}
        self.terlalu_besar = False
        tipe = self.headers.get("Content-Type", "")
        panjang = int(self.headers.get("Content-Length") or 0)
        if tipe.startswith("multipart/form-data"):
            return self._form_berkas(tipe, panjang)
        mentah = self.rfile.read(panjang).decode("utf-8", "replace") if panjang else ""
        return up.parse_qs(mentah, keep_blank_values=True)

    def _form_berkas(self, tipe, panjang):
        """Pembaca multipart/form-data seadanya - isian teks dan berkas unggahan."""
        batas = ""
        for bagian in tipe.split(";"):
            bagian = bagian.strip()
            if bagian.startswith("boundary="):
                batas = bagian[len("boundary="):].strip('"')
        if panjang > MAKS_UNGGAH:
            # Badannya tetap dibaca habis supaya peramban menerima jawaban, bukan
            # sambungan terputus - lalu ditolak utuh, tidak disimpan sebagian.
            self.terlalu_besar = True
            sisa = panjang
            while sisa > 0:
                potong = self.rfile.read(min(sisa, 1 << 20))
                if not potong:
                    break
                sisa -= len(potong)
            return {}
        if not batas or panjang <= 0:
            return {}
        mentah = self.rfile.read(panjang)
        hasil = {}
        for potong in mentah.split(b"--" + batas.encode()):
            if b"\r\n\r\n" not in potong:
                continue
            kepala, isi = potong.split(b"\r\n\r\n", 1)
            if isi.endswith(b"\r\n"):
                isi = isi[:-2]
            teks = kepala.decode("utf-8", "replace")
            nama = re.search(r'name="([^"]*)"', teks)
            if not nama:
                continue
            nama = nama.group(1)
            berkas = re.search(r'filename="([^"]*)"', teks)
            if berkas is not None:
                if berkas.group(1):
                    self.berkas_unggah.setdefault(nama, (berkas.group(1), isi))
                    self.berkas_banyak.setdefault(nama, []).append((berkas.group(1), isi))
            else:
                hasil.setdefault(nama, []).append(isi.decode("utf-8", "replace"))
        return hasil

    def _buka(self):
        """Kunci kartu lipat yang diminta terbuka lewat ?buka= — jalur tanpa JavaScript."""
        q = up.parse_qs(up.urlparse(self.path).query)
        return [b for b in q.get("buka", []) if b][:8]

    def _pesan(self):
        q = up.parse_qs(up.urlparse(self.path).query)
        teks = (q.get("galat") or [None])[0]
        if teks:
            return ("galat", html.escape(teks[:400]))
        teks = (q.get("baik") or [None])[0]       # kabar berhasil yang memuat angka
        if teks:
            return ("baik", html.escape(teks[:400]))
        kode = (q.get("pesan") or [None])[0]
        return PESAN.get(kode)

    def log_message(self, fmt, *args):        # senyap kecuali kesalahan
        if not str(args[1] if len(args) > 1 else "").startswith(("2", "3")):
            sys.stderr.write("  %s %s\n" % (self.command, self.path))

    # ---------- routing ----------
    def do_GET(self):
        jalur = up.urlparse(self.path).path
        if jalur.startswith("/static/"):
            return self._statis(jalur)
        k = db.sambung()
        try:
            pengguna = self._pengguna(k)
            if jalur == "/masuk":
                return self._kirim(web.halaman_masuk())
            if not pengguna:
                if "/bagian/" in jalur:
                    return self._kirim("sesi habis", 401, "text/plain; charset=utf-8")
                return self._alih("/masuk")
            if jalur in ("/", "/berkas"):
                return self._daftar(k, pengguna)
            if jalur == "/berkas/baru":
                return self._kirim(web.halaman_form(k, pengguna, None, muat_referensi(k),
                                                    pesan=self._pesan()))
            if jalur.startswith("/berkas/"):
                sisa = jalur[len("/berkas/"):].split("/")
                if sisa[0].isdigit() and len(sisa) == 1:
                    return self._satu(k, pengguna, int(sisa[0]))
            if jalur == "/referensi":
                return self._referensi(k, pengguna)
            if jalur.startswith("/referensi/desa/"):
                d = _satu_desa(k, _i(jalur[len("/referensi/desa/"):]))
                if not d:
                    return self._alih("/referensi?buka=desa#b-desa")
                kec = [(r["id"], r["nama"]) for r in
                       k.execute("SELECT id, nama FROM ref_kecamatan ORDER BY nama")]
                return self._kirim(web.halaman_desa(pengguna, d, kec, self._pesan()))
            if jalur.startswith("/referensi/bagian/"):
                kunci = up.unquote(jalur[len("/referensi/bagian/"):])
                return self._potongan(web.bagian_referensi(kunci, muat_bagian(k, kunci)))
            if jalur == "/template":
                buka = {b: web.bagian_template(k, b)
                        for b in self._buka() if web.bagian_template(k, b)}
                return self._kirim(web.halaman_template(k, pengguna, self._pesan(), buka))
            if jalur.startswith("/template/bagian/"):
                return self._potongan(
                    web.bagian_template(k, up.unquote(jalur[len("/template/bagian/"):])))
            if jalur.startswith("/template/unduh/"):
                return self._unduh_template(jalur[len("/template/unduh/"):])
            if jalur == "/pengaturan":
                peng = {r["kunci"]: r["nilai"] for r in k.execute("SELECT * FROM pengaturan")}
                daftar = [dict(r) for r in k.execute("SELECT * FROM pengguna ORDER BY id")]
                return self._kirim(web.halaman_pengaturan(
                    pengguna, peng, daftar, self._pesan(), pemeliharaan.ringkas()))
            if jalur == "/keluar":
                token = self._kuki().get("sesi")
                if token:
                    k.execute("DELETE FROM sesi WHERE token=?", (token,))
                    k.commit()
                self.send_response(303)
                self.send_header("Location", "/masuk")
                self.send_header("Set-Cookie", "sesi=; Path=/; Max-Age=0")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if jalur.startswith("/unduh/"):
                return self._unduh(k, up.unquote(jalur[len("/unduh/"):]))
            if jalur.startswith("/foto/"):
                return self._foto(k, _i(jalur[len("/foto/"):]))
            if jalur.startswith("/pratinjau/"):
                return self._pratinjau(k, pengguna, up.unquote(jalur[len("/pratinjau/"):]))
            if jalur.startswith("/pdf/"):
                return self._pdf(k, up.unquote(jalur[len("/pdf/"):]))
            return self._kirim(web.layout("Tidak ditemukan",
                                          '<div class="kartu"><div class="kosong">'
                                          '<b>Halaman tidak ditemukan</b>'
                                          '<a href="/berkas">Kembali ke daftar berkas</a>'
                                          '</div></div>', pengguna), 404)
        finally:
            k.close()

    def do_POST(self):
        jalur = up.urlparse(self.path).path
        k = db.sambung()
        try:
            f = self._form()
            if jalur == "/masuk":
                return self._masuk(k, f)
            pengguna = self._pengguna(k)
            if not pengguna:
                return self._alih("/masuk")

            if self.terlalu_besar:
                mb = MAKS_UNGGAH // (1024 * 1024)
                teks = (f"Unggahan melebihi {mb} MB sehingga tidak ada yang disimpan. "
                        "Unggah fotonya beberapa kali, sedikit demi sedikit.")
                asal = up.urlparse(self.headers.get("Referer") or "").path
                if not asal.startswith("/") or asal.startswith("//"):
                    asal = "/berkas"
                return self._alih(f"{asal}?galat={up.quote(teks)}")
            if jalur == "/berkas/baru":
                bid = simpan_berkas(k, f, None, pengguna["id"])
                return self._alih(self._simpan_foto(k, f, bid, "dibuat"))
            if jalur.startswith("/berkas/"):
                sisa = jalur[len("/berkas/"):].split("/")
                bid = int(sisa[0]) if sisa[0].isdigit() else None
                if bid and len(sisa) == 1:
                    simpan_berkas(k, f, bid, pengguna["id"])
                    return self._alih(self._simpan_foto(k, f, bid, "tersimpan"))
                if bid and sisa[1] == "cetak":
                    return self._cetak(k, pengguna, bid, (f.get("jenis") or ["semua"])[0])
                if bid and sisa[1] == "hapus":
                    foto.hapus_semua(k, bid)
                    k.execute("DELETE FROM berkas WHERE id=?", (bid,))
                    k.commit()
                    return self._alih("/berkas?pesan=dihapus")
            if jalur.startswith("/referensi/panitia"):
                return self._panitia_post(k, f, jalur)
            if (jalur.startswith("/referensi/desa") or jalur.startswith("/referensi/kecamatan")
                    or jalur == "/referensi/wilayah"):
                return self._wilayah_post(k, f, jalur)
            if jalur.startswith("/template/"):
                return self._template_post(k, f, jalur, pengguna)
            if jalur == "/pengaturan":
                for nama, nilai in f.items():
                    if nama.startswith("set_"):
                        k.execute("INSERT OR REPLACE INTO pengaturan (kunci,nilai) VALUES (?,?)",
                                  (nama[4:], nilai[0]))
                k.commit()
                return self._alih("/pengaturan?pesan=pengaturan#p-kantor")
            if jalur == "/pemeliharaan":
                return self._pemeliharaan(k, f)
            if jalur == "/sandi":
                lama = (f.get("lama") or [""])[0]
                baru = (f.get("baru") or [""])[0]
                r = k.execute("SELECT sandi_hash FROM pengguna WHERE id=?",
                              (pengguna["id"],)).fetchone()
                if not baru or not db.cek_sandi(lama, r["sandi_hash"]):
                    return self._alih("/pengaturan?pesan=sandi_salah#p-pengguna")
                k.execute("UPDATE pengguna SET sandi_hash=? WHERE id=?",
                          (db.hash_sandi(baru), pengguna["id"]))
                k.commit()
                return self._alih("/pengaturan?pesan=sandi#p-pengguna")
            if jalur == "/pengguna":
                nama = (f.get("nama") or [""])[0].strip()
                un = (f.get("username") or [""])[0].strip()
                sandi = (f.get("sandi") or [""])[0]
                if not (nama and un and sandi):
                    return self._alih("/pengaturan")
                if k.execute("SELECT 1 FROM pengguna WHERE username=?", (un,)).fetchone():
                    return self._alih("/pengaturan?pesan=pengguna_ada#p-pengguna")
                k.execute("INSERT INTO pengguna (nama,username,sandi_hash) VALUES (?,?,?)",
                          (nama, un, db.hash_sandi(sandi)))
                k.commit()
                return self._alih("/pengaturan?pesan=pengguna#p-pengguna")
            return self._alih("/berkas")
        finally:
            k.close()

    # ---------- foto lapangan ----------
    def _simpan_foto(self, k, f, bid, pesan):
        """Susun ulang/hapus foto yang ada, lalu simpan unggahan baru.
        Kembalikan alamat tujuan sesudah menyimpan."""
        if (f.get("foto_ada") or [""])[0] == "1":
            foto.atur(k, bid, [x for x in (_i(v) for v in f.get("foto_id", [])) if x],
                      [x.strip() for x in f.get("foto_ket", [])])
        gagal, n = [], 0
        for nama, isi in self.berkas_banyak.get("foto_baru", []):
            galat = foto.simpan(k, bid, nama, isi)
            if galat:
                gagal.append(galat)
            else:
                n += 1
        k.commit()
        if gagal:
            teks = f"{len(gagal)} foto tidak tersimpan. " + " ".join(gagal)
            return f"/berkas/{bid}?galat={up.quote(teks)}#p-foto"
        if n:
            return f"/berkas/{bid}?baik={up.quote(f'Tersimpan, dengan {n} foto baru.')}#p-foto"
        return f"/berkas/{bid}?pesan={pesan}"

    def _foto(self, k, fid):
        r = k.execute("SELECT nama_file FROM foto_lapang WHERE id=?", (fid,)).fetchone()             if fid else None
        penuh = foto.jalur(r["nama_file"]) if r else ""
        if not penuh or not os.path.isfile(penuh):
            return self._kirim("foto tidak ditemukan", 404, "text/plain; charset=utf-8")
        tipe = mimetypes.guess_type(penuh)[0] or "application/octet-stream"
        with open(penuh, "rb") as fh:
            self._kirim(fh.read(), 200, tipe, {"Cache-Control": "private, max-age=86400"})

    # ---------- pemeliharaan ----------
    def _pemeliharaan(self, k, f):
        """Buang berkas yang bisa dibuat ulang, atas permintaan petugas."""
        aksi = (f.get("aksi") or [""])[0]
        jumlah = bita = 0
        if aksi == "pratinjau":
            jumlah, bita = pemeliharaan.bersihkan_pratinjau(maks_berkas=0, maks_mb=0)
        elif aksi == "cadangan_db":
            jumlah, bita = pemeliharaan.bersihkan_cadangan_db()
        elif aksi == "keluaran":
            try:
                hari = int((f.get("umur_hari") or ["90"])[0])
            except ValueError:
                hari = pemeliharaan.KELUARAN_UMUR_HARI
            jumlah, bita, _ = pemeliharaan.rapikan_keluaran(k, max(hari, 0))
        pesan = "bersih" if jumlah else "bersih_kosong"
        return self._alih(f"/pengaturan?pesan={pesan}#penyimpanan")

    # ---------- referensi ----------
    def _referensi(self, k, pengguna):
        """Kartu yang tertutup dikirim tanpa isi. Bagian yang diminta lewat
        ?buka=<kunci> dirakit di sini supaya tetap jalan tanpa JavaScript."""
        buka = {}
        for b in self._buka():
            if b == "panitia_baru":       # isinya formulir kosong, tak perlu dibaca
                buka[b] = ""
            else:
                isi = web.bagian_referensi(b, muat_bagian(k, b))
                if isi:
                    buka[b] = isi
        return self._kirim(web.halaman_referensi(
            pengguna, ringkas_referensi(k), buka, self._pesan()))

    # ---------- panitia ----------
    def _panitia_post(self, k, f, jalur):
        """Tambah/ubah/hapus susunan Panitia A beserta anggotanya."""
        def v(nama):
            return _n((f.get(nama) or [""])[0])

        def kembali(pesan, sk=None):
            """Balik ke halaman referensi dengan SK yang disunting tetap terbuka."""
            if not sk:
                return self._alih(f"/referensi?pesan={pesan}#panitia")
            return self._alih(f"/referensi?pesan={pesan}&buka=panitia-{sk}#b-panitia-{sk}")

        pid = _i((f.get("panitia_id") or f.get("id") or [""])[0])

        if jalur == "/referensi/panitia":
            if not v("nomor_sk"):
                return self._alih("/referensi?galat=" +
                                  up.quote("Nomor SK susunan panitia wajib diisi."))
            nilai = (v("nomor_sk"), v("tanggal_sk"), v("berlaku_dari"),
                     v("berlaku_sampai"), v("keterangan"))
            if pid:
                k.execute("UPDATE ref_panitia SET nomor_sk=?, tanggal_sk=?, berlaku_dari=?, "
                          "berlaku_sampai=?, keterangan=? WHERE id=?", nilai + (pid,))
            else:
                pid = k.execute("INSERT INTO ref_panitia (nomor_sk,tanggal_sk,berlaku_dari,"
                                "berlaku_sampai,keterangan) VALUES (?,?,?,?,?)",
                                nilai).lastrowid
            k.commit()
            return kembali("panitia", pid)

        if jalur == "/referensi/panitia/hapus":
            dipakai = k.execute("SELECT COUNT(*) AS n FROM pemeriksaan WHERE panitia_id=?",
                                (pid,)).fetchone()["n"]
            if dipakai:
                return kembali("panitia_dipakai", pid)
            k.execute("DELETE FROM ref_panitia_anggota WHERE panitia_id=?", (pid,))
            k.execute("DELETE FROM ref_panitia WHERE id=?", (pid,))
            k.commit()
            return kembali("panitia_hapus")

        if jalur == "/referensi/panitia/salin":
            asal = k.execute("SELECT * FROM ref_panitia WHERE id=?", (pid,)).fetchone()
            if not asal:
                return self._alih("/referensi#panitia")
            cur = k.execute("INSERT INTO ref_panitia (nomor_sk,tanggal_sk,keterangan) "
                            "VALUES (?,?,?)",
                            (asal["nomor_sk"] + " (salinan)", None,
                             "Disalin dari " + asal["nomor_sk"]))
            baru = cur.lastrowid
            for a in k.execute("SELECT * FROM ref_panitia_anggota WHERE panitia_id=? "
                               "ORDER BY urut, id", (pid,)).fetchall():
                k.execute("INSERT INTO ref_panitia_anggota "
                          "(panitia_id,urut,nama,nip,jabatan,peran,pendapat_baku) "
                          "VALUES (?,?,?,?,?,?,?)",
                          (baru, a["urut"], a["nama"], a["nip"], a["jabatan"], a["peran"],
                           a["pendapat_baku"]))
            k.commit()
            return kembali("panitia_salin", baru)

        if jalur == "/referensi/panitia/anggota":
            aid = _i((f.get("anggota_id") or [""])[0])
            if not v("nama") or not pid:
                return self._alih("/referensi?galat=" +
                                  up.quote("Nama anggota panitia wajib diisi."))
            nilai = (_i((f.get("urut") or ["0"])[0]) or 0, v("nama"), v("nip"),
                     v("jabatan"), v("peran"), v("pendapat_baku"))
            if aid:
                k.execute("UPDATE ref_panitia_anggota SET urut=?, nama=?, nip=?, jabatan=?, "
                          "peran=?, pendapat_baku=? WHERE id=? AND panitia_id=?",
                          nilai + (aid, pid))
            else:
                k.execute("INSERT INTO ref_panitia_anggota "
                          "(panitia_id,urut,nama,nip,jabatan,peran,pendapat_baku) "
                          "VALUES (?,?,?,?,?,?,?)", (pid,) + nilai)
            k.commit()
            return kembali("anggota", pid)

        if jalur == "/referensi/panitia/anggota/hapus":
            k.execute("DELETE FROM ref_panitia_anggota WHERE id=?",
                      (_i((f.get("anggota_id") or [""])[0]),))
            k.commit()
            return kembali("anggota_hapus", pid)

        return self._alih("/referensi#panitia")

    # ---------- wilayah: kecamatan, desa, kepala desa ----------
    def _wilayah_post(self, k, f, jalur):
        """Tambah/ubah/hapus kecamatan dan desa, serta riwayat kepala desa/lurah."""
        def v(nama):
            return _n((f.get(nama) or [""])[0])

        def ke(alamat, tanya):
            """Sisipkan kabar ke alamat tujuan, di belakang query tapi di depan #jangkar."""
            jalan, _, jangkar = alamat.partition("#")
            jalan += ("&" if "?" in jalan else "?") + tanya
            return self._alih(jalan + ("#" + jangkar if jangkar else ""))

        def kembali(pesan, bawaan):
            """Balik ke halaman asal — daftar wilayah atau halaman satu desa."""
            asal = v("asal") or bawaan
            return ke(asal if asal.startswith("/referensi") else bawaan, "pesan=" + pesan)

        daftar_kec = "/referensi?buka=kecamatan#b-kecamatan"
        daftar_desa = "/referensi?buka=desa#b-desa"

        # ----- daftar Kemendagri
        if jalur == "/referensi/wilayah":
            kec, desa = wilayah.selaraskan(k)
            if not (kec or desa):
                return ke(daftar_desa, "pesan=wilayah_lengkap")
            kabar = (f"{kec} kecamatan dan {desa} desa/kelurahan ditambahkan dari daftar "
                     f"Kemendagri {wilayah.KODE_KABUPATEN}. Nama pejabatnya masih kosong.")
            return ke(daftar_desa, "baik=" + up.quote(kabar))

        # ----- kecamatan
        if jalur == "/referensi/kecamatan":
            nama, kid = v("nama"), _i((f.get("id") or [""])[0])
            if not nama:
                return self._alih("/referensi?galat=" + up.quote("Nama kecamatan wajib diisi."))
            try:
                if kid:
                    k.execute("UPDATE ref_kecamatan SET nama=?, kode=? WHERE id=?",
                              (nama, v("kode"), kid))
                else:
                    k.execute("INSERT INTO ref_kecamatan (nama,kode) VALUES (?,?)",
                              (nama, v("kode")))
            except sqlite3.IntegrityError:
                return ke(daftar_kec, "pesan=kecamatan_ada")
            k.commit()
            return kembali("kecamatan", daftar_kec)

        if jalur == "/referensi/kecamatan/hapus":
            kid = _i((f.get("id") or [""])[0])
            if k.execute("SELECT COUNT(*) FROM ref_desa WHERE kecamatan_id=?",
                         (kid,)).fetchone()[0]:
                return ke(daftar_kec, "pesan=kecamatan_isi")
            k.execute("DELETE FROM ref_kecamatan WHERE id=?", (kid,))
            k.commit()
            return ke(daftar_kec, "pesan=kecamatan_hapus")

        # ----- desa / kelurahan
        if jalur == "/referensi/desa":
            did = _i((f.get("id") or [""])[0])
            nama, kid = v("nama"), _i((f.get("kecamatan_id") or [""])[0])
            jenis = v("jenis") or "Desa"
            if not (nama and kid):
                return self._alih("/referensi?galat=" +
                                  up.quote("Kecamatan dan nama desa/kelurahan wajib diisi."))
            try:
                if did:
                    k.execute("UPDATE ref_desa SET kecamatan_id=?, nama=?, jenis=?, kode=? "
                              "WHERE id=?", (kid, nama, jenis, v("kode"), did))
                else:
                    did = k.execute(
                        "INSERT INTO ref_desa (kecamatan_id,nama,jenis,kode,jabatan_pejabat) "
                        "VALUES (?,?,?,?,?)",
                        (kid, nama, jenis, v("kode"), wilayah.jabatan_baku(jenis))).lastrowid
            except sqlite3.IntegrityError:
                return ke(daftar_desa, "pesan=desa_ada")
            # Jabatan pejabat aktif ikut menyesuaikan bila Desa diubah jadi Kelurahan.
            wilayah.segarkan(k, did)
            k.commit()
            return kembali("desa", f"/referensi/desa/{did}")

        if jalur == "/referensi/desa/hapus":
            did = _i((f.get("id") or [""])[0])
            if k.execute("SELECT COUNT(*) FROM bidang_tanah WHERE desa_id=?",
                         (did,)).fetchone()[0]:
                return self._alih(f"/referensi/desa/{did}?pesan=desa_dipakai")
            k.execute("DELETE FROM ref_desa_pejabat WHERE desa_id=?", (did,))
            k.execute("DELETE FROM ref_desa WHERE id=?", (did,))
            k.commit()
            return ke(daftar_desa, "pesan=desa_hapus")

        # ----- kepala desa / lurah
        did = _i((f.get("desa_id") or [""])[0])
        bawaan = f"/referensi/desa/{did}"
        pid = _i((f.get("pejabat_id") or [""])[0])

        if jalur == "/referensi/desa/pejabat":
            if not (did and v("nama")):
                return self._alih("/referensi?galat=" +
                                  up.quote("Nama kepala desa/lurah wajib diisi."))
            wilayah.simpan_pejabat(
                k, did, pid, v("nama"), v("jabatan") or wilayah.jabatan_baku(v("jenis")),
                v("mulai"), v("sampai"), v("sk_nomor"), v("catatan"),
                aktif=bool((f.get("aktif") or [""])[0]))
            k.commit()
            return kembali("pejabat", bawaan)

        if jalur == "/referensi/desa/pejabat/aktif":
            if did:
                wilayah.jadikan_aktif(k, did, pid)
                k.commit()
            return kembali("pejabat_aktif", bawaan)

        if jalur == "/referensi/desa/pejabat/hapus":
            if did and pid:
                wilayah.hapus_pejabat(k, did, pid)
                k.commit()
            return kembali("pejabat_hapus", bawaan)

        return self._alih(daftar_desa)

    # ---------- template ----------
    def _unduh_template(self, jenis):
        jenis = os.path.basename(jenis).replace(".docx", "")
        if jenis not in templat.JENIS:
            return self._kirim("template tidak dikenal", 404, "text/plain; charset=utf-8")
        p = templat.jalur(jenis)
        if not os.path.isfile(p):
            return self._kirim("template belum ada", 404, "text/plain; charset=utf-8")
        with open(p, "rb") as fh:
            self._kirim(fh.read(), 200,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        {"Content-Disposition": "attachment; filename*=UTF-8''" +
                         up.quote("template-" + templat.JENIS[jenis][1])})

    def _template_post(self, k, f, jalur, pengguna):
        jenis = (f.get("jenis") or [""])[0]
        if jenis not in templat.JENIS:
            return self._alih("/template?galat=" + up.quote("Jenis template tidak dikenal."))
        try:
            if jalur == "/template/unggah":
                unggah = getattr(self, "berkas_unggah", {}).get("berkas")
                if not unggah:
                    return self._alih("/template?galat=" +
                                      up.quote("Belum ada berkas yang dipilih."))
                templat.simpan(jenis, unggah[1], unggah[0])
                pesan = "template"
            elif jalur == "/template/pulihkan":
                templat.pulihkan(jenis, (f.get("nama") or [""])[0])
                pesan = "template_pulih"
            else:
                return self._alih("/template")
        except templat.Ditolak as ex:
            return self._alih("/template?galat=" + up.quote(str(ex)))
        galat = templat.uji_rakit(jenis, konteks.konteks_contoh(k)[0])
        if galat:
            return self._alih("/template?galat=" + up.quote(
                "Template tersimpan, tetapi percobaan merakitnya gagal: " + galat +
                " — periksa penandanya, atau kembalikan dari cadangan."))
        return self._alih("/template?pesan=" + pesan)

    # ---------- halaman ----------
    def _masuk(self, k, f):
        un = (f.get("username") or [""])[0].strip()
        sandi = (f.get("sandi") or [""])[0]
        r = k.execute("SELECT * FROM pengguna WHERE username=? AND aktif=1", (un,)).fetchone()
        if not r or not db.cek_sandi(sandi, r["sandi_hash"]):
            return self._kirim(web.halaman_masuk("Nama pengguna atau kata sandi salah."), 401)
        token = secrets.token_urlsafe(32)
        habis = (dt.datetime.now() + dt.timedelta(hours=UMUR_SESI_JAM)).strftime("%Y-%m-%d %H:%M:%S")
        k.execute("DELETE FROM sesi WHERE kedaluwarsa < datetime('now','localtime')")
        k.execute("INSERT INTO sesi (token,pengguna_id,kedaluwarsa) VALUES (?,?,?)",
                  (token, r["id"], habis))
        k.commit()
        self.send_response(303)
        self.send_header("Location", "/berkas")
        self.send_header("Set-Cookie",
                         f"sesi={token}; Path=/; HttpOnly; SameSite=Lax; "
                         f"Max-Age={UMUR_SESI_JAM * 3600}"
                         + ("; Secure" if LEWAT_HTTPS else ""))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _daftar(self, k, pengguna):
        baris = [dict(r) for r in k.execute("""
            SELECT b.id, b.status, b.jenis_kegiatan, b.jenis_hak_dimohon AS kode_hak,
                   (SELECT nama FROM pihak WHERE berkas_id=b.id AND peran IN ('penerima_hak','pemohon')
                     ORDER BY urut LIMIT 1) AS penerima,
                   (SELECT nama FROM pihak WHERE berkas_id=b.id AND peran='kuasa' LIMIT 1) AS kuasa,
                   d.nama AS desa, c.nama AS kecamatan, t.luas_pbt,
                   r.nomor AS nomor_risalah, s.nomor AS nomor_sk
            FROM berkas b
            LEFT JOIN bidang_tanah t ON t.berkas_id=b.id
            LEFT JOIN ref_desa d ON d.id=t.desa_id
            LEFT JOIN ref_kecamatan c ON c.id=d.kecamatan_id
            LEFT JOIN risalah r ON r.berkas_id=b.id
            LEFT JOIN sk s ON s.berkas_id=b.id
            ORDER BY b.id DESC""")]
        q = lambda s: k.execute(s).fetchone()[0]
        ringkas = {
            "total": q("SELECT COUNT(*) FROM berkas"),
            "draf": q("SELECT COUNT(*) FROM berkas WHERE status='draf'"),
            "selesai": q("SELECT COUNT(*) FROM berkas WHERE status='selesai'"),
            "dokumen": q("SELECT COUNT(*) FROM dokumen_terbit"),
            "desa": q("SELECT COUNT(*) FROM ref_desa"),
        }
        self._kirim(web.halaman_daftar(k, pengguna, baris, ringkas, self._pesan()))

    def _satu(self, k, pengguna, bid, terbit=None):
        d = konteks.muat(k, bid)
        if not d:
            return self._alih("/berkas")
        d["_terbit"] = [dict(r) for r in k.execute(
            "SELECT * FROM dokumen_terbit WHERE berkas_id=? ORDER BY id DESC", (bid,))]
        masalah = konteks.periksa(k, bid)
        self._kirim(web.halaman_form(k, pengguna, d, muat_referensi(k), masalah, terbit,
                                     self._pesan()))

    def _cetak(self, k, pengguna, bid, jenis):
        masalah = konteks.periksa(k, bid)
        if any(t == "galat" for t, _ in masalah):
            return self._alih(f"/berkas/{bid}?pesan=galat_cetak")
        if jenis == "semua":
            hasil = terbitkan.terbitkan_semua(k, bid, pengguna["id"])
        else:
            try:
                hasil = [(jenis, terbitkan.terbitkan(k, bid, jenis, pengguna["id"]), None)]
            except Exception as ex:                                   # noqa: BLE001
                hasil = [(jenis, None, str(ex))]
        return self._satu(k, pengguna, bid, hasil)

    # ---------- berkas statis & unduhan ----------
    def _statis(self, jalur):
        nama = os.path.basename(jalur)
        penuh = os.path.join(DIR_STATIS, nama)
        if not os.path.isfile(penuh):
            return self._kirim("tidak ditemukan", 404, "text/plain; charset=utf-8")
        tipe = mimetypes.guess_type(penuh)[0] or "application/octet-stream"
        with open(penuh, "rb") as fh:
            self._kirim(fh.read(), 200, tipe, {"Cache-Control": "max-age=300"})

    def _pastikan_ada(self, k, nama):
        """Jalur dokumen di folder keluaran; dirakit ulang dulu kalau sudah dirapikan."""
        penuh = os.path.join(terbitkan.DIR_KELUARAN, nama)
        if os.path.isfile(penuh):
            return penuh
        try:
            return terbitkan.rakit_ulang(k, nama)
        except Exception as ex:                                    # noqa: BLE001
            sys.stderr.write(f"  ! gagal merakit ulang {nama}: {ex}\n")
            return None

    def _pratinjau(self, k, pengguna, nama):
        nama = os.path.basename(nama)
        penuh = self._pastikan_ada(k, nama) or ""
        r = k.execute("SELECT berkas_id FROM dokumen_terbit WHERE nama_file=? "
                      "ORDER BY id DESC LIMIT 1", (nama,)).fetchone()
        bid = r["berkas_id"] if r else None
        judul = ""
        if bid:
            p = k.execute("SELECT nama FROM pihak WHERE berkas_id=? AND peran IN "
                          "('penerima_hak','pemohon') ORDER BY urut LIMIT 1", (bid,)).fetchone()
            judul = p["nama"] if p else ""
        if not penuh or not os.path.isfile(penuh):
            return self._kirim(web.halaman_pratinjau(
                pengguna, nama, bid, judul,
                galat="Dokumennya belum pernah dicetak, jadi belum ada yang bisa "
                      "ditampilkan."), 404)
        mesin = pdf.mesin_tersedia()
        if not mesin:
            return self._kirim(web.halaman_pratinjau(
                pengguna, nama, bid, judul,
                galat="Pratinjau PDF memerlukan Microsoft Word atau LibreOffice di komputer "
                      "ini. Keduanya tidak ditemukan."))
        if up.parse_qs(up.urlparse(self.path).query).get("segarkan"):
            jalur_pdf = os.path.join(pdf.DIR_PRATINJAU,
                                     os.path.splitext(nama)[0] + ".pdf")
            if os.path.exists(jalur_pdf):
                try:
                    os.remove(jalur_pdf)
                except OSError:
                    pass
        self._kirim(web.halaman_pratinjau(pengguna, nama, bid, judul, mesin))

    def _pdf(self, k, nama):
        nama = os.path.basename(nama)
        q = up.parse_qs(up.urlparse(self.path).query)
        penuh = self._pastikan_ada(k, nama)
        if not penuh or not os.path.isfile(penuh):
            return self._kirim("dokumen tidak ditemukan", 404, "text/plain; charset=utf-8")
        try:
            jalur_pdf = pdf.ke_pdf(penuh, paksa=bool(q.get("segarkan")))
        except pdf.TidakAdaMesin as ex:
            return self._kirim(str(ex), 501, "text/plain; charset=utf-8")
        except Exception as ex:                                    # noqa: BLE001
            return self._kirim(f"Gagal membuat PDF: {ex}", 500, "text/plain; charset=utf-8")
        with open(jalur_pdf, "rb") as fh:
            isi = fh.read()
        nama_pdf = os.path.basename(jalur_pdf)
        sikap = "attachment" if q.get("unduh") else "inline"
        self._kirim(isi, 200, "application/pdf",
                    {"Content-Disposition":
                     f"{sikap}; filename*=UTF-8''" + up.quote(nama_pdf),
                     "Cache-Control": "no-cache"})

    def _unduh(self, k, nama):
        nama = os.path.basename(nama)
        penuh = self._pastikan_ada(k, nama)
        if not penuh or not os.path.isfile(penuh):
            return self._kirim("berkas tidak ditemukan", 404, "text/plain; charset=utf-8")
        with open(penuh, "rb") as fh:
            self._kirim(fh.read(), 200,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        {"Content-Disposition":
                         "attachment; filename*=UTF-8''" + up.quote(nama)})


def main():
    # python server.py [porta] [alamat]  -- alamat 0.0.0.0 untuk dipakai sejaringan,
    # bisa juga lewat lingkungan: PORTA=8000 ALAMAT=0.0.0.0
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORTA", 8000))
    alamat = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ALAMAT", "127.0.0.1")
    sendiri = alamat in ("127.0.0.1", "localhost")
    k = db.siapkan()
    jumlah = k.execute("SELECT COUNT(*) FROM berkas").fetchone()[0]
    k.close()
    # hanya singgahan yang dipangkas sendiri; cadangan basis data menunggu perintah
    pemeliharaan.bersihkan_pratinjau()
    if not os.path.exists(os.path.join(terbitkan.DIR_TEMPLATE, "sk.docx")):
        print("  ! Template belum dibuat. Jalankan dulu: python siapkan_template.py")
    print(f"""
  Berkas Panitia A
  ------------------------------------------------
  Alamat   : http://{"localhost" if sendiri else alamat}:{port}
  Basis data: {db.BERKAS_DB}
  Berkas   : {jumlah}
  Keluaran : {terbitkan.DIR_KELUARAN}
  PDF      : {pdf.mesin_tersedia() or "tidak tersedia (perlu Word / LibreOffice)"}

  Tekan Ctrl+C untuk berhenti.
""")
    srv = ThreadingHTTPServer((alamat, port), Penangan)
    if sendiri:
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:                                             # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Berhenti.")
        srv.server_close()


if __name__ == "__main__":
    main()
