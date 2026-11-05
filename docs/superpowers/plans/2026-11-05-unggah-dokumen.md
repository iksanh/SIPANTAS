# Unggah Dokumen (Tahap 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Petugas mengunggah banyak dokumen sekaligus; sistem memisah & menebak jenis per halaman, petugas memastikan jenis, sistem mengekstrak data, petugas memvalidasi lalu Simpan.

**Architecture:** Pembacaan pindah ke server: `berkas/baca/` berisi OCR (lapisan teks PDF → pypdfium2, sisanya RapidOCR), pemilah kata kunci, dan satu pengurai per jenis. File dan teks disimpan di tabel `unggahan`/`unggahan_dokumen`; di Berkas baru sebagai titipan bertoken yang ditautkan saat Simpan. UI di `static/app.js` memakai ulang pola pratinjau OCR yang ada (`setelMedan`, pratinjau AIW/PBT).

**Tech Stack:** Python 3.13, Flask 3.1, SQLite/PostgreSQL tanpa ORM, unittest, RapidOCR (onnxruntime), pypdfium2, Pillow, JS tanpa kerangka.

**Spec:** `docs/superpowers/specs/2026-11-05-unggah-dokumen-design.md`

## Global Constraints

- Tanpa AI/layanan luar; semua pembacaan di server aplikasi, tanpa GPU.
- Tidak ada yang ditulis ke tabel berkas (`pihak`, `bidang_tanah`, `dokumen_pendukung`, …) sebelum tombol Simpan. Rute unggah hanya menulis `unggahan`/`unggahan_dokumen`.
- Yang tidak yakin dikosongkan, bukan ditebak; isian yang berbeda dari isian sekarang tidak dicentang otomatis.
- Paket baru dipatok versinya di `requirements.txt` dengan komentar seperti paket lain. OCR opsional seperti Pillow: tanpa paketnya aplikasi tetap jalan, fitur unggah menampilkan pesan pemasangan.
- File di `data/unggahan/`; titipan tak tertaut dihapus setelah **7 hari**.
- Batas (diputuskan di sini, spec §11): **20 MB per file**, **30 halaman per file**, format PDF/JPG/PNG.
- Uji: `python -m unittest uji.<modul>`; uji ditulis dulu dan harus gagal. Contoh teks/gambar buatan sendiri; jangan baca `data/`, `uji/emas/`, `keluaran/`, `backup/`.
- Uji acuan (`uji_konteks`, `uji_dokumen`) punya ±80 kegagalan lama yang bukan akibat pekerjaan ini; yang dijaga: jumlahnya tidak bertambah.
- Kerja di branch `feat/unggah-dokumen` dari `main`. Bahasa kode, komentar, dan pesan: Indonesia, gaya yang sudah ada.

## Review Focus

1. **Dua KTP berurutan dalam satu PDF** (suami-istri) harus jadi dua dokumen, bukan satu → uji di Task 2 (`test_ktp_berurutan_tidak_digabung`).
2. **Petugas tanpa hak ubah / pengguna lain** membuka gambar atau teks unggahan orang lain (berisi NIK) → harus 403/404 → uji di Task 6 (`test_unggahan_orang_lain_ditolak`).
3. **Berkas baru tidak jadi disimpan** → titipan dan file-nya hilang setelah 7 hari, bukan menumpuk → uji di Task 5 (`test_titipan_lama_dibersihkan`).
4. **PDF terkunci sandi atau rusak, atau satu halaman gagal OCR** → file/halaman itu saja yang ditolak/"Tidak terbaca", sisanya jalan → uji di Task 1 (`test_pdf_rusak`) dan Task 6 (`test_satu_file_rusak_lainnya_jalan`).
5. **Salah baca OCR lazim pada NIK** (O↔0, I/l↔1, spasi di tengah) → NIK tetap terbaca 16 digit atau dikosongkan + peringatan, tidak pernah dipotong diam-diam → uji di Task 3 (`test_nik_salah_baca_ocr`).

