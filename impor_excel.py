# -*- coding: utf-8 -*-
"""Pindahkan berkas dari Excel lama ke skema baru.

    python impor_excel.py                  semua sumber yang ada
    python impor_excel.py wakaf            satu sumber saja
    python impor_excel.py D:\\data\\lain.xlsx  berkas tertentu (profil ditebak)

Kolomnya dipecah: riwayat perolehan dan dokumen pendukung jadi baris, luas jadi
angka, tanggal jadi satu kolom, dan desa/kecamatan/pejabat masuk daftar induk.
Baris yang datanya kurang tetap dimasukkan dan ditandai, bukan ditolak.

Dua sumber dikenali (lihat PROFIL):

  rutin  «Copy of Rutin 2025 database ...xlsx» - berkas Hak Milik, satu pemohon.
  wakaf  «wakaf.xlsx» - berkas Hak Wakaf: kolom «Atas Nama» memuat seluruh Nazhir
         dipisah koma, «KTP Sebelumnya» adalah Wakif, dan empat surat khusus wakaf
         (Akta Ikrar Wakaf, pengesahan Nazhir, kesediaan, kesediaan diaudit) masuk
         ke slot bakunya sendiri, bukan jadi "tambahan surat" tanpa nama.

Aman dijalankan berulang: berkas yang sudah ada - dikenali dari nama penerima dan
nomor Peta Bidang Tanah - dilewati, tidak digandakan.
"""
import os
import re
import sys

import openpyxl

import db
import konteks
import util
import wilayah

DIR_INDUK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMBER = os.path.join(DIR_INDUK, "RAHMA WONTOGIA",
                      "Copy of Rutin 2025 database new UPDATE DISINI YA (1).xlsx")
SUMBER_WAKAF = os.path.join(DIR_INDUK, "wakaf", "wakaf.xlsx")

PANITIA = {
    "nomor_sk": "02/SK-75.03.HP.01/I/2026",
    "tanggal_sk": "2026-01-05",
    "berlaku_dari": "2026-01-05",
    "keterangan": "Susunan Panitia A yang dirujuk pada dokumen contoh",
    "anggota": [
        ("SILVA R. UNO, S.H.", "19820405 200312 2 002",
         "Kepala Seksi Penetapan Hak dan Pendaftaran", "Ketua merangkap Anggota",
         "Bahwa pemohon telah melengkapi persyaratan administratif dan telah memenuhi syarat "
         "sebagai pemegang hak sehingga dapat dipertimbangkan untuk dikabulkan."),
        ("FIRMANSYAH KADIR SABA, S.Tr.", "19890825 200903 1 001",
         "Kepala Seksi Survei dan Pemetaan", "Anggota",
         "Bahwa data fisik tanah yang dimohon telah memenuhi persyaratan sehingga dapat "
         "mendukung penetapan haknya."),
        ("ASDA ICHSANTO UTOMO, S.T.", "19850728 200912 1 003",
         "Kepala Seksi Penataan dan Pemberdayaan", "Anggota",
         "Bahwa penggunaan tanah yang dimohon telah sesuai rencana tata ruang wilayah "
         "Kabupaten Bone Bolango sehingga dapat mendukung penetapan haknya."),
        ("SRI BINTANG PAMUNGKASLARA, S.Si", "19940830 201903 1 001",
         "Penata Pertanahan Pertama", "Sekretaris merangkap Anggota",
         "Bahwa pemohon telah melengkapi persyaratan administratif terhadap tanah yang dimohon "
         "sehingga dapat dipertimbangkan untuk diberikan haknya."),
    ],
}

