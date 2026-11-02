# -*- coding: utf-8 -*-
"""Surat Perintah Tugas Panitia A: penanda, syarat cetak, dan hasil rakitan.

Surat tugas dicetak di awal proses, sebelum pemeriksaan lapang, jadi tidak
boleh tertahan galat milik BAP/Risalah/SK (tanggal Risalah kosong, dst.).
Syaratnya sendiri cukup: panitia sudah dipilih, desa terisi, pemohon terisi.
"""
import os
import shutil
import tempfile
import unittest

from docx import Document
from docx.oxml.ns import qn

from berkas import db
from berkas.dokumen import konteks, templat, terbitkan

from .uji_web import Dasar


def _c(**kw):
    c = {"nama_penerima": "Fenty Idji", "jenis_desa": "Desa", "nama_desa": "Huntu Utara",
         "kecamatan": "Bulango Selatan", "panitia": [
             {"nama": "SILVA", "nip": "1982", "peran": "Ketua merangkap Anggota",
              "instansi": "Kantor Pertanahan Kabupaten Bone Bolango"},
             {"nama": "DEDDY", "nip": "", "peran": "Anggota", "instansi": ""}]}
    c.update(kw)
    return c


def _d(**kw):
    d = {"hak": {"nama": "Hak Milik"}, "pihak": [],
         "desa": {"nama": "Huntu Utara", "jenis": "Desa", "jabatan_pejabat": "Kepala Desa"},
         "pemeriksaan": {"panitia_id": 1, "tanggal_surat_tugas": None},
         "pengaturan": {"kantor_nama": "Kantor Pertanahan Kabupaten Bone Bolango",
                        "kantor_kota": "Suwawa"}}
    d.update(kw)
    return d


class Penanda(unittest.TestCase):

    def test_dasar_lewat_kuasa(self):
        d = _d(pihak=[{"peran": "kuasa", "nama": "Triyanto Alan Idji"}])
        p = konteks.penanda_surat_tugas(_c(), d)
        self.assertEqual(p["st_dasar"],
                         "Permohonan Hak Milik Triyanto Alan Idji An. Fenty Idji")

    def test_dasar_tanpa_kuasa_mengikuti_jenis_hak(self):
        p = konteks.penanda_surat_tugas(_c(nama_penerima="PT. Cahaya Mitra Gorontalo"),
                                        _d(hak={"nama": "Hak Guna Bangunan"}))
        self.assertEqual(p["st_dasar"],
                         "Permohonan Hak Guna Bangunan An. PT. Cahaya Mitra Gorontalo")

    def test_kuasa_yang_sama_dengan_pemohon_tidak_diulang(self):
        d = _d(pihak=[{"peran": "kuasa", "nama": "FENTY IDJI"}])
        self.assertEqual(konteks.penanda_surat_tugas(_c(), d)["st_dasar"],
                         "Permohonan Hak Milik An. Fenty Idji")

    def test_alamat_dan_pejabat_desa(self):
        p = konteks.penanda_surat_tugas(_c(), _d())
        self.assertEqual(p["kabupaten"], "Kabupaten Bone Bolango")
        self.assertEqual(p["kabupaten_kapital"], "KABUPATEN BONE BOLANGO")
        self.assertEqual(p["kantor_kota_kapital"], "SUWAWA")
        self.assertEqual(p["st_mengetahui"], "KEPALA DESA HUNTU UTARA")

    def test_kelurahan_memakai_jabatan_lurah(self):
        d = _d(desa={"nama": "Tumbihe", "jenis": "Kelurahan", "jabatan_pejabat": "Lurah"})
        self.assertEqual(konteks.penanda_surat_tugas(_c(), d)["st_mengetahui"],
                         "LURAH TUMBIHE")

    def test_kantor_kota(self):
        d = _d(pengaturan={"kantor_nama": "Kantor Pertanahan Kota Gorontalo"})
        self.assertEqual(konteks.penanda_surat_tugas(_c(), d)["kabupaten"], "Kota Gorontalo")

    def test_ketua_diambil_dari_peran(self):
        c = _c(panitia=[{"nama": "A", "nip": "1", "peran": "Anggota", "instansi": "K"},
                        {"nama": "B", "nip": "2", "peran": "Ketua merangkap Anggota",
                         "instansi": "K"}])
        p = konteks.penanda_surat_tugas(c, _d())
        self.assertEqual((p["ketua_panitia_nama"], p["ketua_panitia_nip"]), ("B", "2"))

    def test_tanggal_surat_tugas(self):
        self.assertEqual(konteks.penanda_surat_tugas(_c(), _d())["tgl_surat_tugas"], "")
        d = _d(pemeriksaan={"panitia_id": 1, "tanggal_surat_tugas": "2023-11-20"})
        self.assertEqual(konteks.penanda_surat_tugas(_c(), d)["tgl_surat_tugas"],
                         "20 November 2023")


