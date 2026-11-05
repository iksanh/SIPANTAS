# -*- coding: utf-8 -*-
"""Uji pengurai KK, SPPF, dokumen lain, dan ekstrak.jalankan.

    python -m unittest uji.uji_unggah_jenis
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import aiw                                                # noqa: E402
from berkas.baca import ekstrak                                       # noqa: E402
from berkas.baca.jenis import kk, lainnya, sppf                       # noqa: E402
from uji import contoh_unggah as c                                    # noqa: E402


class UjiKk(unittest.TestCase):
    def test_kk_nomor_dan_anggota(self):
        h = kk.urai(c.TEKS_KK)
        self.assertEqual(h["dokumen"], [{"uraian": "Kartu Keluarga Nomor 7503070101100002",
                                         "kategori": "tambahan"}])
        self.assertEqual(h["pihak"], [{"nama": "HASAN USMAN", "nik": "7503071002850003"},
                                      {"nama": "SITI AMINAH", "nik": "7503074512900001"}])
        self.assertEqual(h["isian"], {})


class UjiSppf(unittest.TestCase):
    def test_sppf_batas_dan_luas(self):
        i = sppf.urai(c.TEKS_SPPF)["isian"]
        self.assertEqual(i["batas_utara"], "Tanah Hasan")
        self.assertEqual(i["batas_timur"], "Jalan Desa")
        self.assertEqual(i["batas_selatan"], "Sungai")
        self.assertEqual(i["batas_barat"], "Tanah Ali")
        self.assertEqual(i["luas_surat"], "1250")
        self.assertEqual(i["baku_sppf"],
                         "Surat Pernyataan Penguasaan Fisik Bidang Tanah tanggal 12 Maret 2024")

    def test_sppf_tulisan_tangan_kosong(self):
        i = sppf.urai(c.TEKS_SPPF.replace("Utara : Tanah Hasan", "Utara : "))["isian"]
        self.assertNotIn("batas_utara", i)


class UjiLainnya(unittest.TestCase):
    def test_lainnya_dari_judul(self):
        h = lainnya.urai(c.TEKS_LAIN)
        self.assertEqual(h["dokumen"], [{"uraian": "Surat Keterangan Domisili Nomor 140/12/2025",
                                         "kategori": "tambahan"}])


class UjiEkstrak(unittest.TestCase):
    def test_ekstrak_aiw_diteruskan(self):
        h = ekstrak.jalankan("aiw", c.TEKS_AIW, None)
        self.assertEqual(h, {"jenis": "aiw", "hasil": aiw.urai(c.TEKS_AIW)})

    def test_ekstrak_ktp(self):
        h = ekstrak.jalankan("ktp", c.TEKS_KTP, None)
        self.assertEqual(h["hasil"]["pihak"][0]["nik"], "7503074512900001")

    def test_ekstrak_tidak_terbaca_ditolak(self):
        with self.assertRaises(ValueError):
            ekstrak.jalankan("tidak_terbaca", "", None)


if __name__ == "__main__":
    unittest.main()
