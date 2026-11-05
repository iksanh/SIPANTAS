# -*- coding: utf-8 -*-
"""Uji pengurai KTP (berkas/baca/jenis/ktp.py) dan pemeriksaan NIK (periksa.py).

    python -m unittest uji.uji_unggah_ktp
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas.baca import periksa                                       # noqa: E402
from berkas.baca.jenis import ktp                                     # noqa: E402
from uji.contoh_unggah import TEKS_KTP                                # noqa: E402


class UjiKtp(unittest.TestCase):
    def test_urai_ktp_lengkap(self):
        h = ktp.urai(TEKS_KTP)
        self.assertEqual(h["isian"], {})
        self.assertEqual(h["dokumen"], [])
        self.assertEqual(h["peringatan"], [])
        self.assertEqual(len(h["pihak"]), 1)
        p = h["pihak"][0]
        self.assertEqual(p["nama"], "SITI AMINAH")
        self.assertEqual(p["nik"], "7503074512900001")
        self.assertEqual(p["ttl"], "Suwawa, 05-12-1990")
        self.assertEqual(p["jenis_kelamin"], "Perempuan")
        self.assertEqual(p["pekerjaan"], "Petani/Pekebun")
        for bagian in ("Dusun II", "RT 001/RW 002", "Bubeya", "Suwawa"):
            self.assertIn(bagian, p["alamat"])

    def test_nik_salah_baca_ocr(self):
        h = ktp.urai(TEKS_KTP.replace("NIK : 7503074512900001", "NIK : 75O3O7 4512 9OOOO1"))
        self.assertEqual(h["pihak"][0]["nik"], "7503074512900001")
        h = ktp.urai(TEKS_KTP.replace("NIK : 7503074512900001", "NIK : 75030745129"))
        self.assertEqual(h["pihak"][0]["nik"], "")
        self.assertTrue(any("16" in x for x in h["peringatan"]), h["peringatan"])

    def test_label_tak_terbaca_dikosongkan(self):
        h = ktp.urai(TEKS_KTP.replace("Pekerjaan : PETANI/PEKEBUN\n", ""))
        self.assertEqual(h["pihak"][0]["pekerjaan"], "")


class UjiPeriksa(unittest.TestCase):
    NIK = "7503074512900001"

    def test_periksa_nik_cocok(self):
        self.assertEqual(periksa.nik(self.NIK, "Suwawa, 05-12-1990", "Perempuan"), [])

    def test_periksa_tanggal_tidak_cocok(self):
        p = periksa.nik(self.NIK, "Suwawa, 06-12-1990", "Perempuan")
        self.assertEqual(len(p), 1)
        self.assertIn("tanggal lahir", p[0])

    def test_periksa_jenis_kelamin_tidak_cocok(self):
        p = periksa.nik(self.NIK, "Suwawa, 05-12-1990", "Laki-laki")
        self.assertEqual(len(p), 1)
        self.assertIn("jenis kelamin", p[0])

    def test_rapikan_nik(self):
        self.assertEqual(periksa.rapikan_nik("75O3O7 4512 9OOOO1"), self.NIK)
        self.assertEqual(periksa.rapikan_nik("1234"), "")


if __name__ == "__main__":
    unittest.main()
