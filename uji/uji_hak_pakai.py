# -*- coding: utf-8 -*-
"""Tata naskah Hak Pakai: perorangan dan badan hukum.

Tidak memakai rekaman acuan — belum ada berkas Hak Pakai sungguhan di basis
data. Sebagai gantinya satu berkas Hak Milik yang sudah lengkap di SALINAN
basis data diubah jadi berkas Hak Pakai, lalu ketiga dokumennya dirakit dua
kali: sekali dengan pemohon perorangan, sekali dengan badan hukum. Yang
diperiksa adalah kalimat yang memang harus berbeda (Lampiran VI dan VII
Permen ATR/BPN 18/2021), dan bahwa tak satu pun kalimat Hak Milik tersisa.

    python -m unittest uji.uji_hak_pakai
"""
import unittest

from berkas import db, pradaftar
from berkas.dokumen import konteks, templat, terbitkan

from . import dasar
from .uji_web import Dasar as DasarWeb

BH = {
    "bentuk": "PT", "kedudukan": "Kota Gorontalo", "bidang_usaha": "perkebunan",
    "akta_nomor": "12", "akta_tanggal": "2020-03-04", "notaris": "Rina Wahyuni, S.H., M.Kn.",
    "notaris_kota": "Gorontalo",
    "pengesahan_oleh": "Menteri Hukum dan Hak Asasi Manusia Republik Indonesia",
    "pengesahan_nomor": "AHU-0012345.AH.01.01.TAHUN 2020", "pengesahan_tanggal": "2020-03-10",
    "akta_ubah_nomor": "7", "akta_ubah_tanggal": "2023-05-02",
    "akta_ubah_notaris": "Rina Wahyuni, S.H., M.Kn.", "akta_ubah_notaris_kota": "Gorontalo",
    "ubah_sah_nomor": "AHU-AH.01.03-0099999", "ubah_sah_tanggal": "2023-05-08",
    "nib": "9120001234567", "nib_tanggal": "2020-04-01",
    "wakil_nama": "Budi Santoso", "wakil_jabatan": "Direktur Utama",
    "csr_akta_nomor": "3", "csr_akta_tanggal": "2024-01-15",
    "csr_notaris": "Rina Wahyuni, S.H., M.Kn.", "csr_notaris_kota": "Gorontalo",
}
NAMA_BH = "PT Maju Jaya Gorontalo"


def _tanpa_penyambung():
    """Kata penyambung lewat Microsoft Word: lambat dan tidak mengubah teks."""
    asli = terbitkan._kata_penyambung
    terbitkan._kata_penyambung = lambda *a, **kw: 0
    return asli


