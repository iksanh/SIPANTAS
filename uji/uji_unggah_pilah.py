# -*- coding: utf-8 -*-
"""Uji pemilah jenis dokumen (berkas/baca/pilah.py).

    python -m unittest uji.uji_unggah_pilah
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas.baca import pilah                                         # noqa: E402
from berkas.baca.ocr import Halaman                                   # noqa: E402
from uji import contoh_unggah as c                                    # noqa: E402


class UjiTebak(unittest.TestCase):
    def test_tebak_tiap_jenis(self):
        for teks, kode in [(c.TEKS_KTP, "ktp"), (c.TEKS_KK, "kk"), (c.TEKS_SPPF, "sppf"),
                           (c.TEKS_AIW, "aiw"), (c.TEKS_PBT, "pbt")]:
            with self.subTest(kode=kode):
                jenis, yakin = pilah.tebak(teks)
                self.assertEqual(jenis, kode)
                self.assertGreaterEqual(yakin, pilah.AMBANG_YAKIN)

    def test_teks_kosong_tidak_terbaca(self):
        for teks in ("", "  \n", "ab"):
            self.assertEqual(pilah.tebak(teks), ("tidak_terbaca", 0.0))

    def test_tidak_dikenal_lainnya(self):
        self.assertEqual(pilah.tebak(c.TEKS_LAIN)[0], "lainnya")

    def test_ocr_huruf_besar_kecil_dan_spasi(self):
        teks = "provinsi gorontalo\nkartu   tanda\npenduduk\nNIK : 7503074512900001\nberlaku hingga"
        self.assertEqual(pilah.tebak(teks)[0], "ktp")


class UjiKelompok(unittest.TestCase):
    def test_halaman_berurutan_digabung(self):
        hal = [Halaman(1, c.TEKS_SPPF), Halaman(2, c.TEKS_SPPF), Halaman(3, c.TEKS_KK)]
        pot = pilah.kelompokkan(hal)
        self.assertEqual([(p.hal_awal, p.hal_akhir, p.jenis) for p in pot],
                         [(1, 2, "sppf"), (3, 3, "kk")])
        self.assertEqual(pot[0].teks, c.TEKS_SPPF + "\n\f\n" + c.TEKS_SPPF)

    def test_ktp_berurutan_tidak_digabung(self):
        pot = pilah.kelompokkan([Halaman(1, c.TEKS_KTP), Halaman(2, c.TEKS_KTP)])
        self.assertEqual([(p.hal_awal, p.hal_akhir) for p in pot], [(1, 1), (2, 2)])

    def test_halaman_gagal_jadi_tidak_terbaca(self):
        hal = [Halaman(1, "", gagal=True), Halaman(2, "", gagal=True), Halaman(3, c.TEKS_KK)]
        pot = pilah.kelompokkan(hal)
        self.assertEqual([(p.hal_awal, p.jenis) for p in pot],
                         [(1, "tidak_terbaca"), (2, "tidak_terbaca"), (3, "kk")])


if __name__ == "__main__":
    unittest.main()
