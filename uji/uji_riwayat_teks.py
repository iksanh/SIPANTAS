# -*- coding: utf-8 -*-
"""Uji pembaca riwayat dari tulisan (berkas/riwayat_teks.py) dan rutenya.

    python -m unittest uji.uji_riwayat_teks

Riwayat tanah diambil dari poin 3 (sampai sebelum poin 4); tiap butirnya
diawali tanda "-". Teks contohnya karangan, meniru surat pernyataan.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import riwayat_teks                                       # noqa: E402
from uji.uji_web import Dasar as DasarWeb                             # noqa: E402

TEKS = """SURAT PERNYATAAN PENGUASAAN FISIK BIDANG TANAH
1. Nama : Ahmad Uji, NIK 7501010101010001
2. Letak tanah di Desa Uji Satu, luas 350 m2
3. Bahwa bidang tanah tersebut saya peroleh dengan riwayat sebagai berikut:
   - Tahun 1975 dikuasai oleh Hasan Saman (alm);
   - Tahun 1990 diwariskan kepada Rahmat Hasan
     berdasarkan Surat Keterangan Waris tanggal 12-05-1990;
   -Tahun 2010 dijual kepada Ahmad Uji; dan
4. Bidang tanah tersebut tidak dalam sengketa.
   - butir ini milik poin 4, tidak ikut dibaca
"""


class UjiUrai(unittest.TestCase):
    def test_butir_poin_3_saja(self):
        h = riwayat_teks.urai(TEKS)
        self.assertEqual(h["riwayat"], [
            "Tahun 1975 dikuasai oleh Hasan Saman (alm)",
            "Tahun 1990 diwariskan kepada Rahmat Hasan berdasarkan Surat Keterangan "
            "Waris tanggal 12-05-1990",
            "Tahun 2010 dijual kepada Ahmad Uji",
        ])
        self.assertEqual(h["peringatan"], [])

    def test_satu_paragraf_dipisah_tanda_minus(self):
        h = riwayat_teks.urai("3. Riwayat: - Tahun 1980 dikuasai A - Tahun 2000 dijual "
                              "kepada B. 4. Tidak sengketa")
        self.assertEqual(h["riwayat"], ["Tahun 1980 dikuasai A", "Tahun 2000 dijual kepada B"])

    def test_tanda_hubung_dalam_kata_tidak_memisah(self):
        h = riwayat_teks.urai("3.\n- Dikuasai Al-Amin sejak 01-01-1990\n4. Lain")
        self.assertEqual(h["riwayat"], ["Dikuasai Al-Amin sejak 01-01-1990"])

    def test_tanpa_poin_3_seluruh_tulisan_dibaca(self):
        h = riwayat_teks.urai("- Dikuasai A\n- Dijual kepada B")
        self.assertEqual(h["riwayat"], ["Dikuasai A", "Dijual kepada B"])
        self.assertTrue(any("poin 3" in p for p in h["peringatan"]))

    def test_tanpa_tanda_minus_jadi_satu_baris(self):
        h = riwayat_teks.urai("3. Tanah dikuasai A sejak 1990.\n4. Lain")
        self.assertEqual(h["riwayat"], ["Tanah dikuasai A sejak 1990"])
        self.assertTrue(any('"-"' in p for p in h["peringatan"]))

    def test_teks_kosong(self):
        h = riwayat_teks.urai("")
        self.assertEqual(h["riwayat"], [])
        self.assertTrue(h["peringatan"])


class UjiRute(DasarWeb):
    def test_urai_json(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")
        j = c.post("/berkas/riwayat/urai", data={"teks": TEKS})
        self.assertEqual(j.status_code, 200)
        self.assertEqual(len(j.get_json()["riwayat"]), 3)

    def test_perlu_masuk(self):
        j = self.klien().post("/berkas/riwayat/urai", data={"teks": TEKS})
        self.assertNotEqual(j.status_code, 200)

    def test_teks_terlalu_panjang_ditolak(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")
        j = c.post("/berkas/riwayat/urai",
                   data={"teks": "x" * (riwayat_teks.BATAS_TEKS + 1)})
        self.assertEqual(j.status_code, 413)

    def test_kartu_di_tab_riwayat(self):
        isi = self.klien(masuk=True).get("/berkas/baru").get_data(as_text=True)
        self.assertIn('data-ocr="riwayat"', isi)
        self.assertIn("data-ocr-teks", isi)


if __name__ == "__main__":
    unittest.main()
