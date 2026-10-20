# Audit Inventaris SIPANTAS

Tanggal audit: 16 Oktober 2026 · Cakupan: seluruh isi `D:\DEV\ba_risalah\` (repo git ada di `app/`).
Tidak ada berkas yang diubah selama audit; basis data hanya dibuka **baca-saja** (`mode=ro`).

Semua path di bawah relatif terhadap `app/`, kecuali yang diawali `../` (folder induk berisi
dokumen mentah). Notasi `berkas/x.py:123` = berkas dan nomor baris.

Ringkasan angka: ±21.000 baris kode (Python 13.500, JS 1.340, CSS 1.050), 7 blueprint Flask,
29 tabel SQLite, 11 template DOCX aktif + 28 cadangan, 224 uji unit.

---

## Daftar isi

1. [Fitur / halaman](#1-fitur--halaman)
2. [Tabel SQLite](#2-tabel-sqlite)
3. [Aturan bisnis tersembunyi](#3-aturan-bisnis-tersembunyi-di-kode)
4. [Template dokumen](#4-template-dokumen-ba-risalah-sk)
5. [Dependensi eksternal dan konfigurasi](#5-dependensi-eksternal-dan-konfigurasi)
6. [Inkonsistensi dan kode duplikat](#6-inkonsistensi-dan-kode-duplikat)

---

## 1. Fitur / halaman

Aplikasi web Flask (bukan Django; folder `django/` tidak ada di repo) yang menerbitkan **BAP,
Risalah Panitia A, dan SK Penetapan Hak** untuk Kantah Kab. Bone Bolango, ditambah
**Pradaftar** (cek kelengkapan di loket). HTML dirakit sebagai string di `berkas/web.py`, bukan Jinja.

### 1.1 Peta modul

| Modul | Peran |
|---|---|
| `jalankan.py` | Titik masuk lokal: `db.siapkan()`, pangkas pratinjau, jalankan waitress, buka peramban |
| `wsgi.py` | Titik masuk produksi (`wsgi:aplikasi`) |
| `berkas/aplikasi.py` | Pabrik Flask: koneksi DB per permintaan, sesi, penjaga login, CSRF, penangan galat 400/403/404/413, sisip token CSRF ke tiap `<form method="post">` |
| `berkas/sesi.py` | Sesi berbasis tabel `sesi` + kuki `sesi` dan `csrf_tamu` |
| `berkas/izin.py` | Peran admin/petugas, kepemilikan berkas, dekorator `perlu_admin` |
| `berkas/kabar.py` | Pesan flash lewat query `?pesan=`/`?baik=`/`?galat=` |
| `berkas/formulir.py` | Simpan formulir berkas ke 11 tabel, daftar & saringan berkas |
| `berkas/pradaftar.py` | Logika pradaftar: pohon butir, hitung lengkap/kurang/koreksi, terima jadi berkas |
| `berkas/susun_kelengkapan.py` | Penyusun formulir kelengkapan dari layar (tambah/geser/hapus butir) |
| `berkas/referensi.py` | Kueri data referensi |
| `berkas/wilayah.py` | Daftar induk Kemendagri 75.03 + riwayat kepala desa |
| `berkas/pemeliharaan.py` | Ukuran folder & pembersihan `pratinjau/`, `keluaran/`, cadangan DB |
| `berkas/util.py` | Terbilang, tanggal, luas, sapaan, hari kerja |
| `berkas/web.py` | Seluruh HTML (3.409 baris) |
| `berkas/dokumen/konteks.py` | Nilai penanda + seluruh validasi sebelum cetak |
| `berkas/dokumen/docxgen.py` | Mesin perakit DOCX (penanda `{{…}}`) |
| `berkas/dokumen/terbitkan.py` | Penomoran Risalah/SK, rakit, catat `dokumen_terbit` |
| `berkas/dokumen/templat.py` | Unduh/unggah/cadangkan/pulihkan template |
| `berkas/dokumen/kelengkapan.py` | Cetakan loket (checklist & pengembalian) |
| `berkas/dokumen/pdf.py` | DOCX→PDF via Word COM atau LibreOffice |
| `berkas/dokumen/penyambung.py` | Kata penyambung kanan bawah halaman via Word COM |
| `berkas/dokumen/foto.py` | Simpan/rapikan/hapus foto lapangan |
| `berkas/perkakas/*.py` | Skrip CLI sekali jalan (lihat 1.9) |
| `static/app.js`, `static/style.css` | Tab, kartu lipat, seret-lepas, hitung ulang pradaftar di peramban |

### 1.2 Masuk & akun — `berkas/rute/auth.py`

| Rute | Fungsi |
|---|---|
| `GET /masuk`, `POST /masuk` | Form login; cocokkan `pengguna.username` aktif + PBKDF2 (`auth.py:25`) |
| `GET /keluar` | Hapus baris `sesi` dan kuki (`auth.py:35`) |
| `POST /sandi` | Ganti sandi sendiri; sandi lama wajib cocok (`auth.py:41`) |
| `POST /pengguna/peran` | (admin) ubah peran; admin tak boleh menurunkan dirinya (`auth.py:55`) |
| `POST /pengguna` | (admin) tambah pengguna; peran tak dikenal → `petugas` (`auth.py:75`) |

### 1.3 Berkas Panitia A — `berkas/rute/berkas.py`

| Rute | Fungsi |
|---|---|
| `GET /`, `GET /berkas` | Daftar berkas berhalaman (10/25/50/100), saringan hak/status/kegiatan/kecamatan/cari di query string (`berkas.py:22`, `formulir.py:59`) |
| `GET /berkas/baru` | Formulir berkas baru, 6 langkah bertahap (`web.py:85` `LANGKAH_BARU`) |
| `GET /berkas/<id>` | Formulir 8 tab: Berkas, Pihak, Bidang tanah, Riwayat/hak asal, Dokumen, Foto, Sidang & dokumen terbit, Cetak (`web.py:1043`) |
| `POST /berkas/baru`, `POST /berkas/<id>` | Simpan seluruh formulir + foto (`formulir.simpan`, `berkas.py:78`) |
| `POST /berkas/<id>/hapus` | (admin) hapus berkas + foto, cascade 11 tabel (`berkas.py:104`) |
| `POST /berkas/<id>/cetak` | Terbitkan BAP/Risalah/SK (satu atau semua); ditolak bila `periksa()` ada galat (`berkas.py:116`) |

Tab **Cetak** menampilkan hasil `konteks.periksa()` dengan lencana merah/kuning/hijau, riwayat
cetak dari `dokumen_terbit`, dan tombol pratinjau/unduh (`web.py:1096`).

### 1.4 Pradaftar (loket) — `berkas/rute/pradaftar.py`

| Rute | Fungsi |
|---|---|
| `GET /pradaftar` | Daftar + tapis keadaan Semua/Belum lengkap/Siap/Diterima/Dikembalikan/Batal (disaring di peramban) |
| `GET /pradaftar/baru`, `POST /pradaftar/baru` | 3 langkah: Pemohon → Letak tanah → Kelengkapan; nomor `PD-NNNN/YYYY` diberi saat simpan pertama |
| `GET/POST /pradaftar/<id>` | 4 tab: Pemohon, Letak tanah, Kelengkapan, Kesimpulan & cetak |
| `GET/POST /pradaftar/<id>/periksa` | Daftar kelengkapan layar penuh; hanya menyimpan centangan (`pradaftar.simpan_jawab`) |
| `POST /pradaftar/<id>/terima` | Naikkan jadi berkas (`pradaftar.terima`, `pradaftar.py:494`) |
| `POST /pradaftar/<id>/status` | Tandai `dikembalikan`/`batal` (lihat temuan 6.2) |
| `POST /pradaftar/<id>/hapus` | (admin) hapus pradaftar; berkas hasilnya tetap |
| `GET /pradaftar/<id>/pratinjau/<jenis>`, `/pdf/<jenis>`, `/docx/<jenis>` | Cetakan loket `kelengkapan` (formulir 184/190) dan `pengembalian`; tidak diarsipkan |

### 1.5 Data referensi — `berkas/rute/referensi.py`

Petugas boleh membaca, semua POST khusus admin. Lima tab (`web.py:2355`):

| Tab | Isi | Rute tulis |
|---|---|---|
| Jenis hak | Matriks `ref_jenis_hak` (baca-saja di layar) | — |
| Klausa | `ref_klausa` (baca-saja di layar) | — |
| Kelengkapan | Formulir kelengkapan + catatan koreksi baku; halaman **Susun formulir** `/referensi/kelengkapan/<fid>` | `POST /referensi/kelengkapan`, `/kelengkapan/baru`, `/kelengkapan/<fid>`, `/hapus`, `/nomori`, `/butir`, `/butir/<bid>/geser`, `/hapus`, `/pulihkan`, `/catatan-koreksi`, `/catatan-koreksi/hapus` |
| Wilayah | Selaras Kemendagri, kecamatan, desa, riwayat kepala desa; halaman `/referensi/desa/<id>` | `POST /referensi/wilayah`, `/kecamatan`, `/kecamatan/hapus`, `/desa`, `/desa/hapus`, `/desa/pejabat`, `/desa/pejabat/aktif`, `/desa/pejabat/hapus` |
| Panitia A | Satu kartu per SK + anggota; salin jadi SK baru | `POST /referensi/panitia`, `/panitia/hapus`, `/panitia/salin`, `/panitia/anggota`, `/panitia/anggota/hapus` |

Kartu lipat dimuat lewat `GET /referensi/bagian/<kunci>` (header `X-Potongan: 1`).

### 1.6 Template — `berkas/rute/template.py` (admin, termasuk membaca)

`GET /template` (5 tab: Hak Milik & lain, Wakaf, Hak Pakai, Cetakan loket, Penanda & cara pakai),
`GET /template/bagian/<kunci>`, `GET /template/unduh/<jenis>`, `POST /template/unggah`
(cadangkan lama, simpan, uji rakit dengan berkas contoh), `POST /template/pulihkan`.

### 1.7 Pengaturan — `berkas/rute/pengaturan.py`

`GET /pengaturan`: petugas hanya melihat kartu ganti sandi; admin melihat 3 tab Kantor
(semua baris `pengaturan` sebagai isian `set_*`), Penyimpanan, Pengguna.
`POST /pengaturan` (admin) upsert setiap medan `set_*`; `POST /pemeliharaan` (admin) dengan
`aksi` = `pratinjau` | `cadangan_db` | `keluaran`.

### 1.8 Unduhan — `berkas/rute/unduhan.py`

`GET /unduh/<nama>` (DOCX; dirakit ulang bila sudah dirapikan), `GET /foto/<fid>`,
`GET /pratinjau/<nama>` (halaman ber-iframe), `GET /pdf/<nama>` (`?unduh=1`, `?segarkan=1`).
Dokumen yang tidak tercatat di `dokumen_terbit` hanya untuk admin (`unduhan.py:34`).

### 1.9 Perkakas baris perintah — `berkas/perkakas/`

| Skrip | Fungsi | Peluncur |
|---|---|---|
| `impor_excel.py` | Impor `../RAHMA WONTOGIA/Copy of Rutin 2025 ….xlsx` (HM) dan `../wakaf/wakaf.xlsx` (Wakaf) | `impor.bat` |
| `siapkan_template.py` | MERGEFIELD Word → template `{{…}}` (set baku & wakaf) | `siapkan_template.bat`, `jalankan.bat` bila `sk.docx` belum ada |
| `siapkan_hak_pakai.py` | Turunkan `*-hp.docx` dari template HM yang terpasang | manual |
| `siapkan_checklist.py` | Bangun `checklist.docx` & `pengembalian.docx` dari kode | manual |
| `perbaiki_dokumen.py` | Rapikan kategori dokumen hasil impor lama (membuat `data/berkas.db.bak-*`) | manual |
| `pindah_ke_pg.py` | Salin SQLite → PostgreSQL, id dipertahankan, satu transaksi | manual |
| `berkas/db.py` (`python -m berkas.db`) | Buat skema + seed | `jalankan.bat`/`.sh` |

### 1.10 Uji — `uji/`

| Berkas | Jumlah uji | Isi |
|---|---|---|
| `uji_web.py` | 188 | Rute, peran, CSRF, langkah form (SQLite & PostgreSQL) |
| `uji_basis.py` | 23 | Konfigurasi & terjemahan dialek SQL |
| `uji_hak_pakai.py` | 7 | Template Hak Pakai perorangan/badan hukum |
| `uji_konteks.py` | 3 | Uji acuan konteks vs `uji/emas/konteks/*.json` |
| `uji_dokumen.py` | 3 | Uji acuan teks DOCX vs `uji/emas/dokumen/*.txt` |

`uji/emas/` berisi data pemohon asli dan tidak dilacak git (`.gitignore`). Peluncur: `uji.bat`
(`penuh`, `rekam`).

### 1.11 Material di folder induk (bukan kode)

| Folder/berkas | Dipakai kode? |
|---|---|
| `../RAHMA WONTOGIA/*.docx`, `*.xlsx` | Ya — sumber template baku dan impor HM (`siapkan_template.py:35`, `impor_excel.py:36`) |
| `../wakaf/*.docx`, `wakaf.xlsx` | Ya — sumber template wakaf dan impor wakaf. Ada duplikat `.doc` yang tidak dipakai |
| `../hak_pakai/*.pdf` | Tidak — hanya acuan manual untuk `siapkan_hak_pakai.py` |
| `../CHECKLIST HM/*.pdf`, `../*Nomor 18 Tahun 2021*.pdf` | Tidak — acuan regulasi |
| `../surat_tugas/`, `../SURAT TUGAS PANITIA*.docx/.pdf` | **Tidak** — belum ada fitur Surat Tugas; aplikasi hanya punya isian `pemeriksaan.tanggal_surat_tugas` |
| `../RAHMA WONTOGIA/~$ISALAH.docx` | Berkas kunci Word yang tertinggal |

---

## 2. Tabel SQLite

Skema di `berkas/db.py:23-367`, kolom tambahan lewat `migrasi()` (`db.py:948`). Basis data
nyata `data/berkas.db` sudah dicocokkan: skema sama, `PRAGMA foreign_key_check` bersih.
Semua kolom waktu bertipe `TEXT 'YYYY-MM-DD HH:MM:SS'`; boolean bertipe `INTEGER 0/1`.
`PRAGMA foreign_keys = ON` dipasang di tiap koneksi (`basis.py:267`).

Jumlah baris saat audit dicantumkan dalam kurung.

### 2.1 Pengguna & sesi

**`pengguna`** (12)
| Kolom | Tipe | Catatan |
|---|---|---|
| id | INTEGER PK | |
| nama | TEXT NN | |
| username | TEXT NN UNIQUE | |
| sandi_hash | TEXT NN | `garam$hex` PBKDF2-SHA256 200.000 putaran (`db.py:561`) |
| peran | TEXT NN `'petugas'` | `petugas` \| `admin` |
| aktif | INTEGER NN 1 | |
| dibuat | TEXT NN `datetime('now','localtime')` | |

**`sesi`** (1) — token TEXT PK · pengguna_id INTEGER NN → `pengguna.id` ON DELETE CASCADE ·
kedaluwarsa TEXT NN · csrf TEXT NN `''`.

### 2.2 Referensi

**`ref_jenis_hak`** (6) — kode TEXT PK · nama TEXT NN · ada_jangka_waktu INTEGER NN 0 ·
jangka_maks / perpanjangan_maks / pembaruan_maks INTEGER (tahun) · wajib_uang_pemasukan
INTEGER NN 0 · subjek_boleh TEXT NN (CSV) · kegiatan_boleh TEXT NN (CSV) · dasar_subjek TEXT ·
kode_sk TEXT · varian_template TEXT NN `''` · urut INTEGER · aktif INTEGER NN 1.

| kode | nama | jangka | subjek_boleh | kegiatan_boleh | kode_sk | varian |
|---|---|---|---|---|---|---|
| HM | Hak Milik | — | perorangan, badan_hukum | baru, peningkatan | HM | `''` |
| HGB | Hak Guna Bangunan | 30/20/30 | perorangan, badan_hukum | baru, perpanjangan, pembaruan | HGB | `''` |
| HP | Hak Pakai | 30/20/30 | perorangan, badan_hukum, instansi | baru, perpanjangan, pembaruan | HP | `hp` |
| HPL | Hak Pengelolaan | — | instansi | baru | HPL | `''` |
| WAKAF | Hak Wakaf | — | perorangan, badan_hukum, instansi | baru | HW | `wakaf` |
| HMSRS | HM Sarusun | — | perorangan, badan_hukum | baru | HMSRS | `''` |

Sumber seed: `db.py:576-607`.

**`ref_kecamatan`** (18) — id PK · nama TEXT NN UNIQUE · kode TEXT.

**`ref_desa`** (165) — id PK · kecamatan_id INTEGER NN → `ref_kecamatan.id` · nama TEXT NN ·
jenis TEXT NN `'Desa'` · kode TEXT · jabatan_pejabat TEXT NN `'Kepala Desa'` · nama_pejabat
TEXT · UNIQUE(kecamatan_id, nama). Dua kolom pejabat adalah **salinan** pejabat aktif dari
`ref_desa_pejabat` (`wilayah.segarkan`, `wilayah.py:188`). 124 desa belum punya pejabat.

**`ref_desa_pejabat`** (41) — id PK · desa_id INTEGER NN → `ref_desa.id` CASCADE · nama TEXT NN
· jabatan TEXT NN · mulai, sampai, sk_nomor, catatan TEXT · aktif INTEGER NN 0.

**`ref_panitia`** (2) — id PK · nomor_sk TEXT NN · tanggal_sk, berlaku_dari, berlaku_sampai,
keterangan TEXT.

**`ref_panitia_anggota`** (8) — id PK · panitia_id INTEGER NN → `ref_panitia.id` CASCADE ·
urut INTEGER · nama TEXT NN · nip, jabatan, peran, pendapat_baku TEXT.

**`ref_klausa`** (10) — id PK · slot TEXT NN · jenis_hak / kegiatan / subjek TEXT NN `'*'` (CSV)
· berlaku_dari, berlaku_sampai TEXT · isi TEXT NN · catatan TEXT.

**`ref_dokumen_syarat`** (20) — id PK · jenis_hak, kegiatan TEXT NN `'*'` · kategori TEXT NN
`'umum'` (`pemohon`/`badan_hukum`/`tanah`) · nama TEXT NN · wajib INTEGER NN 1 · dasar TEXT · urut.

**`ref_kelengkapan`** (2: `184-HM`, `190-HP`) — id PK · kode TEXT NN UNIQUE · judul TEXT NN ·
jenis_hak, kegiatan TEXT NN `'*'` · dasar TEXT · varian_template TEXT NN `''` · aktif INTEGER NN 1
· nomor_otomatis INTEGER NN 1 · urut.

**`ref_kelengkapan_butir`** (62) — id PK · kelengkapan_id INTEGER NN → `ref_kelengkapan.id`
CASCADE · induk_id INTEGER → `ref_kelengkapan_butir.id` CASCADE (pohon) · penanda TEXT NN ·
nama TEXT NN · nama_dokumen TEXT · sifat TEXT NN (`butir`/`judul`/`alternatif`) · wajib INTEGER
NN 1 · isian_bebas INTEGER NN 0 · subjek, asal_tanah TEXT NN `'*'` · slot_baku TEXT · syarat_id
INTEGER → `ref_dokumen_syarat.id` · dasar TEXT · jamak INTEGER NN 0 · aktif INTEGER NN 1 · urut.

**`ref_catatan_koreksi`** (9) — id PK · butir_id INTEGER → `ref_kelengkapan_butir.id` CASCADE
(NULL = semua butir) · teks TEXT NN · aktif INTEGER NN 1 · urut.

**`pengaturan`** (6) — kunci TEXT PK · nilai TEXT. Kunci: `kantor_nama`, `kantor_kode`,
`kantor_kota`, `kepala_kantor_nama`, `kepala_kantor_nip`, `kata_penyambung` (`db.py:895`).

### 2.3 Berkas (inti)

**`berkas`** (68) — id PK · nomor_berkas TEXT · tanggal_permohonan TEXT · jenis_hak_dimohon TEXT NN
→ `ref_jenis_hak.kode` · jenis_hak_rekomendasi TEXT → `ref_jenis_hak.kode` · jenis_kegiatan TEXT
NN `'baru'` · asal_tanah TEXT NN `'tanah_negara'` · kewenangan TEXT NN `'kantah'` · status TEXT
NN `'draf'` (`draf`/`diperiksa`/`selesai`/`ditolak`) · catatan TEXT · dibuat_oleh INTEGER →
`pengguna.id` (NULL = arsip impor; 48 baris) · dibuat TEXT NN · diubah TEXT.

Tabel anak (semua `ON DELETE CASCADE` ke `berkas`):

| Tabel | Relasi | Kolom |
|---|---|---|
| `pihak` (206) | N : 1 berkas | id PK, berkas_id, peran TEXT NN (`penerima_hak`/`kuasa`/`pemilik_sebelumnya`/`ahli_waris`/`saksi`/`nazhir`/`wakif`), jenis_subjek TEXT NN `'perorangan'`, nama TEXT NN, nik, ttl, jenis_kelamin, alamat, pekerjaan TEXT, urut |
| `pihak_badan_hukum` (0) | 1 : 1 `pihak` (PK=FK pihak_id, CASCADE) | bentuk, kedudukan, akta_nomor, akta_tanggal, notaris, akta_ubah_nomor, akta_ubah_tanggal, pengesahan_nomor, pengesahan_tanggal, npwp, nib, wakil_nama, wakil_jabatan, wakil_nik, bidang_usaha, notaris_kota, pengesahan_oleh, akta_ubah_notaris, akta_ubah_notaris_kota, ubah_sah_nomor, ubah_sah_tanggal, nib_tanggal, csr_akta_nomor, csr_akta_tanggal, csr_notaris, csr_notaris_kota — semua TEXT |
| `bidang_tanah` (68) | 1 : 1 (PK=berkas_id) | desa_id → `ref_desa.id`, nomor_pbt, tanggal_pbt, nib TEXT, luas_pbt, luas_surat INTEGER, batas_utara/timur/selatan/barat, penggunaan_sekarang, rencana_penggunaan, rtrw, kesesuaian, tanggal_peta_analisis, uraian_penguasaan_fisik, uraian_selisih_luas TEXT |
| `riwayat_perolehan` (252) | N : 1 | id PK, urut, uraian TEXT NN, dokumen_bukti TEXT |
| `hak_asal` (0) | 1 : 1 | jenis_hak_lama, nomor_sertipikat, nomor_sk, tanggal_sk, tanggal_berakhir TEXT, luas INTEGER |
| `dokumen_pendukung` (1.236) | N : 1 | id PK, urut, kategori TEXT `'tambahan'`, uraian TEXT NN, keaslian TEXT `'Asli'`, jenis, nomor, tanggal, pejabat, wilayah_pejabat TEXT |
| `pemeriksaan` (68) | 1 : 1 | tanggal_surat_tugas, tanggal_bap TEXT, panitia_id → `ref_panitia.id`, keberatan, catatan TEXT |
| `foto_lapang` (194) | N : 1 | id PK, urut, nama_file TEXT NN, keterangan TEXT (berkasnya di `data/foto/`) |
| `pendapat_anggota` (192) | N : 1 | id PK, urut, nama TEXT NN, peran, setuju INTEGER NN 1, alasan, menandatangani INTEGER NN 1, diwakili_oleh |
| `risalah` (68) | 1 : 1 | nomor, tanggal TEXT, kesimpulan TEXT `'dikabulkan'` (`dikabulkan`/`ditolak`/`dilengkapi`), jangka_waktu_tahun INTEGER, alasan TEXT |
| `sk` (68) | 1 : 1 | nomor, tanggal, pejabat_nama, pejabat_nip, validasi_pph TEXT, uang_pemasukan INTEGER |
| `dokumen_terbit` (254) | N : 1 | id PK, jenis_dokumen TEXT NN (`bap`/`risalah`/`sk`), nomor, nama_file TEXT NN, dicetak_oleh → `pengguna.id`, dicetak_pada TEXT NN |

Kategori `dokumen_pendukung` yang terpakai: 11 slot baku (`permohonan`, `sppf`,
`tanah_dipunyai`, `penggunaan`, `keterangan_penguasaan`, `tidak_sengketa`, `pernyataan`,
`tanda_batas`, `selisih`, `absentee`, `kuasa`), 4 slot wakaf (`akta_ikrar`, `pengesahan_nazhir`,
`kesediaan_nazhir`, `bersedia_diaudit`), serta `tambahan` dan `alas_hak` (`db.py:445-492`,
`web.py:547`).

**`nomor_urut`** — PK(jenis, kode, tahun) · terakhir INTEGER NN 0. Isi saat audit:
`(sk,HM,2026)=3`, `(sk,HW,2026)=12`, `(risalah,-,2026)=1`, `(pradaftar,-,2026)=2`.

### 2.4 Pradaftar

**`pradaftar`** (2) — id PK · nomor TEXT · tanggal TEXT NN · jenis_hak TEXT NN →
`ref_jenis_hak.kode` · jenis_kegiatan, asal_tanah TEXT NN · kelengkapan_id → `ref_kelengkapan.id`
· pemohon_nama TEXT NN · pemohon_jenis_subjek TEXT NN · pemohon_nik, pemohon_alamat,
pemohon_telepon, kuasa_nama, kuasa_nik TEXT · desa_id → `ref_desa.id` · letak_lain TEXT ·
luas_surat INTEGER · nomor_pbt TEXT · status TEXT NN `'baru'` (`baru`/`diterima`/`dikembalikan`/
`batal`) · catatan, alasan_terima TEXT · berkas_id → `berkas.id` **ON DELETE SET NULL** ·
dibuat_oleh → `pengguna.id` · dibuat TEXT NN · diubah TEXT.

**`pradaftar_jawab`** (15) — PK(pradaftar_id → `pradaftar` CASCADE, butir_id →
`ref_kelengkapan_butir` CASCADE) · ada INTEGER NN 0 (`0` tidak ada, `1` ada, `2` tidak berlaku,
`3` perlu koreksi) · uraian TEXT (baris dipisah `\n` untuk butir jamak) · catatan TEXT.

### 2.5 Diagram relasi (ringkas)

```
pengguna ─┬─< sesi
          ├─< berkas.dibuat_oleh ──┬─ 1:1 bidang_tanah ── ref_desa >── ref_kecamatan
          ├─< dokumen_terbit       ├─ 1:1 hak_asal / pemeriksaan ── ref_panitia ─< ref_panitia_anggota
          └─< pradaftar            ├─ 1:1 risalah / sk                          ref_desa ─< ref_desa_pejabat
                                   ├─< pihak ── 1:1 pihak_badan_hukum
ref_jenis_hak ─< berkas            ├─< riwayat_perolehan / dokumen_pendukung / foto_lapang
              ─< pradaftar         └─< pendapat_anggota / dokumen_terbit
ref_kelengkapan ─< ref_kelengkapan_butir (pohon via induk_id) ─< pradaftar_jawab >── pradaftar
                                                       └─< ref_catatan_koreksi
pradaftar.berkas_id ──> berkas (satu arah; berkas tidak menyimpan pradaftar_id)
```

Tabel tanpa FK formal tetapi dirujuk lewat teks: `ref_klausa` (dipilih per slot),
`ref_dokumen_syarat` (dicocokkan lewat kata kunci di uraian dokumen), `nomor_urut`.

### 2.6 Isian/kolom yang disimpan tetapi tidak dipakai di mana pun

| Kolom | Bukti |
|---|---|
| `berkas.kewenangan` | Hanya ditulis (`formulir.py:107`) & ditampilkan; tak ada validasi/template (README:756 mengakuinya) |
| `pemeriksaan.catatan` | Tidak pernah ditulis — upsert `formulir.py:232` tidak menyertakannya |
| `ref_jenis_hak.wajib_uang_pemasukan`, `pembaruan_maks` | Hanya di `db.py` |
| `ref_jenis_hak.perpanjangan_maks` | Hanya ditampilkan (`web.py:2516`) |
| `ref_klausa.berlaku_dari/berlaku_sampai`, `catatan` | `pilih_klausa` tidak membacanya (`konteks.py:294`) |
| `ref_panitia.berlaku_dari/berlaku_sampai` | Hanya label "arsip/berlaku" di kartu (`web.py:2921`); tidak dicek terhadap tanggal BAP |
| `ref_kelengkapan_butir.syarat_id` | Tidak pernah diisi (hanya disalin di `susun_kelengkapan.py:396`) |
| `hak_asal.*` (kecuali `nomor_sertipikat`) | Tidak dipakai template mana pun |
| `pihak_badan_hukum.npwp` | Disimpan, tak dipakai konteks |
| `sk.validasi_pph`, `sk.uang_pemasukan`, `sk.pejabat_*` | Ada di konteks, tidak dipakai `sk.docx`/`sk-hp.docx` (lihat 4.3) |

---

## 3. Aturan bisnis tersembunyi di kode

### 3.1 Penomoran

| Aturan | Lokasi |
|---|---|
| Nomor Risalah = `{n}/{tahun}`, tahun dari **tanggal Risalah**, satu urutan per tahun untuk **semua jenis hak** (kode `'-'`) | `dokumen/terbitkan.py:26-36` |
| Nomor SK = `{n}/{kode_sk}/{kantor_kode}/{bulan romawi tgl SK}/{tahun tgl SK}`; urutan per `kode_sk` per tahun; `kode_sk` dari `ref_jenis_hak` (WAKAF→`HW`); `kantor_kode` dari `pengaturan` (bawaan `BPN`) | `terbitkan.py:39-55` |
| Kode yang dipakai = `jenis_hak_rekomendasi` bila ada, kalau tidak `jenis_hak_dimohon` | `terbitkan.py:45` |
| Nomor hanya diberi bila kolom nomor **kosong**; nomor yang diketik/diimpor tidak pernah diganti, walau formatnya salah | `terbitkan.py:155,162` |
| Risalah/SK tidak bisa dicetak tanpa tanggal (ValueError) | `terbitkan.py:150-161` |
| Counter atomik `INSERT … ON CONFLICT DO NOTHING` lalu `UPDATE terakhir+1`, langsung `commit` — nomor yang keluar tidak ditarik walau perakitan gagal | `db.py:1075-1085` |
| Nomor pradaftar `PD-{n:04d}/{tahun}`; tahun = **tanggal hari ini**, bukan isian `tanggal` | `pradaftar.py:480-483` |
| Nama berkas keluaran `{id:04d} - {BAP\|Risalah\|SK} - {nama tanpa tanda baca}.docx` | `terbitkan.py:84-87` |
| Nama cetakan loket `{nomor dengan / jadi -} - {Kelengkapan\|Pengembalian} - {nama}.docx` | `dokumen/kelengkapan.py:142-146` |
| Nama foto `{berkas_id:04d}-{12 hex acak}.jpg/png` | `dokumen/foto.py:76` |
| "Cetak semua" = BAP + Risalah, SK hanya bila kesimpulan `dikabulkan` | `terbitkan.py:175-186` |

### 3.2 Validasi sebelum cetak — `konteks.periksa()` (`dokumen/konteks.py:749-899`)

Galat menghentikan cetak (`rute/berkas.py:121`); peringatan tidak.

| Aturan | Tingkat | Baris |
|---|---|---|
| Harus ada pihak `penerima_hak`/`pemohon` | galat | 762 |
| Jenis subjek penerima ∈ `subjek_boleh` jenis hak | galat | 766 |
| Perorangan: NIK wajib, 16 digit angka | galat | 769-774 |
| Perorangan: jenis kelamin kosong | peringatan | 775 |
| Badan hukum: `akta_nomor` wajib | galat | 777 |
| Kegiatan ∈ `kegiatan_boleh` | galat | 790 |
| Desa, luas PBT, nomor PBT **dan** NIB wajib | galat | 794-799 |
| Batas tanah belum lengkap | peringatan | 800-803 |
| Luas PBT ≠ luas surat tanpa dokumen bertuliskan "perbedaan luas"/"selisih" | peringatan | 804-810 |
| Kegiatan `baru` wajib ada riwayat perolehan | galat | 813 |
| Kegiatan selain `baru` wajib nomor sertipikat hak asal | galat | 815 |
| Jenis hak berjangka: jangka waktu wajib dan ≤ `jangka_maks` | galat | 820-826 |
| Panitia dipilih, ≥ 3 orang, **ganjil** — jumlah **termasuk kepala desa** yang ditambahkan otomatis | galat | 829-840 |
| Foto lapangan (berkasnya ada di disk) ≥ 4 (`foto.MINIMAL`) | galat | 843 |
| Urutan tanggal permohonan ≤ BAP ≤ Risalah ≤ SK | galat | 849-856 |
| Tenggat 14 hari kerja surat tugas → Risalah (Senin–Jumat, **tanpa hari libur**, hari mulai tidak dihitung) | peringatan | 859-867, `util.py:132` |
| Tanggal Risalah kosong; tanggal SK kosong (hanya bila kesimpulan `dikabulkan`) | peringatan | 870-875 |
| Anggota tidak setuju / tidak menandatangani wajib ada alasan | galat | 878-884 |
| Dokumen wajib `ref_dokumen_syarat` dicari lewat **kata kunci** (frasa khas atau 22 huruf pertama) di uraian dokumen; syarat kategori `badan_hukum` dilewati bila bukan badan hukum | peringatan | 887-898, `_kata_kunci` 991 |
| **Wakaf**: Nazhir wajib; Nazhir perorangan < 3 → peringatan; NIK Nazhir ke-2 dst. 16 digit (galat) / kosong (peringatan); TTL kosong; Wakif wajib (galat), domisili/NIK/pekerjaan Wakif (peringatan); AIW wajib (galat); Pengesahan Nazhir (peringatan); rincian AIW/pengesahan; jangka waktu harus kosong | campur | 902-959 |
| **Hak Pakai**: subjek `instansi` (peringatan), rincian badan hukum, akta perubahan tanpa persetujuan, wakil kosong | peringatan | 962-988 |

Catatan: NIK penerima Nazhir pertama hanya dicek bila subjek perorangan (aturan umum); Nazhir
lain dicek di `_periksa_wakaf` mulai indeks 1 (`konteks.py:916`).

### 3.3 Perhitungan & format nilai turunan

| Aturan | Lokasi |
|---|---|
| Terbilang Indonesia s.d. miliar ("seratus", "seribu", "sebelas") | `util.py:21` |
| Pemisah ribuan titik; bilangan dibulatkan | `util.py:61` |
| `luas_teks`: `600 m² (enam ratus meter persegi)`; `luas_kira` (luas surat): `± 450 m² (kurang lebih …)`; luas 0 dianggap kosong | `util.py:70-84` |
| Tanggal panjang `06 Februari 2025` (hari 2 digit), hari "Jum'at" | `util.py:11,87` |
| Sapaan dari huruf pertama jenis kelamin: `p…`→Sdri., `l…`→Sdr., lain→Sdr./Sdri. | `util.py:123` |
| Pembaca tanggal menerima `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY` | `util.py:46` |
| Selisih luas = luas_pbt − luas_surat; kalimat baku selisih + rujukan surat selisih | `konteks.py:349-352, 542-553` |
| Kalimat penguasaan fisik baku + "dimana hal ini sesuai dengan {SPPF}" | `konteks.py:612, 741` |
| Jangka berakhir = tanggal SK + n tahun; 29 Feb → 28 Feb | `konteks.py:371-380` |
| `nama_penerima` pada wakaf = seluruh Nazhir dipisah koma | `konteks.py:386` |
| `nama_pemohon` = nama kuasa bila ada, kalau tidak penerima | `konteks.py:387` |
| Wakif = pihak `wakif`, atau `pemilik_sebelumnya` bila berkas wakaf tanpa wakif | `konteks.py:365-367` |
| Bentuk Nazhir: perorangan→"perseorangan", badan_hukum→"badan hukum", **instansi→"organisasi"** | `konteks.py:275` |
| Sebutan Hak Pakai: instansi → "Hak Pakai selama dipergunakan", lainnya → "Hak Pakai dengan jangka waktu" | `konteks.py:115-128` |
| UU bentuk badan hukum dari awalan `bentuk` atau nama: PT/PERSEROAN, YAYASAN, KOPERASI | `konteks.py:133-149` |
| Frasa akta/keputusan/OSS/CSR disusun hanya dari isian yang terisi | `konteks.py:152-244` |
| **Kepala desa letak tanah selalu ditambahkan** sebagai anggota Panitia A (urut 99, tanpa NIP), dengan **pendapat baku yang di-hardcode** | `konteks.py:72-80` |
| Pendapat anggota dicocokkan ke susunan panitia lewat **nama dinormalisasi** (huruf+angka saja); kosong → `pendapat_baku` | `konteks.py:556-595` |
| `kasi_pgt_nama/nip` = anggota pertama yang jabatannya memuat kata **"Penataan"** | `konteks.py:518, 598-609` |
| Dokumen `sppf` & `kuasa` dikeluarkan dari daftar `dokumen` (punya penanda sendiri) | `konteks.py:339-342, 526` |
| Keaslian dokumen kosong tercetak "Asli" di DATA PENDUKUNG | `konteks.py:618-622`, `web.py:560` |
| Dokumen khusus dicari dulu per kategori, lalu fallback frasa di uraian (mis. "ikrar wakaf", "pengesahan naz") | `konteks.py:625-634` |
| Uraian AIW/pengesahan Nazhir kosong → disusun dari rincian; rincian lama ditebak dari uraian bebas (regex nomor & tanggal, "pengganti"→APAIW) | `konteks.py:41-46, 696-724` |
| Pemilihan klausa: baris paling spesifik (skor jumlah kolom non-`*` yang cocok) menang; `{{x}}` di dalam klausa diganti nilai konteks string | `konteks.py:294-318, 533-538` |
| Berkas WAKAF/HP dideteksi dari `jenis_hak_rekomendasi` lebih dulu | `konteks.py:101-108` |

### 3.4 Mesin template — `dokumen/docxgen.py`

| Aturan | Baris |
|---|---|
| Nilai "benar" untuk `{{?…}}`/`{{!…}}`: bukan None/False, string bukan `""`, `"-"`, atau `"0"`, list tidak kosong. Karena itu klausa `uraian_jangka` = `"-"` untuk HM dianggap kosong | 127-134 |
| `_akhir` = `;` kecuali baris terakhir `.` | 383 |
| `_huruf` a–z, **lewat 26 jadi angka** | 388 |
| `_romawi` kecil i…x (tanpa l/c) | 399-409 |
| Penanda tak dikenal tercetak kosong, tidak gagal | 160-164 |
| Tabel yang semua barisnya habis dibuang | 327-331 |
| Lampiran foto: halaman baru, 2 foto/baris, foto maks ±(½ lebar teks − 0,6 cm) × 0,78, baris `cantSplit`, huruf = huruf terbanyak di dokumen | 497-560 |
| Paragraf kosong di ujung naskah dibuang sebelum lampiran | 481-494 |
| Blok `{{#…}}` tanpa penutup: paragraf pembuka dibuang diam-diam | 291-297 |

### 3.5 Pradaftar & kelengkapan — `berkas/pradaftar.py`

| Aturan | Baris |
|---|---|
| Lengkap/kurang **tidak disimpan**, dihitung ulang tiap kali | 14-17 |
| Butir berlaku bila `subjek` dan `asal_tanah` cocok (`*` = selalu); tidak berlaku **menurun** ke anak | 194-234 |
| Grup terpenuhi bila ≥1 anak `alternatif` berstatus ada **dan** semua anak non-alternatif tidak kurang | 242-293 |
| Butir alternatif tidak pernah "kurang" sendirian | 268-273 |
| `KOREKSI` menahan penerimaan walau butirnya tidak wajib | 264-267 |
| Kurang mengalahkan koreksi pada grup | 284-292 |
| Grup alternatif yang kurang dilaporkan satu baris (bukan per anak) | 296-320 |
| Butir yang belum dijawab dihitung "Tidak Ada" | `web.py:1519` |
| Progres: satu grup alternatif = satu satuan | 342-369 |
| Catatan koreksi dibuang bila pilihan bukan KOREKSI | 457-458 |
| Pradaftar tanpa nama → disimpan "(tanpa nama)"; tanggal kosong → hari ini; jenis hak kosong → HM | 398-404 |
| Formulir yang dipakai: `aktif=1`, jenis_hak cocok (spesifik menang atas `*`), lalu kegiatan, lalu `urut` | 116-130 |
| Terima: status harus `baru`; belum lengkap boleh diterima **asal ada alasan**; hasil berkas status `draf`, `dibuat_oleh` = petugas penerima | 494-538 |
| Salinan ke berkas: pemohon→`penerima_hak`, kuasa→`kuasa`, desa/luas/PBT→`bidang_tanah` (hanya bila salah satu terisi), butir ada/koreksi→`dokumen_pendukung` (kategori = slot butir, warisan induk, atau `tambahan`; butir koreksi diberi akhiran "(perlu koreksi: …)") | 513-588 |
| Pradaftar `diterima`/`batal` terkunci baca-saja; `dikembalikan` **tidak** terkunci | 44, `rute/pradaftar.py:37` |
| Surat pengembalian ditolak bila sudah lengkap | `dokumen/kelengkapan.py:169` |
| mtime DOCX cetakan loket = max(diubah, dibuat, mtime template) agar singgahan PDF dipakai ulang | `dokumen/kelengkapan.py:191-195` |
| Tiga butir (Peta Bidang, Risalah Pemeriksaan Tanah A, Surat Pengantar) bawaan `wajib=0` | `db.py:687-692, 743, 756-758` |
| Formulir resmi dipasang sekali per `kode`; formulir yang dihapus total **dipasang ulang** saat aplikasi menyala berikutnya | `db.py:1005-1021` |
| Butir/formulir yang sudah dijawab pradaftar hanya dinonaktifkan, bukan dihapus | `susun_kelengkapan.py:309-333, 408-415` |
| Penomoran otomatis butir: tingkat atas 1,2,3; di bawahnya huruf berlanjut lintas sub-kelompok; kepala sub-kelompok tanpa huruf | `susun_kelengkapan.py:139-164` |

### 3.6 Hak akses & keamanan — `berkas/izin.py`, `aplikasi.py`, `sesi.py`

| Aturan | Lokasi |
|---|---|
| Admin melihat/mengubah semua; petugas melihat miliknya **+ berkas tanpa pemilik (impor)**, tapi hanya boleh mengubah miliknya | `izin.py:35-53` |
| Hapus berkas/pradaftar, seluruh POST referensi, template (termasuk baca), pengaturan & pengguna: admin | `rute/*.py` `@perlu_admin` |
| Dokumen tak tercatat `dokumen_terbit` hanya untuk admin | `rute/unduhan.py:34-47` |
| Sesi 12 jam; sesi kedaluwarsa dibersihkan saat login berikutnya | `sesi.py:20, 50` |
| CSRF wajib di semua metode selain GET/HEAD/OPTIONS; token di form `_csrf` atau header `X-CSRF-Token`; disisipkan otomatis lewat regex | `aplikasi.py:30-37, 78-89, 157-169` |
| Permintaan `/bagian/` tanpa sesi → 401 teks, bukan redirect | `aplikasi.py:71-75` |
| Batas unggahan 120 MB (selaras `client_max_body_size` nginx) | `aplikasi.py:27`, `deploy/nginx-sipantas.conf` |
| Template unggahan ≤ 30 MB, harus zip berisi `word/document.xml`, dicoba dirakit dengan berkas contoh; cadangan 15 versi | `dokumen/templat.py:100-131, 196` |
| Foto: JPG/PNG (tanpa Pillow) atau format apa pun yang dibaca Pillow; diputar EXIF, sisi terpanjang 1600 px, JPEG mutu 85 | `dokumen/foto.py:19-64` |
| Catatan koreksi dipotong 300 karakter | `rute/referensi.py:329` |
| Pengaturan: **setiap** medan `set_*` di-upsert apa adanya (kunci baru bisa dibuat dari form) | `rute/pengaturan.py:35-38` |

### 3.7 Penyimpanan & pemeliharaan — `berkas/pemeliharaan.py`

PDF pratinjau disisakan 40 berkas / 100 MB terbaru (dipangkas tiap PDF baru dan saat start);
DOCX loket ikut dibuang bila PDF-nya dibuang (`:94-113`). Cadangan DB disisakan 3 (`:116`).
Rapikan keluaran: hanya DOCX lebih tua dari N hari (bawaan 90), tercatat di `dokumen_terbit`,
berkasnya masih ada, dan **mtime ≤ waktu cetak + 300 detik** (dianggap tidak disunting tangan)
(`:120-154`). DOCX yang hilang dirakit ulang saat diunduh (`rute/unduhan.py:50-59`).

### 3.8 Impor Excel — `berkas/perkakas/impor_excel.py`

| Aturan | Baris |
|---|---|
| Berkas sudah ada bila nama penerima + nomor PBT sama (nomor PBT kosong → nama penerima saja) | 387-398 |
| Semua berkas impor: kegiatan `baru`, tanah negara, kewenangan kantah, **status `selesai`**, `dibuat_oleh` NULL | 247-252 |
| Wakaf: "Atas Nama" dipecah koma → orang pertama penerima, sisanya `nazhir`; "KTP Sebelumnya" → `wakif` | 235-280 |
| "Nama Pemohon" ≠ penerima → pihak `kuasa` | 272-274 |
| Riwayat dari 10 pasang kolom; pasangan yang hanya punya "Surat N" tanpa "Jenis Alas Hak N" **dibuang** | 300-309 |
| Kolom bebas `tambahan surat 1..54` → `tambahan`, `Surat 1..10` → `alas_hak`; isi mengandung "surat kuasa"/"ikrar wakaf"/… → slot baku; teks kembar dilewati | 336-356 |
| Awalan Asli/Fotokopi/Fotocopy/Legalisir dipisah ke kolom keaslian (legalisir → "Salinan") | 443-453 |
| Kalimat penguasaan fisik & selisih disimpan hanya bila beda dari kalimat otomatis | 416-433 |
| Susunan panitia (nama, NIP, pendapat) **di-hardcode** dan disalin jadi `pendapat_anggota` tiap berkas | 40-90, 374-376 |
| Pejabat SK diisi dari `pengaturan.kepala_kantor_*` | 365-371 |
| Bulan singkatan "agust", "peb", "nop" dikenali | 130-152 |

---

## 4. Template dokumen (BA, Risalah, SK)

### 4.1 Lokasi dan pemilihan

| Berkas (`templates/`) | Ukuran | Dipakai untuk |
|---|---|---|
| `bap.docx`, `risalah.docx`, `sk.docx` | 308 / 445 / 114 KB | varian `''`: HM, HGB, HPL, HMSRS |
| `bap-wakaf.docx`, `risalah-wakaf.docx`, `sk-wakaf.docx` | 480 / 446 / 97 KB | varian `wakaf`: WAKAF |
| `bap-hp.docx`, `risalah-hp.docx`, `sk-hp.docx` | 304 / 442 / 111 KB | varian `hp`: HP |
| `checklist.docx`, `pengembalian.docx` | 36 / 36 KB | Cetakan loket; varian `checklist-<varian>.docx` dicari dulu (`hm`, `hp` belum ada → pakai baku) |
| `cadangan/*.docx` | 28 berkas, 12 MB | Versi lama (maks 15 per jenis) |

Pemilihan: `ref_jenis_hak.varian_template` dari `jenis_hak_rekomendasi || jenis_hak_dimohon`
(`terbitkan.py:77-81`) → `templat.kunci()` jatuh ke set baku bila varian belum punya berkasnya
(`templat.py:75-84`). Sumber pembangunan ulang: `../RAHMA WONTOGIA/` (baku), `../wakaf/`
(wakaf) lewat `siapkan_template.py`; HP diturunkan dari template baku lewat
`siapkan_hak_pakai.py`; loket dibangun dari kode `siapkan_checklist.py`. Template ikut dilacak
git; `deploy/perbarui.sh` berhenti bila template di server berbeda dari git.

### 4.2 Sintaks penanda (`dokumen/docxgen.py:1-25`)

`{{nama}}` nilai · `{{*daftar.kolom}}` paragraf/baris tabel diulang · `{{*daftar._akhir|_nomor|_huruf|_romawi}}`
· `{{?x}}` paragraf hanya bila x benar · `{{!x}}` bila x salah · `{{@foto}}` lampiran foto ·
`{{#daftar}}…{{/daftar}}` blok berulang (di dalamnya `{{?daftar.kolom}}` per anggota).

### 4.3 Placeholder per template (hasil ekstraksi dari XML, header & footer)

Semua penanda di 11 template dikenali konteksnya — tidak ada penanda asing, tidak ada sisa MERGEFIELD.

**`bap.docx`** (38): `hari_bap tgl_bap_terbilang bulan_bap tahun_bap_terbilang tgl_bap_pendek`
· blok `#panitia` (`*panitia._nomor *panitia.nama ?panitia.nip *panitia.nip *panitia.jabatan_lengkap`)
· `sapaan nama_penerima luas_teks luas_terbilang nomor_pbt tanggal_pbt nib jenis_desa nama_desa
kecamatan` · `*riwayat.uraian *riwayat._akhir ?penguasaan_fisik penguasaan_fisik` ·
`penggunaan_sekarang rencana_penggunaan tanggal_peta_analisis kasi_pgt_nama kasi_pgt_nip rtrw
kesesuaian batas_utara batas_timur batas_selatan batas_barat @foto`.

**`bap-hp.docx`** (38): sama dengan `bap.docx`, `sapaan nama_penerima` → `penerima_disapa`.

**`bap-wakaf.docx`** (33): seperti `bap.docx` tanpa `sapaan`, `tanggal_peta_analisis`,
`kasi_pgt_nama`, `kasi_pgt_nip`, `rtrw`.

**`risalah.docx`** (55): `nomor_risalah hari_risalah tgl_risalah_terbilang bulan_risalah
tahun_risalah_terbilang tgl_risalah_pendek` · tabel `*panitia._nomor *panitia.nama
*panitia.jabatan_lengkap *panitia._akhir` · `panitia_nomor_sk panitia_tanggal_sk panitia_jumlah
panitia_jumlah_terbilang` · `jenis_desa nama_desa kecamatan nama_hak nama_penerima
alamat_penerima nik_penerima pekerjaan_penerima ttl_penerima pemilik_sebelumnya` · `luas_teks
luas_terbilang tanggal_pbt nomor_pbt nib penggunaan_sekarang rencana_penggunaan
tanggal_peta_analisis tgl_bap rtrw kesesuaian batas_*` · `*dokumen.uraian *dokumen._akhir ?sppf
sppf ?surat_kuasa surat_kuasa` · `*riwayat.uraian *riwayat._akhir ?penguasaan_fisik
penguasaan_fisik ?selisih_teks selisih_teks` · blok `#panitia` (`*panitia.peran *panitia.pendapat`).

**`risalah-wakaf.docx`** (70): kerangka `risalah.docx` + blok `#nazhir` (`*nazhir._romawi .nama
.alamat .nik .pekerjaan .ttl ._akhir`), `?wakif` + blok `#wakif` (`*wakif._romawi .nama .alamat
.nik .pekerjaan`), `nama_nazhir nama_wakif nazhir_uraian`; tanpa `alamat/nik/pekerjaan/ttl_penerima`
dan `pemilik_sebelumnya`.

**`risalah-hp.docx`** (80): kerangka `risalah.docx` dengan `nama_hak_lengkap` + blok
`#pemohon_perorangan` (`alamat_penerima nik_penerima pekerjaan_penerima`) / `#pemohon_badan_hukum`
(`bh_kedudukan bh_akta_uraian bh_pengesahan_ringkas bh_nib`), `!badan_hukum ?badan_hukum`,
`?bh_akta_uraian ?bh_perubahan_uraian bh_perubahan_uraian ?bh_pengesahan_ringkas ?bh_nib
?bh_wakil_nama bh_wakil_nama bh_wakil_jabatan ?bh_csr bh_csr bh_uraian_subjek bh_diwakili`,
`?pemilik_sebelumnya jangka_tahun jangka_terbilang`.

**`sk.docx`** (33): `nomor_sk nama_hak_kapital nama_hak nama_penerima ?nama_penerima
alamat_penerima ?alamat_penerima nik_penerima tanggal_permohonan` · `luas_teks luas_terbilang
jenis_desa nama_desa kecamatan tanggal_pbt nomor_pbt nib` · `tgl_risalah nomor_risalah` ·
`*riwayat.uraian *riwayat._akhir ?penguasaan_fisik penguasaan_fisik penggunaan_sekarang
rencana_penggunaan tanggal_peta_analisis rtrw kesesuaian ?selisih_teks selisih_teks` ·
`panitia_nomor_sk panitia_tanggal_sk tgl_sk`.

**`sk-hp.docx`** (45): kerangka `sk.docx` dengan `nama_hak_lengkap_kapital nama_hak_lengkap_judul
domisili_penerima !badan_hukum ?badan_hukum bh_uraian_subjek jangka_tahun ?jangka_tahun
jangka_terbilang jangka_terbilang_kapital ?bh_csr bh_csr ?bh_dasar_bentuk bh_dasar_bentuk`.

**`sk-wakaf.docx`** (26): `nomor_sk nama_penerima nama_pemohon tanggal_permohonan bentuk_nazhir
nama_wakif akta_ikrar_sk pengesahan_nazhir_sk luas_teks luas_terbilang jenis_desa nama_desa
kecamatan tanggal_pbt nomor_pbt nib panitia_nomor_sk panitia_tanggal_sk rencana_penggunaan
penggunaan_sekarang tgl_sk ?pejabat_nama pejabat_nama pejabat_nip ?alamat_penerima alamat_penerima`.

**`checklist.docx`** (17): `judul_formulir dasar_formulir nomor tanggal pemohon pemohon_nik
pemohon_alamat letak luas *butir.penanda *butir.nama *butir.ada *butir.tidak ?catatan catatan kota
petugas`.

**`pengembalian.docx`** (13): `nomor pemohon pemohon_alamat judul_formulir dasar_formulir nama_hak
letak_frasa *dikembalikan._nomor *dikembalikan.nama *dikembalikan.keterangan kota tanggal petugas`.

### 4.4 Penanda yang disediakan konteks tetapi tidak dipakai template mana pun

Dari `konteks.bangun()` (`dokumen/konteks.py:382-538`): **seluruh slot klausa**
(`telaah_subjek`, `uraian_jangka`, `diktum_uang_pemasukan`, `asal_tanah_judul`), `uang_pemasukan`,
`validasi_pph`, `jangka_berakhir`, `ada_jangka_waktu`, `ada_selisih`, `luas_surat_teks`,
`luas_terbilang_saja`, `via_kuasa`, `wakaf`, `kode_hak`, `jenis_kegiatan`, `jabatan_pejabat`,
`nama_pejabat`, `akta_ikrar`, `akta_ikrar_nomor/tanggal`, `ppaiw_nama`, `pengesahan_nazhir(_nomor/_tanggal)`,
`kesediaan_nazhir`, `bersedia_diaudit`, `nazhir_jumlah(_terbilang)`, `bh_akta_nomor/tanggal`,
`bh_notaris(_kota)`, `bh_pengesahan_*`, `bh_bentuk`, `bh_bidang_usaha`, `bh_nib_tanggal`,
`bh_oss_uraian`, `bh_wakil_nik`, daftar `pendapat`. Di `kelengkapan.konteks()`: `kantor`, `kuasa`,
`kurang`, `koreksi`, `nomor_pbt`.

### 4.5 Teks yang di-hardcode di dalam template

| Template | Hardcode | Seharusnya dari |
|---|---|---|
| `sk.docx`, `sk-hp.docx` | Nama "ILKHAM MOODUTO" + NIP 19821006… (masing-masing 1×) | `sk.pejabat_nama/nip` atau `pengaturan.kepala_kantor_*` (dipakai `sk-wakaf.docx`) |
| `risalah.docx` (10×), `sk.docx` (4×) | Teks "Hak Milik" | `{{nama_hak}}` — padahal set baku juga dipakai HGB/HPL/HMSRS |
| Semua BAP/Risalah/SK | "Bone Bolango" (3–37×), "Suwawa", "75.03", "Kepala Kantor Pertanahan" | `pengaturan.kantor_nama/kota/kode` |
| `sk-hp.docx` | Perpanjangan "paling lama 20 (dua puluh) tahun" (`siapkan_hak_pakai.py:377-381`) | `ref_jenis_hak.perpanjangan_maks` |
| `pengembalian.docx` | "Sdr. {{pemohon}}" (`siapkan_checklist.py:166`) | `util.sapaan`, atau tanpa sapaan untuk badan hukum |

Konversi lama juga di-hardcode di kode: nama orang, NIK, nomor SK contoh di
`siapkan_template.py:123-211` dan `siapkan_hak_pakai.py:318-319` ("Kab. Bone Bolango").

---

## 5. Dependensi eksternal dan konfigurasi

### 5.1 Paket Python — `requirements.txt`

| Paket | Versi | Dipakai | Wajib? |
|---|---|---|---|
| python-docx | ==1.2.0 | docxgen, perkakas, uji | ya |
| openpyxl | ==3.1.5 | `perkakas/impor_excel.py` | hanya impor |
| Pillow | ==12.2.0 | `dokumen/foto.py` | opsional |
| Flask | ==3.1.2 | web | ya |
| waitress | ==3.0.2 | server | ya |
| psycopg[binary] | **>=3.2.3** (tidak dipatok) | `basis.py` bila PostgreSQL | opsional |
| **pywin32** (`win32com`, `pythoncom`, `winreg`) | **tidak tercantum** | `dokumen/pdf.py:43-83`, `dokumen/penyambung.py:148-191` | opsional, Windows |

Python ≥ 3.10 (README), CI memakai 3.12. SQLite ≥ 3.35 diperlukan untuk `RETURNING`
(`db.py:406-413`); `ON CONFLICT … DO UPDATE` ≥ 3.24.

### 5.2 Program eksternal

| Program | Untuk | Lokasi/deteksi |
|---|---|---|
| Microsoft Word (COM `Word.Application`) | PDF pratinjau & kata penyambung | `dokumen/pdf.py:43` (registry) |
| LibreOffice `soffice` | PDF pratinjau bila Word tak ada; timeout 180 dtk | `pdf.py:25-29` (4 path tetap) |
| Huruf Bookman Old Style, Times New Roman | Tata letak sama dengan Word | `DEPLOY.md:9-26` |
| nginx + certbot, systemd, sqlite3 CLI, awscli, pg_dump | Produksi | `deploy/` |

### 5.3 Variabel lingkungan / `.env`

| Nama | Dibaca oleh | Lewat `.env`? | Bawaan |
|---|---|---|---|
| `DB_URL` | `konfigurasi.py:148` | ya | SQLite `data/berkas.db` |
| `DB_JENIS`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAMA`, `DB_SSLMODE` | `konfigurasi.py:130-152` | ya | 127.0.0.1:5432 / postgres / panitia_a |
| `KUNCI_RAHASIA` | `aplikasi.py:50`, `jalankan.py:41` | **tidak** (`os.environ`) | `os.urandom(32)` |
| `HTTPS` | `sesi.py:23` | **tidak** | mati |
| `PORTA`, `ALAMAT`, `UTAS` | `jalankan.py:26-31` | **tidak** | 8000 / 127.0.0.1 / 8 |
| `TZ` | systemd, CI | — | Asia/Makassar di server |
| `AKAR`, `DB_PATH`, `TUJUAN_S3`, `SIMPAN_HARI` | `deploy/backup.sh` | `/etc/sipantas.env` | /srv/sipantas, s3://cadangan-bpn-bonbol/sipantas, 30 |

Contoh berkas: `.env.contoh`, `deploy/sipantas.env.contoh`.

### 5.4 Konfigurasi di basis data — tabel `pengaturan`

`kantor_nama` "Kantor Pertanahan Kabupaten Bone Bolango", `kantor_kode` "BPN.75.03", `kantor_kota`
"Suwawa", `kepala_kantor_nama`, `kepala_kantor_nip`, `kata_penyambung` "sk" (`db.py:895-903`).
Akun awal **admin/admin123** di-seed (`db.py:927-929`).

### 5.5 Konstanta di kode yang berfungsi sebagai konfigurasi

| Konstanta | Nilai | Lokasi |
|---|---|---|
| `UMUR_JAM` sesi | 12 | `sesi.py:20` |
| `MAKS_UNGGAH` | 120 MB | `aplikasi.py:27` |
| `MAKS_UKURAN` template | 30 MB | `dokumen/templat.py:100` |
| Cadangan template | 15 | `templat.py:196` |
| `foto.MINIMAL / SISI_MAKS / MUTU_JPEG` | 4 / 1600 / 85 | `dokumen/foto.py:19-21` |
| `PRATINJAU_MAKS_BERKAS/MB`, `CADANGAN_DB_SIMPAN`, `KELUARAN_UMUR_HARI`, `JEDA_SUNTING` | 40 / 100 / 3 / 90 / 300 dtk | `pemeliharaan.py:30-34` |
| Kemendagri `KODE_KABUPATEN` + 18 kec / 160 desa / 5 kel | 75.03 | `wilayah.py:38-90` |
| `PER_HALAMAN`, `PER_BAWAAN` | (10,25,50,100), 25 | `web.py:323-324` |
| Teks login "Kantor Pertanahan Kabupaten Bone Bolango" | — | `web.py:301-302` |

### 5.6 Deploy & CI

- `deploy/sipantas.service`: waitress `127.0.0.1:8002`, 8 utas, `--url-scheme=https`, user `ubuntu`.
- `deploy/nginx-sipantas.conf`: TLS, 120M, timeout 200 dtk, `/static/` langsung dari disk.
- `deploy/backup.sh` + `.timer` (02.30 WITA): `.backup` SQLite + `integrity_check` (atau
  `pg_dump`), tar `templates/`, sync `data/foto` ke S3, simpan lokal 30 hari di `/data/cadangan`.
- `deploy/perbarui.sh`: berhenti bila `templates/` berubah, backup, `git pull --ff-only`, pip, restart.
- `.github/workflows/deploy.yml`: uji `uji_basis` + `uji_web` di SQLite & PostgreSQL 16, lalu
  deploy ke EC2 via OIDC + SSM (`deploy/aws/*.json`, repo `iksanh/SIPANTAS`, environment `produksi`).
- Peluncur Windows: `jalankan.bat`, `jalankan_jaringan.bat` (`ALAMAT=0.0.0.0`), `impor.bat`,
  `siapkan_template.bat`, `uji.bat`; Linux: `jalankan.sh`.

---

## 6. Inkonsistensi dan kode duplikat

Diurutkan dari dampak terbesar. **[Bug]** = perilaku salah yang bisa terjadi sekarang;
**[Data]** = sudah terlihat di `data/berkas.db`; **[Dok]** = dokumentasi/pesan tak sesuai kode;
**[Dup]** = logika ganda.

### 6.1 Keamanan & integritas data

1. **[Data] Akun `admin` masih bersandi bawaan `admin123`** di `data/berkas.db` (dicek dengan
   hash). Seed: `berkas/db.py:927-929`; `DEPLOY.md:143-144` meminta segera diganti.
2. **[Data][Bug] Nomor Risalah bisa kembar dengan nomor hasil impor.** Counter
   `nomor_urut(risalah,-,2026)` = 1, padahal sudah ada nomor impor sampai `78/2026`; dua berkas
   sudah memakai `78/2026`. Counter tidak memperhitungkan nomor yang ada
   (`terbitkan.py:26-36`, `db.py:1075`).
3. **[Data][Bug] 7 SK bernomor `/HW/BPN.75.03/IX/2026` (tanpa angka)** dari impor. Karena
   penomoran otomatis hanya jalan bila kolom kosong (`terbitkan.py:162`), dokumen ini akan terus
   tercetak tanpa nomor urut. Format manual lain juga ada: `12`, `160/SK-75.03.HP.01.02/IX/2026`,
   `/HW/BPN-75.03/…`. Tidak ada validasi format nomor (`formulir.py:261`).
4. **[Bug] Status pradaftar bisa diubah ke `diterima` atau `baru` tanpa lewat `terima()`.**
   `rute/pradaftar.py:147-150` menerima nilai apa pun dari `pradaftar.STATUS`, sehingga pradaftar
   terkunci "diterima" tanpa berkas. Tombol UI hanya mengirim `dikembalikan`/`batal`.
5. **[Bug] Pradaftar tanpa formulir kelengkapan dianggap lengkap.** Jenis hak tanpa formulir
   (HGB, HPL, WAKAF, HMSRS; HP kegiatan non-baru) menghasilkan pohon kosong → `kurang=[]` →
   `lengkap=True` → bisa diterima tanpa alasan (`pradaftar.py:107-110, 509`), padahal layar
   menampilkan "belum punya daftar kelengkapan" (`web.py:1522`).
6. **[Bug] Menyimpan butir grup "Dasar Penguasaan atau Alas Hak" dari halaman Susun menghapus
   `slot_baku='alas_hak'`.** `susun_kelengkapan.py:268-269` hanya menerima slot di
   `db.KATEGORI_BAKU`, sedangkan `alas_hak` bukan slot baku (`db.py:721`, `web.py:547`). Akibatnya
   anak-anak grup itu akan disalin sebagai `tambahan` saat pradaftar diterima. Daftar pilihan slot
   di `web.py:1957` juga tidak memuat `alas_hak`.
7. **[Bug] `pindah_ke_pg` bisa gagal pada tabel berinduk diri sendiri.**
   `ref_kelengkapan_butir.induk_id` diabaikan dalam urutan (`pindah_ke_pg.py:37`) dan baris diambil
   tanpa `ORDER BY` (`:54`); bila butir induk ber-id lebih besar dari anaknya (mungkin setelah
   "Susun formulir" memindah butir), PostgreSQL menolak FK dan seluruh pindahan dibatalkan.
8. **[Dok] Dokumen yang dirakit ulang tidak dijamin sama.** README:927-929 menyebut hasilnya
   "sama", padahal `terbitkan.rakit_ulang()` (`terbitkan.py:133-145`) merakit dari data & template
   **saat ini** — berkas yang sudah disunting atau template yang diganti sesudah cetak akan
   menghasilkan dokumen berbeda dengan yang ditandatangani.
9. **`KUNCI_RAHASIA` praktis tidak berpengaruh.** Hanya mengisi `SECRET_KEY` Flask
   (`aplikasi.py:50`), padahal tidak ada yang memakai `flask.session`; sesi & CSRF sepenuhnya di
   tabel `sesi`. Peringatan di `jalankan.py:41-42` dan `DEPLOY.md:60-66` menyesatkan.
10. **`.env` tidak dibaca untuk `HTTPS`, `KUNCI_RAHASIA`, `ALAMAT`, `PORTA`, `UTAS`** walau
    `.env.contoh:24-31` mencontohkannya — modul memakai `os.environ` langsung (`sesi.py:23`,
    `aplikasi.py:50`, `jalankan.py:26-31`), bukan `konfigurasi.ambil()`. Di Windows dengan `.env`,
    kuki tidak akan bertanda `Secure`.
11. Rute `POST /referensi/panitia/anggota/hapus` menghapus anggota berdasarkan id saja, tanpa
    mencocokkan `panitia_id` (`rute/referensi.py:171-177`); bandingkan `simpan_anggota` yang
    mencocokkan keduanya (`:162`).
12. Pratinjau dan unggah template memakai berkas sementara bernama tetap `uji-{jenis}.docx` di
    temp sistem (`templat.py:261`) — dua admin bersamaan bisa saling timpa.

### 6.2 Jenis hak "dimohon" vs "rekomendasi" tidak konsisten

Bila Panitia merekomendasikan jenis hak lain (`jenis_hak_rekomendasi`, Pasal 139 ayat (5)):

| Yang memakai **rekomendasi** dulu | Yang memakai **dimohon** saja |
|---|---|
| `konteks.wakaf()` / `hak_pakai()` (`konteks.py:101-108`) | `d["hak"]` → nama hak, subjek_boleh, jangka waktu (`konteks.py:61-62`) |
| `pilih_klausa` (`konteks.py:299`) | Syarat dokumen (`konteks.py:887-890`) |
| Varian template & kode nomor SK (`terbitkan.py:45, 79`) | Slot dokumen baku di formulir (`web.py:572, 945`, `formulir.py:208`) |
| Kartu Nazhir di formulir (`web.py:781`) | Tampilan rincian Hak Pakai (`web.py:69` lewat `konteks.hak_pakai` → rekomendasi) |

Akibat: berkas dimohon HM tetapi direkomendasikan WAKAF dicetak dengan template wakaf dan nomor
`HW`, tetapi `nama_hak` = "Hak Milik", validasi jangka waktu/subjek mengikuti HM, dan slot Akta
Ikrar Wakaf tidak muncul di formulir sehingga galat "Akta Ikrar Wakaf belum diisi" sulit dipenuhi.

### 6.3 Fitur yang setengah jadi / mati

1. **Pustaka klausa tidak dipakai.** `ref_klausa` (10 baris, `db.py:859-892`), `pilih_klausa`
   dan pengisian slot (`konteks.py:294-318, 533-538`), serta tab "Klausa" di Data referensi ada,
   tetapi **tak satu pun template** memuat `{{telaah_subjek}}`, `{{uraian_jangka}}`,
   `{{diktum_uang_pemasukan}}`, atau `{{asal_tanah_judul}}` (lihat 4.4). README:630-635 menyebut
   menambah jenis hak cukup lewat klausa — tidak benar untuk template saat ini.
2. **HGB/HPL/HMSRS memakai template HM yang memuat teks "Hak Milik" tetap** (10× di Risalah, 4× di
   SK) dan tidak mencetak jangka waktu, uang pemasukan, atau validasi PPh (4.5). Validasi jangka
   waktu HGB tetap wajib (`konteks.py:820`), tetapi nilainya tak tercetak.
3. **Nama Kepala Kantor di-hardcode di `sk.docx` dan `sk-hp.docx`**, sehingga isian "Pejabat
   penanda tangan" (`web.py:1005`) dan `pengaturan.kepala_kantor_*` tidak berpengaruh untuk HM/HP,
   berbeda dengan `sk-wakaf.docx` yang memakai `{{pejabat_nama}}`.
4. `kesimpulan='ditolak'` tidak menghasilkan dokumen penolakan, walau `dokumen_terbit.jenis_dokumen`
   (`db.py:292`) dan `terbitkan.JUDUL` (`terbitkan.py:19`) menyebut `penolakan`. Tidak ada template
   `penolakan`.
5. `PEMETAAN` di `siapkan_template.py:65,86` membuat penanda `pemilik_sebelumnya_2` dan
   `penggunaan_sk` yang tidak pernah disediakan konteks (saat ini tidak muncul di template aktif,
   tetapi akan muncul kosong bila template dibangun ulang dari sumber yang memuat field itu).
6. Folder template Jinja `tampilan/` dirujuk `aplikasi.py:47` tetapi tidak ada.
7. Material Surat Tugas Panitia (`../surat_tugas/`, `../SURAT TUGAS PANITIA*.docx/.pdf`) belum
   punya fitur; aplikasi hanya menyimpan `tanggal_surat_tugas`.
8. Kolom/atribut tersimpan tetapi tak terpakai — lihat 2.6.

### 6.4 Dokumentasi & pesan yang tidak sesuai kode

| Klaim | Kenyataan |
|---|---|
| README:182-183 "Susunan nomor, huruf, dan tingkatannya sengaja **tidak** bisa diubah dari layar" | Ada halaman Susun formulir lengkap: tambah, geser, pindah, nomori ulang (`susun_kelengkapan.py`, `rute/referensi.py:378-495`) |
| README:187-190 menambah formulir jenis hak lain "tidak mengubah kode, cukup di `db.py`" | Juga bisa dari layar `/referensi/kelengkapan/baru` |
| README:682-683 & `web.py:1151-1152`: nomor Risalah "berurutan per jenis hak per tahun" | Risalah satu urutan untuk semua jenis hak (`terbitkan.py:32`) |
| `db.py:304` komentar `pradaftar.nomor` "diberi saat diterima di loket" | Diberi saat dibuat (`pradaftar.py:425`); README:96 benar |
| README:532 "Tidak ada basis data server … tidak perlu internet" | README:839 dan kode mendukung PostgreSQL |
| README:758 "Keluaran hanya DOCX. Untuk PDF, buka di Word" | Ada pratinjau & unduh PDF (`dokumen/pdf.py`, `rute/unduhan.py:128`) |
| README:732-733 "165 uji" web | 188 `test_` di `uji/uji_web.py` |
| README:223 `python impor_excel.py wakaf`, README:282 `python perbaiki_dokumen.py`, README:516 `python siapkan_template.py wakaf`; docstring `impor_excel.py:4-6`, `perbaiki_dokumen.py:3`, `siapkan_template.py:6`; pesan `terbitkan.py:119`, `jalankan.py:40` | Skrip sudah pindah ke paket: `python -m berkas.perkakas.<nama>` |
| README:513 tabel set template hanya HM & Wakaf | Ada set HP (diturunkan, bukan dari folder sumber) |
| `web.py:1522-1525` "Baru Hak Milik yang formulirnya terpasang" | `190-HP` juga terpasang (`db.py:682`) |
| `rute/__init__.py:4-9` daftar blueprint | Tidak menyebut `pradaftar` |
| `rute/pradaftar.py:26-27` "Tidak ada padanan arsip impor di sini" | `pradaftar.daftar()` tetap menyertakan `dibuat_oleh IS NULL` untuk petugas (`pradaftar.py:54-55`) dan `izin.boleh_lihat` mengizinkan pemilik NULL |
| `jalankan.bat:30` "memasukkan 47 berkas" | Angka tetap yang sudah usang |
| `wsgi.py:4` menyarankan gunicorn | Tidak ada di `requirements.txt` |
| `db.py:2` "Skema dan koneksi SQLite" | Melayani PostgreSQL juga |
| `kelengkapan.py:136` komentar `JENIS` "(kunci template, judul di layar)" | Isinya hanya kunci template; judul di `JUDUL` |
| `requirements.txt` | Tidak mencantumkan `pywin32`, padahal dibutuhkan Word COM; `psycopg` tidak dipatok sementara paket lain dipatok demi kestabilan keluaran |
| `parameter.json` (0 bita) di akar `app/`, belum dilacak git | Sisa langkah CI (`deploy.yml` menulis `parameter.json`) |

### 6.5 Aturan yang berbeda antartempat

1. **Deteksi surat selisih luas**: `periksa` mencari kata "perbedaan luas"/"selisih" di semua
   uraian (`konteks.py:806-807`), sedangkan kalimat selisih memakai `_dokumen_khusus(d, "selisih",
   "perbedaan luas")` (`konteks.py:341`) — dokumen bertuliskan "selisih" tetapi tidak berkategori
   `selisih` meloloskan peringatan namun tidak ikut tercetak.
2. **Checklist syarat di tab Dokumen** memakai `referensi.semua()["syarat"]` = seluruh syarat
   wajib tanpa saring jenis hak/kegiatan (`referensi.py:24-25`, `web.py:935-943`), sehingga berkas
   HM ikut menampilkan syarat WAKAF/perpanjangan; `periksa` menyaringnya (`konteks.py:887-890`).
3. **Huruf urut setelah z**: `docxgen._pembuat_baris` beralih ke angka (`docxgen.py:388`),
   `susun_kelengkapan._huruf` memakai `aa, ab` (`susun_kelengkapan.py:128-136`).
4. **Sapaan**: dokumen Panitia A memakai `util.sapaan`, surat pengembalian menulis "Sdr." tetap
   (`siapkan_checklist.py:166`).
5. **Tahun nomor pradaftar** dari tanggal hari ini (`pradaftar.py:482`), tahun nomor Risalah/SK
   dari tanggal dokumen (`terbitkan.py:29,42`).
6. **Pihak lain** selalu `jenis_subjek='perorangan'` dan tanpa jenis kelamin (`formulir.py:161`),
   padahal Nazhir/Wakif bisa badan hukum; `konteks.BENTUK_NAZHIR` hanya membaca penerima utama.
7. **Urutan pihak kuasa**: formulir `urut=1` (`formulir.py:152`), impor `urut=9`
   (`impor_excel.py:273`), pihak sebelumnya `urut=10` vs pihak lain `2+i`.
8. **Status impor**: semua berkas impor `selesai` (`impor_excel.py:252`), padahal 7 SK-nya belum
   bernomor (6.1-3).
9. **Panitia urut**: `referensi.semua()` mengurutkan SK panitia `tanggal_sk DESC`
   (`referensi.py:21-22`), `referensi.ringkas()` `tanggal_sk DESC, id DESC` (`:54-57`).
10. **Label pilihan ganda**: `web.SUBJEK` "Instansi / BUMN / BUMD" (`web.py:19-20`) vs
    `susun_kelengkapan.SUBJEK` "Instansi" (`susun_kelengkapan.py:29-30`); `web.KEGIATAN` vs
    `susun_kelengkapan.KEGIATAN` (`:33-35`) dengan label berbeda.
11. **Bawaan umur rapikan keluaran** ditulis dua kali: literal `"90"` di
    `rute/pengaturan.py:55` dan `pemeliharaan.KELUARAN_UMUR_HARI` (`pemeliharaan.py:33`).
12. **Folder cadangan DB**: `perbaiki_dokumen.cadangkan()` menulis di samping `db.BERKAS_DB`
    (bisa diatur `DB_URL`), tetapi `pemeliharaan` mencari `*.bak-*` di `jalur.DATA`
    (`pemeliharaan.py:27`). Cadangan juga ada di `backup/berkas.db` dan `tmp/tmp.*/baru.db` yang
    tidak dikelola apa pun.
13. **Impor riwayat**: pasangan kolom yang hanya berisi "Surat N" dibuang (`impor_excel.py:304-309`),
    padahal kolom yang sama juga diimpor lagi sebagai dokumen `alas_hak` (`:336-347`).
14. **Nama berkas keluaran mengikuti nama penerima saat cetak**: di `keluaran/` terdapat
    `0058 - BAP - Dr Hi Muhajirin Yanis MPdI.docx` dan `… Yasin …`, serta campuran huruf besar
    (`0055 - BAP - HASAN GOBEL` vs `0055 - SK - Hasan Gobel`). Versi lama tertinggal dan tidak
    dibersihkan (`terbitkan.py:84-87`).

### 6.6 Kode duplikat

| Duplikasi | Lokasi |
|---|---|
| Aturan kelengkapan pradaftar ditulis dua kali (Python & JS) dan harus dijaga sama manual | `pradaftar.py:242-369` ↔ `static/app.js:817-890`; `web._ringkas_periksa`/`_cap_grup`/`_belum_diperiksa` ↔ `app.js:885-930` |
| Frasa Akta Ikrar Wakaf / pengesahan Nazhir | `konteks.py:655-693` ↔ `app.js:709-727` |
| Hitung selisih luas | `konteks.py:349-352` ↔ `konteks.py:731-732` ↔ `app.js:362-368` ↔ `impor_excel.py:429-433` |
| `templat.kunci()` dan `templat.kunci_kelengkapan()` identik | `dokumen/templat.py:75-84` ↔ `:87-97` |
| `_anggota_peran()` dan `_anggota_nip()` (loop sama, beda kolom) | `konteks.py:598-609` |
| Deteksi wakaf ditulis ulang | `web.py:781` ↔ `konteks.wakaf()` `konteks.py:101` |
| Konstanta `DOCX`, fungsi `_teks()`, `_lampiran()` | `rute/unduhan.py:20-31`, `rute/pradaftar.py:163-170`, `rute/template.py:28-36` |
| Pesan "Pratinjau PDF memerlukan Microsoft Word atau LibreOffice…" + buang PDF singgahan | `rute/unduhan.py:103-113`, `rute/pradaftar.py:205-223`, `dokumen/pdf.py:111-113` |
| Penggantian teks lintas-run (peta karakter → run) | `docxgen._ganti_di_paragraf` (`:56-99`), `siapkan_template._ganti_regex` (`:221-251`), `siapkan_hak_pakai._ganti_run` (`:59-82`) |
| `_semua_paragraf`, `_hapus`/`_hapus_paragraf`/`_buang` | `docxgen.py:102, 213, 412`, `siapkan_template.py:254, 383`, `siapkan_hak_pakai.py:50` |
| Daftar peran/pejabat & penyaringan petugas | `izin.saringan_daftar` (`izin.py:49`) ↔ salinan inline `pradaftar.py:54-55` |
| Subkueri "nama penerima" `peran IN ('penerima_hak','pemohon')` | `formulir.py:29`, `rute/unduhan.py:122`, `konteks.penerima_hak` (`konteks.py:96`) |
| Traversal tulis ulang urut/penanda butir | `susun_kelengkapan._tulis_urut` (`:109-125`) ↔ `nomori` (`:167-182`) |
| Pemilihan "paling khusus menang" | `konteks.pilih_klausa` (`:294`) ↔ SQL `pradaftar.formulir` (`:116`) ↔ `pradaftar._cocok` (`:194`) |
| Peta keaslian | `impor_excel.KEASLIAN` (`:443`) ↔ `web.KEASLIAN` (`:560`) — komentar mengharuskan keduanya selaras |
| Daftar `STATUS` berkas & pradaftar terpisah dan tidak divalidasi di server: `formulir.simpan` menerima status/kesimpulan/kegiatan apa pun dari form (`formulir.py:104-108, 259`) | `web.py:21-23`, `pradaftar.py:40-41` |
| Isian kecamatan/desa + JSON `DAFTAR_DESA` dirakit dua kali | `web.py:845-853` ↔ `web.py:1737-1744` |
| Susunan Panitia contoh di-hardcode, juga tersalin sebagai `pendapat_anggota` per berkas | `impor_excel.py:40-90, 374-376` |

---

### Lampiran: cara pemeriksaan

- Seluruh `.py`, `static/app.js`, README, DEPLOY, berkas deploy & CI dibaca langsung.
- Skema nyata: `sqlite3 file:data/berkas.db?mode=ro` → `PRAGMA table_info/foreign_key_list`.
- Placeholder template: XML `word/document.xml`, `header*.xml`, `footer*.xml` di tiap `.docx`
  dibaca dengan `zipfile`, teks run digabung per paragraf, lalu dicocokkan dengan regex
  `docxgen.PENANDA` dan dibandingkan dengan kunci di `konteks.py` / `kelengkapan.py`.
- Skrip bantu disimpan di scratchpad sesi, bukan di repo.