---

### Task 1: Pembaca halaman (OCR) dan paket

**Files:**
- Create: `berkas/baca/__init__.py` (kosong, docstring modul), `berkas/baca/ocr.py`
- Modify: `requirements.txt`
- Test: `uji/uji_unggah_ocr.py`

**Interfaces:**
- Produces:
  - `ocr.TERSEDIA: bool` — RapidOCR dan pypdfium2 bisa diimpor.
  - `ocr.PESAN_PASANG: str` — "Fitur unggah dokumen perlu paket tambahan: python -m pip install -r requirements.txt"
  - `ocr.BATAS_BITA = 20 * 1024 * 1024`, `ocr.BATAS_HALAMAN = 30`
  - `class GalatBaca(Exception)` — pesan siap tampil.
  - `ocr.baca(nama: str, isi: bytes) -> list[Halaman]`; `Halaman = dataclass(no: int, teks: str, gagal: bool)`. Raise `GalatBaca` untuk format bukan PDF/JPG/PNG, melebihi batas, PDF rusak/bersandi.
  - `ocr.gambar(nama: str, isi: bytes, no: int, lebar: int = 900) -> bytes` — PNG satu halaman untuk layar verifikasi.

- [ ] **Step 1: Branch dan spike paket.** `git switch -c feat/unggah-dokumen`; commit spec + plan. Pasang `rapidocr_onnxruntime` dan `pypdfium2` di Python 3.13 Windows. Bila `rapidocr_onnxruntime` tidak mendukung 3.13, pakai paket `rapidocr` + `onnxruntime`. Catat versi yang terpasang dan patok di `requirements.txt` (komentar: untuk apa, opsional). Ukur waktu OCR satu halaman A4 300 dpi; tulis angkanya di pesan commit.
- [ ] **Step 2: Tulis uji yang gagal** di `uji/uji_unggah_ocr.py`:
  - `test_pdf_berlapisan_teks`: PDF minimal satu halaman yang dirakit sebagai bita di dalam uji (objek Catalog/Pages/Page/Font Helvetica/stream `BT /F1 24 Tf 72 700 Td (KARTU KELUARGA) Tj ET`) → `baca()` mengembalikan 1 halaman, `"KARTU KELUARGA" in teks`, `gagal is False`.
  - `test_gambar_di_ocr` (`skipUnless(ocr.TERSEDIA)`): PNG 1200×400 putih dengan tulisan hitam "KARTU TANDA PENDUDUK" (`ImageFont.load_default(size=64)`) → teks mengandung "KARTU" dan "PENDUDUK" (abaikan huruf besar/kecil).
  - `test_format_ditolak`: `baca("a.docx", b"PK..")` → `GalatBaca`.
  - `test_terlalu_besar`: isi `BATAS_BITA + 1` bita → `GalatBaca` dengan "20 MB" di pesannya.
  - `test_pdf_rusak`: `baca("x.pdf", b"%PDF-1.4 rusak")` → `GalatBaca`.
  - `test_terlalu_banyak_halaman`: PDF 31 halaman → `GalatBaca` dengan "30".
  - `test_gambar_png`: `gambar()` atas PDF uji → bita diawali `b"\x89PNG"`.
- [ ] **Step 3: Jalankan** `python -m unittest uji.uji_unggah_ocr` → GAGAL (modul tidak ada).
- [ ] **Step 4: Implementasi `ocr.py`.** Jenis dikenali dari bita awal (`%PDF`, `\x89PNG`, `\xff\xd8`), bukan ekstensi. PDF: tiap halaman `get_textpage().get_text_range()`; bila teks <20 karakter non-spasi, render 300 dpi → OCR. Gambar: Pillow `ImageOps.exif_transpose` → OCR. Hasil RapidOCR digabung per baris (urut y lalu x) dengan `\n`. OCR satu halaman yang melempar galat → `Halaman(gagal=True, teks="")`, dicatat ke log tanpa isi teks.
- [ ] **Step 5: Jalankan** uji yang sama → LULUS.
- [ ] **Step 6: Commit** `feat(baca): pembaca halaman PDF/gambar dengan RapidOCR`.

