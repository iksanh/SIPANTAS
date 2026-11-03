# -*- coding: utf-8 -*-
"""Tata naskah Hak Guna Bangunan untuk badan hukum (jenis hak HGBBH).

Sama seperti uji_hak_pakai_pemerintah: berkasnya dibuat dari nol di basis data
kosong lewat formulir web, jadi yang diuji sekaligus isian formulirnya dan
dokumen yang dirakit dari isian itu. Data pemohon asli tidak disentuh.

    python -m unittest uji.uji_hgb_badan_hukum
"""
import unittest

from berkas import db
from berkas.dokumen import konteks, templat, terbitkan

from . import dasar
from .uji_web import Dasar as DasarWeb

NAMA = "PT. Maju Bersama Uji"
KEDUDUKAN = "Kota Gorontalo, Provinsi Gorontalo"
KEDUDUKAN_SINGKAT = "Kota Gorontalo"
NOTARIS = "Notaris Uji, S.H., M.Kn."
PENGESAHAN = "AHU-0012345.AH.01.01.TAHUN 2025"
OLEH = "Menteri Hukum dan Hak Asasi Manusia Republik Indonesia"
NIB_OSS = "1234567890123"
WAKIL, JABATAN = "Budi Direktur Uji", "Direktur"
KUASA = "Kuasa Uji"
JALAN = "Jalan Uji Nomor 5"
ASAL = ("tanah yang sudah bersertipikat Sertipikat Hak Milik Nomor 00123/Tunas Baru seluas "
        "1.500 m² yang telah dilepaskan haknya berdasarkan Akta Pernyataan Pelepasan Hak Atas "
        "Tanah Nomor 05 tanggal 2 Februari 2026")
DASAR_PEROLEHAN = "Akta Pernyataan Pelepasan Hak Atas Tanah Nomor 05 tanggal 2 Februari 2026"
TATA_RUANG = ("Surat Pernyataan Usaha Mikro atau Usaha Kecil Terkait Tata Ruang tanggal 15 "
              "Januari 2026 yang ditandatangani oleh Budi Direktur Uji selaku Direktur")
RIWAYAT = [
    "Bahwa bidang tanah yang dimohon sebelumnya dikuasai oleh Penjual Uji sejak tahun 2020 "
    "berdasarkan Sertipikat Hak Milik Nomor 00123/Tunas Baru",
    "Bahwa selanjutnya bidang tanah yang dimohon beralih kepada PT. Maju Bersama Uji sejak "
    "tahun 2026 berdasarkan " + DASAR_PEROLEHAN,
]

# Nilai berkas contoh (PT Sinar Berkah Tinelo) yang dipakai membangun template.
# Tak satu pun boleh tersisa: kalau tersisa, ada kalimat contoh yang lupa diganti.
SISA_CONTOH = ["Sinar Berkah", "Tinelo", "Agus Alimun", "Salma", "Igirisa", "Dutohe",
               "4421", "2116", "59/2025", "58/2025", "Giannini", "Zulkifli", "Abaidata",
               "SILVA", "FIRMANSYAH", "ASDA", "BINTANG", "Rahmat Iswanto", "02/SK-75.03",
               "AHU-0050187", "3007250003557", "Real Estat", "Sardjono", "Erwin",
               "Wirnawat", "Marleni", "Trezy", "Mega Putri", "Perumahan", "Permukiman",
               "18 Februari 2026", "23 Februari 2026", "30 Oktober 2025", "6/2025",
               "Kabila", "01046", "02020", "yang …", "Kepala …", "penerima ..."]


def _tanpa_penyambung():
    asli = terbitkan._kata_penyambung
    terbitkan._kata_penyambung = lambda *a, **kw: 0
    return asli