# Susunan yang dirujuk dokumen contoh wakaf. SK-nya lain dari susunan berkas rutin,
# jadi didaftarkan sendiri - berkas yang sudah dicetak tetap merujuk susunan yang benar.
PANITIA_WAKAF = {
    "nomor_sk": "156.1/SK-75.03.HP.01/VIII/2026",
    "tanggal_sk": "2026-08-30",
    "berlaku_dari": "2026-08-30",
    "keterangan": "Perubahan Keempat - susunan yang dirujuk berkas wakaf",
    "anggota": [
        ("BAHMID KASIM M. HULOPI, S.E.", "19871005 200912 1 002",
         "Kepala Seksi Penetapan Hak dan Pendaftaran", "Ketua merangkap Anggota",
         "Bahwa pemohon telah memenuhi syarat sebagai pemegang hak dan telah melengkapi "
         "persyaratan administratif sehingga dapat dipertimbangkan untuk dikabulkan."),
        ("SEP HAMDAN RIFANUDDIN, S.T.", "19950917 201903 1 003",
         "Kepala Seksi Survei dan Pemetaan", "Anggota",
         "Bahwa data fisik tanah yang dimohon telah memenuhi persyaratan sehingga dapat "
         "mendukung penetapan haknya."),
        ("ASDA ICHSANTO UTOMO, S.T.", "19850728 200912 1 003",
         "Kepala Seksi Penataan dan Pemberdayaan", "Anggota",
         "Bahwa penggunaan tanah yang dimohon telah sesuai rencana tata ruang wilayah "
         "Kabupaten Bone Bolango sehingga dapat mendukung penetapan haknya."),
        ("FAUZAN WAHYA WINASIS, S.H.", "19950319 202204 1 001",
         "Penata Pertanahan Pertama", "Sekretaris merangkap Anggota",
         "Bahwa pemohon telah melengkapi persyaratan administratif terhadap tanah yang "
         "dimohon sehingga dapat dipertimbangkan untuk diberikan haknya."),
    ],
}

# Surat yang sebenarnya punya slot baku tetapi di Excel menumpang kolom «tambahan
# surat N» tanpa nama slot: dikenali dari isinya. '*' berlaku untuk semua jenis hak.
BAKU_DARI_ISI = {
    "*": [
        ("kuasa", ("surat kuasa",)),
    ],
    "WAKAF": [
        ("akta_ikrar", ("akta ikrar wakaf", "akta ikra wakaf", "ikrar wakaf")),
        ("pengesahan_nazhir", ("pengesahan nazir", "pengesahan nazhir")),
        ("kesediaan_nazhir", ("kesediaan menjadi nazhir", "kesediaan menjadi nazir")),
        ("bersedia_diaudit", ("bersedia diaudit",)),
    ],
}

PROFIL = {
    "rutin": {
        "nama": "Rutin (Hak Milik)",
        "berkas": SUMBER,
        "lembar": "rutin",
        "jenis_hak": "HM",
        "panitia": PANITIA,
        "banyak_penerima": False,
        "peran_sebelumnya": "pemilik_sebelumnya",
    },
    "wakaf": {
        "nama": "Wakaf (Hak Wakaf)",
        "berkas": SUMBER_WAKAF,
        "lembar": None,                 # lembar pertama
        "jenis_hak": "WAKAF",
        "panitia": PANITIA_WAKAF,
        # «Atas Nama» memuat seluruh Nazhir dipisah koma
        "banyak_penerima": True,
        "peran_tambahan": "nazhir",
        "peran_sebelumnya": "wakif",
    },
}


BULAN_ID = {b.lower(): i + 1 for i, b in enumerate(util.BULAN)}
BULAN_ID.update({"agust": 8, "peb": 2, "nop": 11, "okt": 10, "des": 12, "jan": 1,
                 "mar": 3, "apr": 4, "jun": 6, "jul": 7, "sep": 9})


def tanggal_id(v):
    """'29 November 2023' / '29/11/2023' / datetime -> 'YYYY-MM-DD'."""
    if v in (None, ""):
        return None
    if hasattr(v, "year"):
        return f"{v.year:04d}-{v.month:02d}-{v.day:02d}"
    s = str(v).strip()
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m:
        d, b, t = map(int, m.groups())
        return f"{t:04d}-{b:02d}-{d:02d}"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", s)
    if m:
        d, nb, t = m.group(1), m.group(2).lower(), m.group(3)
        b = BULAN_ID.get(nb) or BULAN_ID.get(nb[:3])
        if b:
            return f"{int(t):04d}-{b:02d}-{int(d):02d}"
    return None


