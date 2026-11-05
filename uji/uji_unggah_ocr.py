# -*- coding: utf-8 -*-
"""Uji pembaca halaman unggahan (berkas/baca/ocr.py).

    python -m unittest uji.uji_unggah_ocr
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas.baca import ocr                                           # noqa: E402
from uji.contoh_unggah import pdf_teks, png_teks                      # noqa: E402


class UjiBaca(unittest.TestCase):
    def test_pdf_berlapisan_teks(self):
        hal = ocr.baca("kk.pdf", pdf_teks(["KARTU KELUARGA\nNo. 7503070101100002"]))
        self.assertEqual(len(hal), 1)
        self.assertEqual(hal[0].no, 1)
        self.assertIn("KARTU KELUARGA", hal[0].teks)
        self.assertFalse(hal[0].gagal)

    @unittest.skipUnless(ocr.TERSEDIA, "paket OCR belum terpasang")
    def test_gambar_di_ocr(self):
        hal = ocr.baca("ktp.png", png_teks("KARTU TANDA PENDUDUK"))
        self.assertEqual(len(hal), 1)
        teks = hal[0].teks.upper()
        self.assertIn("KARTU", teks)
        self.assertIn("PENDUDUK", teks)

    def test_format_ditolak(self):
        with self.assertRaises(ocr.GalatBaca):
            ocr.baca("a.docx", b"PK\x03\x04isi")

    def test_terlalu_besar(self):
        with self.assertRaises(ocr.GalatBaca) as c:
            ocr.baca("besar.pdf", b"%PDF" + b"0" * ocr.BATAS_BITA)
        self.assertIn("20 MB", str(c.exception))

    def test_pdf_rusak(self):
        with self.assertRaises(ocr.GalatBaca):
            ocr.baca("x.pdf", b"%PDF-1.4 rusak")

    def test_terlalu_banyak_halaman(self):
        with self.assertRaises(ocr.GalatBaca) as c:
            ocr.baca("tebal.pdf", pdf_teks(["halaman"] * 31))
        self.assertIn("30", str(c.exception))

    def test_gambar_png(self):
        png = ocr.gambar("kk.pdf", pdf_teks(["KARTU KELUARGA"]), 1)
        self.assertTrue(png.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
