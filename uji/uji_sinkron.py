# -*- coding: utf-8 -*-
"""Uji tarik data dari aplikasi PHPT (berkas/sinkron.py, rute/sinkron.py).

    python -m unittest uji.uji_sinkron

Tiga lapis:
  Pemetaan   satu rekaman API -> isian formulir, di atas salinan basis data.
  Klien HTTP ambil() terhadap server tiruan: kepala Authorization dan galat.
  Rute       /sinkron/nib lewat klien Flask, dengan ambil() ditiru.
"""
import http.server
import json
import os
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import db, sinkron                                        # noqa: E402
from uji import dasar                                                 # noqa: E402
from uji.uji_web import Dasar as DasarWeb                             # noqa: E402


def rekaman(**ubah):
    """Bentuk persis jawaban GET /api/sinkron/tanah laravel_app."""
    r = {
        "cocok": "sebagian",
        "tanah": {
            "nib": "00571", "nomor_pbt": "36/2025", "tanggal_pbt": "2025-08-25",
            "luas": 349.0, "luas_surat": 342.5, "penggunaan_tanah": "Tanah Pekarangan",
            "rencana_penggunaan_rtrw": "Non Pertanian", "penggunaan_tanah_sk": "Rumah",
            "rtrw_kawasan": "Kawasan Permukiman", "kesesuaian_penggunaan_tanah": "Sesuai",
            "tgl_peta_analisis": "2025-09-08",
            "batas_utara": "Jalan", "batas_timur": "M.622", "batas_selatan": "Sungai",
            "batas_barat": "Harun Saman",
            "desa": {"id": "9999011001", "nama": "UJI SATU", "jenis": "DESA",
                     "kecamatan": {"id": "999901", "nama": "Ujikec"}},
        },
        "pemohon": {
            "nik": "7503135301850001", "nama": "MEGAWATI WANTOGIA",
            "tempat_lahir": "Gorontalo", "tanggal_lahir": "1986-01-13",
            "jenis_kelamin": "P", "pekerjaan": "Mengurus Rumah Tangga", "alamat_detail": "-",
            "desa": {"id": "9999011001", "nama": "UJI SATU", "jenis": "DESA",
                     "kecamatan": {"id": "999901", "nama": "Ujikec"},
                     "kabupaten": {"id": "9999", "nama": "KAB. BONE BOLANGO"},
                     "provinsi": {"id": "99", "nama": "GORONTALO"}},
            "kuasa": {"nama": "Saprina", "nik": "7505031605910001", "no_hp": "0811"},
        },
        "permohonan": {"nomor_registrasi": "REG-001-2026", "nomor_berkas": "1234",
                       "tahun_berkas": 2026, "tgl_pendaftaran": "2026-06-10",
                       "layanan": {"kode": "HM Perorangan", "nama": "HAK MILIK PERORANGAN"}},
        "riwayat_penguasaan": ["Bahwa satu  dua;", "Bahwa tiga; dan", "   "],
    }
    r.update(ubah)
    return r


