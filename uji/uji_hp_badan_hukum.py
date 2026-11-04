# -*- coding: utf-8 -*-
"""Tata naskah Hak Pakai untuk badan hukum (jenis hak HPBH).

Sama seperti uji_hgb_badan_hukum: berkasnya dibuat dari nol di basis data
kosong lewat formulir web, jadi yang diuji sekaligus isian formulirnya dan
dokumen yang dirakit dari isian itu. Data pemohon asli tidak disentuh.

    python -m unittest uji.uji_hp_badan_hukum
"""
import unittest

from berkas import db
from berkas.dokumen import konteks, templat, terbitkan

from . import dasar
from .uji_web import Dasar as DasarWeb

NAMA = "PT. Sinar Pakai Uji"
KEDUDUKAN = "Kota Gorontalo, Provinsi Gorontalo"
KEDUDUKAN_SINGKAT = "Kota Gorontalo"
NOTARIS = "Notaris Uji, S.H., M.Kn."
PENGESAHAN = "AHU-0099999.AH.01.01.TAHUN 2025"
OLEH = "Menteri Hukum dan Hak Asasi Manusia Republik Indonesia"
NIB_OSS = "9876543210123"
WAKIL, JABATAN = "Budi Direktur Uji", "Direktur"
KUASA = "Kuasa Uji"
JALAN = "Jalan Uji Nomor 7"
TATA_RUANG = ("Persetujuan Kesesuaian Kegiatan Pemanfaatan Ruang Nomor 503/PKKPR-UJI/2026 "
              "tanggal 15 Januari 2026")
PERTIMBANGAN = [
    "Bahwa berdasarkan hasil pemeriksaan tanah di lapangan bidang tanah yang dimohon "
    "berbatasan langsung dengan sungai di sebelah timur dengan jarak < 50 m",
    "Bahwa berdasarkan Peraturan Menteri Pekerjaan Umum dan Perumahan Rakyat R.I nomor "
    "28/PRT/M/2015 garis sempadan sungai paling sedikit 50 (lima puluh) meter",
]
RIWAYAT = [
    "Bahwa sebelumnya bidang tanah yang dimohon dikuasai oleh Penggarap Uji sampai tahun 1990",
    "Bahwa selanjutnya bidang tanah yang dimohon dikuasai oleh Penjual Uji sejak tahun 1990",
    "Bahwa selanjutnya bidang tanah yang dimohon beralih kepada PT. Sinar Pakai Uji sejak "
    "tahun 2025 berdasarkan Surat Pernyataan Pelepasan Hak",
]

# Nilai berkas contoh (Reagen Hulukati, perorangan) yang dipakai membangun
# template. Tak satu pun boleh tersisa: kalau tersisa, ada kalimat contoh yang
# lupa diganti — termasuk kalimat perorangan yang harus jadi kalimat badan hukum.
SISA_CONTOH = ["Reagen", "Hulukati", "Hulopi", "Molotabu", "Kabila", "Lefri", "Mooduto",
               "Saleh", "Rostin", "Novan", "Djingo", "Sudirman", "Abdullah", "Jayapura",
               "Entrop", "9171020805900004", "Karyawan Swasta", "171 m", "37/2024", "00320",
               "SILVA", "FIRMANSYAH", "ASDA", "BINTANG", "02/SK-75.03", "Tanah Kosong",
               "Rumah Tinggal", "Permukiman Perdesaan", "21 November 2024", "10 Juli 2024",
               "11 Juli 2024", "20 Februari 2026", "03 Februari 2026", "02 Februari 2026",
               "Tjarbos", "503/DPMPTSP", "Hak Milik", "Warga Negara", "Kewarganegaraan",
               "bertempat tinggal", "Perorangan", "poin 7", "Pasal III", "MEMUTSUKAN",
               "Abdullah …", "Ruang …", "Pakai …", "kepentingan  …", "8) Peraturan"]


def _tanpa_penyambung():
    asli = terbitkan._kata_penyambung
    terbitkan._kata_penyambung = lambda *a, **kw: 0
    return asli