def baca(jalur, lembar=None):
    wb = openpyxl.load_workbook(jalur, data_only=True, read_only=True)
    ws = wb[lembar] if lembar and lembar in wb.sheetnames else wb[wb.sheetnames[0]]
    baris = [r for r in ws.iter_rows(min_row=1, max_row=500, values_only=True)]
    judul = [util.bersihkan(x) for x in baris[0]]
    data = [r for r in baris[1:] if any(v not in (None, "") for v in r)]
    return judul, data


def kol(judul, nama):
    try:
        return judul.index(nama)
    except ValueError:
        return None


def impor(k, jalur=SUMBER, profil="rutin"):
    pf = PROFIL[profil]
    kode_hak = pf["jenis_hak"]
    judul, data = baca(jalur, pf.get("lembar"))
    A = lambda r, n: util.bersihkan(r[kol(judul, n)]) if kol(judul, n) is not None else ""

    # ---- panitia
    c = k.cursor()
    pn = pf["panitia"]
    pan = c.execute("SELECT id FROM ref_panitia WHERE nomor_sk=?",
                    (pn["nomor_sk"],)).fetchone()
    if pan:
        panitia_id = pan[0]
    else:
        c.execute("INSERT INTO ref_panitia (nomor_sk,tanggal_sk,berlaku_dari,keterangan) "
                  "VALUES (?,?,?,?)",
                  (pn["nomor_sk"], pn["tanggal_sk"],
                   pn["berlaku_dari"], pn["keterangan"]))
        panitia_id = c.lastrowid
        for i, (nama, nip, jab, peran, pend) in enumerate(pn["anggota"]):
            c.execute("INSERT INTO ref_panitia_anggota "
                      "(panitia_id,urut,nama,nip,jabatan,peran,pendapat_baku) VALUES (?,?,?,?,?,?,?)",
                      (panitia_id, i, nama, nip, jab, peran, pend))

    # ---- wilayah
    def desa_id(nama_kec, nama_desa, jenis, jabatan, pejabat):
        if not nama_desa:
            return None
        nama_kec = nama_kec or "(tanpa kecamatan)"
        row = c.execute("SELECT id FROM ref_kecamatan WHERE nama=?", (nama_kec,)).fetchone()
        if row:
            kid = row[0]
        else:
            c.execute("INSERT INTO ref_kecamatan (nama) VALUES (?)", (nama_kec,))
            kid = c.lastrowid
        row = c.execute("SELECT id, nama_pejabat FROM ref_desa WHERE kecamatan_id=? AND nama=?",
                        (kid, nama_desa)).fetchone()
        if row:
            did, sudah_ada = row[0], row[1]
        else:
            c.execute("INSERT INTO ref_desa (kecamatan_id,nama,jenis,jabatan_pejabat) "
                      "VALUES (?,?,?,?)",
                      (kid, nama_desa, jenis or "Desa",
                       jabatan or wilayah.jabatan_baku(jenis)))
            did, sudah_ada = c.lastrowid, None
        # Pejabat masuk sebagai baris riwayat, bukan langsung ke ref_desa - yang di
        # Excel dianggap pejabat saat itu dan jadi yang aktif kalau belum ada.
        if pejabat and not sudah_ada:
            wilayah.simpan_pejabat(k, did, None, pejabat,
                                   jabatan or wilayah.jabatan_baku(jenis))
        return did

    masuk, ditandai, dilewati = 0, 0, 0
    for r in data:
        nama_penerima = A(r, "Atas Nama") or A(r, "Nama Pemohon")
        if not nama_penerima:
            continue
        nama_pemohon = A(r, "Nama Pemohon")
        catatan = []

        # Satu sumber boleh diimpor berkali-kali tanpa menggandakan berkas: nama
        # penerima + nomor Peta Bidang Tanah sudah cukup membedakan satu permohonan.
        # nama yang dicocokkan = nama yang memang disimpan sebagai penerima hak.
        # Hanya sumber ber-banyak-penerima yang memecah «Atas Nama» di koma; pada
        # sumber biasa koma justru bagian dari namanya ("Fenny Ansow, SE").
        nama_utama = (nama_penerima.split(",")[0].strip()
                      if pf["banyak_penerima"] else nama_penerima)
        if _sudah_ada(k, nama_utama, A(r, "Nomor PBT")):
            dilewati += 1
            continue

        jenis_desa = (A(r, "Desa / Kelurahan") or "Desa").strip()
        did = desa_id(A(r, "Kecamatan"), A(r, "Desa"), jenis_desa,
                      A(r, "Pejabat Kelurahan desa"), A(r, "Nama Kepala Desa"))
        if not did:
            catatan.append("desa belum terisi")

        c.execute("INSERT INTO berkas (nomor_berkas,tanggal_permohonan,jenis_hak_dimohon,"
                  "jenis_kegiatan,asal_tanah,kewenangan,status,catatan) VALUES (?,?,?,?,?,?,?,?)",
                  (None, tanggal_id(A(r, "Tgl Surat Permohonan")), kode_hak,
                   "baru", "tanah_negara", "kantah", "selesai", None))
        bid = c.lastrowid

        # --- pihak
        # Pada berkas wakaf «Atas Nama» memuat seluruh Nazhir dipisah koma: orang
        # pertama jadi penerima hak, sisanya baris Nazhir tersendiri. Identitas tiap
        # orang diisi sekali di situ - Risalah mencetaknya dari baris itu.
        jk = A(r, "Jenis Kelamin")
        if not jk and not pf["banyak_penerima"]:
            catatan.append("jenis kelamin kosong")
        orang = ([x.strip() for x in nama_penerima.split(",") if x.strip()]
                 if pf["banyak_penerima"] else [nama_penerima])
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,ttl,jenis_kelamin,"
                  "alamat,pekerjaan,urut) VALUES (?,?,?,?,?,?,?,?,?,0)",
                  (bid, "penerima_hak", "perorangan", orang[0], A(r, "NIK"), A(r, "TTL"),
                   jk, A(r, "Alamat"), A(r, "Pekerjaan")))
        for i, nama_lain in enumerate(orang[1:], start=1):
            c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,alamat,urut) "
                      "VALUES (?,?,?,?,?,?)",
                      (bid, pf["peran_tambahan"], "perorangan", nama_lain, A(r, "Alamat"), i))
            catatan.append(f"NIK & TTL {pf['peran_tambahan']} {nama_lain} belum ada di Excel")
        if nama_pemohon and nama_pemohon != orang[0]:
            c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,urut) VALUES (?,?,?,?,9)",
                      (bid, "kuasa", "perorangan", nama_pemohon))
        for judul_kol in ("KTP Sebelumnya", "Pemilik Sebelumnya 2"):
            v = A(r, judul_kol)
            if v:
                c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,urut) "
                          "VALUES (?,?,?,?,10)",
                          (bid, pf["peran_sebelumnya"], "perorangan", v))

        # --- bidang tanah
        luas_pbt = util.angka_dari_teks(A(r, "Luas"))
        luas_surat = util.angka_dari_teks(A(r, "Luas Surat tanah"))
        if luas_pbt is None:
            catatan.append("luas tidak terbaca")
        c.execute("INSERT INTO bidang_tanah (berkas_id,desa_id,nomor_pbt,tanggal_pbt,nib,"
                  "luas_pbt,luas_surat,batas_utara,batas_timur,batas_selatan,batas_barat,"
                  "penggunaan_sekarang,rencana_penggunaan,rtrw,kesesuaian,tanggal_peta_analisis) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (bid, did, A(r, "Nomor PBT"), tanggal_id(A(r, "Tgl PBT")), A(r, "NIB"),
                   luas_pbt, luas_surat,
                   A(r, "Batas Utara"), A(r, "Batas Timur"),
                   A(r, "Batas Selatan"), A(r, "Batas Barat"),
                   A(r, "Penggunaan Tanah"), A(r, "rencana penggunaan"), A(r, "RTRW"),
                   _rapikan_kesesuaian(A(r, "Kesesuaian penggunaan tanah")),
                   tanggal_id(A(r, "tgl Peta analisis"))))

        # --- riwayat: 10 pasang kolom -> baris
        urut = 0
        for i in range(1, 11):
            jenis = A(r, f"Jenis Alas Hak {i}") or A(r, f"jenis alas hak {i}")
            surat = A(r, f"Surat {i}") or A(r, f"surat {i}")
            if not jenis and not surat:
                continue
            if jenis:
                c.execute("INSERT INTO riwayat_perolehan (berkas_id,urut,uraian,dokumen_bukti) "
                          "VALUES (?,?,?,?)", (bid, urut, jenis, surat))
                urut += 1
        # Kolom «Surat Penguasaan Fisik» bukan mata rantai riwayat, melainkan kalimat
        # penutup penguasaan. Template sudah mencetaknya sendiri lewat {{penguasaan_fisik}}
        # tepat setelah daftar riwayat, jadi kalimatnya tidak lagi disalin jadi baris
        # riwayat — dulu tercetak dua kali. Isinya = kalimat baku + rujukan «jenis sppf»,
        # dan itu disusun ulang di konteks.py dari dokumen berkategori 'sppf'.

        # --- dokumen pendukung: kolom bernama + 54 kolom tambahan -> baris
        # Urutan mengikuti DATA PENDUKUNG pada Risalah. Kategori 'sppf' dan 'kuasa'
        # punya penanda sendiri di template ({{sppf}}, {{surat_kuasa}}) sehingga tidak
        # ikut diulang di daftar; 'selisih' dipakai menyusun kalimat selisih luas.
        durut = 0
        baku = {}
        sudah_teks = set()
        for kategori, _, nama_kol, _ in db.dokumen_baku(kode_hak):
            v = A(r, nama_kol)
            if v:
                asli, teks = _pisah_keaslian(v)
                c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian) "
                          "VALUES (?,?,?,?,?)", (bid, durut, kategori, teks, asli))
                baku[kategori] = teks
                sudah_teks.add(_seragam(teks))
                durut += 1

        # Kalimat telaah hanya disimpan bila berbeda dari yang bisa disusun sendiri,
        # supaya nilai turunan tidak menumpuk di basis data.
        _simpan_uraian(c, bid, r, A, baku, luas_pbt, luas_surat)
        kolom_bebas = ([f"tambahan surat {i}" for i in range(1, 55)] +
                       [f"Surat {i}" for i in range(1, 11)])
        for nama_kol in kolom_bebas:
            v = A(r, nama_kol) or A(r, nama_kol.lower())
            if not v:
                continue
            asli, teks = _pisah_keaslian(v)
            # Surat yang sebenarnya punya slot baku (mis. Akta Ikrar Wakaf) dikenali
            # dari isinya, supaya tidak berakhir sebagai "tambahan surat" tanpa nama.
            kategori = _kategori_baku(kode_hak, teks, baku)
            if kategori is None:
                kategori = "alas_hak" if nama_kol.lower().startswith("surat") else "tambahan"
            # dan yang isinya persis sama dengan surat yang sudah masuk tidak diulang
            if _seragam(teks) in sudah_teks:
                continue
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian) "
                      "VALUES (?,?,?,?,?)", (bid, durut, kategori, teks, asli))
            sudah_teks.add(_seragam(teks))
            if kategori not in ("tambahan", "alas_hak"):
                baku[kategori] = teks
            durut += 1

        # --- pemeriksaan, risalah, sk
        tgl_bap = tanggal_id(A(r, "Tgl BAP 1")) or tanggal_id(A(r, "Tgl BAP"))
        c.execute("INSERT INTO pemeriksaan (berkas_id,tanggal_surat_tugas,tanggal_bap,panitia_id) "
                  "VALUES (?,?,?,?)", (bid, None, tgl_bap, panitia_id))
        tgl_ris = tanggal_id(A(r, "Tgl Risalah 1")) or tanggal_id(A(r, "Tgl Risalah"))
        c.execute("INSERT INTO risalah (berkas_id,nomor,tanggal,kesimpulan) VALUES (?,?,?,?)",
                  (bid, A(r, "No. Risalah") or None, tgl_ris, "dikabulkan"))
        peng = k.execute("SELECT kunci,nilai FROM pengaturan").fetchall()
        peng = {x[0]: x[1] for x in peng}
        c.execute("INSERT INTO sk (berkas_id,nomor,tanggal,pejabat_nama,pejabat_nip,validasi_pph) "
                  "VALUES (?,?,?,?,?,?)",
                  (bid, A(r, "No. SK") or None, tanggal_id(A(r, "Tgl. SK")),
                   peng.get("kepala_kantor_nama"), peng.get("kepala_kantor_nip"),
                   A(r, "Validasi pph")))

        # --- pendapat anggota (bawaan dari susunan panitia)
        for i, (nama, nip, jab, peran, pend) in enumerate(pn["anggota"]):
            c.execute("INSERT INTO pendapat_anggota (berkas_id,urut,nama,peran,setuju,alasan,"
                      "menandatangani) VALUES (?,?,?,?,1,?,1)", (bid, i, nama, peran, pend))

        if catatan:
            ditandai += 1
            c.execute("UPDATE berkas SET catatan=? WHERE id=?",
                      ("perlu dilengkapi: " + "; ".join(catatan), bid))
        masuk += 1
    k.commit()
    return masuk, ditandai, dilewati