class Pemetaan(unittest.TestCase):
    def setUp(self):
        self._cm = dasar.sambung_salinan()
        self.k = self._cm.__enter__()
        self.k.execute("INSERT INTO ref_kecamatan (nama, kode) VALUES ('Ujikec', '99.99.01')")
        kec = self.k.execute("SELECT id FROM ref_kecamatan WHERE kode='99.99.01'").fetchone()[0]
        self.k.execute("INSERT INTO ref_desa (kecamatan_id, nama, jenis) "
                       "VALUES (?, 'Uji Satu', 'Kelurahan')", (kec,))
        self.kec = kec
        self.desa = self.k.execute("SELECT id FROM ref_desa WHERE nama='Uji Satu'").fetchone()[0]

    def tearDown(self):
        self._cm.__exit__(None, None, None)

    def test_isian_berkas(self):
        h = sinkron.olah(self.k, rekaman(), "30.05.02.10.00571", "berkas")
        i = h["isian"]
        self.assertEqual(i["jenis_hak_dimohon"], "HM")
        self.assertEqual(i["nomor_berkas"], "1234/2026")
        self.assertEqual(i["penerima_nama"], "MEGAWATI WANTOGIA")
        self.assertEqual(i["penerima_ttl"], "Gorontalo, 13 Januari 1986")
        self.assertEqual(i["penerima_jenis_kelamin"], "Perempuan")
        self.assertEqual(i["penerima_jenis_subjek"], "perorangan")
        # jenis & ejaan desa diambil dari daftar di sini, kabupaten dirapikan
        self.assertEqual(i["penerima_alamat"], "Kelurahan Uji Satu, Kecamatan Ujikec, "
                                               "Kabupaten Bone Bolango, Provinsi Gorontalo")
        self.assertEqual((i["kuasa_nama"], i["kuasa_nik"]), ("Saprina", "7505031605910001"))
        self.assertEqual((i["kecamatan"], i["desa_id"]), (self.kec, self.desa))
        self.assertEqual(i["nib"], "30.05.02.10.00571")   # yang lengkap menang
        self.assertEqual((i["luas_pbt"], i["luas_surat"]), (349, 342))
        self.assertEqual(i["penggunaan_sekarang"], "Tanah Pekarangan")
        self.assertEqual(i["rencana_penggunaan"], "Non Pertanian")
        self.assertEqual(i["rtrw"], "Kawasan Permukiman")
        self.assertEqual(i["kesesuaian"], "Sesuai")
        self.assertNotIn("kesesuaian_lain", i)
        self.assertEqual(h["riwayat"], ["Bahwa satu dua", "Bahwa tiga"])
        self.assertTrue(any("dibulatkan" in p for p in h["peringatan"]))
        self.assertTrue(any("tidak persis sama" in p for p in h["peringatan"]))

    def test_isian_pradaftar(self):
        h = sinkron.olah(self.k, rekaman(), "00571", "pradaftar")
        i = h["isian"]
        self.assertEqual(i["jenis_hak"], "HM")
        self.assertEqual(i["pemohon_nama"], "MEGAWATI WANTOGIA")
        self.assertEqual(i["pemohon_telepon"], "0811")
        self.assertEqual(i["desa_id"], self.desa)
        self.assertNotIn("penerima_nama", i)
        self.assertEqual(h["riwayat"], [])

    def test_wakaf_badan_hukum_dan_kesesuaian_bebas(self):
        r = rekaman()
        r["permohonan"]["layanan"] = {"kode": "HW Badan Hukum", "nama": "HAK WAKAF BADAN HUKUM"}
        r["tanah"]["kesesuaian_penggunaan_tanah"] = "Sesuai seluas 200 m²"
        i = sinkron.olah(self.k, r, "00571")["isian"]
        self.assertEqual(i["jenis_hak_dimohon"], "WAKAF")
        self.assertEqual(i["penerima_jenis_subjek"], "badan_hukum")
        self.assertNotIn("kesesuaian", i)
        self.assertEqual(i["kesesuaian_lain"], "Sesuai seluas 200 m²")

    def test_hgu_tidak_dikenal_dan_desa_asing(self):
        r = rekaman()
        r["permohonan"]["layanan"] = {"kode": "HGU Perorangan", "nama": "HGU"}
        r["tanah"]["desa"] = {"id": "1", "nama": "Antah Berantah",
                              "kecamatan": {"id": "1", "nama": "Entah"}}
        h = sinkron.olah(self.k, r, "00571")
        self.assertNotIn("jenis_hak_dimohon", h["isian"])
        self.assertNotIn("desa_id", h["isian"])
        self.assertEqual(len([p for p in h["peringatan"]
                              if "padanan" in p or "tidak ditemukan" in p]), 2)

    def test_tanpa_pemohon_tidak_mengosongkan(self):
        h = sinkron.olah(self.k, rekaman(pemohon=None, permohonan=None), "00571")
        self.assertNotIn("penerima_nama", h["isian"])
        self.assertNotIn("penerima_alamat", h["isian"])
        self.assertTrue(all(v not in (None, "") for v in h["isian"].values()))

    def test_nib_terlalu_pendek(self):
        with self.assertRaises(sinkron.SinkronGagal):
            sinkron.cari(self.k, "ab", "berkas")