### Task 2: Pemilah jenis per halaman

**Files:**
- Create: `berkas/baca/pilah.py`, `berkas/baca/jenis/__init__.py`
- Test: `uji/uji_unggah_pilah.py`

**Interfaces:**
- Produces:
  - `jenis.DAFTAR: dict[str, Jenis]`; `Jenis = dataclass(kode: str, label: str, pola: list[tuple[str, float]], satu_halaman: bool)`. Kode: `ktp`, `kk`, `sppf`, `aiw`, `pbt`, `lainnya`, `tidak_terbaca`. `lainnya`/`tidak_terbaca` tanpa pola.
  - `pilah.tebak(teks: str) -> tuple[str, float]` — (kode, yakin 0..1).
  - `pilah.kelompokkan(halaman: list[Halaman]) -> list[Potongan]`; `Potongan = dataclass(hal_awal: int, hal_akhir: int, jenis: str, yakin: float, teks: str)`.
  - `pilah.AMBANG_YAKIN = 0.6` (di bawahnya UI menandai "kurang yakin").

- [ ] **Step 1: Tulis uji yang gagal.** Contoh teks buatan per jenis (pola di `jenis/__init__.py`, contoh: KTP "PROVINSI GORONTALO / KABUPATEN BONE BOLANGO / NIK : … / Nama … / Berlaku Hingga"; KK "KARTU KELUARGA / No. …"; SPPF "SURAT PERNYATAAN PENGUASAAN FISIK BIDANG TANAH"; AIW "AKTA IKRAR WAKAF"; PBT "PETA BIDANG TANAH").
  - `test_tebak_tiap_jenis`: tiap contoh → kodenya, yakin ≥ 0.6.
  - `test_teks_kosong_tidak_terbaca`: `""`, `"  \n"`, dan `"ab"` → `("tidak_terbaca", 0.0)`.
  - `test_tidak_dikenal_lainnya`: "SURAT KETERANGAN DOMISILI Nomor 12/2025" → `"lainnya"`.
  - `test_ocr_huruf_besar_kecil_dan_spasi`: "kartu   tanda\npenduduk" tetap `ktp`.
  - `test_halaman_berurutan_digabung`: halaman [sppf, sppf, kk] → 2 potongan, (1,2,sppf) dan (3,3,kk), teks potongan pertama = gabungan dua halaman dipisah `"\n\f\n"`.
  - `test_ktp_berurutan_tidak_digabung`: [ktp, ktp] → 2 potongan.
  - `test_halaman_gagal_jadi_tidak_terbaca`: `Halaman(gagal=True)` → potongan `tidak_terbaca`, tidak digabung dengan tetangga.
- [ ] **Step 2: Jalankan** `python -m unittest uji.uji_unggah_pilah` → GAGAL.
- [ ] **Step 3: Implementasi.** Teks dinormalkan (huruf kecil, spasi rapat) sebelum dicocokkan. Skor jenis = jumlah bobot pola yang cocok / total bobot jenis itu; ambil skor tertinggi; skor < 0.3 → `lainnya`. Teks < 20 karakter non-spasi → `tidak_terbaca`. Gabungkan halaman berurutan berjenis sama kecuali `satu_halaman=True` (KTP) dan `tidak_terbaca`; yakin potongan = rata-rata halaman.
- [ ] **Step 4: Jalankan** → LULUS.
- [ ] **Step 5: Commit** `feat(baca): pemilah jenis dokumen per halaman`.

### Task 3: Pengurai KTP dan pemeriksaan NIK

**Files:**
- Create: `berkas/baca/jenis/ktp.py`, `berkas/baca/periksa.py`
- Test: `uji/uji_unggah_ktp.py`

