# -*- coding: utf-8 -*-
"""Tata naskah Hak Pakai Tanah Pemerintah (Hak Pakai selama dipergunakan).

Berbeda dengan uji_hak_pakai, uji ini tidak menyentuh data pemohon asli: berkasnya
dibuat dari nol di basis data kosong, lewat formulir web yang sama dengan yang
dipakai petugas. Jadi yang diuji sekaligus dua hal — isian formulirnya terbaca
dan tersimpan, lalu ketiga dokumennya dirakit dari isian itu.

    python -m unittest uji.uji_hak_pakai_pemerintah
"""
import unittest

from berkas import db
from berkas.dokumen import konteks, templat, terbitkan

from . import dasar
from .uji_web import Dasar as DasarWeb

NAMA = "Pemerintah Daerah Kabupaten Bone Bolango"
DASAR = ("Undang-Undang Nomor 6 Tahun 2003 tentang Pembentukan Kabupaten Bone Bolango "
         "dan Kabupaten Pohuwato di Provinsi Gorontalo")
KEDUDUKAN = "Jl. Uji Coba Nomor 1, Kecamatan Suwawa, Kabupaten Bone Bolango"
WAKIL, JABATAN = "Dr. Andi Wijaya, M.Si.", "Sekretaris Daerah"
RIWAYAT = [
    "Bidang I seluas 1.500 m² sebelumnya dikuasai oleh Budi Lamato berdasarkan Surat "
    "Keterangan Penguasaan Tanah, selanjutnya diserahkan kepada Pemerintah Daerah",
    "Bidang II seluas 2.000 m² diperoleh berdasarkan Hibah sebagaimana tercantum dalam "
    "Kartu Inventaris Barang Nomor Register 000002",
]
KIB = ("Kartu Inventaris Barang (KIB) dengan No. Kode Lokasi : 12.01.30.04 tanggal 12 "
       "Oktober 2026, No. Kode Barang : 1.3.1.01.001.004.003 register 000001")

# Nilai berkas contoh yang dipakai membangun template. Tak satu pun boleh tersisa:
# kalau tersisa, berarti ada kalimat contoh yang lupa diganti penanda.
SISA_CONTOH = ["Tombulilato", "Feddy", "Iwan Mustapa", "31.475", "191/2026", "00394",
               "Hardjo", "Tangahu", "Inomata", "Ulanta", "6449", "RSUD", "Kejaksaan",
               "Haina", "BAHMID", "IRHAM", "INDRAWATY", "156.1/SK", "tersebut ...",
               "Saud, ...", "MEMUTUSKAN ..."]


def _tanpa_penyambung():
    asli = terbitkan._kata_penyambung
    terbitkan._kata_penyambung = lambda *a, **kw: 0
    return asli