class _Tiruan(http.server.BaseHTTPRequestHandler):
    def do_GET(self):                                                   # noqa: N802
        if self.headers.get("Authorization") != "Bearer rahasia":
            self.send_response(401)
            body = b'{"message":"Kunci API tidak sah."}'
        else:
            self.send_response(200)
            body = json.dumps({"data": [{"path": self.path}]}).encode()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class KlienHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), _Tiruan)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _env(self, **v):
        return mock.patch.dict(os.environ, v)

    def test_kunci_benar(self):
        with self._env(SINKRON_URL=self.url + "/", SINKRON_KUNCI="rahasia"):
            data = sinkron.ambil("30.05 00571")
        self.assertEqual(data[0]["path"], "/api/sinkron/tanah?nib=30.05+00571")

    def test_kunci_salah(self):
        with self._env(SINKRON_URL=self.url, SINKRON_KUNCI="salah"):
            with self.assertRaisesRegex(sinkron.SinkronGagal, "Kunci API ditolak"):
                sinkron.ambil("00571")

    def test_server_mati(self):
        with self._env(SINKRON_URL="http://127.0.0.1:1", SINKRON_KUNCI="x"):
            with self.assertRaisesRegex(sinkron.SinkronGagal, "tidak bisa dihubungi"):
                sinkron.ambil("00571")

    def test_belum_diatur(self):
        with self._env(SINKRON_URL="", SINKRON_KUNCI=""):
            self.assertFalse(sinkron.aktif())
            with self.assertRaisesRegex(sinkron.SinkronGagal, "belum diatur"):
                sinkron.ambil("00571")


class Rute(DasarWeb):
    def test_tanpa_masuk_401_bukan_halaman_masuk(self):
        j = self.klien().get("/sinkron/nib?nib=00571")
        self.assertEqual(j.status_code, 401)

    def test_hasil_json(self):
        with mock.patch.object(sinkron, "ambil", return_value=[rekaman()]):
            j = self.klien(masuk=True).get("/sinkron/nib?nib=00571&untuk=pradaftar")
        self.assertEqual(j.status_code, 200)
        h = j.get_json()["hasil"][0]
        self.assertEqual(h["isian"]["pemohon_nama"], "MEGAWATI WANTOGIA")

    def test_galat_jadi_pesan(self):
        with mock.patch.object(sinkron, "ambil", side_effect=sinkron.SinkronGagal("putus")):
            j = self.klien(masuk=True).get("/sinkron/nib?nib=00571")
        self.assertEqual((j.status_code, j.get_json()["galat"]), (502, "putus"))

    def test_kartu_hanya_muncul_bila_diatur(self):
        c = self.klien(masuk=True)
        with mock.patch.object(sinkron, "aktif", return_value=False):
            self.assertNotIn(b"data-sinkron=", c.get("/berkas/baru").data)
        with mock.patch.object(sinkron, "aktif", return_value=True):
            self.assertIn(b'data-sinkron="berkas"', c.get("/berkas/baru").data)
            self.assertIn(b'data-sinkron="pradaftar"', c.get("/pradaftar/baru").data)