class DokumenHakPakai(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._sambungan = dasar.sambung_salinan()
        cls.k = cls._sambungan.__enter__()
        db.migrasi(cls.k)                    # kolom rincian badan hukum, formulir 190-HP
        cls._penyambung = _tanpa_penyambung()
        hm = [b for b in dasar.berkas_contoh(cls.k) if cls.k.execute(
            "SELECT jenis_hak_dimohon FROM berkas WHERE id=?", (b,)).fetchone()[0] == "HM"]
        if not hm:
            raise unittest.SkipTest("Tidak ada berkas Hak Milik untuk dijadikan contoh.")
        cls.bid = hm[0]
        k = cls.k
        k.execute("UPDATE berkas SET jenis_hak_dimohon='HP', jenis_hak_rekomendasi=NULL "
                  "WHERE id=?", (cls.bid,))
        k.execute(db.upsert("risalah", "berkas_id,jangka_waktu_tahun"), (cls.bid, 30))
        k.commit()

    @classmethod
    def tearDownClass(cls):
        terbitkan._kata_penyambung = cls._penyambung
        cls._sambungan.__exit__(None, None, None)

    def _jadikan(self, subjek):
        k = self.k
        p = k.execute("SELECT id, nama FROM pihak WHERE berkas_id=? AND peran IN "
                      "('penerima_hak','pemohon') ORDER BY urut LIMIT 1",
                      (self.bid,)).fetchone()
        k.execute("DELETE FROM pihak_badan_hukum WHERE pihak_id=?", (p["id"],))
        if subjek == "badan_hukum":
            k.execute("UPDATE pihak SET jenis_subjek='badan_hukum', nama=? WHERE id=?",
                      (NAMA_BH, p["id"]))
            kol = ["pihak_id"] + list(BH)
            k.execute(f"INSERT INTO pihak_badan_hukum ({','.join(kol)}) "
                      f"VALUES ({','.join('?' * len(kol))})", [p["id"]] + list(BH.values()))
        else:
            k.execute("UPDATE pihak SET jenis_subjek='perorangan' WHERE id=?", (p["id"],))
        k.commit()

    def _teks(self, jenis):
        return dasar.rakit_teks(self.k, self.bid, jenis)

    def _umum(self, teks, jenis):
        self.assertNotIn("{{", teks, f"penanda tersisa di {jenis}")
        self.assertNotIn("Hak Milik", teks, f"sisa kalimat Hak Milik di {jenis}")

    def test_template_hp_yang_dipakai(self):
        self.assertEqual(terbitkan._varian(self.k, konteks.muat(self.k, self.bid)), "hp")
        for jenis in ("bap", "risalah", "sk"):
            self.assertEqual(templat.kunci(jenis, "hp"), f"{jenis}-hp")
            self.assertEqual(templat.kunci(jenis, ""), jenis)   # Hak Milik tetap

    def test_perorangan(self):
        self._jadikan("perorangan")
        ris, sk = self._teks("risalah"), self._teks("sk")
        for jenis, teks in (("risalah", ris), ("sk", sk), ("bap", self._teks("bap"))):
            self._umum(teks, jenis)
        self.assertIn("Hak Pakai dengan jangka waktu", ris)
        self.assertIn("| 30 Tahun |", ris)
        self.assertIn("Pasal 111 ayat (2) huruf a", ris)
        self.assertIn("selama 30 (tiga puluh) tahun.", ris)
        self.assertNotIn("Badan Hukum", ris)
        self.assertIn("adalah Warga Negara Indonesia", sk)
        self.assertIn("HAK PAKAI DENGAN JANGKA WAKTU SELAMA 30 (TIGA PULUH) TAHUN ATAS NAMA", sk)
        self.assertIn("Hak Pakai ini dapat diperpanjang", sk)
        self.assertNotIn("Perseroan Terbatas", sk)
        self.assertNotIn("Corporate Social Responsibility", sk)

    def test_badan_hukum(self):
        self._jadikan("badan_hukum")
        bap, ris, sk = self._teks("bap"), self._teks("risalah"), self._teks("sk")
        for jenis, teks in (("bap", bap), ("risalah", ris), ("sk", sk)):
            self._umum(teks, jenis)
            self.assertIn(NAMA_BH, teks)
        self.assertNotIn(f"Sdr. {NAMA_BH}", bap)
        self.assertNotIn("Sdr./Sdri.", bap)
        # Risalah: tabel Uraian mengenai Pemohon dan telaah subjek badan hukum
        self.assertIn("| Badan Hukum |", ris)
        self.assertIn("| Pengesahan Badan Hukum | : | Keputusan Menteri Hukum", ris)
        self.assertNotIn("| Perorangan |", ris)
        self.assertNotIn("Nomor Induk Kependudukan", ris)
        self.assertIn("Pasal 111 ayat (2) huruf b", ris)
        self.assertIn("dalam hal ini diwakili oleh Budi Santoso selaku Direktur Utama", ris)
        self.assertIn("Fotokopi Nomor Induk Berusaha 9120001234567", ris)
        # SK: Menimbang huruf a sesuai format A.1.b Lampiran VI
        self.assertIn(f"bahwa {NAMA_BH} adalah badan hukum, berkedudukan di Kota Gorontalo, "
                      "yang menjalankan usaha antara lain dalam bidang perkebunan, yang "
                      "didirikan berdasarkan Akta tanggal 04 Maret 2020 Nomor 12 yang dibuat "
                      "oleh dan di hadapan Rina Wahyuni, S.H., M.Kn., Notaris di Gorontalo", sk)
        self.assertIn("yang perubahannya telah diterima dan dicatat/disetujui berdasarkan "
                      "Keputusan tanggal 08 Mei 2023", sk)
        self.assertIn("Online Single Submission (OSS) tanggal 01 April 2020 dengan Nomor "
                      "Induk Berusaha 9120001234567, sehingga telah memenuhi syarat sebagai "
                      "subjek Hak Pakai Dengan Jangka Waktu;", sk)
        self.assertIn("Corporate Social Responsibility", sk)
        self.assertIn("Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas;", sk)
        self.assertIn(f"Memberikan kepada {NAMA_BH} berkedudukan di Kota Gorontalo, HAK PAKAI "
                      "DENGAN JANGKA WAKTU selama 30 (tiga puluh) tahun", sk)
        self.assertNotIn("Warga Negara Indonesia", sk)
        self.assertNotIn("Kartu Tanda Penduduk", sk)

    def test_badan_hukum_kurang_rincian_diperingatkan(self):
        self._jadikan("badan_hukum")
        self.k.execute("UPDATE pihak_badan_hukum SET bidang_usaha=NULL, nib=NULL WHERE "
                       "pihak_id IN (SELECT id FROM pihak WHERE berkas_id=?)", (self.bid,))
        self.k.commit()
        pesan = " ".join(p for _, p in konteks.periksa(self.k, self.bid))
        self.assertIn("bidang usaha", pesan)
        self.assertIn("NIB/OSS", pesan)

    def test_formulir_loket_hak_pakai(self):
        f = pradaftar.formulir(self.k, "HP", "baru")
        self.assertEqual(f["kode"], "190-HP")
        self.assertEqual(pradaftar.formulir(self.k, "HM", "baru")["kode"], "184-HM")
        butir = self.k.execute("SELECT * FROM ref_kelengkapan_butir WHERE kelengkapan_id=? "
                               "ORDER BY urut", (f["id"],)).fetchall()
        b = [dict(x) for x in butir]
        pohon_po = pradaftar._rakit(b, {}, "perorangan", "tanah_negara")
        pohon_bh = pradaftar._rakit(b, {}, "badan_hukum", "tanah_negara")
        cari = lambda pohon: next(n for n in pohon[1]["anak"] if n["nama"] == "Badan Hukum")
        self.assertFalse(cari(pohon_po)["berlaku"])
        self.assertTrue(cari(pohon_bh)["berlaku"])
        self.assertEqual([n["penanda"] for n in pohon_bh],
                         [str(i) for i in range(1, 12)])


class WebHakPakai(DasarWeb):
    """Isian rincian badan hukum di tab Pihak, dan tab Hak Pakai di menu Template."""

    def _form(self, jenis_hak, **lain):
        data = {"status": "draf", "jenis_kegiatan": "baru", "jenis_hak_dimohon": jenis_hak,
                "penerima_jenis_subjek": "badan_hukum", "penerima_nama": NAMA_BH,
                "bh_akta_nomor": "12", "bh_kedudukan": "Kota Gorontalo"}
        data.update(lain)
        return data

    def _rincian(self, bid):
        k = db.sambung()
        try:
            r = k.execute("SELECT b.* FROM pihak_badan_hukum b JOIN pihak p ON p.id=b.pihak_id "
                          "WHERE p.berkas_id=?", (bid,)).fetchone()
            return dict(r) if r else {}
        finally:
            k.close()

    def test_rincian_badan_hukum_tersimpan_dan_tidak_hilang(self):
        c = self.klien(masuk=True)
        j = c.post("/berkas/baru", data=self._form("HP"))
        bid = j.headers["Location"].split("/berkas/")[1].split("?")[0]
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertIn("Rincian untuk SK Hak Pakai", halaman)
        j = c.post(f"/berkas/{bid}", data=self._form(
            "HP", bh_bidang_usaha="perkebunan", bh_notaris_kota="Gorontalo",
            bh_wakil_nik="7501020907600001", bh_akta_ubah_nomor="7"))
        self.assertEqual(j.status_code, 303)
        r = self._rincian(bid)
        self.assertEqual(r["bidang_usaha"], "perkebunan")
        self.assertEqual(r["wakil_nik"], "7501020907600001")
        self.assertEqual(r["akta_ubah_nomor"], "7")

        # Jenis haknya diganti: medannya tak tampak, tetapi isinya ikut terkirim
        c.post(f"/berkas/{bid}", data=self._form(
            "HM", bh_bidang_usaha="perkebunan", bh_notaris_kota="Gorontalo",
            bh_wakil_nik="7501020907600001", bh_akta_ubah_nomor="7"))
        halaman = c.get(f"/berkas/{bid}").get_data(as_text=True)
        self.assertNotIn("Rincian untuk SK Hak Pakai", halaman)
        self.assertIn('name="bh_bidang_usaha" value="perkebunan"', halaman)
        self.assertEqual(self._rincian(bid)["bidang_usaha"], "perkebunan")

    def test_tab_hak_pakai_di_menu_template(self):
        halaman = self.klien(masuk=True).get("/template").get_data(as_text=True)
        self.assertIn('id="t-hp"', halaman)
        for nama in ("BAP · Hak Pakai", "Risalah · Hak Pakai", "SK · Hak Pakai"):
            self.assertIn(nama, halaman)


if __name__ == "__main__":
    unittest.main()