class HakPakaiPemerintah(DasarWeb):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._penyambung = _tanpa_penyambung()
        k = db.sambung()
        try:
            kec = db.sisip_id(k, "INSERT INTO ref_kecamatan (nama) VALUES (?)", ("Kabila Uji",))
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
                    ("SEKRETARIS UJI, S.H.", "Koordinator Kelompok Substansi",
                     "Sekretaris merangkap Anggota"))):
                k.execute("INSERT INTO ref_panitia_anggota (panitia_id,urut,nama,nip,jabatan,"
                          "peran) VALUES (?,?,?,?,?,?)",
                          (cls.panitia, i, nama, f"1980010120090110{i:02d}", jabatan, peran))
            k.commit()
        finally:
            k.close()
        cls.c = None

    @classmethod
    def tearDownClass(cls):
        terbitkan._kata_penyambung = cls._penyambung
        super().tearDownClass()

    # ------------------------------------------------------------ pembantu
    def _form(self, **lain):
        data = {
            "status": "draf", "jenis_kegiatan": "baru", "jenis_hak_dimohon": "HPTP",
            "nomor_berkas": "123/2026", "tanggal_permohonan": "2026-09-29",
            "penerima_jenis_subjek": "instansi", "penerima_nama": NAMA,
            "penerima_alamat": KEDUDUKAN,
            "bh_kedudukan": KEDUDUKAN, "bh_dasar_pembentukan": DASAR,
            "bh_jenis_instansi": "daerah", "bh_wakil_nama": WAKIL,
            "bh_wakil_jabatan": JABATAN, "bh_wakil_nik": "7503010101800001",
            "desa_id": str(self.desa), "nomor_pbt": "55/2026", "tanggal_pbt": "2026-10-15",
            "nib": "30.05.10.01.00777", "luas_pbt": "3500",
            "batas_utara": "Jalan Trans Sulawesi", "batas_timur": "Tanah Negara",
            "batas_selatan": "Sungai", "batas_barat": "Kantor Desa",
            "penggunaan_sekarang": "Puskesmas Tunas Baru",
            "rencana_penggunaan": "Puskesmas Tunas Baru",
            "rtrw": "Kawasan Permukiman Perdesaan", "kesesuaian": "Sesuai",
            "tanggal_peta_analisis": "2026-10-08",
            "jenis_tanah": "Pekarangan", "keadaan_tanah": "terdapat bangunan di atasnya",
            "riwayat_uraian": RIWAYAT, "riwayat_bukti": ["", ""],
            "baku_permohonan": "Formulir permohonan Pemberian Hak Pakai tanggal 29 September 2026",
            "baku_asli_permohonan": "Asli",
            "baku_sppf": "Surat Pernyataan Penguasaan Fisik Bidang Tanah tanggal 25 September "
                         "2026 yang dibuat dan ditandatangani oleh " + WAKIL,
            "baku_asli_sppf": "Asli",
            "baku_penguasaan_aset": "Surat Pernyataan Penguasaan Aset tanggal 29 September 2026",
            "baku_asli_penguasaan_aset": "Asli",
            "dokumen_uraian": [KIB], "dokumen_keaslian": ["Fotokopi"],
            "dokumen_kategori": ["tambahan"],
            "tanggal_surat_tugas": "2026-10-20", "tanggal_bap": "2026-10-22",
            "panitia_id": str(self.panitia),
            "risalah_nomor": "7/2026", "risalah_tanggal": "2026-10-22",
            "risalah_kesimpulan": "dikabulkan",
            "sk_nomor": "12/HP/BPN-75.03/X/2026", "sk_tanggal": "2026-10-30",
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

    def _bersih(self, teks, jenis):
        self.assertFalse("{{" in teks, f"penanda tersisa di {jenis}: "
                                       f"{teks[teks.find('{{'):teks.find('{{') + 60]!r}")
        sisa = [x for x in SISA_CONTOH if x in teks]
        self.assertEqual(sisa, [], f"isi berkas contoh tersisa di {jenis}")

    # ------------------------------------------------------------- uji
    def test_jenis_hak_dan_template(self):
        k = db.sambung()
        try:
            r = k.execute("SELECT * FROM ref_jenis_hak WHERE kode='HPTP'").fetchone()
            # basis data baru tetap berisi semua jenis hak, bukan HPTP saja
            kode = {x[0] for x in k.execute("SELECT kode FROM ref_jenis_hak")}
        finally:
            k.close()
        self.assertEqual(kode, {x[0] for x in db.JENIS_HAK})
        self.assertIsNotNone(r, "jenis hak HPTP belum ada")
        self.assertEqual(r["varian_template"], "hptp")
        self.assertEqual(r["kode_sk"], "HP")
        self.assertEqual(r["ada_jangka_waktu"], 0)
        self.assertEqual(r["subjek_boleh"], "instansi")
        for jenis in ("bap", "risalah", "sk"):
            self.assertEqual(templat.kunci(jenis, "hptp"), f"{jenis}-hptp")

    def test_isian_instansi_tampil_dan_tersimpan(self):
        c, bid = self._berkas()
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn("Instansi pemerintah", halaman)
        self.assertIn('name="bh_dasar_pembentukan"', halaman)
        self.assertIn('name="jenis_tanah"', halaman)
        # kartu badan hukum tidak ditampilkan dua kali dengan nama medan yang sama
        self.assertEqual(halaman.count('name="bh_kedudukan"'), 1)
        self.assertEqual(halaman.count('name="bh_wakil_nik"'), 1)
        k = db.sambung()
        try:
            d = konteks.muat(k, bid)
        finally:
            k.close()
        bh = konteks.penerima_hak(d)["badan_hukum"]
        self.assertEqual(bh["dasar_pembentukan"], DASAR)
        self.assertEqual(bh["jenis_instansi"], "daerah")
        self.assertEqual(bh["wakil_nama"], WAKIL)
        self.assertEqual(d["tanah"]["jenis_tanah"], "Pekarangan")
        self.assertEqual(d["tanah"]["keadaan_tanah"], "terdapat bangunan di atasnya")
        self.assertEqual(len(d["riwayat"]), 2)

    def test_isian_lain_tidak_hilang_saat_ganti_jenis_hak(self):
        c, bid = self._berkas()
        # disimpan ulang sebagai Hak Pakai biasa: medan instansi tak tampak, tetapi terbawa
        c.post(f"/berkas/{bid}", data=self._form(jenis_hak_dimohon="HP"))
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn('name="bh_dasar_pembentukan"', halaman)
        self.assertIn('type="hidden" name="jenis_tanah"', halaman)
        k = db.sambung()
        try:
            d = konteks.muat(k, bid)
        finally:
            k.close()
        self.assertEqual(konteks.penerima_hak(d)["badan_hukum"]["dasar_pembentukan"], DASAR)
        self.assertEqual(d["tanah"]["jenis_tanah"], "Pekarangan")

    def test_bap(self):
        _, bid = self._berkas()
        bap = self._teks(bid, "bap")
        self._bersih(bap, "bap")
        self.assertIn(f"permohonan dari {WAKIL} selaku {JABATAN} yang bertindak untuk dan "
                      f"atas nama {NAMA} atas sebidang tanah seluas 3.500 m²", bap)
        self.assertIn(f"dikuasai oleh {NAMA} yang berasal dari 2 (dua) bidang tanah "
                      "dengan riwayat:", bap)
        for r in RIWAYAT:
            self.assertIn(r, bap)
        self.assertIn("berupa tanah pekarangan yang keadaan tanahnya terdapat bangunan", bap)
        self.assertRegex(bap, r"Utara\s*:\s*berbatasan dengan Jalan Trans Sulawesi")
        self.assertIn("KETUA UJI, S.H.", bap)
        self.assertIn("Rahmat Uji", bap)                  # kepala desa ikut anggota

    def test_risalah(self):
        _, bid = self._berkas()
        ris = self._teks(bid, "risalah")
        self._bersih(ris, "risalah")
        self.assertIn("NOMOR : 7/2026", ris)
        self.assertIn(f"Nama Pemohon\t\t\t : \t{NAMA}".split("\t")[0], ris)
        self.assertIn(DASAR, ris)
        self.assertIn("Selama Dipergunakan", ris)
        self.assertIn("Pasal 111 ayat (3) huruf b", ris)
        self.assertIn("Fotokopi " + KIB, ris)
        self.assertIn(f"Fotokopi KTP atas nama {WAKIL}", ris)
        self.assertIn("Asli Surat Pernyataan Penguasaan Aset", ris)
        self.assertIn("77/SK-75.03/I/2026", ris)
        self.assertIn("5 (lima) orang", ris)
        for nama in ("KETUA UJI", "WAKIL UJI", "TATA UJI", "SEKRETARIS UJI", "Rahmat Uji"):
            self.assertIn(nama, ris)
        for r in RIWAYAT:
            self.assertIn(r, ris)
        self.assertIn("tidak dikenakan Pajak Bumi dan Bangunan", ris)

    def test_sk(self):
        _, bid = self._berkas()
        sk = self._teks(bid, "sk")
        self._bersih(sk, "sk")
        self.assertIn("NOMOR : 12/HP/BPN-75.03/X/2026", sk)
        self.assertIn("PEMBERIAN HAK PAKAI ATAS NAMA PEMERINTAH DAERAH KABUPATEN BONE BOLANGO",
                      sk)
        self.assertIn("TERLETAK DI DESA TUNAS BARU KECAMATAN KABILA UJI", sk)
        self.assertIn("Nomor berkas 123/2026", sk)
        self.assertIn(f"{WAKIL} selaku {JABATAN} bertindak untuk dan atas nama serta mewakili "
                      f"{NAMA}", sk)
        self.assertIn(f"Bahwa {NAMA} berkedudukan di {KEDUDUKAN}, yang dibentuk berdasarkan "
                      f"{DASAR} sehingga telah memenuhi syarat sebagai subjek Hak Pakai;", sk)
        self.assertIn("Hak Pakai Selama Dipergunakan atas sebidang tanah Pekarangan", sk)
        self.assertIn("dikecualikan dari objek BPHTB", sk)
        self.assertIn("tidak dapat dijadikan jaminan utang", sk)
        self.assertIn("30 Oktober 2026", sk)                 # tanggal SK di tanda tangan
        for r in RIWAYAT:
            self.assertIn(r, sk)
        kepada = sk[sk.index("Kepada"):]
        self.assertIn(NAMA, kepada)
        self.assertIn(KEDUDUKAN, kepada)

    def test_periksa_instansi(self):
        _, bid = self._berkas(bh_dasar_pembentukan="", bh_wakil_nama="", risalah_jangka="30")
        k = db.sambung()
        try:
            m = konteks.periksa(k, bid)
        finally:
            k.close()
        pesan = " ".join(p for _, p in m)
        galat = " ".join(p for t, p in m if t == "galat")
        self.assertIn("Dasar pembentukan instansi", pesan)
        self.assertIn("Pejabat yang mewakili instansi", pesan)
        self.assertIn("selama dipergunakan", pesan)
        self.assertNotIn("NIK", galat)
        self.assertNotIn("Kartu Keluarga", pesan)
        self.assertNotIn("tidak dapat diberikan kepada subjek", galat)

    def test_periksa_subjek_bukan_instansi(self):
        _, bid = self._berkas(penerima_jenis_subjek="perorangan")
        k = db.sambung()
        try:
            galat = " ".join(p for t, p in konteks.periksa(k, bid) if t == "galat")
        finally:
            k.close()
        self.assertIn("tidak dapat diberikan kepada subjek 'perorangan'", galat)

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
        self.assertIn('id="t-hptp"', halaman)
        for nama in ("BAP · Hak Pakai Tanah Pemerintah", "Risalah · Hak Pakai Tanah Pemerintah",
                     "SK · Hak Pakai Tanah Pemerintah"):
            self.assertIn(nama, halaman)
        self.assertIn("{{ins_dasar}}", halaman)              # penandanya dikenali


if __name__ == "__main__":
    unittest.main()
