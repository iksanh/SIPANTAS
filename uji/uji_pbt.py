# -*- coding: utf-8 -*-
"""Uji pengurai teks Peta Bidang Tanah (berkas/pbt.py) dan rutenya.

    python -m unittest uji.uji_pbt

Teks contohnya karangan, meniru hasil OCR lembar PBT: label "Nomor :",
"NIB :", "Luas :", letak tanah, dan batas-batas.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import pbt                                                # noqa: E402
from uji.uji_web import Dasar as DasarWeb                             # noqa: E402

TEKS_PBT = """
KEMENTERIAN AGRARIA DAN TATA RUANG / BADAN PERTANAHAN NASIONAL
PETA BIDANG TANAH
Nomor : 36 / 2025
Tanggal : 25-08-2025
NIB : 23.01.07.03.0O571
Luas : 1.349 M2
Desa/Kel : UJI SATU
Kecamatan : UJIKEC
Kabupaten : Bone Bolango
Penggunaan Tanah : Tanah Pekarangan
Batas-batas :
Utara : Jalan Desa
Timur : M. 622
Selatan : Sungai
Barat : Harun Saman
"""

DESA = [{"id": 11, "kecamatan_id": 3, "nama": "Uji Satu", "kecamatan": "Ujikec"},
        {"id": 12, "kecamatan_id": 4, "nama": "Uji Satu", "kecamatan": "Lainkec"},
        {"id": 13, "kecamatan_id": 3, "nama": "Uji Dua", "kecamatan": "Ujikec"}]


class UjiUrai(unittest.TestCase):
    def setUp(self):
        self.h = pbt.urai(TEKS_PBT, DESA)
        self.i = self.h["isian"]

    def test_identitas_peta(self):
        self.assertEqual(self.i["nomor_pbt"], "36/2025")
        self.assertEqual(self.i["tanggal_pbt"], "2025-08-25")
        self.assertEqual(self.i["nib"], "23.01.07.03.00571")     # huruf O dibaca 0

    def test_luas_ribuan_bertitik(self):
        self.assertEqual(self.i["luas_pbt"], 1349)

    def test_luas_desimal_dibulatkan(self):
        h = pbt.urai("Luas : 349,6 m²", [])
        self.assertEqual(h["isian"]["luas_pbt"], 350)
        self.assertTrue(any("dibulatkan" in x for x in h["peringatan"]))

    def test_batas_dan_penggunaan(self):
        self.assertEqual(self.i["batas_utara"], "Jalan Desa")
        self.assertEqual(self.i["batas_timur"], "M. 622")
        self.assertEqual(self.i["batas_selatan"], "Sungai")
        self.assertEqual(self.i["batas_barat"], "Harun Saman")
        self.assertEqual(self.i["penggunaan_sekarang"], "Tanah Pekarangan")

    def test_desa_dicocokkan_dengan_kecamatannya(self):
        self.assertEqual(self.i["desa_id"], 11)
        self.assertEqual(self.i["kecamatan"], 3)

    def test_desa_kembar_tanpa_kecamatan_tidak_ditebak(self):
        h = pbt.urai("Desa : Uji Satu", DESA)
        self.assertNotIn("desa_id", h["isian"])
        self.assertTrue(any("Uji Satu" in x for x in h["peringatan"]))

    def test_teks_kosong(self):
        h = pbt.urai("", DESA)
        self.assertEqual(h["isian"], {})
        self.assertTrue(h["peringatan"])


class UjiRute(DasarWeb):
    def test_urai_json(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")
        j = c.post("/berkas/pbt/urai", data={"teks": TEKS_PBT})
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.get_json()["isian"]["nib"], "23.01.07.03.00571")

    def test_perlu_masuk(self):
        j = self.klien().post("/berkas/pbt/urai", data={"teks": TEKS_PBT})
        self.assertNotEqual(j.status_code, 200)

    def test_teks_terlalu_panjang_ditolak(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")
        j = c.post("/berkas/pbt/urai", data={"teks": "x" * (pbt.BATAS_TEKS + 1)})
        self.assertEqual(j.status_code, 413)

    def test_kartu_pbt_di_formulir(self):
        isi = self.klien(masuk=True).get("/berkas/baru").get_data(as_text=True)
        self.assertIn('data-ocr="pbt"', isi)
        self.assertIn('data-ocr="aiw"', isi)


if __name__ == "__main__":
    unittest.main()