class Syarat(unittest.TestCase):

    def test_lengkap_tanpa_pesan(self):
        self.assertEqual(konteks.syarat_surat_tugas(_c(), _d()), [])

    def test_panitia_desa_pemohon_wajib(self):
        d = _d(desa={}, pemeriksaan={})
        pesan = " ".join(konteks.syarat_surat_tugas(_c(nama_penerima=""), d))
        for kata in ("Panitia A", "desa", "pemohon"):
            self.assertIn(kata, pesan)


class Template(unittest.TestCase):

    def test_terdaftar_dan_berkasnya_ada(self):
        self.assertIn("surat_tugas", templat.JENIS)
        self.assertTrue(os.path.isfile(templat.jalur("surat_tugas")))

    def test_varian_jenis_hak_jatuh_ke_template_baku(self):
        for varian in ("", "wakaf", "hp"):
            self.assertEqual(templat.kunci("surat_tugas", varian), "surat_tugas")


class Cetak(Dasar):
    """Cetak lewat rute web, dengan basis data kosong yang dibuat uji."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._keluaran = tempfile.mkdtemp(prefix="uji-keluaran-")
        cls._keluaran_asli = terbitkan.DIR_KELUARAN
        terbitkan.DIR_KELUARAN = cls._keluaran

    @classmethod
    def tearDownClass(cls):
        terbitkan.DIR_KELUARAN = cls._keluaran_asli
        shutil.rmtree(cls._keluaran, ignore_errors=True)
        super().tearDownClass()

    def berkas(self, c, lengkap=True):
        j = c.post("/berkas/baru", data={"status": "draf", "jenis_kegiatan": "baru",
                                         "jenis_hak_dimohon": "HM",
                                         "penerima_nama": "Fenty Idji"})
        bid = int(j.headers["Location"].split("/berkas/")[1].split("?")[0])
        if not lengkap:
            return bid
        k = db.sambung()
        try:
            kec = db.sisip_id(k, "INSERT INTO ref_kecamatan (nama) VALUES (?)",
                              (f"Kec Uji {bid}",))
            desa = db.sisip_id(k, "INSERT INTO ref_desa (kecamatan_id,nama,nama_pejabat) "
                                  "VALUES (?,?,?)", (kec, f"Huntu {bid}", "Deddy Djuma"))
            pan = db.sisip_id(k, "INSERT INTO ref_panitia (nomor_sk) VALUES ('SK/UJI')")
            for i, (nama, nip, jab, peran) in enumerate([
                    ("SILVA UJI", "19820405 200312 2 002", "Kepala Seksi Penetapan Hak",
                     "Ketua merangkap Anggota"),
                    ("ASDA UJI", "19850728 200912 1 003", "Kepala Seksi Penataan",
                     "Anggota")]):
                k.execute("INSERT INTO ref_panitia_anggota (panitia_id,urut,nama,nip,jabatan,"
                          "peran) VALUES (?,?,?,?,?,?)", (pan, i, nama, nip, jab, peran))
            k.execute(db.upsert("bidang_tanah", "berkas_id,desa_id"), (bid, desa))
            k.execute(db.upsert("pemeriksaan", "berkas_id,panitia_id"), (bid, pan))
            k.execute("INSERT INTO pihak (berkas_id,peran,nama,urut) VALUES (?,'kuasa',?,1)",
                      (bid, "Triyanto Alan Idji"))
            k.commit()
        finally:
            k.close()
        return bid

    def test_tercetak_walau_dokumen_lain_masih_galat(self):
        c = self.klien(masuk=True)
        bid = self.berkas(c)
        k = db.sambung()
        try:
            galat = [m for t, m in konteks.periksa(k, bid) if t == "galat"]
        finally:
            k.close()
        self.assertTrue(galat, "berkas uji mestinya masih punya galat BAP/Risalah/SK")

        j = c.post(f"/berkas/{bid}/cetak", data={"jenis": "surat_tugas"})
        self.assertEqual(j.status_code, 200)
        self.assertIn("berhasil dirakit", j.get_data(as_text=True))

        k = db.sambung()
        try:
            r = k.execute("SELECT nama_file FROM dokumen_terbit WHERE berkas_id=? AND "
                          "jenis_dokumen='surat_tugas'", (bid,)).fetchone()
        finally:
            k.close()
        self.assertIsNotNone(r, "cetakan surat tugas tidak tercatat di arsip")
        teks = self._teks(os.path.join(self._keluaran, r["nama_file"]))

        self.assertNotIn("{{", teks, "masih ada penanda yang tidak terganti")
        self.assertEqual(teks.count("SURAT PERINTAH TUGAS"), 2)
        self.assertIn("Permohonan Hak Milik Triyanto Alan Idji An. Fenty Idji", teks)
        self.assertIn("Melaksanakan Pemeriksaan Lapang", teks)
        self.assertIn("Melaksanakan Sidang Panitia A", teks)
        self.assertIn(f"Desa Huntu {bid} Kecamatan Kec Uji {bid}", teks)
        self.assertIn(f"KEPALA DESA HUNTU {bid}", teks)
        # 2 anggota + kepala desa, di 2 tabel surat dan 2 halaman tanda tangan
        # ketua: tabel tiap surat (2), tanda tangan tiap surat (2), dua halaman ttd (2)
        self.assertEqual(teks.count("SILVA UJI"), 2 + 2 + 2)
        self.assertEqual(teks.count("Deddy Djuma"), 4)
        self.assertIn("19850728 200912 1 003", teks)

    def test_tanpa_panitia_ditolak_dengan_pesan(self):
        c = self.klien(masuk=True)
        bid = self.berkas(c, lengkap=False)
        j = c.post(f"/berkas/{bid}/cetak", data={"jenis": "surat_tugas"})
        self.assertEqual(j.status_code, 200)
        self.assertIn("Panitia A", j.get_data(as_text=True))

    def test_tombol_tetap_aktif_walau_ada_galat(self):
        c = self.klien(masuk=True)
        bid = self.berkas(c, lengkap=False)
        h = c.get(f"/berkas/{bid}").get_data(as_text=True)
        i = h.find('value="surat_tugas"')
        self.assertGreater(i, 0, "tombol Surat Tugas tidak ada")
        self.assertNotIn("disabled", h[i:h.find(">", i)])

    @staticmethod
    def _teks(jalur):
        """Teks tiap paragraf di badan dokumen, termasuk di dalam tabel.

        Dibaca dari XML langsung: python-docx mengembalikan sel gabungan
        berulang kali lewat row.cells, sehingga isinya terhitung ganda."""
        badan = Document(jalur).element.body
        return "\n".join("".join(t.text or "" for t in p.iter(qn("w:t")))
                         for p in badan.iter(qn("w:p")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