def _sudah_ada(k, nama, nomor_pbt):
    """Benar bila berkas dengan penerima dan nomor PBT itu sudah pernah diimpor."""
    if not nama:
        return False
    if nomor_pbt:
        return bool(k.execute(
            "SELECT 1 FROM berkas b JOIN pihak p ON p.berkas_id=b.id "
            "JOIN bidang_tanah t ON t.berkas_id=b.id "
            "WHERE p.nama=? AND t.nomor_pbt=? LIMIT 1", (nama, nomor_pbt)).fetchone())
    return bool(k.execute(
        "SELECT 1 FROM berkas b JOIN pihak p ON p.berkas_id=b.id "
        "WHERE p.peran='penerima_hak' AND p.nama=? LIMIT 1", (nama,)).fetchone())


def _kategori_baku(kode_hak, teks, sudah):
    """Slot baku yang cocok dengan isi surat, atau None kalau tidak ada.

    Dipakai untuk sumber lama yang menaruh semua surat khusus di kolom «tambahan
    surat N»; slot yang sudah terisi tidak ditimpa.
    """
    rendah = (teks or "").lower()
    for kategori, kata in BAKU_DARI_ISI.get("*", []) + BAKU_DARI_ISI.get(kode_hak, []):
        if kategori in sudah:
            continue
        if any(x in rendah for x in kata):
            return kategori
    return None


