# Unggah Dokumen: pilah, verifikasi, ekstrak — Rancangan (Tahap 1)

Tanggal: 2026-11-05 · Status: **draf, menunggu persetujuan pemilik**

## 1. Tujuan

Petugas backoffice mengunggah beberapa dokumen sekaligus (file terpisah atau
satu PDF gabungan). Sistem memisahkan dan mengenali jenis tiap dokumen, petugas
memastikan jenisnya, sistem mengekstrak datanya ke formulir berkas, dan petugas
memvalidasi sebelum menyimpan.

Ukuran berhasil: untuk berkas yang dokumennya ketikan dan cukup jelas, petugas
cukup **memeriksa**, bukan mengetik ulang, isian Pihak, Bidang tanah, dan
Dokumen pendukung.

## 2. Batasan yang disepakati

- **Tanpa AI luar.** Tidak ada data pemohon yang keluar dari komputer kantor.
  Semua pembacaan berjalan di server aplikasi, tanpa GPU.
- **Hanya modul Berkas.** Pradaftar tidak termasuk rancangan ini.
- **Manusia memutuskan dua kali:** jenis dokumen, lalu data hasil ekstrak.
- **Tidak ada yang masuk ke tabel berkas sebelum tombol Simpan.** Sama dengan
  pola AIW/PBT yang sudah ada.
- Yang tidak yakin dikosongkan, bukan ditebak. Isian yang sudah diketik
  petugas tidak pernah ditimpa diam-diam.

Di luar cakupan tahap 1: membaca tulisan tangan dengan andal, model penglihat
lokal (tahap 2, butuh GPU), pemilah hasil latihan sendiri (memakai data koreksi
yang dikumpulkan tahap ini), dan pradaftar.

## 3. Alur

```
1. UNGGAH & PISAH      (otomatis)
   File diunggah → tiap halaman dibaca → dideteksi jenisnya
   halaman berurutan yang jenisnya sama digabung jadi satu dokumen

2. VERIFIKASI JENIS    (petugas, satu dokumen per layar)
   "Apakah ini <JENIS>?"   [Ya]  [Bukan]
   Bukan → "Ini adalah: [pilih jenis ▾]"  atau  [Abaikan]

3. EKSTRAK DATA        (otomatis, hanya dokumen yang jenisnya sudah pasti)

4. VALIDASI DATA       (petugas)
   tabel Isian | Hasil baca | Isian sekarang → Terapkan ke formulir → Simpan
```

## 4. Letak di aplikasi

Satu komponen dipasang di dua tempat:

1. **Berkas baru**: langkah pertama yang baru, *Unggah dokumen*, bertanda
   **boleh nanti** dan punya tombol Lewati. Langkah berikutnya bergeser satu
   (Jenis permohonan menjadi langkah 2, dan seterusnya). Usulan yang diterapkan
   langsung mengisi medan di langkah-langkah berikutnya.
2. **Berkas yang sudah ada**: bagian di tab **Dokumen** untuk menyusulkan
   dokumen.

### Layar verifikasi jenis

```
┌─ Verifikasi dokumen ─────────────────────── 2 dari 5 ─┐
│  ┌──────────────┐   scan_berkas.pdf · halaman 2        │
│  │  (gambar     │   Apakah ini  KARTU KELUARGA ?       │
│  │   halaman)   │   [ Ya ]   [ Bukan ]                 │
│  └──────────────┘                                      │
│  ◂ sebelumnya                         berikutnya ▸     │
└────────────────────────────────────────────────────────┘
```

Sebelum masuk ke layar ini, petugas melihat ringkasan hasil pilahan: file,
halaman, jenis tebakan, dan tingkat yakin.

## 5. Jenis dokumen tahap 1