**Interfaces:**
- Produces:
  - Kontrak semua pengurai (dipakai Task 4 & 6): `urai(teks: str) -> Hasil` dengan `Hasil = {"isian": dict[str,str], "pihak": list[dict], "dokumen": list[dict], "peringatan": list[str]}`. Kunci `pihak`: `nama, nik, ttl, jenis_kelamin, pekerjaan, alamat` (sama dengan kolom tabel `pihak`; `jenis_kelamin` "Laki-laki"/"Perempuan"). Kunci `dokumen`: `uraian, kategori`.
  - `periksa.nik(nik: str, ttl: str = "", jenis_kelamin: str = "") -> list[str]` — daftar peringatan.
  - `periksa.rapikan_nik(mentah: str) -> str` — 16 digit atau `""`.

- [ ] **Step 1: Tulis uji yang gagal.**
  - `test_urai_ktp_lengkap`: teks KTP buatan (NIK `7503074512900001`, "Nama : SITI AMINAH", "Tempat/Tgl Lahir : SUWAWA, 05-12-1990", "Jenis Kelamin : PEREMPUAN", "Alamat : DUSUN II", "RT/RW : 001/002", "Kel/Desa : BUBEYA", "Kecamatan : SUWAWA", "Pekerjaan : PETANI/PEKEBUN") → satu pihak: nama "SITI AMINAH", nik "7503074512900001", ttl "Suwawa, 05-12-1990", jenis_kelamin "Perempuan", pekerjaan "Petani/Pekebun", alamat memuat "Dusun II", "RT 001/RW 002", "Bubeya", "Suwawa".
  - `test_nik_salah_baca_ocr`: "NIK : 75O3O7 4512 9OOOO1" → nik `7503074512900001`; "NIK : 75030745129" → nik `""` dan peringatan memuat "16".
  - `test_periksa_nik_cocok`: `periksa.nik("7503074512900001", "Suwawa, 05-12-1990", "Perempuan") == []`.
  - `test_periksa_tanggal_tidak_cocok`: ttl "06-12-1990" → satu peringatan memuat "tanggal lahir".
  - `test_periksa_jenis_kelamin_tidak_cocok`: NIK di atas + "Laki-laki" → satu peringatan memuat "jenis kelamin".
  - `test_label_tak_terbaca_dikosongkan`: teks tanpa baris Pekerjaan → kunci `pekerjaan` `""`, bukan tebakan.
- [ ] **Step 2: Jalankan** `python -m unittest uji.uji_unggah_ktp` → GAGAL.
- [ ] **Step 3: Implementasi.** Pakai ulang gaya label dari `berkas/aiw.py` (`_POLA_LABEL`, `_tanggal`) bila cocok; jangan ubah `aiw.py`. NIK: ambil token sesudah label, terjemahkan `O o→0, I l |→1, S→5, B→8` hanya di dalam token itu, buang non-digit. Tanggal di NIK: digit 7–12 `ddmmyy`, `dd > 40` → perempuan, `dd - 40`. `urai()` menjalankan `periksa.nik` dan menambahkan peringatannya.
- [ ] **Step 4: Jalankan** → LULUS.
- [ ] **Step 5: Commit** `feat(baca): pengurai KTP dan pemeriksaan NIK`.

### Task 4: Pengurai KK, SPPF, Lainnya, dan penyambung AIW/PBT

**Files:**
- Create: `berkas/baca/jenis/kk.py`, `berkas/baca/jenis/sppf.py`, `berkas/baca/jenis/lainnya.py`, `berkas/baca/ekstrak.py`
- Test: `uji/uji_unggah_jenis.py`

**Interfaces:**
- Consumes: kontrak `Hasil` (Task 3), `aiw.urai(teks)`, `pbt.urai(teks, daftar_desa)`.
- Produces: `ekstrak.jalankan(jenis: str, teks: str, k) -> dict` → `{"jenis": str, "hasil": Hasil | <keluaran aiw.urai> | <keluaran pbt.urai>}`. Untuk `aiw`/`pbt` keluaran pengurai lama diteruskan apa adanya supaya JS memakai pratinjau yang sudah ada. `tidak_terbaca` → `ValueError`.

