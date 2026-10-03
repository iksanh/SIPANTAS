# -*- coding: utf-8 -*-
"""Skema dan koneksi SQLite.

Struktur mengikuti dokumen rancangan: daftar berulang jadi baris (bukan kolom),
nilai turunan tidak disimpan, dan perbedaan antar jenis hak jadi data referensi.
"""
import datetime as dt
import hashlib
import os
import secrets
import sqlite3
from . import basis, jalur, konfigurasi

SAMBUNGAN = konfigurasi.sambungan()

# Untuk SQLite, jalur berkasnya diambil dari konfigurasi — bukan dipatok ke
# data/berkas.db. Tetap variabel modul karena uji dan perkakas pindah data
# menggantinya sewaktu jalan untuk bekerja di atas salinan.
BERKAS_DB = (SAMBUNGAN.argumen["berkas"] if not SAMBUNGAN.postgres
             else jalur.BASIS_DATA)
DIR_DATA = os.path.dirname(BERKAS_DB) or jalur.DATA

SKEMA = """
PRAGMA foreign_keys = ON;

-- ---------- pengguna & sesi ----------
CREATE TABLE IF NOT EXISTS pengguna (
  id INTEGER PRIMARY KEY,
  nama TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  sandi_hash TEXT NOT NULL,
  peran TEXT NOT NULL DEFAULT 'petugas',      -- petugas | admin
  aktif INTEGER NOT NULL DEFAULT 1,
  dibuat TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS sesi (
  token TEXT PRIMARY KEY,
  pengguna_id INTEGER NOT NULL REFERENCES pengguna(id) ON DELETE CASCADE,
  kedaluwarsa TEXT NOT NULL,
  csrf TEXT NOT NULL DEFAULT ''        -- token anti-CSRF, seumur sesi
);

-- ---------- referensi ----------
CREATE TABLE IF NOT EXISTS ref_jenis_hak (
  kode TEXT PRIMARY KEY,                      -- HM, HGB, HP, HPL, WAKAF, HMSRS
  nama TEXT NOT NULL,
  ada_jangka_waktu INTEGER NOT NULL DEFAULT 0,
  jangka_maks INTEGER,                        -- tahun
  perpanjangan_maks INTEGER,
  pembaruan_maks INTEGER,
  wajib_uang_pemasukan INTEGER NOT NULL DEFAULT 0,
  subjek_boleh TEXT NOT NULL DEFAULT 'perorangan,badan_hukum',
  kegiatan_boleh TEXT NOT NULL DEFAULT 'baru',
  dasar_subjek TEXT,                          -- rujukan pasal
  kode_sk TEXT,                               -- kode pada nomor SK (HM, HGB, HW, ...)
  varian_template TEXT NOT NULL DEFAULT '',   -- '' = template baku, 'wakaf' = templat wakaf
  urut INTEGER NOT NULL DEFAULT 0,
  aktif INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS ref_kecamatan (
  id INTEGER PRIMARY KEY, nama TEXT NOT NULL UNIQUE,
  kode TEXT                                   -- kode wilayah Kemendagri, mis. 75.03.02
);
CREATE TABLE IF NOT EXISTS ref_desa (
  id INTEGER PRIMARY KEY,
  kecamatan_id INTEGER NOT NULL REFERENCES ref_kecamatan(id),
  nama TEXT NOT NULL,
  jenis TEXT NOT NULL DEFAULT 'Desa',         -- Desa | Kelurahan
  kode TEXT,                                  -- kode wilayah Kemendagri
  -- Dua kolom di bawah ini salinan pejabat yang sedang aktif di ref_desa_pejabat,
  -- dipelihara wilayah.segarkan(); dokumen membacanya dari sini.
  jabatan_pejabat TEXT NOT NULL DEFAULT 'Kepala Desa',
  nama_pejabat TEXT,
  UNIQUE (kecamatan_id, nama)
);
-- Kepala desa/lurah berganti (definitif, Pj., Plt.) sementara berkas lama harus
-- tetap terbaca, jadi yang lama disimpan sebagai riwayat dan satu ditandai aktif.
CREATE TABLE IF NOT EXISTS ref_desa_pejabat (
  id INTEGER PRIMARY KEY,
  desa_id INTEGER NOT NULL REFERENCES ref_desa(id) ON DELETE CASCADE,
  nama TEXT NOT NULL,
  jabatan TEXT NOT NULL DEFAULT 'Kepala Desa',
  mulai TEXT, sampai TEXT,
  sk_nomor TEXT, catatan TEXT,
  aktif INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ref_panitia (
  id INTEGER PRIMARY KEY,
  nomor_sk TEXT NOT NULL,
  tanggal_sk TEXT,
  berlaku_dari TEXT,
  berlaku_sampai TEXT,
  keterangan TEXT
);
CREATE TABLE IF NOT EXISTS ref_panitia_anggota (
  id INTEGER PRIMARY KEY,
  panitia_id INTEGER NOT NULL REFERENCES ref_panitia(id) ON DELETE CASCADE,
  urut INTEGER NOT NULL DEFAULT 0,
  nama TEXT NOT NULL, nip TEXT, jabatan TEXT, peran TEXT,
  pendapat_baku TEXT
);
CREATE TABLE IF NOT EXISTS ref_klausa (
  id INTEGER PRIMARY KEY,
  slot TEXT NOT NULL,                         -- nama slot yang dipanggil template
  jenis_hak TEXT NOT NULL DEFAULT '*',        -- '*' atau daftar dipisah koma
  kegiatan TEXT NOT NULL DEFAULT '*',
  subjek TEXT NOT NULL DEFAULT '*',
  berlaku_dari TEXT, berlaku_sampai TEXT,
  isi TEXT NOT NULL,
  catatan TEXT
);
CREATE TABLE IF NOT EXISTS ref_dokumen_syarat (
  id INTEGER PRIMARY KEY,
  jenis_hak TEXT NOT NULL DEFAULT '*',
  kegiatan TEXT NOT NULL DEFAULT '*',
  kategori TEXT NOT NULL DEFAULT 'umum',
  nama TEXT NOT NULL,
  wajib INTEGER NOT NULL DEFAULT 1,
  dasar TEXT,
  urut INTEGER NOT NULL DEFAULT 0
);

-- ---------- referensi: daftar kelengkapan (formulir loket) ----------
-- Sengaja terpisah dari ref_dokumen_syarat, yang menjawab pertanyaan lain:
-- "apa yang harus dikutip Risalah/SK". Formulir lampiran Permen memuat butir
-- yang justru keluaran Kantah sendiri — Peta Bidang Tanah, Risalah Pemeriksaan
-- Tanah A, Surat Pengantar — dan itu tidak masuk akal sebagai peringatan pada
-- berkas. Yang beririsan ditautkan lewat slot_baku dan syarat_id.
CREATE TABLE IF NOT EXISTS ref_kelengkapan (
  id INTEGER PRIMARY KEY,
  kode TEXT NOT NULL UNIQUE,                  -- 184-HM
  judul TEXT NOT NULL,
  jenis_hak TEXT NOT NULL DEFAULT '*',
  kegiatan TEXT NOT NULL DEFAULT '*',
  dasar TEXT,                                 -- rujukan lampiran & halamannya
  varian_template TEXT NOT NULL DEFAULT '',   -- '' -> checklist.docx, 'hm' -> checklist-hm.docx
  aktif INTEGER NOT NULL DEFAULT 1,
  -- 1 = nomor & huruf butir disusun ulang sendiri tiap kali susunannya diubah
  nomor_otomatis INTEGER NOT NULL DEFAULT 1,
  urut INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ref_kelengkapan_butir (
  id INTEGER PRIMARY KEY,
  kelengkapan_id INTEGER NOT NULL REFERENCES ref_kelengkapan(id) ON DELETE CASCADE,
  induk_id INTEGER REFERENCES ref_kelengkapan_butir(id) ON DELETE CASCADE,
  penanda TEXT NOT NULL DEFAULT '',           -- '1','2','a','j' — apa adanya dari formulir
  -- nama = bunyi formulirnya, disalin verbatim supaya cetakannya sama persis
  -- dengan lampiran Permen, termasuk keterangan dalam kurung.
  -- nama_dokumen = nama pendek suratnya, dipakai saat butir ini disalin jadi
  -- baris dokumen pada berkas. Kosong berarti pakai `nama`.
  nama TEXT NOT NULL,
  nama_dokumen TEXT,
  -- butir       dicentang Ada / Tidak Ada
  -- judul       sub-judul tebal, tidak dicentang ("Identitas Pemohon")
  -- alternatif  salah satu di antara sesama anak induknya sudah cukup
  sifat TEXT NOT NULL DEFAULT 'butir',
  wajib INTEGER NOT NULL DEFAULT 1,
  isian_bebas INTEGER NOT NULL DEFAULT 0,     -- butir yang berakhir "……"
  -- kapan butir ini berlaku; '*' = selalu. Polanya sama dengan ref_klausa.
  subjek TEXT NOT NULL DEFAULT '*',
  asal_tanah TEXT NOT NULL DEFAULT '*',
  slot_baku TEXT,                             -- kategori di DOKUMEN_BAKU, bila sepadan
  syarat_id INTEGER REFERENCES ref_dokumen_syarat(id),
  dasar TEXT,
  -- jamak = boleh diisi lebih dari satu surat (mis. dua akta pemindahan hak).
  -- Uraiannya disimpan berbaris di pradaftar_jawab.uraian, satu surat sebaris.
  jamak INTEGER NOT NULL DEFAULT 0,
  -- aktif=0: dihapus dari formulir, tetapi masih dijawab pradaftar lama, jadi
  -- barisnya disimpan supaya cetakan dan berkas lama tidak berubah.
  aktif INTEGER NOT NULL DEFAULT 1,
  urut INTEGER NOT NULL DEFAULT 0
);

-- ---------- berkas ----------
CREATE TABLE IF NOT EXISTS berkas (
  id INTEGER PRIMARY KEY,
  nomor_berkas TEXT,
  tanggal_permohonan TEXT,
  jenis_hak_dimohon TEXT NOT NULL REFERENCES ref_jenis_hak(kode),
  jenis_hak_rekomendasi TEXT REFERENCES ref_jenis_hak(kode),   -- Ps. 139 ayat (5)
  jenis_kegiatan TEXT NOT NULL DEFAULT 'baru',  -- baru|perpanjangan|pembaruan|peningkatan
  asal_tanah TEXT NOT NULL DEFAULT 'tanah_negara',  -- tanah_negara | hak_pengelolaan
  kewenangan TEXT NOT NULL DEFAULT 'kantah',    -- kantah | kanwil | menteri
  status TEXT NOT NULL DEFAULT 'draf',          -- draf|diperiksa|selesai|ditolak
  catatan TEXT,
  dibuat_oleh INTEGER REFERENCES pengguna(id),
  dibuat TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  diubah TEXT
);
CREATE TABLE IF NOT EXISTS pihak (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  peran TEXT NOT NULL,                        -- pemohon|kuasa|pemilik_sebelumnya|ahli_waris|saksi|nazhir|wakif
  jenis_subjek TEXT NOT NULL DEFAULT 'perorangan',
  nama TEXT NOT NULL, nik TEXT, ttl TEXT, jenis_kelamin TEXT,
  alamat TEXT, pekerjaan TEXT, urut INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pihak_badan_hukum (
  pihak_id INTEGER PRIMARY KEY REFERENCES pihak(id) ON DELETE CASCADE,
  bentuk TEXT, kedudukan TEXT,
  akta_nomor TEXT, akta_tanggal TEXT, notaris TEXT,
  akta_ubah_nomor TEXT, akta_ubah_tanggal TEXT,
  pengesahan_nomor TEXT, pengesahan_tanggal TEXT,
  npwp TEXT, nib TEXT,
  wakil_nama TEXT, wakil_jabatan TEXT, wakil_nik TEXT,
  -- rincian Menimbang huruf a SK Hak Pakai untuk badan hukum (Lampiran VI
  -- Permen ATR/BPN 18/2021); lihat KOLOM_BH_RINCIAN
  bidang_usaha TEXT, notaris_kota TEXT, pengesahan_oleh TEXT,
  akta_ubah_notaris TEXT, akta_ubah_notaris_kota TEXT,
  ubah_sah_nomor TEXT, ubah_sah_tanggal TEXT, nib_tanggal TEXT,
  csr_akta_nomor TEXT, csr_akta_tanggal TEXT, csr_notaris TEXT, csr_notaris_kota TEXT
);
CREATE TABLE IF NOT EXISTS bidang_tanah (
  berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id) ON DELETE CASCADE,
  desa_id INTEGER REFERENCES ref_desa(id),
  nomor_pbt TEXT, tanggal_pbt TEXT, nib TEXT,
  luas_pbt INTEGER, luas_surat INTEGER,
  batas_utara TEXT, batas_timur TEXT, batas_selatan TEXT, batas_barat TEXT,
  penggunaan_sekarang TEXT, rencana_penggunaan TEXT,
  rtrw TEXT, kesesuaian TEXT, tanggal_peta_analisis TEXT,
  -- dua kalimat telaah di bawah ini dihitung sendiri bila dikosongkan;
  -- diisi hanya kalau kalimat bawaannya perlu ditulis lain
  uraian_penguasaan_fisik TEXT,
  uraian_selisih_luas TEXT
);
CREATE TABLE IF NOT EXISTS riwayat_perolehan (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  urut INTEGER NOT NULL DEFAULT 0,
  uraian TEXT NOT NULL,
  dokumen_bukti TEXT
);
CREATE TABLE IF NOT EXISTS hak_asal (
  berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id) ON DELETE CASCADE,
  jenis_hak_lama TEXT, nomor_sertipikat TEXT, nomor_sk TEXT,
  tanggal_sk TEXT, tanggal_berakhir TEXT, luas INTEGER
);
CREATE TABLE IF NOT EXISTS dokumen_pendukung (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  urut INTEGER NOT NULL DEFAULT 0,
  kategori TEXT DEFAULT 'tambahan',
  uraian TEXT NOT NULL,
  keaslian TEXT DEFAULT 'Asli',
  -- rincian surat yang kalimat SK-nya berformat tetap (lihat RINCIAN_BAKU)
  jenis TEXT, nomor TEXT, tanggal TEXT, pejabat TEXT, wilayah_pejabat TEXT
);
CREATE TABLE IF NOT EXISTS pemeriksaan (
  berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id) ON DELETE CASCADE,
  tanggal_surat_tugas TEXT,                   -- awal tenggat 14 hari kerja (Ps. 136)
  tanggal_bap TEXT,
  panitia_id INTEGER REFERENCES ref_panitia(id),
  keberatan TEXT, catatan TEXT
);
CREATE TABLE IF NOT EXISTS foto_lapang (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  urut INTEGER NOT NULL DEFAULT 0,
  nama_file TEXT NOT NULL, keterangan TEXT
);
CREATE TABLE IF NOT EXISTS pendapat_anggota (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  urut INTEGER NOT NULL DEFAULT 0,
  nama TEXT NOT NULL, peran TEXT,
  setuju INTEGER NOT NULL DEFAULT 1,          -- Ps. 139 ayat (4)
  alasan TEXT,
  menandatangani INTEGER NOT NULL DEFAULT 1,  -- Ps. 139 ayat (6) & (7)
  diwakili_oleh TEXT                          -- Ps. 139 ayat (3)
);
CREATE TABLE IF NOT EXISTS risalah (
  berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id) ON DELETE CASCADE,
  nomor TEXT, tanggal TEXT,
  kesimpulan TEXT DEFAULT 'dikabulkan',       -- dikabulkan|ditolak|dilengkapi
  jangka_waktu_tahun INTEGER,
  alasan TEXT
);
CREATE TABLE IF NOT EXISTS sk (
  berkas_id INTEGER PRIMARY KEY REFERENCES berkas(id) ON DELETE CASCADE,
  nomor TEXT, tanggal TEXT,
  pejabat_nama TEXT, pejabat_nip TEXT,
  validasi_pph TEXT, uang_pemasukan INTEGER
);
CREATE TABLE IF NOT EXISTS nomor_urut (
  jenis TEXT NOT NULL, kode TEXT NOT NULL, tahun INTEGER NOT NULL,
  terakhir INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (jenis, kode, tahun)
);
CREATE TABLE IF NOT EXISTS dokumen_terbit (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER NOT NULL REFERENCES berkas(id) ON DELETE CASCADE,
  jenis_dokumen TEXT NOT NULL,                -- bap|risalah|sk|penolakan
  nomor TEXT, nama_file TEXT NOT NULL,
  dicetak_oleh INTEGER REFERENCES pengguna(id),
  dicetak_pada TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ---------- pradaftar: kelengkapan berkas sebelum didaftar di loket ----------
-- Berdiri sendiri, bukan tahap di dalam `berkas`: permohonan yang belum
-- lengkap tidak boleh memakan nomor berkas, dan seluruh pemeriksaan Panitia A
-- tidak berlaku untuknya. Naik jadi berkas lewat pradaftar.py:terima().
CREATE TABLE IF NOT EXISTS pradaftar (
  id INTEGER PRIMARY KEY,
  nomor TEXT,                                 -- diberi saat diterima di loket
  tanggal TEXT NOT NULL,
  jenis_hak TEXT NOT NULL REFERENCES ref_jenis_hak(kode),
  jenis_kegiatan TEXT NOT NULL DEFAULT 'baru',
  asal_tanah TEXT NOT NULL DEFAULT 'tanah_negara',
  kelengkapan_id INTEGER REFERENCES ref_kelengkapan(id),
  pemohon_nama TEXT NOT NULL,
  pemohon_jenis_subjek TEXT NOT NULL DEFAULT 'perorangan',
  pemohon_nik TEXT, pemohon_alamat TEXT, pemohon_telepon TEXT,
  kuasa_nama TEXT, kuasa_nik TEXT,
  desa_id INTEGER REFERENCES ref_desa(id),
  letak_lain TEXT, luas_surat INTEGER, nomor_pbt TEXT,
  -- baru | diterima | dikembalikan | batal
  -- "lengkap"/"kurang" TIDAK disimpan di sini: dihitung dari pradaftar_jawab,
  -- supaya tidak ada baris bertanda lengkap yang jawabannya sudah berubah.
  status TEXT NOT NULL DEFAULT 'baru',
  catatan TEXT,
  alasan_terima TEXT,                         -- bila diterima walau belum lengkap
  berkas_id INTEGER REFERENCES berkas(id) ON DELETE SET NULL,
  dibuat_oleh INTEGER REFERENCES pengguna(id),
  dibuat TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  diubah TEXT
);
CREATE TABLE IF NOT EXISTS pradaftar_jawab (
  pradaftar_id INTEGER NOT NULL REFERENCES pradaftar(id) ON DELETE CASCADE,
  butir_id INTEGER NOT NULL REFERENCES ref_kelengkapan_butir(id) ON DELETE CASCADE,
  -- 0 tidak ada | 1 ada | 2 tidak berlaku | 3 ada tapi perlu koreksi
  ada INTEGER NOT NULL DEFAULT 0,
  uraian TEXT,                                -- isi titik-titik pada butir isian_bebas
  -- apa yang harus diperbaiki, bila ada=3. Disimpan sebagai teks, bukan
  -- rujukan ke ref_catatan_koreksi: menyunting daftar baku tidak boleh
  -- mengubah bunyi pemeriksaan dan surat pengembalian yang sudah lewat.
  catatan TEXT,
  PRIMARY KEY (pradaftar_id, butir_id)
);

-- ---------- referensi: catatan koreksi baku ----------
-- Pilihan cepat untuk kotak catatan pada butir yang "ada tapi perlu koreksi".
-- Petugas tetap boleh mengetik catatan sendiri; daftar ini hanya supaya
-- kalimat yang sering dipakai tidak diketik ulang dengan ejaan berbeda-beda.
-- butir_id kosong = berlaku untuk semua butir.
CREATE TABLE IF NOT EXISTS ref_catatan_koreksi (
  id INTEGER PRIMARY KEY,
  butir_id INTEGER REFERENCES ref_kelengkapan_butir(id) ON DELETE CASCADE,
  teks TEXT NOT NULL,
  aktif INTEGER NOT NULL DEFAULT 1,
  urut INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pengaturan (
  kunci TEXT PRIMARY KEY, nilai TEXT
);

CREATE INDEX IF NOT EXISTS ix_pihak_berkas ON pihak(berkas_id);
CREATE INDEX IF NOT EXISTS ix_riwayat_berkas ON riwayat_perolehan(berkas_id, urut);
CREATE INDEX IF NOT EXISTS ix_dok_berkas ON dokumen_pendukung(berkas_id, urut);
CREATE INDEX IF NOT EXISTS ix_desa_kec ON ref_desa(kecamatan_id);
CREATE INDEX IF NOT EXISTS ix_pejabat_desa ON ref_desa_pejabat(desa_id, aktif);
CREATE INDEX IF NOT EXISTS ix_butir_formulir
  ON ref_kelengkapan_butir(kelengkapan_id, urut);
CREATE INDEX IF NOT EXISTS ix_jawab_pradaftar ON pradaftar_jawab(pradaftar_id);
CREATE INDEX IF NOT EXISTS ix_catatan_koreksi_butir ON ref_catatan_koreksi(butir_id);
CREATE INDEX IF NOT EXISTS ix_pradaftar_berkas ON pradaftar(berkas_id);
"""