class PengaturanPhpt(DasarWeb):
    """Alamat dan kunci API PHPT diisi admin lewat Pengaturan, bukan .env."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), _Tiruan)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        super().tearDownClass()

    def setUp(self):
        # .env pemasangan ini tidak boleh ikut menentukan hasil uji
        self._env = mock.patch.dict(os.environ, {"SINKRON_URL": "", "SINKRON_KUNCI": ""})
        self._env.start()
        self.addCleanup(self._env.stop)
        k = db.sambung()
        k.execute("DELETE FROM pengaturan WHERE kunci LIKE 'sinkron_%'")
        k.commit()
        k.close()

    def _setelan(self):
        k = db.sambung()
        try:
            return sinkron.setelan(k)
        finally:
            k.close()

    def _petugas(self):
        a = self.klien(masuk=True)
        a.post("/pengguna", data={"nama": "Tugas", "username": "tugasphpt",
                                  "sandi": "rahasia123", "peran": "petugas"})
        c = self.app.test_client()
        c.get("/masuk")
        c.post("/masuk", data={"username": "tugasphpt", "sandi": "rahasia123"})
        c.segarkan()
        return c

    def test_admin_menyimpan_dan_kartu_muncul(self):
        c = self.klien(masuk=True)
        self.assertNotIn(b"data-sinkron=", c.get("/berkas/baru").data)
        j = c.post("/pengaturan/sinkron", data={"url": self.url + "/", "kunci": "rahasia"})
        self.assertEqual(j.status_code, 303)
        self.assertEqual(self._setelan(), (self.url, "rahasia"))
        self.assertIn(b'data-sinkron="berkas"', c.get("/berkas/baru").data)
        self.assertIn(b'data-sinkron="pradaftar"', c.get("/pradaftar/baru").data)

    def test_kunci_tidak_dicetak_dan_kosong_berarti_tetap(self):
        c = self.klien(masuk=True)
        c.post("/pengaturan/sinkron", data={"url": self.url, "kunci": "rahasia-sekali"})
        halaman = c.get("/pengaturan").get_data(as_text=True)
        self.assertIn('id="p-phpt"', halaman)
        self.assertNotIn("rahasia-sekali", halaman)
        c.post("/pengaturan/sinkron", data={"url": self.url, "kunci": ""})
        self.assertEqual(self._setelan()[1], "rahasia-sekali")
        c.post("/pengaturan/sinkron", data={"url": self.url, "hapus_kunci": "1"})
        self.assertEqual(self._setelan()[1], "")

    def test_alamat_tidak_sah_ditolak(self):
        c = self.klien(masuk=True)
        j = c.post("/pengaturan/sinkron", data={"url": "javascript:alert(1)", "kunci": "x"})
        self.assertIn("galat=", j.headers["Location"])
        self.assertEqual(self._setelan(), ("", ""))

    def test_petugas_ditolak(self):
        c = self._petugas()
        j = c.post("/pengaturan/sinkron", data={"url": self.url, "kunci": "rahasia"})
        # 403 dijawab aplikasi sebagai alihan ke daftar berkas dengan pesan galat
        self.assertEqual(j.status_code, 303)
        self.assertIn("hanya%20untuk%20admin", j.headers["Location"])
        self.assertEqual(self._setelan(), ("", ""))
        self.assertNotIn(b'id="p-phpt"', c.get("/pengaturan").data)

    def test_formulir_kantor_tidak_bisa_menyelipkan_setelan_phpt(self):
        c = self.klien(masuk=True)
        c.post("/pengaturan", data={"set_sinkron_url": "http://jahat.example"})
        self.assertEqual(self._setelan()[0], "")

    def test_uji_sambungan(self):
        c = self.klien(masuk=True)
        j = c.post("/pengaturan/sinkron", data={"url": self.url, "kunci": "rahasia",
                                                "aksi": "uji"})
        self.assertIn("baik=", j.headers["Location"])
        j = c.post("/pengaturan/sinkron", data={"url": self.url, "kunci": "salah",
                                                "aksi": "uji"})
        self.assertIn("galat=", j.headers["Location"])

    def test_isian_pengaturan_menang_atas_env(self):
        with mock.patch.dict(os.environ, {"SINKRON_URL": "http://lama:1",
                                          "SINKRON_KUNCI": "lama"}):
            self.assertEqual(self._setelan(), ("http://lama:1", "lama"))
            self.klien(masuk=True).post("/pengaturan/sinkron",
                                        data={"url": self.url, "kunci": "baru"})
            self.assertEqual(self._setelan(), (self.url, "baru"))


if __name__ == "__main__":
    unittest.main()