- [ ] **Step 1: Tulis uji yang gagal.**
  - `test_kk_nomor_dan_anggota`: teks KK buatan ("No. 7503070101100002", dua baris anggota nama+NIK) → `dokumen == [{"uraian": "Kartu Keluarga Nomor 7503070101100002", "kategori": "tambahan"}]`, `pihak` berisi dua anggota (nama, nik saja), `isian == {}`.
  - `test_sppf_batas_dan_luas`: teks SPPF buatan ("Utara : Tanah Hasan", "Timur : Jalan Desa", "Selatan : Sungai", "Barat : Tanah Ali", "Luas : ± 1.250 M2", "Tanggal 12 Maret 2024") → `isian` memuat `batas_utara`…`batas_barat`, `luas_surat == "1250"`, dan `baku_sppf` = "Surat Pernyataan Penguasaan Fisik Bidang Tanah tanggal 12 Maret 2024".
  - `test_sppf_tulisan_tangan_kosong`: batas tanpa nilai ("Utara : ") → kunci tidak dikirim.
  - `test_lainnya_dari_judul`: "PEMERINTAH DESA BUBEYA\nSURAT KETERANGAN DOMISILI\nNomor : 140/12/2025\n…" → `dokumen == [{"uraian": "Surat Keterangan Domisili Nomor 140/12/2025", "kategori": "tambahan"}]`.
  - `test_ekstrak_aiw_diteruskan`: `ekstrak.jalankan("aiw", TEKS, k)["hasil"] == aiw.urai(TEKS)`.
  - `test_ekstrak_tidak_terbaca_ditolak`: `ValueError`.
- [ ] **Step 2: Jalankan** `python -m unittest uji.uji_unggah_jenis` → GAGAL.
- [ ] **Step 3: Implementasi.** Sebelum menulis `sppf.py`, pastikan nama medan `luas_surat`, `batas_*`, dan `baku_sppf` di `berkas/formulir.py`; bila berbeda, pakai nama yang ada dan sesuaikan uji. Luas memakai `pbt._angka_luas`. `ekstrak.jalankan` untuk `pbt` mengambil daftar desa dengan kueri yang sama seperti `rute/berkas.py:urai_pbt` (pindahkan kueri itu ke fungsi `referensi.daftar_desa_ocr(k)` dan pakai di kedua tempat).
- [ ] **Step 4: Jalankan** uji ini dan `python -m unittest uji.uji_pbt uji.uji_aiw` → LULUS.
- [ ] **Step 5: Commit** `feat(baca): pengurai KK, SPPF, dokumen lain; sambungan AIW/PBT`.

### Task 5: Tabel dan penyimpanan unggahan

**Files:**
- Modify: `berkas/db.py` (SKEMA), `berkas/jalur.py` (tambah `UNGGAHAN = os.path.join(DATA, "unggahan")`)
- Create: `berkas/unggah.py`
- Test: `uji/uji_unggah_simpan.py` (turunan `uji.uji_web.Dasar` agar dapat basis data kosong)

**Interfaces:**
- Consumes: `ocr.baca`, `pilah.kelompokkan`.
- Produces:
  - Tabel `unggahan` dan `unggahan_dokumen` persis seperti spec §7, ditambah ke `SKEMA` dengan `CREATE TABLE IF NOT EXISTS` dan dua indeks.
  - `unggah.simpan(k, nama: str, isi: bytes, pengguna_id: int, berkas_id: int | None, titipan: str | None) -> dict` → `{"id", "nama_asli", "kembar": bool, "dokumen": [{"id","hal_awal","hal_akhir","jenis_tebakan","label","yakin"}]}`. `GalatBaca` diteruskan. `kembar` = sidik sama sudah ada untuk berkas/titipan yang sama.
  - `unggah.dokumen(k, did: int) -> dict | None` (baris dokumen + `berkas_id`, `titipan`, `pengguna_id`, `nama_file` induknya).
  - `unggah.setel_jenis(k, did: int, jenis: str | None, status: str)` — status `pasti`/`diabaikan`; `jenis` harus kunci `jenis.DAFTAR` selain `tidak_terbaca`.
  - `unggah.tautkan(k, titipan: str, berkas_id: int, pengguna_id: int) -> int` — jumlah unggahan yang ditautkan (hanya milik pengguna itu).
  - `unggah.bersihkan_titipan(k, umur_hari: int = 7) -> int` — hapus baris dan file.