def sekarang():
    """Waktu setempat sebagai teks 'YYYY-MM-DD HH:MM:SS'.

    Dihitung di Python, bukan lewat datetime('now','localtime') yang hanya ada
    di SQLite. Selain soal dialek, ini juga menaruh sumber waktunya di satu
    tempat: kalau diserahkan ke server basis data, zona waktunya ikut
    ditentukan di sana — dan server itu belum tentu di kantor yang sama.
    """
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def upsert(tabel, kolom, kunci="berkas_id"):
    """INSERT ... ON CONFLICT ... DO UPDATE — dimengerti SQLite 3.24+ maupun
    PostgreSQL, jadi kueri yang sama jalan di dua-duanya.

    Menggantikan INSERT OR REPLACE yang khas SQLite. Bedanya nyata: REPLACE
    menghapus barisnya lalu menyisipkan yang baru, sehingga kolom yang tidak
    disebut kembali ke nilai bawaan dan ON DELETE CASCADE ikut terpicu. Yang
    ini hanya memperbarui kolom yang disebut.

    Untuk ketujuh tabel yang memakainya di sini keduanya setara: tak satu pun
    punya tabel anak, dan kolom yang tak disebut upsert pihak_badan_hukum
    (akta perubahan, NIK pengurus, dan rincian KOLOM_BH_RINCIAN lainnya)
    ditulis tersendiri oleh formulir.py, hanya bila formulirnya memuatnya.

    Daftar kolomnya dipakai sekaligus untuk menghitung penampung nilai, jadi
    jumlahnya tidak bisa lagi meleset dari jumlah kolom.
    """
    kol = [x.strip() for x in kolom.split(",") if x.strip()]
    knc = [x.strip() for x in kunci.split(",") if x.strip()]
    ubah = ", ".join(f"{x}=excluded.{x}" for x in kol if x not in knc)
    return (f"INSERT INTO {tabel} ({','.join(kol)}) "
            f"VALUES ({','.join('?' * len(kol))}) "
            f"ON CONFLICT ({','.join(knc)}) DO UPDATE SET {ubah}")


