# -*- coding: utf-8 -*-
"""Isi DOCX yang dirakit harus tetap sama.

Uji ini merakit BAP, Risalah, dan SK untuk beberapa berkas contoh, lalu
membandingkan teksnya dengan rekaman di `uji/emas/dokumen/`.

Yang dijaga di sini adalah hal-hal yang tidak kelihatan di konteks: pengulangan
paragraf `{{*daftar}}`, penomoran a/i/romawi, paragraf bersyarat `{{?}}`/`{{!}}`,
baris ";" yang harus jadi "." di ujung daftar, tabel kosong yang harus dibuang,
dan ekor halaman yang kosong.

Lambat - beberapa detik per dokumen, jadi hanya berkas yang bentuknya
berbeda-beda yang dipakai (lihat dasar.berkas_contoh). Untuk pemeriksaan
sehari-hari yang cepat, jalankan uji_konteks saja.
"""
import unittest

from . import dasar


class UjiDokumen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._sambungan = dasar.sambung_salinan()
        cls.k = cls._sambungan.__enter__()
        cls.ids = dasar.berkas_contoh(cls.k)
        cls._singgahan = {}

    @classmethod
    def tearDownClass(cls):
        cls._sambungan.__exit__(None, None, None)

    @classmethod
    def teks(cls, berkas_id, jenis):
        """Teks dokumen, dirakit sekali lalu disinggahi.

        Dua uji di bawah memeriksa dokumen yang sama. Tanpa singgahan,
        perakitan yang mahal itu terjadi dua kali.
        """
        kunci = (berkas_id, jenis)
        if kunci not in cls._singgahan:
            cls._singgahan[kunci] = dasar.rakit_teks(cls.k, berkas_id, jenis)
        return cls._singgahan[kunci]

    def test_ada_berkas_contoh(self):
        self.assertTrue(
            self.ids,
            "Tidak ada berkas yang bisa dijadikan contoh. Isi minimal satu berkas dulu.")

    def test_dokumen_sama_dengan_acuan(self):
        for berkas_id in self.ids:
            for jenis in dasar.JENIS_DOKUMEN:
                nama = f"{berkas_id:04d}-{jenis}.txt"
                with self.subTest(berkas=berkas_id, jenis=jenis):
                    acuan = dasar.baca_emas("dokumen", nama)
                    if acuan is None:
                        self.skipTest(
                            f"Belum ada rekaman acuan untuk {nama}. "
                            "Rekam dengan: python -m uji.bikin_emas dokumen")

                    sekarang = self.teks(berkas_id, jenis)
                    self.assertEqual(
                        acuan, sekarang,
                        f"\n\nDokumen {jenis} untuk berkas {berkas_id} berbeda dari "
                        f"rekaman acuan.\n\n{dasar.beda(acuan, sekarang, nama)}\n"
                        "Kalau perubahan ini MEMANG dimaksudkan - misalnya tata "
                        "naskahnya berubah - rekam ulang dengan:\n"
                        "    python -m uji.bikin_emas dokumen\n")

    def test_tidak_ada_penanda_tersisa(self):
        """Tidak boleh ada `{{...}}` yang lolos ke dokumen jadi.

        Uji ini berdiri sendiri, tidak perlu rekaman acuan: penanda yang tidak
        tergantikan selalu salah, mau rekamannya sudah ada atau belum.
        """
        for berkas_id in self.ids:
            for jenis in dasar.JENIS_DOKUMEN:
                with self.subTest(berkas=berkas_id, jenis=jenis):
                    sisa = [b for b in self.teks(berkas_id, jenis).splitlines()
                            if "{{" in b or "}}" in b]
                    self.assertFalse(
                        sisa,
                        f"Penanda belum tergantikan di {jenis} berkas {berkas_id}:\n  "
                        + "\n  ".join(sisa[:5]))


if __name__ == "__main__":
    unittest.main()