- [ ] **Step 1: Tulis uji yang gagal.**
  - `test_simpan_membuat_baris_dan_file`: PDF uji 2 halaman (sppf, kk) → 1 baris `unggahan`, 2 baris `unggahan_dokumen`, file ada di `jalur.UNGGAHAN` (alihkan ke folder sementara di `setUp`).
  - `test_kembar_ditandai`: unggah isi sama dua kali ke titipan sama → kedua `kembar is True`, baris tetap dibuat.
  - `test_tidak_menyentuh_tabel_berkas`: hitung baris `pihak`, `bidang_tanah`, `dokumen_pendukung` sebelum/sesudah → sama.
  - `test_setel_jenis`: `setel_jenis(did, "kk", "pasti")` → `jenis == "kk"`, `status == "pasti"`; jenis `"tidak_terbaca"` atau kode asing → `ValueError`.
  - `test_tautkan_titipan`: dua unggahan titipan "T1" milik pengguna 1 dan satu milik pengguna 2 → `tautkan("T1", bid, 1) == 2`, `berkas_id` terisi, `titipan` jadi NULL.
  - `test_titipan_lama_dibersihkan`: titipan dengan `dibuat` 8 hari lalu dan 1 hari lalu → `bersihkan_titipan() == 1`, file yang lama hilang, yang baru tetap.
- [ ] **Step 2: Jalankan** `python -m unittest uji.uji_unggah_simpan` → GAGAL.
- [ ] **Step 3: Implementasi.** Nama file `u{id-atau-T}-{secrets.token_hex(8)}.{pdf|png|jpg}`, tulis file sesudah baris dibuat; bila penulisan file gagal, rollback. `dibuat` pakai `db.sekarang()`. `simpan()` memanggil `bersihkan_titipan(k)` di awal (murah; tidak perlu penjadwal).
- [ ] **Step 4: Jalankan** uji ini dan `python -m unittest uji.uji_basis uji.uji_web` → LULUS (skema baru tidak mengganggu, termasuk di PostgreSQL bila `DB_URL` disetel).
- [ ] **Step 5: Commit** `feat(unggah): tabel dan penyimpanan unggahan beserta titipan`.

### Task 6: Rute unggah

**Files:**
- Create: `berkas/rute/unggah.py`
- Modify: `berkas/aplikasi.py` (daftarkan blueprint), `berkas/rute/berkas.py:buat()` (tautkan titipan sesudah berkas dibuat)
- Test: `uji/uji_unggah_rute.py` (turunan `uji.uji_web.Dasar`, pakai `klien(masuk=True)` dan `petugas()`)

**Interfaces:**
- Consumes: Task 1–5.
- Produces (semua JSON kecuali gambar; semua perlu masuk; POST ber-CSRF seperti rute lain):
  - `POST /unggah` — form: `berkas` (file), `berkas_id` atau `titipan`. → 200 `unggah.simpan(...)`; 400 `{"galat": pesan}` untuk `GalatBaca`; 503 `{"galat": ocr.PESAN_PASANG}` bila `not ocr.TERSEDIA`.
  - `GET /unggah/dok/<did>/gambar?hal=<n>` → PNG.
  - `POST /unggah/dok/<did>/jenis` — form `jenis`, `status` → 200 `{"ok": true}`.
  - `GET /unggah/dok/<did>/ekstrak` → 200 `ekstrak.jalankan(...)`; 409 bila status bukan `pasti`.
  - `berkas.buat()` membaca `request.form["titipan"]` dan memanggil `unggah.tautkan` sebelum commit.
  - Aturan akses (`_pastikan(dok)`): bila `berkas_id` → `izin.pastikan_ubah(g.k, berkas_id)`; bila titipan → `pengguna_id == g.pengguna["id"]` atau admin; selain itu 404.