def sisip_id(k, sql, nilai=()):
    """Jalankan INSERT lalu kembalikan id baris barunya.

    Dipakai menggantikan cursor.lastrowid, yang hanya ada di SQLite. RETURNING
    dimengerti SQLite 3.35+ maupun PostgreSQL, jadi satu bentuk untuk keduanya.
    k boleh koneksi maupun kursor — keduanya punya execute().
    """
    return k.execute(sql.rstrip().rstrip(";") + " RETURNING id", nilai).fetchone()[0]


def sisip_bila_belum(tabel, kolom):
    """INSERT ... ON CONFLICT DO NOTHING. Pengganti INSERT OR IGNORE."""
    kol = [x.strip() for x in kolom.split(",") if x.strip()]
    return (f"INSERT INTO {tabel} ({','.join(kol)}) "
            f"VALUES ({','.join('?' * len(kol))}) ON CONFLICT DO NOTHING")


def postgres():
    return SAMBUNGAN.postgres


def sambung():
    """Koneksi baru. Satu per permintaan; lihat aplikasi.py."""
    if postgres():
        return basis.buka(SAMBUNGAN)
    # Untuk SQLite, BERKAS_DB yang menentukan — bukan SAMBUNGAN. Uji
    # menggantinya supaya bekerja di atas salinan sementara, dan perkakas
    # pindah data mengarahkannya ke berkas lain.
    os.makedirs(DIR_DATA, exist_ok=True)
    return basis.buka(konfigurasi.Sambungan(
        konfigurasi.JENIS_SQLITE, {"berkas": BERKAS_DB}, f"sqlite {BERKAS_DB}"))


# ------------------------------------------------------- dokumen baku
# Sebelas surat ini satu kesatuan dengan formulir permohonan: selalu ada slotnya,
# masing-masing punya isian sendiri, dan urutannya = urutan DATA PENDUKUNG pada
# Risalah. `kategori` dipakai sebagai kunci di dokumen_pendukung, jadi jangan
# diganti tanpa memperbarui perbaiki_dokumen.py.
#   (kategori, label formulir, judul kolom Excel lama, petunjuk)
DOKUMEN_BAKU = [
    ("permohonan", "Formulir permohonan", "Formulir permohonan",
     "surat permohonan hak yang ditandatangani pemohon"),
    ("sppf", "Jenis SPPF", "jenis sppf",
     "Surat Pernyataan Penguasaan Fisik Bidang Tanah"),
    ("tanah_dipunyai", "Surat Pernyataan tanah-tanah yang dipunyai pemohon",
     "Surat Pernyataan tanah-Tanah Yang dipunyai Pemohon", ""),
    ("penggunaan", "Surat Pernyataan Penggunaan Tanah",
     "Surat Pernyataan Penggunaan Tanah", ""),
    ("keterangan_penguasaan", "Surat Keterangan Penguasaan Tanah",
     "Surat Keterangan Penguasaan Tanah", ""),
    ("tidak_sengketa", "Surat Pernyataan Tidak Sengketa dan belum Bersertipikat",
     "Surat Pernyataan Tidak Sengketa dan belum Bersertipikat", ""),
    ("pernyataan", "Surat Pernyataan", "Surat Pernyataan", ""),
    ("tanda_batas", "Surat pemasangan tanda batas", "surat pemasangan tanda batas", ""),
    ("selisih", "Surat pernyataan selisih luas", "surat pernyataan selisih luas",
     "Surat Pernyataan Perbedaan Luas; ikut dirujuk kalimat selisih luas"),
    ("absentee", "Surat Absentee Kecamatan", "Tgl Surat Absentee Kecamatan",
     "surat pernyataan absentee yang diketahui Camat; judul kolomnya menyebut Tgl"),
    ("kuasa", "Surat kuasa", "surat kuasa", "diisi bila permohonan diajukan lewat kuasa"),
]