def _simpan_uraian(c, bid, r, A, baku, luas_pbt, luas_surat):
    """Isi «Surat Penguasaan Fisik» dan «selisih luas» dari Excel, tetapi hanya
    yang tidak sama dengan kalimat bawaan sistem."""
    otomatis = {
        "uraian_penguasaan_fisik": konteks._penguasaan_fisik(baku.get("sppf", "")),
        "uraian_selisih_luas": _selisih_otomatis(baku, luas_pbt, luas_surat),
    }
    for kolom, _, nama_kol, _ in db.URAIAN_BAKU:
        v = A(r, nama_kol)
        if v and _seragam(v) != _seragam(otomatis[kolom]):
            c.execute(f"UPDATE bidang_tanah SET {kolom}=? WHERE berkas_id=?", (v, bid))


def _selisih_otomatis(baku, luas_pbt, luas_surat):
    if luas_pbt is None or luas_surat is None:
        return ""
    return konteks._kalimat_selisih(int(luas_pbt) - int(luas_surat), luas_pbt, luas_surat,
                                    baku.get("selisih", ""))


def _seragam(t):
    """Bandingkan kalimat tanpa terganggu spasi ganda dan tanda baca menggantung."""
    return re.sub(r"[\s.;,]+", " ", (t or "").lower()).strip()