- [ ] **Step 1: Tulis uji yang gagal.**
  - `test_unggah_titipan_lalu_simpan_berkas`: POST `/unggah` (PDF uji, `titipan="T1"`) → 200 dengan 2 dokumen; POST `/berkas/baru` dengan `titipan="T1"` → unggahan tertaut ke berkas baru.
  - `test_alur_jenis_lalu_ekstrak`: setel jenis `sppf`/`pasti` → ekstrak 200 dengan `hasil.isian.batas_utara`; dokumen berstatus `baru` → ekstrak 409.
  - `test_tidak_ada_tulisan_ke_berkas_sebelum_simpan`: sesudah unggah+jenis+ekstrak, baris `pihak`/`bidang_tanah`/`dokumen_pendukung` berkas tidak berubah.
  - `test_unggahan_orang_lain_ditolak`: unggahan titipan petugas A; petugas B → gambar, jenis, ekstrak semua 404; unggahan di berkas milik A → B 403.
  - `test_satu_file_rusak_lainnya_jalan`: POST file rusak → 400 berisi pesan; POST file sah berikutnya → 200.
  - `test_perlu_masuk`: tanpa sesi → dialihkan ke `/masuk`, seperti `uji_pbt.test_perlu_masuk`.
  - `test_ocr_tidak_tersedia`: tambal `ocr.TERSEDIA = False` → 503 berisi "pip install".
- [ ] **Step 2: Jalankan** `python -m unittest uji.uji_unggah_rute` → GAGAL.
- [ ] **Step 3: Implementasi** rute sesuai Interfaces. Batasi `MAX_CONTENT_LENGTH` rute ini ke `ocr.BATAS_BITA` + 1 MB (cek apakah aplikasi sudah menyetel batas global; jangan menurunkannya untuk rute lain).
- [ ] **Step 4: Jalankan** uji ini, `uji.uji_web`, `uji.uji_pbt`, `uji.uji_aiw` → LULUS.
- [ ] **Step 5: Commit** `feat(unggah): rute unggah, verifikasi jenis, ekstrak`.

### Task 7: Antarmuka: langkah Unggah, verifikasi jenis, validasi data

**Files:**
- Modify: `berkas/web.py` (`LANGKAH_BARU`, `isi_panel`, `p_dok`, fungsi baru `_panel_unggah(d, baru)`), `static/app.js` (bagian baru "Unggah dokumen" sesudah bagian OCR), `static/style.css`
- Test: `uji/uji_unggah_rute.py` (tambahan uji HTML)

**Interfaces:**
- Consumes: rute Task 6; di JS: `setelMedan`, `escOcr`, dan fungsi pratinjau/terapkan AIW & PBT yang sudah ada (`OLAH_OCR`).
- Produces:
  - `LANGKAH_BARU` diawali `("p-unggah", "Unggah dokumen", True, "<petunjuk>")`; `isi_panel["p-unggah"] = _panel_unggah(d, baru=True)`.
  - Di berkas yang sudah ada, `_panel_unggah(d, baru=False)` disisipkan di awal `p_dok` (tab Dokumen).
  - Markup: `<div class="kartu" data-unggah data-berkas-id="…" data-titipan="…">` berisi `<input type="file" multiple accept="image/*,application/pdf">` **tanpa name**; untuk berkas baru, `<input type="hidden" name="titipan" value="<token>">` di dalam `form-berkas`, token = `secrets.token_urlsafe(16)` dibuat server.