# Dua kalimat telaah yang menyertai dokumen baku. Kolom di bidang_tanah,
# dikosongkan = disusun otomatis oleh konteks.py.
URAIAN_BAKU = [
    ("uraian_penguasaan_fisik", "Surat Penguasaan Fisik", "Surat Penguasaan Fisik",
     "kalimat “Bahwa … dikuasai terus menerus …”; kosongkan agar disusun dari SPPF"),
    ("uraian_selisih_luas", "Selisih luas", "selisih luas",
     "kalimat selisih luas; kosongkan agar dihitung dari luas PBT, luas surat, dan surat selisih"),
]

# ------------------------------------------------ dokumen baku khusus wakaf
# Empat surat yang hanya ada pada berkas wakaf. Template wakaf memanggilnya lewat
# penanda sendiri ({{akta_ikrar}}, {{pengesahan_nazhir}}, ...), jadi isinya tidak
# perlu diketik ulang di Menimbang SK maupun di daftar DATA PENDUKUNG Risalah.
#   (kategori, label formulir, judul kolom Excel lama, petunjuk)
DOKUMEN_BAKU_HAK = {
    "WAKAF": [
        ("akta_ikrar", "Akta Ikrar Wakaf", "Akta Ikrar Wakaf",
         "AIW/APAIW yang ditandatangani Wakif, Nazhir, saksi, dan PPAIW"),
        ("pengesahan_nazhir", "Pengesahan Nazhir oleh PPAIW", "Pengesahan Nazhir",
         "surat pengesahan Nazhir perseorangan/organisasi/badan hukum oleh PPAIW"),
        ("kesediaan_nazhir", "Surat Pernyataan Kesediaan Menjadi Nazhir",
         "Surat Pernyataan Kesediaan Menjadi Nazhir", ""),
        ("bersedia_diaudit", "Surat Pernyataan Bersedia Diaudit",
         "Surat Pernyataan bersedia diaudit", ""),
    ],
}


# Surat wakaf yang kalimat Menimbang SK-nya berformat tetap (Permen ATR/BPN 2/2017):
#   b. ... sesuai AIW/APAIW tanggal ... yang dibuat oleh ... / Pejabat Pembuat AIW/APAIW ...;
#   c. ... telah disahkan oleh ... / Pejabat AIW/APAIW tanggal ... Nomor ...;
# Karena itu keduanya diisi per unsur, bukan satu kalimat bebas. Uraian bebasnya
# tetap ada: kalau dikosongkan, disusun dari unsur-unsur ini (konteks.py).
#   kategori -> [(kolom dokumen_pendukung, label, petunjuk)]
JENIS_AKTA_IKRAR = [("AIW", "Akta Ikrar Wakaf (AIW)"),
                    ("APAIW", "Akta Pengganti Akta Ikrar Wakaf (APAIW)")]
RINCIAN_BAKU = {
    "akta_ikrar": [
        ("jenis", "Jenis akta", ""),
        ("nomor", "Nomor akta", "mis. WT.1/00001/7503071/2026"),
        ("tanggal", "Tanggal akta", ""),
        ("pejabat", "Dibuat oleh (nama PPAIW)", "mis. Charles Yusuf, S.Ag"),
        ("wilayah_pejabat", "PPAIW wilayah", "mis. Kecamatan Botupingge"),
    ],
    "pengesahan_nazhir": [
        ("nomor", "Nomor pengesahan", "mis. WT.4/d.377/Kua.30.02.04/89/09/2026"),
        ("tanggal", "Tanggal pengesahan", ""),
        ("pejabat", "Disahkan oleh (nama PPAIW)", "biasanya sama dengan pembuat AIW"),
        ("wilayah_pejabat", "PPAIW wilayah", "mis. Kecamatan Botupingge"),
    ],
}
KOLOM_RINCIAN = ("jenis", "nomor", "tanggal", "pejabat", "wilayah_pejabat")

# --------------------------------------- rincian badan hukum (SK Hak Pakai)
# Menimbang huruf a SK pemberian Hak Pakai untuk badan hukum (Lampiran VI
# Permen ATR/BPN 18/2021, format A.1.b) menyebut bidang usaha, akta pendirian
# dan notarisnya, pengesahan, akta perubahan terakhir berikut persetujuannya,
# pendaftaran OSS, dan - bagi usaha di bidang sumber daya alam - akta
# kesanggupan CSR (Pasal 114 ayat (1) huruf f angka 9). Kolom-kolom ini hanya
# diisi lewat formulir berkas Hak Pakai; yang kosong tidak ikut tercetak.
#   (kolom, label, jenis isian, petunjuk)
KOLOM_BH_RINCIAN = [
    ("bidang_usaha", "Bidang usaha", "", "mis. perdagangan dan jasa; dicetak «… antara lain dalam bidang …»"),
    ("notaris_kota", "Notaris di (kota)", "", "kedudukan notaris akta pendirian"),
    ("pengesahan_oleh", "Disahkan oleh", "", "mis. Menteri Hukum dan Hak Asasi Manusia Republik Indonesia"),
    ("wakil_nik", "NIK pengurus", "", ""),
    ("akta_ubah_nomor", "Akta perubahan terakhir nomor", "", "kosongkan bila belum pernah diubah"),
    ("akta_ubah_tanggal", "Tanggal akta perubahan", "date", ""),
    ("akta_ubah_notaris", "Notaris akta perubahan", "", ""),
    ("akta_ubah_notaris_kota", "Notaris di (kota)", "", ""),
    ("ubah_sah_nomor", "Persetujuan/pencatatan perubahan nomor", "", "keputusan/surat penerimaan perubahan"),
    ("ubah_sah_tanggal", "Tanggal persetujuan perubahan", "date", ""),
    ("nib_tanggal", "Tanggal terdaftar di OSS", "date", "tanggal NIB diterbitkan"),
    ("csr_akta_nomor", "Akta kesanggupan CSR nomor", "", "hanya untuk usaha di bidang sumber daya alam"),
    ("csr_akta_tanggal", "Tanggal akta CSR", "date", ""),
    ("csr_notaris", "Notaris akta CSR", "", ""),
    ("csr_notaris_kota", "Notaris di (kota)", "", ""),
]


def dokumen_baku(kode_hak=None):
    """Slot dokumen baku yang berlaku untuk satu jenis hak.

    Sebelas surat yang berlaku untuk semua berkas, ditambah surat khusus jenis
    haknya — supaya berkas Hak Milik tidak ikut menampilkan isian Akta Ikrar Wakaf.
    """
    return DOKUMEN_BAKU + DOKUMEN_BAKU_HAK.get((kode_hak or "").upper(), [])


SEMUA_BAKU = DOKUMEN_BAKU + [x for v in DOKUMEN_BAKU_HAK.values() for x in v]
KATEGORI_BAKU = [x[0] for x in SEMUA_BAKU]


# ---------------------------------------------------------------- sandi
def hash_sandi(sandi, garam=None):
    garam = garam or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), garam.encode("utf-8"), 200_000)
    return f"{garam}${h.hex()}"


def cek_sandi(sandi, tersimpan):
    try:
        garam, _ = tersimpan.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_sandi(sandi, garam), tersimpan)


# ---------------------------------------------------------------- seed
JENIS_HAK = [
    # kode, nama, jangka?, maks, perpanjang, perbarui, uang pemasukan?, subjek, kegiatan,
    # dasar, kode nomor SK, varian template, urut
    ("HM", "Hak Milik", 0, None, None, None, 0,
     "perorangan,badan_hukum",
     "baru,peningkatan",
     "Pasal 52 Permen ATR/BPN 18/2021", "HM", "", 1),
    ("HGB", "Hak Guna Bangunan", 1, 30, 20, 30, 1,
     "perorangan,badan_hukum",
     "baru,perpanjangan,pembaruan",
     "Pasal 85 & 87 Permen ATR/BPN 18/2021", "HGB", "", 2),
    # Hak Pakai punya tata naskahnya sendiri (bap-hp, risalah-hp, sk-hp): satu
    # set untuk perorangan maupun badan hukum, bagian yang berbeda bersyarat.
    ("HP", "Hak Pakai", 1, 30, 20, 30, 1,
     "perorangan,badan_hukum,instansi",
     "baru,perpanjangan,pembaruan",
     "Pasal 111 & 113 Permen ATR/BPN 18/2021", "HP", "hp", 3),
    ("HPL", "Hak Pengelolaan", 0, None, None, None, 1,
     "instansi",
     "baru",
     "Pasal 30 Permen ATR/BPN 18/2021", "HPL", "", 4),
    # Wakaf memakai tata naskahnya sendiri: Risalah dan SK-nya lain, penerima haknya
    # Nazhir (boleh lebih dari satu orang), dan nomor SK-nya berkode HW.
    ("WAKAF", "Hak Wakaf", 0, None, None, None, 0,
     "perorangan,badan_hukum,instansi",
     "baru",
     "UU 41/2004 tentang Wakaf jo. PP 42/2006", "HW", "wakaf", 5),
    ("HMSRS", "Hak Milik Atas Satuan Rumah Susun", 0, None, None, None, 0,
     "perorangan,badan_hukum",
     "baru",
     "PP 18/2021 BAB V", "HMSRS", "", 6),
]