class HpBadanHukum(DasarWeb):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._penyambung = _tanpa_penyambung()
        k = db.sambung()
        try:
            kec = db.sisip_id(k, "INSERT INTO ref_kecamatan (nama) VALUES (?)", ("Bulango Uji",))
            cls.desa = db.sisip_id(
                k, "INSERT INTO ref_desa (kecamatan_id,nama,jenis,nama_pejabat) "
                   "VALUES (?,?,?,?)", (kec, "Tunas Pakai", "Desa", "Rahmat Uji"))
            cls.panitia = db.sisip_id(
                k, "INSERT INTO ref_panitia (nomor_sk,tanggal_sk) VALUES (?,?)",
                ("88/SK-75.03/I/2026", "2026-01-05"))
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
            "status": "draf", "jenis_kegiatan": "baru", "jenis_hak_dimohon": "HPBH",
            "nomor_berkas": "189/2026", "tanggal_permohonan": "2026-01-12",
            "penerima_jenis_subjek": "badan_hukum", "penerima_nama": NAMA,
            "bh_bentuk": "PT", "bh_kedudukan": KEDUDUKAN,
            "bh_akta_nomor": "21", "bh_akta_tanggal": "2025-04-14", "bh_notaris": NOTARIS,
            "bh_notaris_kota": "Kota Gorontalo",
            "bh_pengesahan_nomor": PENGESAHAN, "bh_pengesahan_tanggal": "2025-04-16",
            "bh_pengesahan_oleh": OLEH, "bh_nib": NIB_OSS,
            "bh_bidang_usaha": "Perdagangan Eceran",
            "bh_wakil_nama": WAKIL, "bh_wakil_jabatan": JABATAN,
            "kuasa_nama": KUASA,
            "lain_peran": ["pemilik_sebelumnya"], "lain_nama": ["Penjual Uji"],
            "lain_nik": [""], "lain_ttl": [""], "lain_pekerjaan": [""], "lain_alamat": [""],
            "desa_id": str(self.desa), "nomor_pbt": "41/2026", "tanggal_pbt": "2026-01-08",
            "nib": "30.05.08.02.00777", "luas_pbt": "850",
            "batas_utara": "Jalan Desa", "batas_timur": "Sungai",
            "batas_selatan": "Tanah Negara", "batas_barat": "Kebun Warga",
            "penggunaan_sekarang": "Gudang", "rencana_penggunaan": "Gudang",
            "rtrw": "Kawasan Perdagangan dan Jasa", "kesesuaian": "Sesuai",
            "tanggal_peta_analisis": "2026-01-10",
            "jalan": JALAN, "jenis_tanah": "Non Pertanian",
            "pertimbangan_lapang": PERTIMBANGAN[0] + ";\n\n" + PERTIMBANGAN[1] + ".",
            "riwayat_uraian": RIWAYAT, "riwayat_bukti": ["", "", ""],
            "baku_permohonan": "Surat permohonan hak tanggal 12 Januari 2026",
            "baku_asli_permohonan": "Asli",
            "baku_sppf": "Surat Pernyataan Penguasaan Fisik Bidang Tanah tanggal 9 Januari "
                         "2026 yang ditandatangani oleh " + WAKIL,
            "baku_asli_sppf": "Asli",
            "baku_tata_ruang": TATA_RUANG, "baku_asli_tata_ruang": "Fotokopi",
            "dokumen_uraian": ["Akta Pendirian Perseroan Terbatas Nomor 21"],
            "dokumen_keaslian": ["Fotokopi"], "dokumen_kategori": ["tambahan"],
            "tanggal_surat_tugas": "2026-01-20", "tanggal_bap": "2026-01-26",
            "panitia_id": str(self.panitia),
            "risalah_nomor": "7/2026", "risalah_tanggal": "2026-02-04",
            "risalah_kesimpulan": "dikabulkan", "risalah_jangka": "30",
            "sk_nomor": "4/HP/BPN-75.03/II/2026", "sk_tanggal": "2026-02-24",
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

    def _periksa(self, bid):
        k = db.sambung()
        try:
            return konteks.periksa(k, bid)
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
            r = k.execute("SELECT * FROM ref_jenis_hak WHERE kode='HPBH'").fetchone()
            hp = k.execute("SELECT * FROM ref_jenis_hak WHERE kode='HP'").fetchone()
            kode = {x[0] for x in k.execute("SELECT kode FROM ref_jenis_hak")}
        finally:
            k.close()
        self.assertEqual(kode, {x[0] for x in db.JENIS_HAK})
        self.assertIsNotNone(r, "jenis hak HPBH belum ada")
        self.assertEqual(r["nama"], "Hak Pakai Badan Hukum")
        self.assertEqual(r["varian_template"], "hpbh")
        self.assertEqual(r["kode_sk"], "HP")                # bernomor bersama Hak Pakai
        self.assertEqual(r["ada_jangka_waktu"], 1)
        self.assertEqual(r["jangka_maks"], 30)
        self.assertEqual(r["subjek_boleh"], "badan_hukum")
        # Hak Pakai biasa tidak berubah
        self.assertEqual(hp["varian_template"], "hp")
        self.assertEqual(hp["subjek_boleh"], "perorangan,badan_hukum,instansi")
        self.assertEqual(templat.kunci("risalah", "hpbh"), "risalah-hpbh")
        self.assertEqual(templat.kunci("sk", "hpbh"), "sk-hpbh")
        # BAP sama dengan BAP baku
        self.assertEqual(templat.kunci("bap", "hpbh"), "bap")
        self.assertNotIn("bap-hpbh", templat.JENIS)

    def test_slot_tata_ruang_tidak_dobel(self):
        kategori = [x[0] for x in db.SEMUA_BAKU]
        self.assertEqual(kategori.count("tata_ruang"), 1)
        self.assertIn("tata_ruang", [x[0] for x in db.dokumen_baku("HPBH")])
        self.assertIn("tata_ruang", [x[0] for x in db.dokumen_baku("HGBBH")])

    def test_migrasi_menyisipkan_ke_basis_data_lama(self):
        k = db.sambung()
        try:
            k.execute("PRAGMA foreign_keys=OFF")
            k.execute("DELETE FROM ref_jenis_hak WHERE kode='HPBH'")
            db.migrasi(k)
            k.execute("PRAGMA foreign_keys=ON")
            r = k.execute("SELECT varian_template FROM ref_jenis_hak WHERE kode='HPBH'"
                          ).fetchone()
            kolom = db.kolom_tabel(k, "bidang_tanah")
        finally:
            k.close()
        self.assertEqual(r["varian_template"], "hpbh")
        self.assertIn("pertimbangan_lapang", kolom)

    # --------------------------------------------------------- formulir
    def test_isian_hpbh_tampil_dan_tersimpan(self):
        c, bid = self._berkas()
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        for nama in ("bh_bidang_usaha", "bh_notaris_kota", "bh_pengesahan_oleh",
                     "jalan", "jenis_tanah", "asal_tanah_uraian", "pertimbangan_lapang",
                     "baku_tata_ruang"):
            self.assertIn(f'name="{nama}"', halaman)
            self.assertEqual(halaman.count(f'name="{nama}"'), 1, nama)
        self.assertNotIn('type="hidden" name="pertimbangan_lapang"', halaman)
        self.assertIn("Hak Pakai Badan Hukum", halaman)
        d = self._muat(bid)
        bh = konteks.penerima_hak(d)["badan_hukum"]
        self.assertEqual(bh["bidang_usaha"], "Perdagangan Eceran")
        self.assertEqual(d["tanah"]["jalan"], JALAN)
        self.assertIn(PERTIMBANGAN[1], d["tanah"]["pertimbangan_lapang"])
        self.assertIn(TATA_RUANG, [r["uraian"] for r in d["dokumen"]])

    def test_isian_tidak_tampil_di_hp_biasa_tetapi_tidak_hilang(self):
        c, bid = self._berkas()
        c.post(f"/berkas/{bid}", data=self._form(jenis_hak_dimohon="HP"))
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn('type="hidden" name="pertimbangan_lapang"', halaman)
        self.assertEqual(halaman.count('name="pertimbangan_lapang"'), 1)
        d = self._muat(bid)
        self.assertIn(PERTIMBANGAN[0], d["tanah"]["pertimbangan_lapang"])
        self.assertEqual(d["tanah"]["jalan"], JALAN)

    def test_isian_pertimbangan_tidak_hilang_di_hgb_badan_hukum(self):
        c, bid = self._berkas()
        c.post(f"/berkas/{bid}", data=self._form(jenis_hak_dimohon="HGBBH"))
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn('type="hidden" name="pertimbangan_lapang"', halaman)
        self.assertEqual(halaman.count('name="pertimbangan_lapang"'), 1)
        self.assertIn(PERTIMBANGAN[0], self._muat(bid)["tanah"]["pertimbangan_lapang"])

    # --------------------------------------------------------- dokumen
    def test_bap_memakai_bap_baku(self):
        _, bid = self._berkas()
        bap = self._teks(bid, "bap")
        self.assertNotIn("{{", bap)
        self.assertIn(NAMA, bap)

    def test_risalah(self):
        _, bid = self._berkas()
        ris = self._teks(bid, "risalah")
        self._bersih(ris, "risalah")
        self.assertIn("NOMOR : 7/2026", ris)
        self.assertIn("Permohonan Hak Pakai dengan Jangka Waktu atas Nama : " + NAMA, ris)
        self.assertIn("88/SK-75.03/I/2026", ris)
        self.assertIn("5 (lima) orang", ris)
        # uraian mengenai pemohon: baris badan hukum, bukan perorangan
        self.assertIn("Badan Hukum", ris)
        self.assertIn(KEDUDUKAN_SINGKAT, ris)
        self.assertIn("Nomor : 21 tanggal 14 April 2025", ris)
        self.assertIn(f"Nomor : {PENGESAHAN} tanggal 16 April 2025", ris)
        self.assertIn(NIB_OSS, ris)
        self.assertIn("Perdagangan Eceran", ris)
        self.assertNotIn("NIK", ris)
        # tanah dan hak
        self.assertIn(JALAN, ris)
        self.assertIn("Tunas Pakai", ris)
        self.assertIn("850 m²", ris)
        self.assertIn("No. 41/2026, Tanggal 08 Januari 2026", ris)
        self.assertRegex(ris, r"Jenis hak\s*:\s*Hak Pakai dengan Jangka Waktu")
        self.assertRegex(ris, r"Jangka Waktu\s*:\s*30 Tahun")
        self.assertIn("Gudang", ris)
        # data pendukung
        self.assertIn("Asli Surat permohonan hak tanggal 12 Januari 2026", ris)
        self.assertIn("Fotokopi " + TATA_RUANG, ris)
        self.assertIn("Fotokopi Akta Pendirian Perseroan Terbatas Nomor 21", ris)
        self.assertIn("Asli Peta Bidang Tanah Nomor : 41/2026", ris)
        self.assertIn("Berita Acara Pemeriksaan Lapang Tanggal 26 Januari 2026", ris)
        # telaah subjek badan hukum
        self.assertIn(f"Bahwa pemohon yaitu {NAMA} yang berkedudukan di {KEDUDUKAN_SINGKAT}, "
                      f"adalah Badan Hukum yang didirikan berdasarkan Akta Pendirian Nomor 21 "
                      f"tanggal 14 April 2025 yang dibuat di hadapan {NOTARIS} selaku Notaris "
                      f"di Kota Gorontalo, yang telah mendapatkan pengesahan dari {OLEH}", ris)
        self.assertIn("Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas", ris)
        self.assertIn("Nomor Induk Berusaha : " + NIB_OSS, ris)
        self.assertIn("Pasal 42 huruf c", ris)
        self.assertIn("Pasal 111 ayat (2) huruf b", ris)
        self.assertIn(f"{NAMA} memenuhi syarat sebagai subyek Hak Pakai dengan Jangka Waktu", ris)
        # telaah objek
        for r in RIWAYAT:
            self.assertIn(r, ris)
        self.assertIn("Tanah Negara yang belum dilekati dengan sesuatu Hak", ris)
        self.assertIn("berada dalam Kawasan Perdagangan dan Jasa", ris)
        self.assertIn("dilengkapi " + TATA_RUANG, ris)
        self.assertIn("penggunaan tanahnya untuk Non Pertanian", ris)
        self.assertRegex(ris, r"Utara\s*:\s*berbatasan dengan Jalan Desa")
        # pertimbangan lapangan: satu paragraf per baris isian, tanda baca seragam
        for p in PERTIMBANGAN:
            self.assertIn(p + ";", ris)
        self.assertNotIn(";;", ris)
        self.assertIn(f"di mohonkan oleh {KUASA} bertindak untuk dan atas nama {NAMA}", ris)
        self.assertNotIn("direkomendasikan", ris)
        # pendapat anggota dari susunan panitia, termasuk kepala desa
        for nama in ("KETUA UJI", "WAKIL UJI", "TATA UJI", "SEKRETARIS UJI", "Rahmat Uji"):
            self.assertIn(nama, ris)
        self.assertIn("Pendapat baku KETUA UJI, S.H.", ris)
        self.assertIn("permohonan Hak Pakai dengan Jangka Waktu atas nama pemohon dapat "
                      "diberikan", ris)
        self.assertIn("dapat dipertimbangkan untuk diberikan Hak Pakai dengan Jangka Waktu.",
                      ris)

    def test_risalah_tanpa_isian_tambahan(self):
        _, bid = self._berkas(kuasa_nama="", jalan="", asal_tanah_uraian="",
                              pertimbangan_lapang="", baku_tata_ruang="")
        ris = self._teks(bid, "risalah")
        self._bersih(ris, "risalah")
        self.assertIn(f"di mohonkan oleh {NAMA} telah memenuhi", ris)
        self.assertRegex(ris, r"Jalan\s*:\s*-")
        self.assertNotIn("dilengkapi  ", ris)
        self.assertNotIn("28/PRT/M/2015", ris)
        self.assertNotIn("< 50 m", ris)
        self.assertNotIn(" ,", ris)

    def test_risalah_dengan_asal_tanah(self):
        asal = "tanah bekas Hak Guna Usaha Nomor 1/Uji yang telah berakhir haknya"
        _, bid = self._berkas(asal_tanah_uraian=asal)
        ris = self._teks(bid, "risalah")
        self.assertIn("Tanah Negara yang berasal dari " + asal, ris)
        self.assertNotIn("belum dilekati", ris)

    def test_risalah_rekomendasi_dari_jenis_hak_lain(self):
        _, bid = self._berkas(jenis_hak_dimohon="HGB", jenis_hak_rekomendasi="HPBH")
        ris = self._teks(bid, "risalah")
        self.assertNotIn("{{", ris)
        self.assertIn("Permohonan Hak Guna Bangunan atas Nama : " + NAMA, ris)
        self.assertIn("direkomendasikan untuk diberikan Hak Pakai dengan Jangka Waktu", ris)
        self.assertRegex(ris, r"Jenis hak\s*:\s*Hak Pakai dengan Jangka Waktu")
        self.assertIn("dapat dipertimbangkan untuk diberikan Hak Pakai dengan Jangka Waktu.",
                      ris)
        sk = self._teks(bid, "sk")
        self.assertIn("Surat Permohonan Hak Guna Bangunan tanggal 12 Januari 2026", sk)
        self.assertIn("PEMBERIAN HAK PAKAI DENGAN JANGKA WAKTU ATAS NAMA " + NAMA, sk)

    def test_sk(self):
        _, bid = self._berkas()
        sk = self._teks(bid, "sk")
        self._bersih(sk, "sk")
        self.assertIn("NOMOR : 4/HP/BPN-75.03/II/2026", sk)
        self.assertIn("PEMBERIAN HAK PAKAI DENGAN JANGKA WAKTU ATAS NAMA " + NAMA, sk)
        self.assertIn("TERLETAK DI Desa Tunas Pakai KECAMATAN Bulango Uji", sk)
        self.assertIn(f"Surat Permohonan Hak Pakai dengan Jangka Waktu tanggal 12 Januari 2026 "
                      f"dari {NAMA} berkedudukan di {KEDUDUKAN};", sk)
        # Menimbang huruf a: uraian badan hukum lengkap
        self.assertIn(f"Bahwa {NAMA} adalah badan hukum, berkedudukan di {KEDUDUKAN}", sk)
        self.assertIn(f"dalam hal ini diwakili oleh {WAKIL} selaku {JABATAN}", sk)
        self.assertIn("sehingga telah memenuhi syarat sebagai subjek Hak Pakai Dengan Jangka "
                      "Waktu;", sk)
        self.assertIn("Tanggal 04 Februari 2026 Nomor 7/2026", sk)
        for r in RIWAYAT:
            self.assertIn(r, sk)
        for p in PERTIMBANGAN:
            self.assertIn(p + ";", sk)
        self.assertIn("dilengkapi " + TATA_RUANG, sk)
        self.assertIn("88/SK-75.03/I/2026 Tanggal 05 Januari 2026", sk)
        # Mengingat: undang-undang bentuk badan hukumnya
        self.assertIn("Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas;", sk)
        self.assertIn("HAK PAKAI DENGAN JANGKA WAKTU SELAMA 30 (TIGA PULUH TAHUN) ATAS NAMA "
                      + NAMA, sk)
        self.assertIn(f"Memberikan kepada {NAMA} berkedudukan di {KEDUDUKAN}", sk)
        self.assertIn("HAK PAKAI DENGAN JANGKA WAKTU atas sebidang tanah Non Pertanian", sk)
        self.assertIn("Peta Bidang tanggal 08 Januari 2026 Nomor 41/2026", sk)
        self.assertIn("NIB. 30.05.08.02.00777", sk)
        self.assertIn("KELIMABELAS", sk)
        self.assertIn("24 Februari 2026", sk)              # tanggal SK di tanda tangan
        alamat = sk[sk.index("NIP."):]
        self.assertIn(NAMA, alamat)
        self.assertIn(KEDUDUKAN, alamat)

    # -------------------------------------------------------- periksa
    def test_periksa_rincian_badan_hukum(self):
        _, bid = self._berkas(bh_bidang_usaha="", bh_nib="", baku_tata_ruang="")
        m = self._periksa(bid)
        pesan = " ".join(p for _, p in m)
        galat = " ".join(p for t, p in m if t == "galat")
        self.assertIn("bidang usaha", pesan)
        self.assertIn("NIB", pesan)
        self.assertIn("kesesuaian tata ruang", pesan)
        self.assertNotIn("tidak dapat diberikan kepada subjek", galat)
        self.assertNotIn("NIK", galat)

    def test_periksa_subjek_perorangan_ditolak(self):
        _, bid = self._berkas(penerima_jenis_subjek="perorangan")
        galat = " ".join(p for t, p in self._periksa(bid) if t == "galat")
        self.assertIn("tidak dapat diberikan kepada subjek 'perorangan'", galat)

    def test_periksa_jangka_melebihi_batas(self):
        _, bid = self._berkas(risalah_jangka="35")
        galat = " ".join(p for t, p in self._periksa(bid) if t == "galat")
        self.assertIn("melebihi batas 30 tahun", galat)

    def test_nomor_sk_berkode_hp(self):
        _, bid = self._berkas(sk_nomor="")
        k = db.sambung()
        try:
            nomor = terbitkan.nomor_sk(k, bid)
        finally:
            k.close()
        self.assertRegex(nomor, r"^\d+/HP/")

    def test_tab_template(self):
        halaman = self.klien(masuk=True).get("/template").get_data(as_text=True)
        self.assertIn('id="t-hpbh"', halaman)
        for nama in ("Risalah · Hak Pakai Badan Hukum", "SK · Hak Pakai Badan Hukum"):
            self.assertIn(nama, halaman)
        self.assertIn("{{hpbh_tata_ruang_frasa}}", halaman)    # penandanya dikenali


if __name__ == "__main__":
    unittest.main()