| Jenis | Ciri pengenal (kata kunci, contoh) | Hasil ekstrak → tujuan |
|---|---|---|
| KTP | "KARTU TANDA PENDUDUK", "NIK", "PROVINSI" | Tab Pihak: nama, NIK, tempat/tgl lahir, jenis kelamin, pekerjaan, alamat. Petugas memilih pihak/peran tujuan. |
| Kartu Keluarga | "KARTU KELUARGA", "No. KK" | Formulir tidak punya medan Nomor KK, jadi KK menjadi baris Dokumen tambahan "Kartu Keluarga Nomor …". Nama/NIK anggota dicocokkan dengan pihak yang ada (hanya peringatan). |
| Surat Pernyataan Penguasaan Fisik | "PENGUASAAN FISIK", "BIDANG TANAH" | Slot dokumen baku **SPPF** (uraian + tanggal), serta batas dan luas surat di tab Bidang tanah. Hanya bagian ketikan. |
| AIW / APAIW | "AKTA IKRAR WAKAF" | `aiw.urai()` yang sudah ada → tab Pihak |
| PBT | "PETA BIDANG TANAH" | `pbt.urai()` yang sudah ada → tab Bidang tanah |
| Lainnya | tidak cocok dengan pola mana pun | Usulan baris `dokumen_pendukung`: uraian (dari judul), nomor, tanggal bila terbaca |
| Tidak terbaca | teks kosong/terlalu sedikit | Petugas memilih jenis atau mengabaikan |

Pengenal tiap jenis dibuat sebagai satu unit kecil (pola + pengurai), supaya
jenis baru seperti SPPT atau surat keterangan desa bisa ditambahkan tanpa
mengubah alur.

## 6. Komponen

| Unit | Tugas | Bergantung pada |
|---|---|---|
| `berkas/baca/ocr.py` | Berkas (PDF/JPG/PNG) → teks + gambar per halaman. PDF ber-lapisan-teks dibaca langsung, sisanya dengan RapidOCR. | pypdfium2 (atau setara) untuk PDF, rapidocr-onnxruntime, Pillow |
| `berkas/baca/pilah.py` | Teks per halaman → (jenis, yakin). Halaman berurutan sejenis digabung. | daftar jenis |
| `berkas/baca/jenis/*.py` | Satu berkas per jenis: pola pengenal + `urai(teks) → {isian, peringatan}` | aiw.py, pbt.py untuk jenisnya |
| `berkas/baca/periksa.py` | Pemeriksaan silang: NIK 16 angka, tanggal lahir & jenis kelamin dari NIK, file kembar | — |
| `berkas/rute/unggah.py` | Rute unggah, ambil hasil pilah, setel jenis, ekstrak, gambar halaman | unit di atas, `unggah.py` (DB) |
| `static/app.js` | Layar ringkasan, verifikasi jenis, tabel validasi, penerapan ke formulir | memakai ulang `setelMedan`, pola pratinjau OCR |

Pembacaan OCR di peramban (Tesseract.js) untuk kartu AIW/PBT yang sekarang
**dibiarkan** di tahap 1. Penggantiannya diputuskan setelah pembacaan di server
terbukti.

Versi paket baru dipatok di `requirements.txt` seperti paket lain.

## 7. Penyimpanan

```sql
CREATE TABLE unggahan (
  id INTEGER PRIMARY KEY,
  berkas_id INTEGER REFERENCES berkas(id) ON DELETE CASCADE, -- NULL = titipan
  titipan TEXT,                 -- token acak selama Berkas baru belum disimpan
  nama_asli TEXT NOT NULL,
  nama_file TEXT NOT NULL,      -- di data/unggahan/
  sidik TEXT NOT NULL,          -- sha256 isi file
  jml_halaman INTEGER NOT NULL,
  pengguna_id INTEGER REFERENCES pengguna(id),
  dibuat TEXT NOT NULL
);

CREATE TABLE unggahan_dokumen (
  id INTEGER PRIMARY KEY,
  unggahan_id INTEGER NOT NULL REFERENCES unggahan(id) ON DELETE CASCADE,
  hal_awal INTEGER NOT NULL,
  hal_akhir INTEGER NOT NULL,
  jenis_tebakan TEXT NOT NULL,
  yakin REAL NOT NULL,
  jenis TEXT,                   -- ditetapkan petugas; NULL = belum diverifikasi
  status TEXT NOT NULL DEFAULT 'baru', -- baru | pasti | diabaikan | diterapkan
  teks TEXT NOT NULL
);
CREATE INDEX ix_unggahan_berkas ON unggahan(berkas_id);
CREATE INDEX ix_unggahan_dok ON unggahan_dokumen(unggahan_id);
```