# Sepuluh butir wajib surat pernyataan penguasaan fisik - Pasal 54 ayat (1) huruf d
BUTIR_PENGUASAAN_FISIK = [
    "tanah benar milik yang bersangkutan, bukan milik orang lain, dan berstatus Tanah Negara",
    "tanah telah dikuasai secara fisik",
    "penguasaan dilakukan dengan iktikad baik dan secara terbuka",
    "perolehan tanah dibuat sesuai data yang sebenarnya",
    "tidak terdapat keberatan dari pihak lain / tidak dalam sengketa",
    "tidak terdapat keberatan dari pihak Kreditur bila tanah menjadi jaminan utang",
    "tanah bukan aset Pemerintah Pusat/Daerah atau BUMN/BUMD",
    "tanah berada di luar kawasan hutan dan areal yang dihentikan perizinannya",
    "bersedia tidak mengurung/menutup akses publik dan/atau jalan air",
    "bersedia melepaskan tanah untuk kepentingan umum",
]

DOKUMEN_SYARAT = [
    # jenis_hak, kegiatan, kategori, nama, wajib, dasar
    ("*", "baru", "pemohon", "Surat permohonan hak", 1, "Pasal 54 ayat (1)"),
    ("*", "*", "pemohon", "Fotokopi KTP dan Kartu Keluarga pemohon", 1, "Pasal 54 ayat (1) huruf a"),
    ("*", "*", "pemohon", "Surat kuasa dan identitas penerima kuasa (bila dikuasakan)", 0, "Pasal 54 ayat (1) huruf a"),
    ("*", "*", "badan_hukum", "Akta pendirian dan perubahan terakhir beserta pengesahannya", 1, "Pasal 54 ayat (1) huruf a angka 2"),
    ("*", "*", "badan_hukum", "Nomor Induk Berusaha (OSS)/TDP/TDY", 1, "Pasal 54 ayat (1) huruf a angka 2"),
    ("HM", "*", "badan_hukum", "SK penunjukan sebagai badan hukum yang dapat mempunyai Hak Milik", 1, "Pasal 52 ayat (2)"),
    ("*", "baru", "tanah", "Alas hak / dasar penguasaan tanah", 1, "Pasal 54 ayat (1) huruf b angka 1"),
    ("*", "baru", "tanah", "Surat Pernyataan Penguasaan Fisik Bidang Tanah (2 saksi, diketahui kepala desa/lurah)", 1, "Pasal 54 ayat (1) huruf b angka 1 huruf b"),
    ("*", "*", "tanah", "Peta Bidang Tanah", 1, "Pasal 54 ayat (1) huruf b angka 2"),
    ("*", "*", "tanah", "Bukti perpajakan yang berkaitan dengan tanah (SPPT PBB/SSPD-BPHTB)", 0, "Pasal 54 ayat (1) huruf c"),
    ("*", "*", "tanah", "Peta Analisis Penatagunaan Tanah", 1, "praktik Kantah"),
    ("*", "*", "tanah", "Surat Pernyataan Pemasangan Tanda Batas dan persetujuan pemilik berbatasan", 1, "praktik Kantah"),
    ("*", "*", "tanah", "Surat Pernyataan Perbedaan Luas (bila ada selisih)", 0, "praktik Kantah"),
    ("*", "perpanjangan", "tanah", "Sertipikat hak yang dimohon perpanjangannya", 1, "Pasal 159 ayat (1) huruf b"),
    ("*", "pembaruan", "tanah", "Sertipikat hak yang telah berakhir", 1, "Pasal 159 ayat (1) huruf b"),
    ("HM", "peningkatan", "tanah", "Sertipikat HGB/Hak Pakai yang dimohon peningkatannya", 1, "Pasal 149"),
    ("WAKAF", "*", "tanah", "Akta Ikrar Wakaf / Akta Pengganti Akta Ikrar Wakaf", 1,
     "Pasal 32 UU 41/2004 jo. Pasal 39 PP 42/2006"),
    ("WAKAF", "*", "pemohon", "Surat Pengesahan Nazhir dari PPAIW", 1,
     "Pasal 4 & 14 PP 42/2006 jo. Permen ATR/BPN 2/2017"),
    ("WAKAF", "*", "pemohon", "Surat Pernyataan Kesediaan Menjadi Nazhir", 1,
     "Permen ATR/BPN 2/2017"),
    # dicetak Risalah sebagai baris tetap, bukan baris dokumen - jadi tidak diperiksa
    # sebagai baris yang harus ada, cukup diingatkan
    ("WAKAF", "*", "pemohon", "Fotokopi KTP dan Kartu Keluarga Wakif", 0,
     "Permen ATR/BPN 2/2017"),
]


# ------------------------------------------- daftar kelengkapan (formulir loket)
# Salinan setia Lampiran Permen ATR/BPN 18/2021 halaman 184-185: nomor, huruf,
# dan bunyi kalimatnya dibiarkan apa adanya, termasuk butir yang berakhir titik-
# titik. Yang ditambahkan hanya keterangan mesin: kapan sebuah butir berlaku
# (subjek/asal tanah), butir mana yang cukup salah satu, dan butir mana yang
# sepadan dengan slot dokumen baku sehingga bisa disalin saat berkas dibuat.
#
# Menambah formulir untuk jenis hak lain = menambah satu FORMULIR + satu daftar
# butir di bawah ini, lalu satu berkas template. Tidak ada kode yang berubah.

def _butir(penanda, nama, *, sifat="butir", wajib=1, isian=0, subjek="*",
           asal="*", slot=None, dokumen=None, dasar=None, jamak=0, anak=()):
    """Satu baris formulir kelengkapan.

    sifat: butir (dicentang) | judul (kepala kelompok) | alternatif (salah satu
    di antara sesama anak induknya sudah cukup). slot = kategori DOKUMEN_BAKU
    yang sepadan, dipakai pradaftar.terima() untuk mengisi berkas.
    """
    return {"penanda": penanda, "nama": nama, "nama_dokumen": dokumen,
            "sifat": sifat, "wajib": wajib, "isian_bebas": isian,
            "subjek": subjek, "asal_tanah": asal, "slot_baku": slot,
            "dasar": dasar, "jamak": jamak, "anak": list(anak)}


# (kode, judul, jenis_hak, kegiatan, dasar, varian_template)
KELENGKAPAN = [
    ("184-HM", "Daftar Kelengkapan Persyaratan Permohonan Hak Milik", "HM", "*",
     "Lampiran Permen ATR/BPN 18/2021 angka 2, hlm. 184-185", "hm"),
    ("190-HP", "Daftar Kelengkapan Persyaratan Permohonan Hak Pakai dengan Jangka Waktu",
     "HP", "baru",
     "Lampiran Permen ATR/BPN 18/2021 angka 5 huruf a, hlm. 190-191", "hp"),
]

