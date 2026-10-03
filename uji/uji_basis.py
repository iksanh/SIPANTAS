# -*- coding: utf-8 -*-
"""Uji lapisan konfigurasi dan penerjemah dialek.

Uji di sini tidak menyentuh basis data sungguhan: yang diperiksa penguraian
setelan dan penerjemahan SQL. Yang memastikan aplikasinya benar-benar jalan di
PostgreSQL adalah uji_web.py, dijalankan dua kali:

    python -m unittest uji.uji_web
    DB_URL=postgresql://panitia:sandi@host:5432/panitia_a python -m unittest uji.uji_web
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from berkas import basis, db, konfigurasi                            # noqa: E402


class Konfigurasi(unittest.TestCase):
    def setUp(self):
        self._asli = {n: os.environ.pop(n, None) for n in
                      ("DB_URL", "DB_JENIS", "DB_HOST", "DB_PORT", "DB_USER",
                       "DB_PASSWORD", "DB_NAMA")}

    def tearDown(self):
        for n, v in self._asli.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v

    def test_bawaan_sqlite(self):
        s = konfigurasi.sambungan()
        self.assertEqual(s.jenis, konfigurasi.JENIS_SQLITE)
        self.assertFalse(s.postgres)

    def test_url_postgres_terurai(self):
        os.environ["DB_URL"] = "postgresql://petugas:rahasia@10.1.2.3:6543/panitia"
        s = konfigurasi.sambungan()
        self.assertTrue(s.postgres)
        self.assertEqual(s.argumen["host"], "10.1.2.3")
        self.assertEqual(s.argumen["port"], 6543)
        self.assertEqual(s.argumen["user"], "petugas")
        self.assertEqual(s.argumen["password"], "rahasia")
        self.assertEqual(s.argumen["dbname"], "panitia")

    def test_sandi_bersandi_persen_dipulihkan(self):
        """Kata sandi ber-@ atau ber-/ harus disandikan di dalam URL; kalau
        tidak dipulihkan, sambungannya gagal tanpa sebab yang jelas."""
        os.environ["DB_URL"] = "postgresql://a:s%40ndi%2Faneh@h/d"
        self.assertEqual(konfigurasi.sambungan().argumen["password"], "s@ndi/aneh")

    def test_opsi_ssl_diteruskan(self):
        os.environ["DB_URL"] = "postgresql://a:b@h/d?sslmode=require"
        self.assertEqual(konfigurasi.sambungan().argumen["sslmode"], "require")

    def test_kata_sandi_tidak_ikut_tercetak(self):
        """sebutan dipakai di banner dan pesan galat — jangan sampai kata
        sandinya ikut muncul di layar atau di catatan log."""
        os.environ["DB_URL"] = "postgresql://a:sandi-sangat-rahasia@h/d"
        s = konfigurasi.sambungan()
        self.assertNotIn("sandi-sangat-rahasia", s.sebutan)
        self.assertNotIn("sandi-sangat-rahasia", repr(s))

    def test_setelan_per_bagian_tanpa_menyandikan(self):
        os.environ["DB_JENIS"] = "postgres"
        os.environ["DB_PASSWORD"] = "s@ndi/apa adanya"
        self.assertEqual(konfigurasi.sambungan().argumen["password"], "s@ndi/apa adanya")

    def test_skema_tak_dikenal_ditolak_terang_terangan(self):
        os.environ["DB_URL"] = "mysql://a:b@h/d"
        with self.assertRaises(ValueError) as ex:
            konfigurasi.sambungan()
        self.assertIn("mysql", str(ex.exception))

    def test_env_dibaca_dan_dikalahkan_variabel_lingkungan(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, ".env")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# komentar\nDB_URL=\"postgresql://dari:env@h/d\"\nKOSONG=\n")
        isi = konfigurasi._baca_env(p)
        self.assertEqual(isi["DB_URL"], "postgresql://dari:env@h/d")
        self.assertEqual(isi["KOSONG"], "")


class Dialek(unittest.TestCase):
    def test_penampung_diterjemahkan(self):
        self.assertEqual(basis.ke_persen("SELECT * FROM t WHERE a=? AND b=?", True),
                         "SELECT * FROM t WHERE a=%s AND b=%s")

    def test_tanya_di_literal_dibiarkan(self):
        sql = "SELECT 'a ? b' FROM t WHERE c=?"
        self.assertEqual(basis.ke_persen(sql, True), "SELECT 'a ? b' FROM t WHERE c=%s")

    def test_tanya_di_komentar_dibiarkan(self):
        sql = "SELECT a -- kenapa? entah\nFROM t WHERE b=?"
        self.assertEqual(basis.ke_persen(sql, True),
                         "SELECT a -- kenapa? entah\nFROM t WHERE b=%s")

    def test_persen_digandakan_saat_ada_nilai(self):
        """psycopg membaca % sebagai awal penampung saat menyulih nilai."""
        self.assertEqual(basis.ke_persen("SELECT 100 % ? FROM t", True),
                         "SELECT 100 %% %s FROM t")

    def test_persen_dibiarkan_saat_tanpa_nilai(self):
        self.assertEqual(basis.ke_persen("SELECT 100 % 7", False), "SELECT 100 % 7")

    def test_kutip_ganda_di_dalam_literal(self):
        sql = "SELECT 'it''s ?' FROM t WHERE a=?"
        self.assertEqual(basis.ke_persen(sql, True), "SELECT 'it''s ?' FROM t WHERE a=%s")

    # ----- DDL
    def test_id_auto_jadi_identity(self):
        pg = basis.ddl_postgres(db.SKEMA)
        self.assertIn("id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY", pg)
        self.assertNotIn("id INTEGER PRIMARY KEY,", pg)

    def test_kunci_asing_tetap_integer(self):
        """berkas_id INTEGER PRIMARY KEY REFERENCES ... bukan auto-increment —
        itu kunci utama yang sekaligus menunjuk tabel lain."""
        pg = basis.ddl_postgres(db.SKEMA)
        self.assertIn("berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id)", pg)

    def test_pragma_dibuang(self):
        self.assertNotIn("PRAGMA", basis.ddl_postgres(db.SKEMA))

    def test_waktu_bawaan_diterjemahkan(self):
        pg = basis.ddl_postgres(db.SKEMA)
        self.assertNotIn("datetime('now'", pg)
        self.assertIn("to_char(localtimestamp", pg)

    def test_tiap_perintah_ddl_utuh(self):
        """Pemecah yang tersandung komentar menghasilkan perintah terpotong —
        dan galatnya muncul jauh dari sebabnya."""
        potong = basis._pecah_perintah(basis.ddl_postgres(db.SKEMA))
        self.assertGreater(len(potong), 20)
        for p in potong:
            self.assertIn("CREATE", p.upper())

    def test_titik_koma_di_komentar_tidak_memecah(self):
        naskah = "CREATE TABLE a (x TEXT); -- catatan; masih komentar\nCREATE TABLE b (y TEXT);"
        self.assertEqual(len(basis._pecah_perintah(naskah)), 2)


class KueriSetara(unittest.TestCase):
    """Bentuk SQL yang harus dimengerti kedua basis data."""

    def test_upsert_memakai_on_conflict(self):
        sql = db.upsert("risalah", "berkas_id,nomor,tanggal")
        self.assertIn("ON CONFLICT (berkas_id) DO UPDATE SET", sql)
        self.assertIn("nomor=excluded.nomor", sql)
        self.assertNotIn("berkas_id=excluded.berkas_id", sql, "kunci tak perlu diperbarui")

    def test_jumlah_penampung_ikut_jumlah_kolom(self):
        sql = db.upsert("t", "a,b,c,d,e", kunci="a")
        self.assertEqual(sql.count("?"), 5)

    def test_tidak_ada_lagi_dialek_khas_sqlite(self):
        """Penjaga: satu INSERT OR REPLACE yang lolos akan gagal di PostgreSQL,
        dan gagalnya baru ketahuan saat petugas menyimpan berkas."""
        import pathlib
        import re

        akar = pathlib.Path(__file__).resolve().parent.parent / "berkas"
        pola = ("INSERT OR REPLACE", "INSERT OR IGNORE", "datetime('now'", ".lastrowid")
        # Yang sah menyebutnya: komentar, docstring yang menerangkan, dan DDL
        # (nilai bawaan kolom waktu) yang memang diterjemahkan ddl_postgres().
        sah = re.compile(r'DEFAULT \(datetime\(|"""|Menggantikan|Pengganti'
                         r'|hanya ada|Dipakai menggantikan')
        tersangka = []
        for p in akar.rglob("*.py"):
            for n, baris in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                bersih = baris.strip()
                if bersih.startswith("#") or sah.search(bersih):
                    continue
                tersangka += [f"{p.name}:{n} {x}" for x in pola if x in bersih]
        self.assertEqual(tersangka, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