# Ejaan yang muncul di Excel -> bentuk baku. Harus salah satu nilai di
# web.KEASLIAN, kalau tidak pilihan itu hilang begitu berkas disimpan ulang.
KEASLIAN = {"asli": "Asli", "fotokopi": "Fotokopi", "foto kopi": "Fotokopi",
            "fotocopy": "Fotokopi", "foto copy": "Fotokopi", "salinan": "Salinan",
            "legalisir": "Salinan"}


def _pisah_keaslian(teks):
    t = teks.strip()
    for ejaan, baku in KEASLIAN.items():
        if t.lower().startswith(ejaan + " "):
            return baku, t[len(ejaan):].strip()
    return "", t


def _rapikan_kesesuaian(v):
    """Seragamkan huruf besar/kecil; kalimat bebas dibiarkan apa adanya."""
    t = (v or "").strip()
    rendah = t.lower()
    if rendah == "sesuai":
        return "Sesuai"
    if rendah == "sesuai bersyarat":
        return "Sesuai Bersyarat"
    return t


def _profil_dari_jalur(jalur):
    """Tebak profil dari nama berkasnya; pakai 'rutin' bila tidak terkenali."""
    nama = os.path.basename(jalur).lower()
    for kunci, pf in PROFIL.items():
        if os.path.normcase(os.path.abspath(pf["berkas"])) == \
                os.path.normcase(os.path.abspath(jalur)):
            return kunci
    for kunci in PROFIL:
        if kunci in nama:
            return kunci
    return "rutin"