# Tiga butir di bawah ini keluaran Kantor Pertanahan sendiri, bukan dokumen yang
# dibawa pemohon ke loket: Peta Bidang Tanah terbit sesudah pengukuran, Risalah
# Pemeriksaan Tanah A sesudah sidang Panitia A, dan Surat Pengantar menyertai
# berkas ke tahap berikutnya. Karena itu wajib=0 - tetap tercetak di formulir dan
# tetap bisa dicentang, tapi tidak menahan penerimaan berkas di loket. Kantor
# yang alurnya berbeda tinggal menyalakan wajibnya di menu Data referensi.
KELENGKAPAN_BUTIR = {
    "184-HM": [
        _butir("1", "Permohonan Hak Milik", slot="permohonan",
               dokumen="Surat permohonan Hak Milik", dasar="Pasal 54 ayat (1)"),
        _butir("2", "Identitas Pemohon", sifat="judul", anak=[
            _butir("a", "KTP Pemohon", sifat="alternatif",
                   dasar="Pasal 54 ayat (1) huruf a"),
            _butir("b", "KTP pemohon dan kuasanya serta surat kuasa apabila "
                        "dikuasakan", sifat="alternatif", slot="kuasa",
                   dokumen="Surat kuasa", dasar="Pasal 54 ayat (1) huruf a"),
            _butir("", "Badan Hukum yang ditetapkan oleh Pemerintah",
                   sifat="judul", subjek="badan_hukum", anak=[
                _butir("c", "Akta pendirian dan perubahan terakhir atau Peraturan "
                            "Pendirian Perusahaan", subjek="badan_hukum",
                       dasar="Pasal 54 ayat (1) huruf a angka 2"),
                _butir("d", "Pengesahan Badan Hukum dari instansi yang berwenang",
                       subjek="badan_hukum",
                       dasar="Pasal 54 ayat (1) huruf a angka 2"),
                _butir("e", "Nomor Induk Berusaha/Tanda Daftar Perusahaan/Tanda "
                            "Daftar Yayasan", subjek="badan_hukum",
                       dasar="Pasal 54 ayat (1) huruf a angka 2"),
                _butir("f", "Surat keputusan penunjukan sebagai badan hukum yang "
                            "dapat mempunyai Hak Milik", subjek="badan_hukum",
                       dasar="Pasal 52 ayat (2)"),
                _butir("g", "izin perolehan tanah", subjek="badan_hukum"),
            ]),
        ]),
        _butir("3", "Dasar Penguasaan atau Alas Hak", sifat="judul",
               slot="alas_hak",          # kategori yang diwarisi anak-anaknya
               dasar="Pasal 54 ayat (1) huruf b angka 1", anak=[
            _butir("a", "Sertipikat", sifat="alternatif"),
            _butir("b", "Akta pemindahan hak", sifat="alternatif", jamak=1),
            _butir("c", "Akta/surat bukti pelepasan hak", sifat="alternatif", jamak=1),
            _butir("d", "surat penunjukan atau pembelian kaveling", sifat="alternatif"),
            _butir("e", "surat bukti pelunasan tanah dan rumah dan/atau tanah yang "
                        "telah dibeli dari pemerintah", sifat="alternatif"),
            _butir("f", "Risalah lelang", sifat="alternatif"),
            _butir("g", "Putusan pengadilan", sifat="alternatif"),
            _butir("h", "surat persetujuan pemberian Hak Milik atas bagian tanah "
                        "Hak Pengelolaan dari pemegang Hak Pengelolaan (untuk "
                        "permohonan Hak Milik di atas Hak Pengelolaan); atau",
                   sifat="alternatif", asal="hak_pengelolaan"),
            _butir("i", "keputusan yang diterbitkan oleh instansi yang berwenang "
                        "menyelenggarakan urusan pemerintahan di bidang "
                        "transmigrasi, untuk tanah transmigrasi (untuk permohonan "
                        "Hak Milik di atas Hak Pengelolaan transmigrasi)",
                   sifat="alternatif", asal="hak_pengelolaan"),
            _butir("j", "Surat bukti perolehan tanah lainnya", sifat="alternatif",
                   isian=1, jamak=1),
        ]),
        _butir("4", "Peta Bidang Tanah", wajib=0,
               dasar="Pasal 54 ayat (1) huruf b angka 2"),
        _butir("5", "Bukti perpajakan yang berkaitan dengan tanah yang dimohon",
               sifat="judul", dasar="Pasal 54 ayat (1) huruf c", anak=[
            _butir("a", "SPPT PBB", sifat="alternatif"),
            _butir("b", "SSP/PPh; dan/atau", sifat="alternatif"),
            _butir("c", "bukti lainnya", sifat="alternatif", isian=1),
        ]),
        _butir("6", "Surat Pernyataan Penguasaan Fisik Bidang Tanah (untuk "
                    "permohonan Hak Milik di atas Tanah Negara)",
               asal="tanah_negara", slot="sppf",
               dokumen="Surat Pernyataan Penguasaan Fisik Bidang Tanah",
               dasar="Pasal 54 ayat (1) huruf b angka 1 huruf b"),
        _butir("7", "Risalah Pemeriksaan Tanah A atau Risalah Pemeriksaan Tanah "
                    "(Konstatering Rapport)", wajib=0, dasar="Pasal 138"),
        _butir("8", "Surat Pengantar dari Kantor Pertanahan", wajib=0),
    ],
    # Lampiran angka 5 huruf a. Bedanya dengan 184-HM yang dibawa ke sini:
    # identitas boleh visa/paspor (Orang Asing), grup badan hukum tanpa SK
    # penunjukan Hak Milik, alas hak menambah pelepasan kawasan hutan,
    # Perjanjian Pemanfaatan Tanah (HPL), dan APHP dari PPAT (di atas Hak
    # Milik). Bukti perpajakan cukup "apabila ada" (Pasal 114 ayat (1) huruf
    # e), jadi grupnya tidak wajib. Butir 8 ditulis apa adanya walau
    # sebenarnya milik Hak Pakai selama dipergunakan - bunyi formulirnya
    # memang begitu; ia hanya berlaku di atas Hak Pengelolaan.
    "190-HP": [
        _butir("1", "Permohonan Hak Pakai dengan Jangka Waktu", slot="permohonan",
               dokumen="Surat permohonan Hak Pakai dengan Jangka Waktu",
               dasar="Pasal 114 ayat (1)"),
        _butir("2", "Identitas Pemohon", sifat="judul", anak=[
            _butir("a", "KTP atau visa/paspor/izin tinggal Pemohon; atau",
                   sifat="alternatif", dasar="Pasal 114 ayat (1) huruf a angka 1-2"),
            _butir("b", "KTP atau visa/paspor/izin tinggal Pemohon dan kuasanya serta "
                        "surat kuasa apabila dikuasakan", sifat="alternatif",
                   slot="kuasa", dokumen="Surat kuasa",
                   dasar="Pasal 114 ayat (1) huruf a angka 1"),
            _butir("", "Badan Hukum", sifat="judul", subjek="badan_hukum", anak=[
                _butir("c", "Akta pendirian dan perubahan terakhir, atau Peraturan "
                            "Pendirian Perusahaan", subjek="badan_hukum",
                       dasar="Pasal 114 ayat (1) huruf a angka 3"),
                _butir("d", "Pengesahan Badan Hukum dari instansi yang berwenang",
                       subjek="badan_hukum", dasar="Pasal 114 ayat (1) huruf a angka 3"),
                _butir("e", "Nomor Induk Berusaha/Tanda Daftar Perusahaan",
                       subjek="badan_hukum", dasar="Pasal 114 ayat (1) huruf a angka 3"),
            ]),
        ]),
        _butir("3", "Dasar Penguasaan atau Alas Hak", sifat="judul",
               slot="alas_hak", dasar="Pasal 114 ayat (1) huruf b angka 1", anak=[
            _butir("a", "Sertipikat", sifat="alternatif"),
            _butir("b", "Akta pemindahan hak", sifat="alternatif", jamak=1),
            _butir("c", "Akta/surat bukti pelepasan hak", sifat="alternatif", jamak=1),
            _butir("d", "Surat penunjukan atau pembelian kaveling", sifat="alternatif"),
            _butir("e", "Keputusan pelepasan kawasan hutan dari instansi yang berwenang",
                   sifat="alternatif"),
            _butir("f", "Risalah lelang", sifat="alternatif"),
            _butir("g", "Putusan pengadilan", sifat="alternatif"),
            _butir("h", "Perjanjian Pemanfaatan Tanah (untuk permohonan Hak Pakai di "
                        "atas tanah Hak Pengelolaan)", sifat="alternatif",
                   asal="hak_pengelolaan", dasar="Pasal 114 ayat (2) huruf b angka 1"),
            _butir("i", "Akta Pemberian Hak Pakai yang dibuat oleh Pejabat Pembuat Akta "
                        "Tanah (untuk permohonan Hak Pakai di atas tanah Hak Milik)",
                   sifat="alternatif", dasar="Pasal 114 ayat (3) huruf b angka 1"),
            _butir("j", "Surat bukti perolehan tanah lainnya", sifat="alternatif",
                   isian=1, jamak=1),
            _butir("k", "Daftar Perolehan Tanah, apabila tanah yang dimohon lebih dari "
                        "5 (lima) bidang", wajib=0,
                   dasar="Pasal 114 ayat (1) huruf b angka 2"),
        ]),
        _butir("4", "surat persetujuan pemberian Hak Pakai selama dipergunakan atas "
                    "bagian tanah Hak Pengelolaan dari pemegang Hak Pengelolaan (untuk "
                    "permohonan di atas Hak Pengelolaan)", asal="hak_pengelolaan"),
        _butir("5", "Peta Bidang Tanah", wajib=0,
               dasar="Pasal 114 ayat (1) huruf b angka 3"),
        _butir("6", "Dokumen Perizinan (untuk permohonan Hak Pakai di atas Tanah Negara)",
               sifat="judul", asal="tanah_negara",
               dasar="Pasal 114 ayat (1) huruf c", anak=[
            _butir("a", "KKPR", dokumen="Kesesuaian Kegiatan Pemanfaatan Ruang (KKPR)"),
            _butir("b", "perizinan berusaha untuk pelaksanaan reklamasi dalam hal tanah "
                        "yang dimohon merupakan Tanah Reklamasi", wajib=0),
        ]),
        _butir("7", "Dokumen Perencanaan Peruntukan, Penggunaan dan Pemanfaatan Tanah "
                    "(untuk permohonan Hak Pakai di atas Tanah Negara atau tanah Hak "
                    "Milik)", asal="tanah_negara",
               dasar="Pasal 114 ayat (1) huruf d"),
        _butir("8", "Bukti perpajakan yang berkaitan dengan tanah yang dimohon",
               sifat="judul", wajib=0, dasar="Pasal 114 ayat (1) huruf e", anak=[
            _butir("a", "SPPT PBB", sifat="alternatif"),
            _butir("b", "SSP/PPh", sifat="alternatif"),
            _butir("c", "bukti lainnya", sifat="alternatif", isian=1),
        ]),
        _butir("9", "Surat Pernyataan Penguasaan Fisik Bidang Tanah (untuk permohonan "
                    "Hak Pakai di atas Tanah Negara)",
               asal="tanah_negara", slot="sppf",
               dokumen="Surat Pernyataan Penguasaan Fisik Bidang Tanah",
               dasar="Pasal 114 ayat (1) huruf f"),
        _butir("10", "Risalah Pemeriksaan Tanah A atau Risalah Pemeriksaan Tanah "
                     "(Konstatering Rapport)", wajib=0, dasar="Pasal 138"),
        _butir("11", "Surat Pengantar dari Kantor Pertanahan", wajib=0),
    ],
}

