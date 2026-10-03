# -*- coding: utf-8 -*-
"""Nilai penanda dan hasil pemeriksaan harus tetap sama.

Uji ini menjalankan `konteks.bangun()` dan `konteks.periksa()` untuk SETIAP
berkas di basis data, lalu membandingkan hasilnya dengan rekaman di
`uji/emas/konteks/`.

Di sinilah sebagian besar logika yang rawan itu terjaga: terbilang, luas
berhuruf, selisih ukuran, sapaan, kalimat otomatis, frasa akta ikrar wakaf,
dan daftar panitia. Kalau salah satunya berubah, selisihnya langsung menunjuk
nama penandanya.

Cepat - seluruh berkas selesai dalam hitungan detik.
"""
import unittest

from berkas.dokumen import konteks

from . import dasar


class UjiKonteks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._sambungan = dasar.sambung_salinan()
        cls.k = cls._sambungan.__enter__()
        cls.ids = dasar.semua_berkas(cls.k)

    @classmethod
    def tearDownClass(cls):
        cls._sambungan.__exit__(None, None, None)

    def test_ada_berkas(self):
        """Tanpa data, uji acuan tidak menguji apa pun - itu harus kelihatan."""
        self.assertTrue(
            self.ids,
            "Basis data kosong, jadi tidak ada yang bisa diuji. Isi minimal satu "
            "berkas lalu jalankan: python -m uji.bikin_emas")

    def test_konteks_sama_dengan_acuan(self):
        belum = []
        for berkas_id in self.ids:
            nama = f"{berkas_id:04d}.json"
            with self.subTest(berkas=berkas_id):
                sekarang = dasar.potret_konteks(self.k, berkas_id)
                self.assertIsNotNone(sekarang, f"Berkas {berkas_id} gagal dibangun")

                acuan = dasar.baca_emas("konteks", nama)
                if acuan is None:
                    belum.append(nama)
                    continue

                self.assertEqual(
                    acuan, sekarang,
                    f"\n\nBerkas {berkas_id} menghasilkan konteks yang berbeda dari "
                    f"rekaman acuan.\n\n{dasar.beda(acuan, sekarang, nama)}\n"
                    "Kalau perubahan ini MEMANG dimaksudkan, rekam ulang dengan:\n"
                    "    python -m uji.bikin_emas konteks\n")

        if belum:
            self.fail(
                f"{len(belum)} berkas belum punya rekaman acuan "
                f"(mis. {', '.join(belum[:3])}).\n"
                "Rekam dulu sekali dengan: python -m uji.bikin_emas konteks")

    def test_semua_berkas_bisa_dibangun(self):
        """Jaring pengaman paling dasar: tidak ada berkas yang bikin galat.

        Berguna juga untuk berkas yang baru dimasukkan dan belum ada acuannya.
        """
        for berkas_id in self.ids:
            with self.subTest(berkas=berkas_id):
                c, d = konteks.bangun(self.k, berkas_id)
                self.assertIsNotNone(c, f"Berkas {berkas_id} tidak terbaca")
                self.assertIsInstance(d, dict)
                self.assertIsInstance(konteks.periksa(self.k, berkas_id), list)


if __name__ == "__main__":
    unittest.main()