class HgbBadanHukum(DasarWeb):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._penyambung = _tanpa_penyambung()
        k = db.sambung()
        try:
            kec = db.sisip_id(k, "INSERT INTO ref_kecamatan (nama) VALUES (?)", ("Suwawa Uji",))
            cls.desa = db.sisip_id(
                k, "INSERT INTO ref_desa (kecamatan_id,nama,jenis,nama_pejabat) "
                   "VALUES (?,?,?,?)", (kec, "Tunas Baru", "Desa", "Rahmat Uji"))
            cls.panitia = db.sisip_id(
                k, "INSERT INTO ref_panitia (nomor_sk,tanggal_sk) VALUES (?,?)",
                ("77/SK-75.03/I/2026", "2026-01-05"))
            for i, (nama, jabatan, peran) in enumerate((
                    ("KETUA UJI, S.H.", "Kepala Seksi Penetapan Hak dan Pendaftaran",
                     "Ketua merangkap Anggota"),
                    ("WAKIL UJI, S.T.", "Kepala Seksi Survei dan Pemetaan", "Anggota"),
                    ("TATA UJI, S.T.", "Kepala Seksi Penataan dan Pemberdayaan", "Anggota"),
                    ("SEKRETARIS UJI, S.H.", "Penata Pertanahan Pertama",
                     "Sekretaris merangkap Anggota"))):
                k.execute("INSERT INTO ref_panitia_anggota (panitia_id,urut,nama,nip,jabatan,"
                          "peran,pendapat_baku) VALUES (?,?,?,?,?,?,?)",
                          (cls.panitia, i, nama, f"1980010120090110{i:02d}", jabatan, peran,
                           f"Pendapat baku {nama}"))
            k.commit()
        finally:
            k.close()

    @classmethod
    def tearDownClass(cls):
        terbitkan._kata_penyambung = cls._penyambung
        super().tearDownClass()

    # ------------------------------------------------------------ pembantu
    def _form(self, **lain):
        data = {
            "status": "draf", "jenis_kegiatan": "baru", "jenis_hak_dimohon": "HGBBH",
            "nomor_berkas": "321/2026", "tanggal_permohonan": "2026-01-29",
            "penerima_jenis_subjek": "badan_hukum", "penerima_nama": NAMA,
            "bh_bentuk": "PT", "bh_kedudukan": KEDUDUKAN,
            "bh_akta_nomor": "12", "bh_akta_tanggal": "2025-03-10", "bh_notaris": NOTARIS,
            "bh_notaris_kota": "Kota Gorontalo",
            "bh_pengesahan_nomor": PENGESAHAN, "bh_pengesahan_tanggal": "2025-03-12",
            "bh_pengesahan_oleh": OLEH, "bh_nib": NIB_OSS,
            "bh_bidang_usaha": "Perdagangan Besar",
            "bh_wakil_nama": WAKIL, "bh_wakil_jabatan": JABATAN,
            "kuasa_nama": KUASA,
            "lain_peran": ["pemilik_sebelumnya"], "lain_nama": ["Penjual Uji"],
            "lain_nik": [""], "lain_ttl": [""], "lain_pekerjaan": [""], "lain_alamat": [""],
            "desa_id": str(self.desa), "nomor_pbt": "77/2026", "tanggal_pbt": "2026-01-20",
            "nib": "30.05.10.01.00888", "luas_pbt": "1500",
            "batas_utara": "Jalan Trans Sulawesi", "batas_timur": "Tanah Negara",
            "batas_selatan": "Sungai", "batas_barat": "Kantor Desa",
            "penggunaan_sekarang": "Pertokoan", "rencana_penggunaan": "Pertokoan",
            "rtrw": "Kawasan Perdagangan dan Jasa", "kesesuaian": "Sesuai",
            "tanggal_peta_analisis": "2026-01-25",
            "jalan": JALAN, "jenis_tanah": "Non Pertanian",
            "asal_tanah_uraian": ASAL, "dasar_perolehan": DASAR_PEROLEHAN,
            "riwayat_uraian": RIWAYAT, "riwayat_bukti": ["", ""],
            "baku_permohonan": "Surat permohonan hak tanggal 29 Januari 2026",
            "baku_asli_permohonan": "Asli",
            "baku_sppf": "Surat Pernyataan Penguasaan Fisik Bidang Tanah tanggal 20 Januari "
                         "2026 yang ditandatangani oleh " + WAKIL,
            "baku_asli_sppf": "Asli",
            "baku_tata_ruang": TATA_RUANG, "baku_asli_tata_ruang": "Asli",
            "dokumen_uraian": ["Akta Pendirian Perseroan Terbatas Nomor 12"],
            "dokumen_keaslian": ["Fotokopi"], "dokumen_kategori": ["tambahan"],
            "tanggal_surat_tugas": "2026-02-05", "tanggal_bap": "2026-02-10",
            "panitia_id": str(self.panitia),
            "risalah_nomor": "9/2026", "risalah_tanggal": "2026-02-19",
            "risalah_kesimpulan": "dikabulkan", "risalah_jangka": "30",
            "sk_nomor": "5/HGB/BPN-75.03/II/2026", "sk_tanggal": "2026-02-24",
        }
        data.update(lain)
        return data

    def _berkas(self, **lain):
        c = self.klien(masuk=True)
        j = c.post("/berkas/baru", data=self._form(**lain))
        self.assertEqual(j.status_code, 303, j.get_data(as_text=True)[:300])
        bid = int(j.headers["Location"].split("/berkas/")[1].split("?")[0])
        return c, bid

    def _teks(self, bid, jenis):
        k = db.sambung()
        try:
            return dasar.rakit_teks(k, bid, jenis)
        finally:
            k.close()

    def _muat(self, bid):
        k = db.sambung()
        try:
            return konteks.muat(k, bid)
        finally:
            k.close()

    def _bersih(self, teks, jenis):
        self.assertFalse("{{" in teks, f"penanda tersisa di {jenis}: "
                                       f"{teks[teks.find('{{'):teks.find('{{') + 60]!r}")
        sisa = [x for x in SISA_CONTOH if x in teks]
        self.assertEqual(sisa, [], f"isi berkas contoh tersisa di {jenis}")

    # ------------------------------------------------------- jenis hak
    def test_jenis_hak_dan_template(self):
        k = db.sambung()
        try:
            r = k.execute("SELECT * FROM ref_jenis_hak WHERE kode='HGBBH'").fetchone()
            hgb = k.execute("SELECT * FROM ref_jenis_hak WHERE kode='HGB'").fetchone()
            kode = {x[0] for x in k.execute("SELECT kode FROM ref_jenis_hak")}
        finally:
            k.close()
        self.assertEqual(kode, {x[0] for x in db.JENIS_HAK})
        self.assertIsNotNone(r, "jenis hak HGBBH belum ada")
        self.assertEqual(r["nama"], "Hak Guna Bangunan Badan Hukum")
        self.assertEqual(r["varian_template"], "hgbbh")
        self.assertEqual(r["kode_sk"], "HGB")               # bernomor bersama HGB biasa
        self.assertEqual(r["ada_jangka_waktu"], 1)
        self.assertEqual(r["subjek_boleh"], "badan_hukum")
        # HGB biasa tidak berubah: tetap memakai template baku
        self.assertEqual(hgb["varian_template"], "")
        self.assertEqual(hgb["subjek_boleh"], "perorangan,badan_hukum")
        self.assertEqual(templat.kunci("risalah", "hgbbh"), "risalah-hgbbh")
        self.assertEqual(templat.kunci("sk", "hgbbh"), "sk-hgbbh")
        # BAP sama dengan BAP baku
        self.assertEqual(templat.kunci("bap", "hgbbh"), "bap")
        self.assertNotIn("bap-hgbbh", templat.JENIS)

    def test_migrasi_menyisipkan_ke_basis_data_lama(self):
        k = db.sambung()
        try:
            # basis data lama: barisnya belum ada (berkas uji lain yang merujuknya
            # dibiarkan, jadi pemeriksaan kunci tamu dimatikan sebentar)
            k.execute("PRAGMA foreign_keys=OFF")
            k.execute("DELETE FROM ref_jenis_hak WHERE kode='HGBBH'")
            db.migrasi(k)
            k.execute("PRAGMA foreign_keys=ON")
            r = k.execute("SELECT varian_template FROM ref_jenis_hak WHERE kode='HGBBH'"
                          ).fetchone()
            kolom = db.kolom_tabel(k, "bidang_tanah")
        finally:
            k.close()
        self.assertEqual(r["varian_template"], "hgbbh")
        for x in ("jalan", "asal_tanah_uraian", "dasar_perolehan"):
            self.assertIn(x, kolom)

    # --------------------------------------------------------- formulir
    def test_isian_hgb_tampil_dan_tersimpan(self):
        c, bid = self._berkas()
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        for nama in ("bh_bidang_usaha", "bh_notaris_kota", "bh_pengesahan_oleh",
                     "jalan", "jenis_tanah", "asal_tanah_uraian", "dasar_perolehan",
                     "baku_tata_ruang"):
            self.assertIn(f'name="{nama}"', halaman)
            # satu medan satu kali: tidak tertimpa salinan tersembunyinya
            self.assertEqual(halaman.count(f'name="{nama}"'), 1, nama)
        self.assertNotIn('type="hidden" name="asal_tanah_uraian"', halaman)
        d = self._muat(bid)
        bh = konteks.penerima_hak(d)["badan_hukum"]
        self.assertEqual(bh["bidang_usaha"], "Perdagangan Besar")
        self.assertEqual(bh["pengesahan_oleh"], OLEH)
        self.assertEqual(d["tanah"]["jalan"], JALAN)
        self.assertEqual(d["tanah"]["jenis_tanah"], "Non Pertanian")
        self.assertEqual(d["tanah"]["asal_tanah_uraian"], ASAL)
        self.assertEqual(d["tanah"]["dasar_perolehan"], DASAR_PEROLEHAN)
        self.assertIn(TATA_RUANG, [r["uraian"] for r in d["dokumen"]])

    def test_isian_tidak_tampil_di_hgb_biasa_tetapi_tidak_hilang(self):
        c, bid = self._berkas()
        c.post(f"/berkas/{bid}", data=self._form(jenis_hak_dimohon="HGB"))
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn('type="hidden" name="asal_tanah_uraian"', halaman)
        self.assertIn('type="hidden" name="jalan"', halaman)
        self.assertNotIn('name="baku_tata_ruang"', halaman)
        d = self._muat(bid)
        self.assertEqual(d["tanah"]["asal_tanah_uraian"], ASAL)
        self.assertEqual(d["tanah"]["jalan"], JALAN)
        self.assertEqual(konteks.penerima_hak(d)["badan_hukum"]["bidang_usaha"],
                         "Perdagangan Besar")

    # --------------------------------------------------------- dokumen
    def test_bap_memakai_bap_baku(self):
        _, bid = self._berkas()
        bap = self._teks(bid, "bap")
        self.assertNotIn("{{", bap)
        self.assertIn(NAMA, bap)
        self.assertIn("KETUA UJI, S.H.", bap)

    def test_risalah(self):
        _, bid = self._berkas()
        ris = self._teks(bid, "risalah")
        self._bersih(ris, "risalah")
        self.assertIn("NOMOR : 9/2026", ris)
        self.assertIn("Permohonan Hak Guna Bangunan atas Nama : " + NAMA, ris)
        self.assertIn("77/SK-75.03/I/2026", ris)
        self.assertIn("5 (lima) orang", ris)
        self.assertIn("Nomor : 12 tanggal 10 Maret 2025", ris)
        self.assertIn(f"Nomor : {PENGESAHAN} tanggal 12 Maret 2025", ris)
        self.assertIn(NIB_OSS, ris)
        self.assertIn("Perdagangan Besar", ris)
        self.assertIn(JALAN, ris)
        self.assertIn("Tunas Baru", ris)
        self.assertIn("1.500 m²", ris)
        self.assertIn("No.77/2026, Tanggal 20 Januari 2026", ris)
        self.assertIn("30 Tahun", ris)
        self.assertIn("Pertokoan", ris)
        # data pendukung
        self.assertIn("Asli Surat permohonan hak tanggal 29 Januari 2026", ris)
        self.assertIn("Asli " + TATA_RUANG, ris)
        self.assertIn("Fotokopi Akta Pendirian Perseroan Terbatas Nomor 12", ris)
        self.assertIn("Asli Peta Bidang Tanah Nomor : 77/2026", ris)
        self.assertIn("Berita Acara Pemeriksaan Lapang Tanggal 10 Februari 2026", ris)
        # telaah subjek
        self.assertIn(f"Bahwa pemohon yaitu {NAMA} yang berkedudukan di {KEDUDUKAN_SINGKAT}, "
                      f"adalah Badan Hukum yang didirikan berdasarkan Akta Pendirian Nomor 12 "
                      f"tanggal 10 Maret 2025 yang dibuat di hadapan {NOTARIS} selaku Notaris "
                      f"di Kota Gorontalo, yang telah mendapatkan pengesahan dari {OLEH}", ris)
        self.assertIn("Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas", ris)
        # telaah objek
        self.assertIn("Tanah Negara yang berasal dari " + ASAL, ris)
        for r in RIWAYAT:
            self.assertIn(r, ris)
        self.assertIn(f"yang diperoleh pemohon dari Penjual Uji berdasarkan {DASAR_PEROLEHAN}",
                      ris)
        self.assertIn("berada dalam Kawasan Perdagangan dan Jasa", ris)
        self.assertIn("dilengkapi dengan " + TATA_RUANG, ris)
        self.assertIn("penggunaan tanahnya untuk Non Pertanian", ris)
        self.assertRegex(ris, r"Utara\s*:\s*berbatasan dengan Jalan Trans Sulawesi")
        self.assertIn(f"di mohonkan oleh {KUASA} bertindak untuk dan atas nama {NAMA}", ris)
        # pendapat anggota dari susunan panitia, termasuk kepala desa
        for nama in ("KETUA UJI", "WAKIL UJI", "TATA UJI", "SEKRETARIS UJI", "Rahmat Uji"):
            self.assertIn(nama, ris)
        self.assertIn("Pendapat baku KETUA UJI, S.H.", ris)

    def test_risalah_tanpa_kuasa_dan_tanpa_isian_tambahan(self):
        _, bid = self._berkas(kuasa_nama="", jalan="", asal_tanah_uraian="",
                              dasar_perolehan="", baku_tata_ruang="")
        ris = self._teks(bid, "risalah")
        self._bersih(ris, "risalah")
        self.assertIn(f"di mohonkan oleh {NAMA} telah memenuhi", ris)
        self.assertRegex(ris, r"Jalan\s*:\s*-")
        self.assertNotIn("berasal dari  ", ris)
        self.assertNotIn("dilengkapi dengan  ", ris)
        self.assertNotIn(" ,", ris)

    def test_sk(self):
        _, bid = self._berkas()
        sk = self._teks(bid, "sk")
        self._bersih(sk, "sk")
        self.assertIn("NOMOR : 5/HGB/BPN-75.03/II/2026", sk)
        self.assertIn("PEMBERIAN HAK GUNA BANGUNAN ATAS NAMA " + NAMA, sk)
        self.assertIn("TERLETAK DI Desa Tunas Baru KECAMATAN Suwawa Uji", sk)
        self.assertIn(f"Surat Permohonan Hak Guna Bangunan tanggal 29 Januari 2026 dari {NAMA} "
                      f"berkedudukan di {KEDUDUKAN};", sk)
        self.assertIn(f"Bahwa {NAMA}, berkedudukan di {KEDUDUKAN}, sehingga telah memenuhi "
                      "syarat sebagai subjek Hak Guna Bangunan;", sk)
        self.assertIn("Tanggal 19 Februari 2026 Nomor 9/2026", sk)
        self.assertIn("Tanah Negara yang berasal dari " + ASAL, sk)
        for r in RIWAYAT:
            self.assertIn(r, sk)
        self.assertIn("dilengkapi dengan " + TATA_RUANG, sk)
        self.assertIn("77/SK-75.03/I/2026 Tanggal 05 Januari 2026", sk)
        self.assertIn("Kabupaten Bone Bolango Tahun 2026.", sk)
        self.assertIn(f"Memberikan kepada {NAMA} berkedudukan di {KEDUDUKAN}", sk)
        self.assertIn("HAK GUNA BANGUNAN atas sebidang tanah Non Pertanian", sk)
        self.assertIn("Peta Bidang tanggal 20 Januari 2026 Nomor 77/2026 NIB.30.05.10.01.00888",
                      sk)
        self.assertIn("KELIMABELAS", sk)
        self.assertIn("24 Februari 2026", sk)              # tanggal SK di tanda tangan
        alamat = sk[sk.index("NIP."):]
        self.assertIn(NAMA, alamat)
        self.assertIn(KEDUDUKAN, alamat)

    # -------------------------------------------------------- periksa
    def test_periksa_rincian_badan_hukum(self):
        _, bid = self._berkas(bh_bidang_usaha="", bh_nib="", asal_tanah_uraian="",
                              baku_tata_ruang="")
        k = db.sambung()
        try:
            m = konteks.periksa(k, bid)
        finally:
            k.close()
        pesan = " ".join(p for _, p in m)
        galat = " ".join(p for t, p in m if t == "galat")
        self.assertIn("bidang usaha", pesan)
        self.assertIn("NIB", pesan)
        self.assertIn("Asal tanah negara", pesan)
        self.assertIn("kesesuaian tata ruang", pesan)
        self.assertNotIn("tidak dapat diberikan kepada subjek", galat)
        self.assertNotIn("NIK", galat)

    def test_periksa_subjek_perorangan_ditolak(self):
        _, bid = self._berkas(penerima_jenis_subjek="perorangan")
        k = db.sambung()
        try:
            galat = " ".join(p for t, p in konteks.periksa(k, bid) if t == "galat")
        finally:
            k.close()
        self.assertIn("tidak dapat diberikan kepada subjek 'perorangan'", galat)

    def test_nomor_sk_berkode_hgb(self):
        _, bid = self._berkas(sk_nomor="")
        k = db.sambung()
        try:
            nomor = terbitkan.nomor_sk(k, bid)
        finally:
            k.close()
        self.assertRegex(nomor, r"^\d+/HGB/")

    def test_tab_template(self):
        halaman = self.klien(masuk=True).get("/template").get_data(as_text=True)
        self.assertIn('id="t-hgbbh"', halaman)
        for nama in ("Risalah · HGB Badan Hukum", "SK · HGB Badan Hukum"):
            self.assertIn(nama, halaman)
        self.assertIn("{{hgb_asal_frasa}}", halaman)          # penandanya dikenali


if __name__ == "__main__":
    unittest.main()
