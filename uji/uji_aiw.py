# -*- coding: utf-8 -*-
"""Uji pengurai teks Akta Ikrar Wakaf (berkas/aiw.py) dan rutenya.

    python -m unittest uji.uji_aiw

Teks contohnya karangan, meniru hasil OCR halaman 2 AIW/APAIW: label
"Nama :", "NIK :", dst. per baris, bagian WAKIF / NAZHIR / SAKSI, dan
salah baca khas OCR (huruf O di NIK, alamat terpotong ke baris berikutnya).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import aiw                                                # noqa: E402
from uji.uji_web import Dasar as DasarWeb                             # noqa: E402

TEKS_AIW = """
AKTA IKRAR WAKAF
Nomor : W.2 / 012 / K.30.02.04 / 2026
Pada hari ini Senin tanggal 12 Januari 2026 telah datang menghadap kepada saya
Charles Yusuf, S.Ag Kepala KUA Kecamatan Botupingge selaku Pejabat Pembuat Akta Ikrar Wakaf
I. WAKIF
Nama lengkap : HASAN ABDULLAH
Tempat/Tgl. Lahir : Gorontalo, 01-02-1960
NIK : 7503 O710 0260 0001
Jenis Kelamin : LAKI-LAKI
Agama : Islam
Pekerjaan : Petani
Alamat : Desa Ujisatu
RT/RW : 001/002
Kecamatan : Botupingge
II. NAZHIR
1. Nama : AMIN LATIF
   NIK : 7503071234560002
   Tempat dan tanggal lahir : Gorontalo, 3 Maret 1970
   Pekerjaan : Wiraswasta
   Alamat : Desa Ujidua
2. Nama : SITI RAHMA
   NIK : 7503071234560003
   Tempat Lahir : Limboto
   Tanggal Lahir : 4 April 1975
   Jenis Kelamin : Perempuan
   Pekerjaan : Guru
   Alamat : Desa Ujidua
III. SAKSI-SAKSI
1. Nama : YUSUF KARIM
   Pekerjaan : PNS
   Alamat : Desa Ujisatu
"""

TEKS_APAIW_SELAKU = """
AKTA PENGGANTI AKTA IKRAR WAKAF
Nomor: APAIW.1/007/2025
Dibuat pada tanggal 5-6-2025
Nama : RAHMAN PAKAYA
NIK : 7503071234560009
Alamat : Desa Ujitiga
selaku Wakif
Nama : MUSA DAI
Alamat : Desa Ujitiga
selaku Nazhir
"""


class UjiUrai(unittest.TestCase):
    def setUp(self):
        self.h = aiw.urai(TEKS_AIW)
        self.per = {}
        for p in self.h["pihak"]:
            self.per.setdefault(p["peran"], []).append(p)

    def test_akta(self):
        a = self.h["akta"]
        self.assertEqual(a["jenis"], "AIW")
        self.assertEqual(a["nomor"], "W.2/012/K.30.02.04/2026")
        self.assertEqual(a["tanggal"], "2026-01-12")
        self.assertEqual(a["pejabat"], "Charles Yusuf, S.Ag")
        self.assertEqual(a["wilayah_pejabat"], "Kecamatan Botupingge")

    def test_wakif(self):
        self.assertEqual(len(self.per["wakif"]), 1)
        w = self.per["wakif"][0]
        self.assertEqual(w["nama"], "HASAN ABDULLAH")
        self.assertEqual(w["nik"], "7503071002600001")      # huruf O dibaca 0
        self.assertEqual(w["ttl"], "Gorontalo, 01-02-1960")
        self.assertEqual(w["jenis_kelamin"], "Laki-laki")
        self.assertEqual(w["pekerjaan"], "Petani")
        self.assertEqual(w["alamat"], "Desa Ujisatu, RT/RW 001/002, Kecamatan Botupingge")

    def test_nazhir_berurutan(self):
        nz = self.per["nazhir"]
        self.assertEqual([p["nama"] for p in nz], ["AMIN LATIF", "SITI RAHMA"])
        self.assertEqual(nz[0]["ttl"], "Gorontalo, 3 Maret 1970")
        self.assertEqual(nz[1]["ttl"], "Limboto, 4 April 1975")   # tempat & tanggal terpisah
        self.assertEqual(nz[1]["jenis_kelamin"], "Perempuan")

    def test_saksi(self):
        self.assertEqual([p["nama"] for p in self.per["saksi"]], ["YUSUF KARIM"])

    def test_ppaiw_bukan_pihak(self):
        nama = [p["nama"] for p in self.h["pihak"]]
        self.assertNotIn("Charles Yusuf, S.Ag", nama)
        self.assertEqual(len(nama), 4)

    def test_selaku_menentukan_peran_dan_apaiw(self):
        h = aiw.urai(TEKS_APAIW_SELAKU)
        self.assertEqual(h["akta"]["jenis"], "APAIW")
        self.assertEqual(h["akta"]["nomor"], "APAIW.1/007/2025")
        self.assertEqual(h["akta"]["tanggal"], "2025-06-05")
        self.assertEqual([(p["peran"], p["nama"]) for p in h["pihak"]],
                         [("wakif", "RAHMAN PAKAYA"), ("nazhir", "MUSA DAI")])

    def test_nik_tidak_16_digit_diberi_peringatan(self):
        h = aiw.urai("WAKIF\nNama : ALI\nNIK : 7503 12")
        self.assertEqual(h["pihak"][0]["nik"], "750312")
        self.assertTrue(any("NIK" in x for x in h["peringatan"]))

    def test_teks_kosong(self):
        h = aiw.urai("")
        self.assertEqual(h["pihak"], [])
        self.assertTrue(h["peringatan"])


class UjiRute(DasarWeb):
    def test_urai_json(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")                 # memungut token CSRF halaman formulir
        j = c.post("/berkas/aiw/urai", data={"teks": TEKS_AIW})
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.get_json()["akta"]["nomor"], "W.2/012/K.30.02.04/2026")

    def test_perlu_masuk(self):
        c = self.klien()
        j = c.post("/berkas/aiw/urai", data={"teks": TEKS_AIW})
        self.assertNotEqual(j.status_code, 200)

    def test_teks_terlalu_panjang_ditolak(self):
        c = self.klien(masuk=True)
        c.get("/berkas/baru")
        j = c.post("/berkas/aiw/urai", data={"teks": "x" * (aiw.BATAS_TEKS + 1)})
        self.assertEqual(j.status_code, 413)

    def test_kartu_aiw_di_formulir_baru(self):
        c = self.klien(masuk=True)
        isi = c.get("/berkas/baru").get_data(as_text=True)
        self.assertIn('data-ocr="aiw"', isi)
        # slot Akta Ikrar Wakaf belum tampil di berkas baru (bawaan HM), jadi
        # kartunya membawa medan tersembunyi supaya isiannya tetap tersimpan
        self.assertIn('name="baku_nomor_akta_ikrar"', isi)


if __name__ == "__main__":
    unittest.main()