- File asli disimpan di `data/unggahan/`, seperti foto di `data/foto/`.
- **Titipan**: di Berkas baru, unggahan bertanda token. Saat Simpan, token itu
  ditautkan ke `berkas_id`. Titipan yang tidak ditautkan dihapus (baris dan
  file) setelah 7 hari oleh rutinitas pemeliharaan yang sudah ada.
- Selisih `jenis_tebakan` dan `jenis` adalah **catatan salah tebak**, bahan
  pemilah buatan sendiri di tahap berikutnya.
- Hak akses mengikuti berkasnya: hanya yang boleh mengubah berkas yang boleh
  mengunggah atau melihat unggahannya (`izin.boleh_ubah`).

## 8. Validasi dan bentrok

Di tabel validasi, tiap isian:

- **kosong di formulir** → hasil baca dicentang untuk diterapkan;
- **sama** → ditandai "sama", tanpa tindakan;
- **berbeda** → tidak dicentang, diberi warna, petugas memilih.

Peringatan (tidak memblokir):

- NIK bukan 16 angka;
- tanggal lahir atau jenis kelamin tidak cocok dengan NIK (digit 7–12 =
  ddmmyy, tanggal + 40 untuk perempuan);
- nama/NIK di KK tidak ada di daftar pihak;
- file yang sama (sidik sama) sudah pernah diunggah ke berkas ini.

## 9. Penanganan galat

| Keadaan | Perilaku |
|---|---|
| Format bukan PDF/JPG/PNG | Ditolak per file dengan pesan; file lain tetap diproses |
| File terlalu besar / halaman terlalu banyak | Ditolak dengan pesan batasnya (batas angka ditetapkan di rencana) |
| PDF rusak/terkunci sandi | Ditolak per file dengan pesan |
| OCR gagal pada satu halaman | Halaman itu berjenis *Tidak terbaca*; yang lain jalan terus |
| Paket OCR belum terpasang | Fitur unggah menampilkan pesan pemasangan; bagian aplikasi lain tetap jalan |
| Halaman ditutup sebelum Simpan | Titipan dibersihkan otomatis setelah 7 hari |

Galat dicatat ke log dengan nomor unggahan, tanpa isi teks dokumen.

## 10. Pengujian

Uji ditulis dulu dan harus gagal sebelum kodenya dibuat (aturan proyek).

- `pilah`: teks contoh buatan tiap jenis dikenali dengan benar; teks campuran
  terpisah di halaman yang tepat; teks kosong menjadi *Tidak terbaca*.
- `jenis/*`: tiap pengurai mengeluarkan isian yang benar dari teks contoh,
  termasuk teks dengan salah baca OCR yang lazim (O/0, I/1, spasi hilang).
- `periksa`: NIK ↔ tanggal lahir ↔ jenis kelamin, termasuk kasus perempuan
  (+40).
- `ocr`: satu PDF ber-lapisan-teks dan satu gambar yang **dibuat di dalam uji**
  terbaca.
- Web: unggah → verifikasi → ekstrak → Simpan; dipastikan tabel berkas tidak
  berubah sebelum Simpan, titipan tertaut sesudahnya, dan pengguna tanpa hak
  ubah ditolak.
- Semua contoh adalah data buatan; tidak memakai `data/` atau `uji/emas/`.

## 11. Pertanyaan terbuka (diputuskan di rencana)

- Batas ukuran file dan jumlah halaman per unggahan.
- Pustaka pembaca PDF (pypdfium2 atau lainnya), ditentukan setelah dicoba di
  Windows dan Linux.
- Kecepatan RapidOCR di server kantor; bila terlalu lambat, pembacaan dijalankan
  per halaman dengan indikator kemajuan.