- [ ] **Step 1: Tulis uji yang gagal.**
  - `test_langkah_unggah_pertama_di_berkas_baru`: GET `/berkas/baru` → "Unggah dokumen" muncul sebelum "Jenis permohonan", ada `name="titipan"` berisi token, cap "boleh nanti".
  - `test_unggah_di_tab_dokumen`: GET `/berkas/<bid>` → `data-unggah` dengan `data-berkas-id="<bid>"`, tanpa `name="titipan"`.
  - `test_baca_saja_tanpa_unggah`: berkas milik orang lain dibuka petugas lain → tidak ada `data-unggah`.
- [ ] **Step 2: Jalankan** → GAGAL.
- [ ] **Step 3: Implementasi `web.py`** sesuai Interfaces; langkah lain bergeser otomatis karena penomoran dari `enumerate`.
- [ ] **Step 4: Implementasi JS**, tiga layar dalam kartu `data-unggah`:
  1. **Ringkasan**: unggah file satu per satu ke `POST /unggah` (indikator "file 2 dari 5"); galat per file tampil di barisnya. Tabel: file · halaman · jenis tebakan · "✓ yakin" bila `yakin ≥ 0.6`, selain itu "? kurang yakin" · tanda "sudah pernah diunggah" bila `kembar`. Tombol "Mulai verifikasi".
  2. **Verifikasi jenis** (satu dokumen per layar, "2 dari 5"): gambar dari `/unggah/dok/<id>/gambar?hal=<hal_awal>`, "Apakah ini <LABEL>?" [Ya] [Bukan]. Bukan → `<select>` jenis (tanpa `tidak_terbaca`) + [Abaikan]. Tiap jawaban → `POST /unggah/dok/<id>/jenis`. `tidak_terbaca` langsung menampilkan pilihan jenis.
  3. **Validasi data**: untuk tiap dokumen `pasti` → `GET …/ekstrak`. `aiw`/`pbt` → fungsi pratinjau yang ada. Lainnya → tabel generik Isian | Hasil baca | Isian sekarang: kosong → dicentang; sama → "sama", tanpa kotak; berbeda → tidak dicentang + kelas `bentrok`. `pihak` dari KTP: `<select>` tujuan (Penerima hak, atau baris pihak lain baru/yang ada, memakai `barisLain`). `dokumen` → baris baru Dokumen tambahan. `pihak` dari KK tidak diterapkan; tiap anggota yang nama/NIK-nya tidak ada di pihak formulir menambah peringatan "… tercantum di KK tetapi tidak ada di daftar pihak" (hanya bila formulir sudah punya pihak). Peringatan tampil di atas tabel. "Terapkan ke formulir" memakai `setelMedan`. Tidak ada `fetch` yang menulis isian; penyimpanan tetap lewat Simpan.
- [ ] **Step 5: Jalankan** uji Task 7 dan `uji.uji_web` → LULUS.
- [ ] **Step 6: Uji manual** dengan skill `run`: jalankan aplikasi, buat Berkas baru, unggah PDF gabungan buatan (KTP+KK+SPPF hasil cetak dari teks contoh uji) dan satu foto; jalani tiga layar; Simpan; pastikan isian tersimpan dan unggahan tertaut. Ulangi di tab Dokumen berkas yang ada. Cek tampilan di lebar ponsel.
- [ ] **Step 7: Commit** `feat(unggah): langkah unggah, verifikasi jenis, dan validasi data`.

### Task 8: Penutup

**Files:**
- Modify: `README.md` (bagian singkat "Unggah dokumen": alur 4 langkah, jenis yang dikenali, paket tambahan), spec §5 & §7 bila ada nama medan yang berubah di Task 4.

- [ ] **Step 1: Jalankan seluruh uji** `python -m unittest discover -s uji -p "uji_*.py"` → semua uji `uji_unggah_*` lulus; jumlah kegagalan uji acuan tidak bertambah dari sebelum Task 1 (catat angka awal di Task 1).
- [ ] **Step 2: Perbarui README** sesuai Files.
- [ ] **Step 3: Commit** `docs: unggah dokumen`.
