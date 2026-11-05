# -*- coding: utf-8 -*-
"""Uji penyimpanan unggahan (berkas/unggah.py) dan tabelnya.

    python -m unittest uji.uji_unggah_simpan
"""
import datetime as dt
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import db, unggah                                         # noqa: E402
from uji import contoh_unggah as c                                    # noqa: E402
from uji.uji_web import Dasar                                         # noqa: E402

PDF = c.pdf_teks([c.TEKS_SPPF, c.TEKS_KK])


class UjiSimpan(Dasar):
    def setUp(self):
        self._dir_asli = unggah.DIR_UNGGAHAN
        unggah.DIR_UNGGAHAN = tempfile.mkdtemp(prefix="uji-unggahan-")
        self.k = db.sambung()
        self.uid = self.k.execute("SELECT id FROM pengguna WHERE username='admin'").fetchone()[0]

    def tearDown(self):
        self.k.rollback()
        self.k.close()
        shutil.rmtree(unggah.DIR_UNGGAHAN, ignore_errors=True)
        unggah.DIR_UNGGAHAN = self._dir_asli

    def _jumlah(self, tabel):
        return self.k.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]

    def test_simpan_membuat_baris_dan_file(self):
        h = unggah.simpan(self.k, "berkas.pdf", PDF, self.uid, None, "T-simpan")
        self.assertEqual([(d["hal_awal"], d["jenis_tebakan"]) for d in h["dokumen"]],
                         [(1, "sppf"), (2, "kk")])
        self.assertEqual(h["dokumen"][1]["label"], "Kartu Keluarga")
        self.assertFalse(h["kembar"])
        u = self.k.execute("SELECT * FROM unggahan WHERE id=?", (h["id"],)).fetchone()
        self.assertEqual(u["jml_halaman"], 2)
        self.assertTrue(os.path.isfile(os.path.join(unggah.DIR_UNGGAHAN, u["nama_file"])))
        d = unggah.dokumen(self.k, h["dokumen"][0]["id"])
        self.assertIn("PENGUASAAN FISIK", d["teks"])
        self.assertEqual(d["titipan"], "T-simpan")

    def test_kembar_ditandai(self):
        unggah.simpan(self.k, "a.pdf", PDF, self.uid, None, "T-kembar")
        h = unggah.simpan(self.k, "b.pdf", PDF, self.uid, None, "T-kembar")
        self.assertTrue(h["kembar"])

    def test_tidak_menyentuh_tabel_berkas(self):
        sebelum = [self._jumlah(t) for t in ("pihak", "bidang_tanah", "dokumen_pendukung")]
        unggah.simpan(self.k, "berkas.pdf", PDF, self.uid, None, "T-utuh")
        self.assertEqual([self._jumlah(t) for t in ("pihak", "bidang_tanah", "dokumen_pendukung")],
                         sebelum)

    def test_setel_jenis(self):
        h = unggah.simpan(self.k, "berkas.pdf", PDF, self.uid, None, "T-jenis")
        did = h["dokumen"][0]["id"]
        unggah.setel_jenis(self.k, did, "kk", "pasti")
        d = unggah.dokumen(self.k, did)
        self.assertEqual((d["jenis"], d["status"]), ("kk", "pasti"))
        unggah.setel_jenis(self.k, did, None, "diabaikan")
        self.assertEqual(unggah.dokumen(self.k, did)["status"], "diabaikan")
        for jenis in ("tidak_terbaca", "asing"):
            with self.assertRaises(ValueError):
                unggah.setel_jenis(self.k, did, jenis, "pasti")
        with self.assertRaises(ValueError):
            unggah.setel_jenis(self.k, did, "kk", "diterapkan-asal")

    def test_tautkan_titipan(self):
        lain = db.sisip_id(self.k, "INSERT INTO pengguna (nama,username,sandi_hash,peran) "
                                   "VALUES ('Lain','lain_tautkan','x','petugas')")
        unggah.simpan(self.k, "a.pdf", PDF, self.uid, None, "T1")
        unggah.simpan(self.k, "b.pdf", c.pdf_teks([c.TEKS_KTP]), self.uid, None, "T1")
        unggah.simpan(self.k, "c.pdf", c.pdf_teks([c.TEKS_LAIN]), lain, None, "T1")
        bid = db.sisip_id(self.k, "INSERT INTO berkas (jenis_hak_dimohon,dibuat_oleh) "
                                  "VALUES ('HM', ?)", (self.uid,))
        self.assertEqual(unggah.tautkan(self.k, "T1", bid, self.uid), 2)
        baris = self.k.execute("SELECT berkas_id, titipan FROM unggahan "
                               "WHERE pengguna_id=?", (self.uid,)).fetchall()
        self.assertTrue(all(r["berkas_id"] == bid and r["titipan"] is None for r in baris))

    def test_hapus_semua_membuang_file(self):
        bid = db.sisip_id(self.k, "INSERT INTO berkas (jenis_hak_dimohon,dibuat_oleh) "
                                  "VALUES ('HM', ?)", (self.uid,))
        h = unggah.simpan(self.k, "a.pdf", PDF, self.uid, bid, None)
        f = self.k.execute("SELECT nama_file FROM unggahan WHERE id=?", (h["id"],)).fetchone()[0]
        unggah.hapus_semua(self.k, bid)
        self.assertFalse(os.path.exists(os.path.join(unggah.DIR_UNGGAHAN, f)))
        self.assertEqual(self.k.execute("SELECT COUNT(*) FROM unggahan WHERE berkas_id=?",
                                        (bid,)).fetchone()[0], 0)

    def test_titipan_lama_dibersihkan(self):
        lama = unggah.simpan(self.k, "a.pdf", PDF, self.uid, None, "T-lama")
        baru = unggah.simpan(self.k, "b.pdf", c.pdf_teks([c.TEKS_KTP]), self.uid, None, "T-baru")
        delapan = (dt.datetime.now() - dt.timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
        self.k.execute("UPDATE unggahan SET dibuat=? WHERE id=?", (delapan, lama["id"]))
        f_lama, f_baru = [self.k.execute("SELECT nama_file FROM unggahan WHERE id=?",
                                         (x["id"],)).fetchone()[0] for x in (lama, baru)]
        self.assertEqual(unggah.bersihkan_titipan(self.k), 1)
        self.assertFalse(os.path.exists(os.path.join(unggah.DIR_UNGGAHAN, f_lama)))
        self.assertTrue(os.path.exists(os.path.join(unggah.DIR_UNGGAHAN, f_baru)))
        self.assertIsNone(unggah.dokumen(self.k, lama["dokumen"][0]["id"]))


if __name__ == "__main__":
    unittest.main()