# Catatan koreksi baku yang berlaku untuk semua butir. Yang khusus untuk satu
# butir tertentu ("SPPT PBB bukan tahun berjalan") ditambahkan kantor sendiri
# lewat Data referensi — id butirnya baru diketahui setelah formulirnya terpasang.
CATATAN_KOREKSI = [
    "Belum dilegalisir pejabat yang berwenang",
    "Hanya fotokopi, aslinya tidak diperlihatkan",
    "Nama tidak sesuai dengan identitas pemohon",
    "NIK tidak sesuai dengan identitas pemohon",
    "Belum ditandatangani",
    "Belum bermeterai",
    "Tanggal atau nomor surat tidak terbaca",
    "Masa berlakunya sudah habis",
    "Luas atau letak tanah tidak sesuai dengan permohonan",
]

KLAUSA = [
    # slot, jenis_hak, kegiatan, subjek, isi
    ("telaah_subjek", "*", "*", "perorangan",
     "bahwa {{nama_penerima}} adalah Warga Negara Indonesia, bertempat tinggal di {{alamat_penerima}}, "
     "pemegang Kartu Tanda Penduduk NIK {{nik_penerima}}, sehingga telah memenuhi syarat sebagai subjek {{nama_hak}};"),
    ("telaah_subjek", "*", "*", "badan_hukum",
     "bahwa {{nama_penerima}} adalah badan hukum berkedudukan di {{bh_kedudukan}}, didirikan berdasarkan "
     "Akta tanggal {{bh_akta_tanggal}} Nomor {{bh_akta_nomor}} yang dibuat oleh dan di hadapan {{bh_notaris}}, "
     "yang telah disahkan sesuai Keputusan tanggal {{bh_pengesahan_tanggal}} Nomor {{bh_pengesahan_nomor}}, "
     "sehingga telah memenuhi syarat sebagai subjek {{nama_hak}};"),
    ("telaah_subjek", "HPL", "*", "instansi",
     "bahwa {{nama_penerima}} merupakan subjek Hak Pengelolaan sebagaimana dimaksud dalam Pasal 30 "
     "Peraturan Menteri Agraria dan Tata Ruang/Kepala Badan Pertanahan Nasional Nomor 18 Tahun 2021, "
     "yang tugas pokok dan fungsinya berhubungan langsung dengan pengelolaan tanah;"),
    ("uraian_jangka", "HM,HPL,WAKAF,HMSRS", "*", "*", "-"),
    ("uraian_jangka", "HGB,HP", "*", "*",
     "{{jangka_tahun}} ({{jangka_terbilang}}) tahun, sampai dengan {{jangka_berakhir}}"),
    ("diktum_uang_pemasukan", "HGB,HP,HPL", "*", "*",
     "penerima hak wajib membayar uang pemasukan kepada negara sebesar Rp{{uang_pemasukan}} "
     "sesuai dengan ketentuan peraturan perundang-undangan;"),
    ("asal_tanah_judul", "*", "baru", "*", "Riwayat Perolehan Tanah"),
    ("asal_tanah_judul", "*", "perpanjangan,pembaruan,peningkatan", "*", "Data Hak Yang Telah Ada"),
    # --- wakaf: subjek haknya Nazhir, dasar hukumnya UU 41/2004 jo. PP 42/2006
    ("telaah_subjek", "WAKAF", "*", "perorangan",
     "bahwa {{nama_nazhir}} memenuhi persyaratan yang ditetapkan dalam Undang-Undang Nomor 41 "
     "Tahun 2004 tentang Wakaf Pasal 9 huruf a dan Peraturan Pemerintah Nomor 42 Tahun 2006 "
     "tentang Pelaksanaan Undang-Undang Nomor 41 Tahun 2004 tentang Wakaf Pasal 2 huruf a, "
     "sehingga memenuhi syarat sebagai Nazhir perseorangan;"),
    ("telaah_subjek", "WAKAF", "*", "badan_hukum",
     "bahwa {{nama_nazhir}} memenuhi persyaratan yang ditetapkan dalam Undang-Undang Nomor 41 "
     "Tahun 2004 tentang Wakaf Pasal 11 dan Peraturan Pemerintah Nomor 42 Tahun 2006 tentang "
     "Pelaksanaan Undang-Undang Nomor 41 Tahun 2004 tentang Wakaf Pasal 11, sehingga memenuhi "
     "syarat sebagai Nazhir badan hukum;"),
]


PENGATURAN_AWAL = [
    ("kantor_nama", "Kantor Pertanahan Kabupaten Bone Bolango"),
    ("kantor_kode", "BPN.75.03"),
    ("kantor_kota", "Suwawa"),
    ("kepala_kantor_nama", "ILKHAM MOODUTO, S.H"),
    ("kepala_kantor_nip", "19821006 200604 1 002"),
    # dokumen yang diberi kata penyambung di kanan bawah halaman; dipisah koma
    ("kata_penyambung", "sk"),
]


def seed(k):
    """Isi data referensi bila masih kosong. Aman dipanggil berulang."""
    c = k.cursor()
    if not c.execute("SELECT 1 FROM ref_jenis_hak LIMIT 1").fetchone():
        c.executemany(
            "INSERT INTO ref_jenis_hak (kode,nama,ada_jangka_waktu,jangka_maks,perpanjangan_maks,"
            "pembaruan_maks,wajib_uang_pemasukan,subjek_boleh,kegiatan_boleh,dasar_subjek,"
            "kode_sk,varian_template,urut) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", JENIS_HAK)
    if not c.execute("SELECT 1 FROM ref_dokumen_syarat LIMIT 1").fetchone():
        c.executemany(
            "INSERT INTO ref_dokumen_syarat (jenis_hak,kegiatan,kategori,nama,wajib,dasar,urut) "
            "VALUES (?,?,?,?,?,?,?)",
            [(a, b, cc, d, e, f, i) for i, (a, b, cc, d, e, f) in enumerate(DOKUMEN_SYARAT)])
    if not c.execute("SELECT 1 FROM ref_klausa LIMIT 1").fetchone():
        c.executemany(
            "INSERT INTO ref_klausa (slot,jenis_hak,kegiatan,subjek,isi) VALUES (?,?,?,?,?)", KLAUSA)
    if not c.execute("SELECT 1 FROM ref_catatan_koreksi LIMIT 1").fetchone():
        c.executemany("INSERT INTO ref_catatan_koreksi (teks,urut) VALUES (?,?)",
                      [(t, i) for i, t in enumerate(CATATAN_KOREKSI)])
    for kunci, nilai in PENGATURAN_AWAL:
        c.execute(sisip_bila_belum("pengaturan", "kunci,nilai"), (kunci, nilai))
    if not c.execute("SELECT 1 FROM pengguna LIMIT 1").fetchone():
        c.execute("INSERT INTO pengguna (nama,username,sandi_hash,peran) VALUES (?,?,?,?)",
                  ("Administrator", "admin", hash_sandi("admin123"), "admin"))
    k.commit()