def main():
    """Tanpa argumen: impor semua sumber yang berkasnya ada. Sudah masuk = dilewati."""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and arg in PROFIL:
        tugas = [(arg, PROFIL[arg]["berkas"])]
    elif arg:
        tugas = [(_profil_dari_jalur(arg), arg)]
    else:
        tugas = [(kunci, pf["berkas"]) for kunci, pf in PROFIL.items()]

    k = db.siapkan()
    total_masuk = total_lewat = 0
    ada_sumber = False
    for profil, jalur in tugas:
        if not os.path.exists(jalur):
            print(f"  ! {PROFIL[profil]['nama']}: berkas Excel tidak ada di {jalur}")
            continue
        ada_sumber = True
        masuk, ditandai, dilewati = impor(k, jalur, profil)
        print(f"  {PROFIL[profil]['nama']:<22} {masuk:>3} berkas masuk, "
              f"{ditandai} ditandai 'perlu dilengkapi', {dilewati} dilewati (sudah ada)")
        total_masuk += masuk
        total_lewat += dilewati
    if not ada_sumber:
        print("Tidak ada berkas Excel yang bisa diimpor.")
        return 1
    print()
    ringkas(k)
    print(f"\n{total_masuk} berkas masuk, {total_lewat} dilewati karena sudah ada.")
    return 0


def ringkas(k):
    q = lambda s: k.execute(s).fetchone()[0]
    print("  berkas            :", q("SELECT COUNT(*) FROM berkas"))
    print("  pihak             :", q("SELECT COUNT(*) FROM pihak"))
    print("  riwayat perolehan :", q("SELECT COUNT(*) FROM riwayat_perolehan"),
          "baris (dulu 20 kolom)")
    print("  dokumen pendukung :", q("SELECT COUNT(*) FROM dokumen_pendukung"),
          "baris (dulu 64 kolom)")
    print("  kecamatan / desa  :", q("SELECT COUNT(*) FROM ref_kecamatan"), "/",
          q("SELECT COUNT(*) FROM ref_desa"))


if __name__ == "__main__":
    raise SystemExit(main())
