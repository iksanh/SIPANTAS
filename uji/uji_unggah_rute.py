# -*- coding: utf-8 -*-
"""Uji rute unggah dokumen (berkas/rute/unggah.py) dan tampilannya.

    python -m unittest uji.uji_unggah_rute
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import db, unggah                                         # noqa: E402
from berkas.baca import ocr                                           # noqa: E402
from uji import contoh_unggah as c                                    # noqa: E402
from uji import uji_web                                               # noqa: E402

PDF = c.pdf_teks([c.TEKS_SPPF, c.TEKS_KK])


class Dasarunggah(uji_web.Dasar):
    # Dipinjam tanpa mengimpor nama Rbac, supaya uji Rbac tidak ikut terjalankan di sini.
    petugas = uji_web.Rbac.petugas
    buat_berkas = uji_web.Rbac.buat_berkas

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._dir_asli = unggah.DIR_UNGGAHAN
        unggah.DIR_UNGGAHAN = tempfile.mkdtemp(prefix="uji-unggahan-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(unggah.DIR_UNGGAHAN, ignore_errors=True)
        unggah.DIR_UNGGAHAN = cls._dir_asli
        super().tearDownClass()

    def unggah(self, klien, isi=PDF, nama="berkas.pdf", **tujuan):
        return klien.post("/unggah", data=dict(tujuan, berkas=(io.BytesIO(isi), nama)),
                          content_type="multipart/form-data")

    def hitung(self, bid):
        k = db.sambung()
        try:
            return [k.execute(f"SELECT COUNT(*) FROM {t} WHERE berkas_id=?", (bid,)).fetchone()[0]
                    for t in ("pihak", "bidang_tanah", "dokumen_pendukung")]
        finally:
            k.close()


class UjiRute(Dasarunggah):
    def test_unggah_titipan_lalu_simpan_berkas(self):
        a = self.klien(masuk=True)
        j = self.unggah(a, titipan="T-rute-1")
        self.assertEqual(j.status_code, 200, j.get_data(as_text=True))
        self.assertEqual([d["jenis_tebakan"] for d in j.get_json()["dokumen"]], ["sppf", "kk"])
        j = a.post("/berkas/baru", data={"status": "draf", "jenis_kegiatan": "baru",
                                         "penerima_nama": "Uji", "titipan": "T-rute-1"})
        bid = int(j.headers["Location"].split("/berkas/")[1].split("?")[0])
        k = db.sambung()
        try:
            r = k.execute("SELECT berkas_id, titipan FROM unggahan WHERE nama_asli='berkas.pdf' "
                          "ORDER BY id DESC").fetchone()
        finally:
            k.close()
        self.assertEqual((r["berkas_id"], r["titipan"]), (bid, None))

    def test_alur_jenis_lalu_ekstrak(self):
        a = self.klien(masuk=True)
        dok = self.unggah(a, titipan="T-rute-2").get_json()["dokumen"]
        self.assertEqual(a.get(f"/unggah/dok/{dok[0]['id']}/ekstrak").status_code, 409)
        j = a.post(f"/unggah/dok/{dok[0]['id']}/jenis", data={"jenis": "sppf", "status": "pasti"})
        self.assertEqual(j.status_code, 200)
        j = a.get(f"/unggah/dok/{dok[0]['id']}/ekstrak")
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.get_json()["hasil"]["isian"]["batas_utara"], "Tanah Hasan")
        g = a.get(f"/unggah/dok/{dok[0]['id']}/gambar")
        self.assertEqual(g.status_code, 200)
        self.assertTrue(g.data.startswith(b"\x89PNG"))

    def test_jenis_tidak_sah_400(self):
        a = self.klien(masuk=True)
        dok = self.unggah(a, titipan="T-rute-3").get_json()["dokumen"]
        j = a.post(f"/unggah/dok/{dok[0]['id']}/jenis", data={"jenis": "asing", "status": "pasti"})
        self.assertEqual(j.status_code, 400)

    def test_tidak_ada_tulisan_ke_berkas_sebelum_simpan(self):
        a = self.klien(masuk=True)
        bid = self.buat_berkas(a)
        sebelum = self.hitung(bid)
        dok = self.unggah(a, berkas_id=str(bid)).get_json()["dokumen"]
        a.post(f"/unggah/dok/{dok[0]['id']}/jenis", data={"jenis": "sppf", "status": "pasti"})
        a.get(f"/unggah/dok/{dok[0]['id']}/ekstrak")
        self.assertEqual(self.hitung(bid), sebelum)

    def test_unggahan_orang_lain_ditolak(self):
        pa, pb = self.petugas("unggah_a"), self.petugas("unggah_b")
        did = self.unggah(pa, titipan="T-rute-4").get_json()["dokumen"][0]["id"]
        self.assertEqual(pb.get(f"/unggah/dok/{did}/gambar").status_code, 404)
        self.assertEqual(pb.get(f"/unggah/dok/{did}/ekstrak").status_code, 404)
        self.assertEqual(pb.post(f"/unggah/dok/{did}/jenis",
                                 data={"jenis": "kk", "status": "pasti"}).status_code, 404)
        bid = self.buat_berkas(pa)
        did = self.unggah(pa, berkas_id=str(bid)).get_json()["dokumen"][0]["id"]
        self.assertEqual(pb.get(f"/unggah/dok/{did}/gambar").status_code, 403)
        self.assertEqual(self.unggah(pb, berkas_id=str(bid)).status_code, 403)

    def test_satu_file_rusak_lainnya_jalan(self):
        a = self.klien(masuk=True)
        j = self.unggah(a, isi=b"%PDF-1.4 rusak", nama="rusak.pdf", titipan="T-rute-5")
        self.assertEqual(j.status_code, 400)
        self.assertIn("rusak.pdf", j.get_json()["galat"])
        self.assertEqual(self.unggah(a, titipan="T-rute-5").status_code, 200)

    def test_tanpa_tujuan_400(self):
        a = self.klien(masuk=True)
        self.assertEqual(self.unggah(a).status_code, 400)

    def test_perlu_masuk(self):
        j = self.unggah(self.klien(), titipan="T-rute-6")
        self.assertNotEqual(j.status_code, 200)

    def test_ocr_tidak_tersedia(self):
        a = self.klien(masuk=True)
        with mock.patch.object(ocr, "TERSEDIA", False):
            j = self.unggah(a, titipan="T-rute-7")
        self.assertEqual(j.status_code, 503)
        self.assertIn("pip install", j.get_json()["galat"])


class UjiTampilan(Dasarunggah):
    def test_langkah_unggah_pertama_di_berkas_baru(self):
        h = self.klien(masuk=True).get("/berkas/baru").get_data(as_text=True)
        self.assertLess(h.index("Unggah dokumen"), h.index("Jenis permohonan"))
        self.assertIn('id="p-unggah"', h)
        self.assertRegex(h, r'name="titipan" value="[\w-]{16,}"')
        self.assertIn("data-unggah", h)
        self.assertIn("data-jenis=", h)
        self.assertIn("Surat Pernyataan Penguasaan Fisik", h)
        self.assertNotIn("Tidak terbaca", h)
        langkah = h[h.index('data-panel="p-unggah"'):h.index('data-panel="p-berkas"')]
        self.assertIn("boleh nanti", langkah)

    def test_unggah_di_tab_dokumen(self):
        a = self.klien(masuk=True)
        bid = self.buat_berkas(a)
        h = a.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn(f'data-berkas-id="{bid}"', h)
        self.assertNotIn('name="titipan"', h)
        self.assertNotIn('id="p-unggah"', h)

    def test_unggah_juga_di_tab_berkas(self):
        """Berkas yang sudah ada terbuka di tab Berkas; kartu yang hanya di tab
        Dokumen terlewat oleh petugas."""
        a = self.klien(masuk=True)
        bid = self.buat_berkas(a)
        h = a.get(f"/berkas/{bid}").get_data(as_text=True)
        panel = lambda p: h[h.index(f'<div class="panel" id="{p}">'):]  # noqa: E731
        berkas = panel("p-berkas")[:panel("p-berkas").index('<div class="panel" id="p-pihak">')]
        self.assertIn("data-unggah", berkas)
        self.assertIn("data-unggah", panel("p-dokumen"))
        ids = re.findall(r'id="(f_unggah[^"]*)"', h)
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2, "id medan file harus unik per kartu")

    def test_baca_saja_tanpa_unggah(self):
        pa, pb = self.petugas("tampil_a"), self.petugas("tampil_b")
        bid = self.buat_berkas(pa)
        j = pb.get(f"/berkas/{bid}")
        if j.status_code == 200:
            self.assertNotIn("data-unggah", j.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