def kolom_tabel(k, tabel):
    """Nama kolom sebuah tabel. PRAGMA hanya ada di SQLite."""
    if postgres():
        return {r[0] for r in k.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name=?", (tabel,))}
    return {r[1] for r in k.execute(f"PRAGMA table_info({tabel})")}


def _tambah_kolom(k, tabel, kolom, tipe="TEXT"):
    """ALTER TABLE yang aman dipanggil berulang."""
    if kolom not in kolom_tabel(k, tabel):
        k.execute(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {tipe}")


def migrasi(k):
    """Samakan basis data lama dengan skema sekarang."""
    for kolom, _, _, _ in URAIAN_BAKU:
        _tambah_kolom(k, "bidang_tanah", kolom)
    for kolom in KOLOM_RINCIAN:
        _tambah_kolom(k, "dokumen_pendukung", kolom)
    _tambah_kolom(k, "ref_jenis_hak", "kode_sk")
    _tambah_kolom(k, "ref_jenis_hak", "varian_template", "TEXT NOT NULL DEFAULT ''")
    # Kode nomor SK dan varian template baru ditambahkan bersama tata naskah wakaf;
    # basis data yang sudah terisi diisikan nilainya sekali, tanpa menyentuh yang lain.
    for kode, nama, *_ , kode_sk, varian, _urut in JENIS_HAK:
        k.execute("UPDATE ref_jenis_hak SET kode_sk=COALESCE(NULLIF(kode_sk,''),?), "
                  "varian_template=CASE WHEN varian_template='' THEN ? ELSE varian_template END "
                  "WHERE kode=?", (kode_sk, varian, kode))
    # Namanya ikut tercetak di judul SK; 'Wakaf' saja bukan sebutan haknya.
    k.execute("UPDATE ref_jenis_hak SET nama='Hak Wakaf' WHERE kode='WAKAF' AND nama='Wakaf'")
    # Sesi lama belum punya token CSRF. Diisikan satu per satu, bukan satu
    # nilai untuk semua: token yang sama di semua sesi sama saja dengan tidak
    # ada penjagaan.
    _tambah_kolom(k, "sesi", "csrf", "TEXT NOT NULL DEFAULT ''")
    for r in k.execute("SELECT token FROM sesi WHERE csrf=''").fetchall():
        k.execute("UPDATE sesi SET csrf=? WHERE token=?",
                  (secrets.token_urlsafe(32), r["token"]))
    _tambah_kolom(k, "ref_kelengkapan_butir", "nama_dokumen")
    _tambah_kolom(k, "ref_kelengkapan_butir", "aktif", "INTEGER NOT NULL DEFAULT 1")
    _tambah_kolom(k, "ref_kelengkapan", "nomor_otomatis", "INTEGER NOT NULL DEFAULT 1")
    if "jamak" not in kolom_tabel(k, "ref_kelengkapan_butir"):
        _tambah_kolom(k, "ref_kelengkapan_butir", "jamak", "INTEGER NOT NULL DEFAULT 0")
        # Sekali saja, saat kolomnya lahir: butir isian bebas dan anak-anak
        # "Dasar Penguasaan atau Alas Hak" boleh berisi lebih dari satu surat.
        # Sesudah itu pilihannya milik admin di menu Susun formulir.
        k.execute("UPDATE ref_kelengkapan_butir SET jamak=1 WHERE isian_bebas=1 "
                  "OR induk_id IN (SELECT id FROM ref_kelengkapan_butir "
                  "                WHERE slot_baku='alas_hak')")
    for kolom, *_ in KOLOM_BH_RINCIAN:
        _tambah_kolom(k, "pihak_badan_hukum", kolom)
    _tambah_kolom(k, "ref_kecamatan", "kode")
    _tambah_kolom(k, "ref_desa", "kode")
    _pindahkan_pejabat_desa(k)
    _lengkapi_referensi(k)
    k.commit()


def _pindahkan_pejabat_desa(k):
    """Nama pejabat yang dulu tersimpan di ref_desa dijadikan baris riwayat pertama.

    Sebelum ada ref_desa_pejabat, satu desa hanya punya satu nama pejabat yang
    ditimpa tiap ganti kepala desa. Yang tersimpan sekarang dianggap pejabat yang
    sedang menjabat, supaya berkas lama tetap mencetak nama yang sama.
    """
    for r in k.execute("SELECT id, nama_pejabat, jabatan_pejabat FROM ref_desa "
                       "WHERE nama_pejabat IS NOT NULL AND nama_pejabat <> '' "
                       "AND id NOT IN (SELECT desa_id FROM ref_desa_pejabat)").fetchall():
        k.execute("INSERT INTO ref_desa_pejabat (desa_id,nama,jabatan,aktif) VALUES (?,?,?,1)",
                  (r["id"], r["nama_pejabat"], r["jabatan_pejabat"] or "Kepala Desa"))


def _sisip_kelengkapan(c):
    """Masukkan formulir kelengkapan yang belum ada, berikut seluruh butirnya.

    Yang dipakai sebagai tanda "sudah ada" adalah `kode` formulirnya, bukan tiap
    butir: butir formulir resmi dipasang sekali sebagai satu kesatuan, dan sesudah
    itu jadi milik kantor — admin boleh menyunting, mematikan wajibnya, atau
    menambah butir sendiri tanpa takut tertimpa saat aplikasi diperbarui.
    Memasang ulang satu formulir yang sudah disunting = hapus dulu formulirnya
    di menu Data referensi.
    """
    for kode, judul, hak, keg, dasar, varian in KELENGKAPAN:
        if c.execute("SELECT 1 FROM ref_kelengkapan WHERE kode=?", (kode,)).fetchone():
            continue
        fid = sisip_id(c, "INSERT INTO ref_kelengkapan (kode,judul,jenis_hak,kegiatan,"
                          "dasar,varian_template) VALUES (?,?,?,?,?,?)",
                       (kode, judul, hak, keg, dasar, varian))
        _sisip_butir(c, fid, None, KELENGKAPAN_BUTIR.get(kode, []), [0])


def _sisip_butir(c, kelengkapan_id, induk_id, butir, urut):
    """Ratakan pohon butir jadi baris, sambil menjaga urutan bacanya.

    urut dibawa sebagai daftar satu unsur supaya nomornya terus bertambah lintas
    tingkat — dengan begitu ORDER BY urut sudah menghasilkan urutan formulir apa
    adanya, tanpa perlu menyusun ulang pohonnya saat mencetak.
    """
    for b in butir:
        urut[0] += 1
        bid = sisip_id(c, "INSERT INTO ref_kelengkapan_butir (kelengkapan_id,induk_id,"
                          "penanda,nama,nama_dokumen,sifat,wajib,isian_bebas,subjek,"
                          "asal_tanah,slot_baku,dasar,jamak,urut) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (kelengkapan_id, induk_id, b["penanda"], b["nama"],
                        b["nama_dokumen"], b["sifat"], b["wajib"], b["isian_bebas"],
                        b["subjek"], b["asal_tanah"], b["slot_baku"], b["dasar"],
                        b.get("jamak", 0), urut[0]))
        _sisip_butir(c, kelengkapan_id, bid, b["anak"], urut)


def _lengkapi_referensi(k):
    """Tambahkan baris referensi baru ke basis data yang seed-nya sudah terlanjur jalan.

    `seed()` hanya mengisi tabel yang masih kosong, jadi klausa dan syarat dokumen
    yang ditambahkan belakangan (mis. wakaf) tidak akan pernah masuk tanpa ini.
    Yang sudah ada — termasuk yang sudah disunting petugas — tidak disentuh.
    """
    c = k.cursor()
    _sisip_kelengkapan(c)
    for slot, hak, keg, subjek, isi in KLAUSA:
        ada = c.execute("SELECT 1 FROM ref_klausa WHERE slot=? AND jenis_hak=? AND kegiatan=? "
                        "AND subjek=?", (slot, hak, keg, subjek)).fetchone()
        if not ada:
            c.execute("INSERT INTO ref_klausa (slot,jenis_hak,kegiatan,subjek,isi) "
                      "VALUES (?,?,?,?,?)", (slot, hak, keg, subjek, isi))
    for i, (hak, keg, kat, nama, wajib, dasar) in enumerate(DOKUMEN_SYARAT):
        ada = c.execute("SELECT 1 FROM ref_dokumen_syarat WHERE jenis_hak=? AND kegiatan=? "
                        "AND nama=?", (hak, keg, nama)).fetchone()
        if not ada:
            c.execute("INSERT INTO ref_dokumen_syarat (jenis_hak,kegiatan,kategori,nama,wajib,"
                      "dasar,urut) VALUES (?,?,?,?,?,?,?)", (hak, keg, kat, nama, wajib, dasar, i))


def siapkan():
    k = sambung()
    k.executescript(basis.ddl_postgres(SKEMA) if postgres() else SKEMA)
    migrasi(k)
    seed(k)
    return k


def ambil_nomor(k, jenis, kode, tahun):
    """Nomor urut berikutnya per (jenis dokumen, kode hak, tahun). Aman dari duplikat."""
    c = k.cursor()
    c.execute(sisip_bila_belum("nomor_urut", "jenis,kode,tahun,terakhir"),
              (jenis, kode, tahun, 0))
    c.execute("UPDATE nomor_urut SET terakhir = terakhir + 1 "
              "WHERE jenis=? AND kode=? AND tahun=?", (jenis, kode, tahun))
    n = c.execute("SELECT terakhir FROM nomor_urut WHERE jenis=? AND kode=? AND tahun=?",
                  (jenis, kode, tahun)).fetchone()[0]
    k.commit()
    return n


if __name__ == "__main__":
    siapkan()
    print("Basis data siap:", BERKAS_DB)
