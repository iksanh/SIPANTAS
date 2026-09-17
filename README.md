# Berkas Panitia A

Aplikasi penerbitan **BAP, Risalah Panitia A, dan SK Penetapan Hak** untuk Kantor
Pertanahan Kabupaten Bone Bolango. Satu berkas diinput sekali, tiga dokumen keluar.

Menggantikan alur lama: isi 133 kolom di Excel → mail merge tiga file Word →
rapikan manual di tiap dokumen.

---

## Menjalankan

Klik dua kali **`jalankan.bat`**. Peramban terbuka sendiri di `http://localhost:8000`.

Masuk pertama kali:

| | |
|---|---|
| Nama pengguna | `admin` |
| Kata sandi | `admin123` |

Ganti kata sandi lewat menu **Pengaturan** setelah masuk.

Untuk berhenti: tutup jendela hitamnya, atau tekan `Ctrl+C`.

## Isi halaman

Empat menu, dan tiap halaman hanya menampilkan yang sedang dipakai:

| Menu | Bentuknya |
|---|---|
| **Berkas** | Satu tabel, disaring kotak cari dan tombol status (Semua / Draf / Diperiksa / Selesai / Ditolak) yang berikut jumlahnya. |
| **Berkas yang dibuka** | Delapan tab. Judul, tombol Simpan, dan bilah tabnya menempel di atas, jadi tetap terjangkau sampai bawah. Tab **Cetak** memakai angka: merah kalau ada yang menghalangi pencetakan, kuning kalau cuma peringatan, centang hijau kalau bersih. |
| **Data referensi** | Kartu lipat: matriks jenis hak, pustaka klausa, tiap SK panitia, dan wilayah (daftar induk Kemendagri, kecamatan, desa/kelurahan). |
| **Template** | Kartu lipat per template — BAP, Risalah, SK untuk Hak Milik, dan ketiganya lagi untuk Hak Wakaf — berikut penjelasan penandanya. |
| **Pengaturan** | Tiga tab: Kantor, Penyimpanan, Pengguna. |

Kartu lipat berarti isi kartunya baru diambil dari server saat kartunya diklik —
halaman referensi dan template tidak pernah memuat semua isinya sekaligus. Kartu yang
terakhir dibuka dan tab yang terakhir dipakai diingat peramban. Kalau JavaScript mati,
kepala kartunya tetap tautan biasa yang membuka bagian itu lewat server.

## Memasukkan data lama

Klik dua kali **`impor.bat`**. Dua sumber diambil sekaligus:

| Sumber | Isi |
|---|---|
| `RAHMA WONTOGIA/Copy of Rutin 2025 database new UPDATE DISINI YA (1).xlsx` | berkas Hak Milik |
| `wakaf/wakaf.xlsx` | berkas Hak Wakaf |

Kolomnya dipecah ke struktur baru: riwayat perolehan dan dokumen pendukung jadi baris,
luas jadi angka, tanggal jadi satu kolom, desa/kecamatan/pejabat masuk daftar induk.

Berkas yang datanya kurang tetap masuk, ditandai `perlu dilengkapi` — tidak ditolak.

**Aman diulang.** Berkas yang sudah ada — dikenali dari nama penerima dan nomor Peta
Bidang Tanah — dilewati, tidak digandakan. Jadi menambah baris baru di Excel lalu
menjalankan `impor.bat` lagi hanya memasukkan yang belum ada. Untuk satu sumber saja:
`python impor_excel.py wakaf`, atau sebutkan jalur berkasnya sendiri.

Khusus sumber wakaf: kolom «Atas Nama» memuat seluruh Nazhir dipisah koma — orang
pertama jadi penerima hak, sisanya baris Nazhir tersendiri; «KTP Sebelumnya» masuk
sebagai **Wakif**; dan empat surat wakaf (Akta Ikrar Wakaf, pengesahan Nazhir,
kesediaan menjadi Nazhir, kesediaan diaudit) dikenali dari isinya lalu masuk ke slot
bakunya masing-masing, bukan jadi "tambahan surat" tanpa nama. Surat yang isinya
persis sama tidak dimasukkan dua kali.

### Dokumen baku

Sebelas surat di bawah ini satu kesatuan dengan formulir permohonan, jadi masing-masing
punya isian sendiri di tab **Dokumen** — bukan baris yang ditambah-kurang. Slot yang
dikosongkan tidak ikut tercetak. Berlaku untuk semua jenis hak.

| # | Isian | Kolom Excel |
|---|---|---|
| 1 | Formulir permohonan | `Formulir permohonan` |
| 2 | Jenis SPPF | `jenis sppf` |
| 3 | Surat Pernyataan tanah-tanah yang dipunyai pemohon | `Surat Pernyataan tanah-Tanah Yang dipunyai Pemohon` |
| 4 | Surat Pernyataan Penggunaan Tanah | `Surat Pernyataan Penggunaan Tanah` |
| 5 | Surat Keterangan Penguasaan Tanah | `Surat Keterangan Penguasaan Tanah` |
| 6 | Surat Pernyataan Tidak Sengketa dan belum Bersertipikat | `Surat Pernyataan Tidak Sengketa dan belum Bersertipikat` |
| 7 | Surat Pernyataan | `Surat Pernyataan` |
| 8 | Surat pemasangan tanda batas | `surat pemasangan tanda batas` |
| 9 | Surat pernyataan selisih luas | `surat pernyataan selisih luas` |
| 10 | Surat Absentee Kecamatan | `Tgl Surat Absentee Kecamatan` |
| 11 | Surat kuasa | `surat kuasa` |

Dua isian lagi menyertainya, berisi kalimat telaah, bukan nama surat:

| Isian | Kolom Excel | Kalau dikosongkan |
|---|---|---|
| Surat Penguasaan Fisik | `Surat Penguasaan Fisik` | disusun dari kalimat baku + isian **Jenis SPPF** |
| Selisih luas | `selisih luas` | dihitung dari luas PBT, luas surat, dan isian **Surat pernyataan selisih luas** |

Isi keduanya hanya kalau kalimat bawaannya perlu ditulis lain — contoh kalimat bawaan
muncul sebagai teks samar di kotaknya.

Di bawah kartu itu ada **Dokumen tambahan & alas hak**, tempat baris bebas seperti dulu
(`tambahan surat 1..54` dan `Surat 1..10` dari Excel).

Slot **Jenis SPPF** dan **Surat kuasa** sengaja tidak ikut daftar berulang di Risalah:
template sudah punya barisnya sendiri, kalau ikut nanti tercetak dua kali.

Empat slot lagi hanya muncul pada berkas berjenis hak **wakaf**, karena hanya tata
naskah wakaf yang merujuknya:

| Isian | Dirujuk oleh |
|---|---|
| Akta Ikrar Wakaf | Menimbang SK (`{{akta_ikrar}}`) dan DATA PENDUKUNG Risalah |
| Pengesahan Nazhir oleh PPAIW | Menimbang SK (`{{pengesahan_nazhir}}`) |
| Surat Pernyataan Kesediaan Menjadi Nazhir | DATA PENDUKUNG Risalah |
| Surat Pernyataan Bersedia Diaudit | DATA PENDUKUNG Risalah |

Jenis hak lain tidak menampilkan keempatnya, jadi formulir Hak Milik tidak bertambah
panjang karenanya.

Basis data yang sudah terlanjur diisi versi lama dirapikan sekali dengan
`python perbaiki_dokumen.py` (aman diulang, basis data disalin dulu).

## Foto lapangan

Tab **Foto lapangan** pada berkas. Pilih foto (boleh beberapa sekaligus; di ponsel
bisa langsung memotret), lalu tekan **Simpan** — fotonya terunggah bersama isian
lain. Pratinjau foto yang baru dipilih langsung tampak di bawah kotak pilihnya.

- **Paling sedikit 4 foto.** Kurang dari itu, pemeriksaan sebelum cetak memberi
  galat dan tombol cetak mati. Lencana di tab menunjukkan jumlahnya: merah bila
  belum cukup, hijau bila sudah.
- **Urutan dan keterangan.** ↑ ↓ mengatur urutan, × membuang foto, kotak
  *Keterangan* (opsional) tercetak di bawah fotonya. Semuanya berlaku setelah Simpan;
  foto yang dibuang ikut dihapus dari disk.
- **Dirapikan saat diunggah.** Foto ponsel diputar tegak menurut tanda EXIF-nya dan
  diperkecil ke sisi terpanjang 1600 piksel (JPEG), jadi BAP tetap ringan. Ini
  memerlukan Pillow, yang dipasang `jalankan.bat`; tanpa Pillow hanya JPG/PNG yang
  diterima dan disimpan apa adanya. Satu kali simpan paling besar 120 MB.

Di BAP, foto dilampirkan pada **halaman baru di akhir dokumen**: judul *Lampiran
Dokumentasi Pemeriksaan Lapang*, identitas berkas (pemohon/Nazhir, letak tanah,
PBT/NIB, tanggal pemeriksaan), lalu tabel dua foto per baris. Keterangan tercetak di
bawah fotonya; foto tanpa keterangan tampil sendiri, tanpa tulisan apa pun.
Satu baris foto tidak pernah terbelah dua halaman; foto yang tidak muat pindah ke
halaman berikutnya. Yang menentukan ada-tidaknya lampiran adalah penanda `{{@foto}}`
di template — letaknya bebas, paragraf penandanya sendiri dibuang saat dirakit.

Berkasnya disimpan di `data/foto/`, barisnya di tabel `foto_lapang`.

## Kecamatan, desa, dan kepala desa

Menu **Data referensi** → bagian **Wilayah**, tiga kartu berurutan.

**Daftar induk Kemendagri.** Seluruh 18 kecamatan, 160 desa, dan 5 kelurahan Kabupaten
Bone Bolango (kode wilayah 75.03) sudah tersimpan di `wilayah.py`. Kartunya menyebut apa
saja yang belum ada di basis data, dan tombol **Tambahkan yang belum ada** memasukkannya
sekaligus. Tombol itu hanya *menambah*: nama, jenis, dan pejabat yang sudah tersimpan
tidak pernah diubah, dan tidak ada baris yang dihapus — jadi aman ditekan berulang.

**Kecamatan.** Tambah, ganti nama, atau isi kode wilayahnya di kartu ini. Kecamatan yang
masih punya desa tidak bisa dihapus.

**Desa dan kelurahan.** Tabelnya menampilkan siapa yang menjabat sekarang di tiap desa,
dan bisa diganti langsung dari situ. Tombol **Kelola** membuka halaman desa itu sendiri —
untuk mengubah nama/jenis/kode, dan mengurus riwayat kepala desanya. Desa yang sudah
ditunjuk sebagai letak tanah pada suatu berkas tidak bisa dihapus.

### Kepala desa yang berganti

Kepala desa berganti: yang definitif habis masa jabatannya, diisi **Pj.** atau **Plt.**,
lalu ada kepala desa baru. Karena itu nama pejabat **tidak ditimpa**. Tiap orang jadi satu
baris riwayat berisi nama, jabatan (Kepala Desa / Pj. / Plt. / Pjs., atau Lurah / Plt.
Lurah / Pj. Lurah untuk kelurahan), masa jabatan, dan nomor SK pengangkatan. Satu di
antaranya ditandai **sedang menjabat** — itulah yang ikut tercetak sebagai anggota
Panitia A (Pasal 138 ayat (1) huruf c) pada dokumen yang dibuat setelahnya.

Jadi kalau kepala desa diganti Pj.: tambahkan Pj.-nya sebagai baris baru dan centang
*Jadikan yang menjabat sekarang*. Yang lama tetap ada sebagai riwayat, lengkap dengan
tanggal, sehingga masih bisa ditelusuri siapa yang menandatangani berkas lama.

Nama dan jabatan yang aktif disalin balik ke tabel `ref_desa`, jadi template dan penanda
`{{nama_pejabat}}`/`{{jabatan_pejabat}}` tidak berubah sama sekali. Basis data lama
dimigrasikan sendiri saat pertama dijalankan: nama pejabat yang sudah ada jadi baris
riwayat pertama dan langsung ditandai aktif.

## Menambah susunan Panitia A

Menu **Data referensi** → bagian **Susunan Panitia A**. Satu SK penunjukan = satu susunan.
Isi nomor dan tanggal SK, simpan, lalu tambahkan anggotanya satu per satu: nama, NIP,
jabatan, dan kedudukan dalam panitia (Ketua/Sekretaris/Anggota).

Tiap SK tampil sebagai satu kartu tertutup — nomor, tanggal, jumlah anggota, dan masa
berlakunya sudah terbaca dari kepalanya. Isinya baru diambil dari server saat kartunya
diklik, jadi halaman referensi tidak pernah memuat semua SK sekaligus. Kartu yang terakhir
dibuka diingat peramban, dan setelah menyimpan halaman kembali ke SK yang tadi disunting.

Kalau susunannya cuma berganti sebagian, tekan **Salin jadi SK baru** — anggotanya ikut
tersalin, tinggal ganti nomor SK dan orang yang berubah.

Aturan mainnya:

- **Jangan menimpa SK lama.** Tambah SK baru setiap kali susunannya berganti, supaya
  berkas yang sudah dicetak tetap merujuk susunan yang benar saat itu. SK yang sudah
  dipakai berkas tidak bisa dihapus.
- **Kepala desa/lurah letak tanah tidak perlu didaftarkan** — ditambahkan otomatis
  sebagai anggota (Pasal 138 ayat (1) huruf c). Karena itu jumlah anggota yang terpasang
  di kartu SK ditampilkan sudah termasuk dia, dan diberi tanda merah kalau genap.
- **Kolom Jabatan dipakai mesin.** Penanda `{{kasi_pgt_nama}}` dan `{{kasi_pgt_nip}}`
  mencari anggota yang jabatannya memuat kata "Penataan", jadi tulis jabatannya lengkap.
- **Pendapat baku** dipakai kalau pendapat anggota pada suatu berkas dikosongkan.

Di berkas, susunannya dipilih pada tab **Sidang** → *Susunan Panitia A*, per SK.

Nama panitia **tidak lagi diketik di template**. Tabel susunan panitia di Risalah, tabel
Nama/NIP/Jabatan di BAP, kalimat "… dan 5 (lima) orang anggota …", dan blok *Pendapat
Anggota Panitia* semuanya dirakit dari susunan yang dipilih itu, jadi barisnya ikut
bertambah atau berkurang sesuai jumlah anggota. Ganti susunan cukup lewat menu Referensi;
berkas yang sudah dicetak tetap memakai susunan yang berlaku waktu itu. Baris NIP dilewati
untuk anggota yang tidak punya NIP, seperti kepala desa.

## Dua tata naskah: Hak Milik dan Hak Wakaf

Tata naskah wakaf berbeda cukup jauh dari Hak Milik — SK-nya *menegaskan sebagai tanah
wakaf* dengan tujuh diktum (bukan lima belas), penerima haknya **Nazhir** yang boleh
lebih dari satu orang, dasar hukumnya UU 41/2004 jo. PP 42/2006, dan nomor SK-nya
berkode `HW`. Karena itu Risalah dan SK-nya punya template sendiri.

Yang menentukan template mana yang dipakai adalah **jenis hak berkasnya**, lewat kolom
*varian template* di matriks jenis hak. Tidak ada tombol "pilih template": pilih jenis
hak `WAKAF` di tab Berkas, dan ketiga dokumennya otomatis dirakit dari set wakaf.
Varian yang salah satu dokumennya belum ada jatuh kembali ke template baku.

| Berkas template | Dipakai oleh |
|---|---|
| `bap.docx`, `risalah.docx`, `sk.docx` | Hak Milik dan hak lainnya |
| `bap-wakaf.docx`, `risalah-wakaf.docx`, `sk-wakaf.docx` | Hak Wakaf |

### Yang diisi pada berkas wakaf

Semuanya diisi sekali, di tempat yang sudah ada — tidak ada isian kembar:

| Yang dicetak dokumen | Diisi di |
|---|---|
| Nama seluruh Nazhir di judul SK dan Risalah | tab **Pihak**: Nazhir pertama di kartu *Penerima hak*, sisanya baris *Pihak lain* berperan **Nazhir** |
| Nama, NIK, TTL, domisili, pekerjaan tiap Nazhir (Risalah mencetaknya per orang, a.i/a.ii/a.iii) | baris Nazhir itu juga — barisnya bertambah sendiri sesuai jumlah Nazhir |
| Nama Wakif di Menimbang SK dan di DATA PENDUKUNG | baris *Pihak lain* berperan **Wakif** |
| Akta Ikrar Wakaf yang dirujuk Menimbang SK | tab **Dokumen** → slot *Akta Ikrar Wakaf* |
| Pengesahan Nazhir oleh PPAIW | tab **Dokumen** → slot *Pengesahan Nazhir oleh PPAIW* |
| Bentuk Nazhir (perseorangan / organisasi / badan hukum) | *Jenis subjek* penerima hak |

Empat slot dokumen khusus wakaf — Akta Ikrar Wakaf, pengesahan Nazhir, kesediaan
menjadi Nazhir, dan kesediaan diaudit — hanya muncul pada berkas berjenis hak wakaf.

Yang diperiksa sebelum cetak, selain pemeriksaan yang berlaku umum:

| Pemeriksaan | Dasar |
|---|---|
| Nazhir perseorangan paling sedikit 3 orang | Pasal 4 ayat (2) PP 42/2006 |
| Wakif wajib ada | Permen ATR/BPN 2/2017 |
| Akta Ikrar Wakaf wajib ada | Pasal 32 UU 41/2004 |
| Pengesahan Nazhir dari PPAIW | Pasal 14 PP 42/2006 |
| NIK dan TTL tiap Nazhir terisi | Risalah mencetaknya per orang |
| Hak Wakaf tidak berjangka waktu | UU 41/2004 |

## Kalau tata naskah berubah

Menu **Template**. Tiga langkah:

1. **Unduh** template BAP, Risalah, atau SK — dari kartu tata naskah yang mau diubah
   (Hak Milik atau Hak Wakaf; keduanya berdiri sendiri).
2. **Sunting di Microsoft Word** seperti dokumen biasa. Penanda `{{nama_penerima}}` adalah
   teks biasa — boleh dipindah, disalin, dihapus, atau ditambah. Kop, tabel, gaya huruf,
   dan penomoran ikut apa adanya. Simpan sebagai `.docx`.
3. **Unggah lagi.** Versi lama otomatis dicadangkan (15 versi terakhir disimpan, bisa
   dikembalikan kapan saja), dan sistem langsung mencoba merakit satu dokumen contoh
   untuk memastikan templatenya masih bisa dipakai.

Halaman itu juga memuat daftar seluruh penanda yang tersedia beserta contoh isinya dari
berkas sungguhan, dan menandai merah penanda yang salah ketik — yang salah ketik tercetak
kosong, bukan bikin gagal.

Cara lama masih ada: sunting dokumen ber-MERGEFIELD di folder sumbernya, lalu klik
dua kali **`siapkan_template.bat`**. Template sistem dibuat ulang dari dokumen itu — dan
**menimpa hasil unggahan**. Pakai yang itu hanya kalau tata naskahnya dirombak dari
sumber aslinya.

Satu set dokumen contoh per tata naskah:

| Set | Folder sumber | Keluaran |
|---|---|---|
| Hak Milik & hak lainnya | `RAHMA WONTOGIA/` | `bap.docx`, `risalah.docx`, `sk.docx` |
| Hak Wakaf | `wakaf/` | `bap-wakaf.docx`, `risalah-wakaf.docx`, `sk-wakaf.docx` |

`siapkan_template.bat` membangun ulang keduanya. Untuk satu set saja — supaya tata
naskah yang satunya tidak ikut tertimpa — jalankan `python siapkan_template.py wakaf`.
Dokumen sumbernya harus `.docx`; kalau masih `.doc`, buka di Word lalu simpan ulang.

---

## Yang dibutuhkan

- Python 3.10 atau lebih baru
- `python-docx` dan `openpyxl` — dipasang otomatis oleh `jalankan.bat`
- `Pillow` (dianjurkan) — untuk memutar tegak dan memperkecil foto lapangan; juga
  dipasang `jalankan.bat`

Tidak ada kerangka kerja web, tidak ada basis data server, tidak perlu internet.
HTML, CSS, dan JavaScript ditulis sendiri di folder `static/`.

---

## Isi folder

| Berkas | Isi |
|---|---|
| `server.py` | Server web dan penyimpanan formulir |
| `web.py` | Perakit halaman HTML |
| `db.py` | Skema SQLite dan data referensi awal |
| `wilayah.py` | Daftar induk kecamatan/desa Kemendagri dan riwayat kepala desa |
| `konteks.py` | Nilai turunan dan seluruh aturan validasi |
| `docxgen.py` | Mesin perakit DOCX (perulangan, kondisi, lampiran foto) |
| `foto.py` | Simpan, putar tegak, perkecil, dan buang foto lapangan |
| `siapkan_template.py` | Pengubah dokumen Word ber-MERGEFIELD jadi template sistem |
| `templat.py` | Unduh, unggah, cadangkan, dan pulihkan template dari halaman Template |
| `terbitkan.py` | Penomoran otomatis dan pencatatan arsip cetak |
| `penyambung.py` | Kata penyambung di kanan bawah halaman, lewat Microsoft Word |
| `pemeliharaan.py` | Hitung isi folder dan buang berkas yang bisa dibuat ulang |
| `pdf.py` | Pratinjau PDF lewat Microsoft Word atau LibreOffice |
| `impor_excel.py` | Pemindah data dari Excel lama (rutin dan wakaf) |
| `util.py` | Terbilang, nama hari/bulan, luas, hari kerja |
| `static/` | style.css dan app.js |
| `templates/` | Template DOCX hasil konversi, satu set per tata naskah (`cadangan/` berisi versi sebelumnya) |
| `keluaran/` | Dokumen yang sudah dicetak |
| `data/berkas.db` | Basis data — **backup berkas ini** |
| `data/foto/` | Foto lapangan yang diunggah — **ikut di-backup** |

---

## Cara kerjanya

### Satu fakta, satu tempat

Yang disimpan hanya tanggal dan angka. Hari, terbilang, nama bulan, luas berhuruf,
selisih luas, dan sapaan Sdr./Sdri. dihitung ulang setiap kali dokumen dirakit
(`util.py`, `konteks.py`). Tidak ada lagi satu tanggal yang ditulis di lima kolom.

### Daftar adalah baris, bukan kolom

`riwayat_perolehan` dan `dokumen_pendukung` adalah tabel. Boleh 2 baris, boleh 54 —
dokumen menyesuaikan sendiri lewat penanda berulang. Baris terakhir otomatis
diakhiri titik, sisanya titik koma. Tidak ada lagi baris `;` menggantung.

### Template tetap dibuat di Word

`siapkan_template.py` mengubah `«Atas_Nama»` menjadi `{{nama_penerima}}`, menciutkan
slot `Jenis_Alas_Hak_1..10` dan `tambahan_surat_1..54` menjadi satu paragraf berulang,
dan mengubah nilai yang selama ini diketik tetap (NIK pemohon, nomor SK, tahun
terbilang, sapaan, nama jenis hak) menjadi penanda. Susunan panitia yang diketik tetap
di BAP dan Risalah ikut diciutkan jadi satu baris berulang. Kop, gaya huruf, penomoran,
tabel, dan gambar tidak disentuh.

Penanda yang dikenali di dalam template:

```
{{nama}}            diganti nilai
{{*riwayat.uraian}} paragraf diulang satu kali per baris
{{*riwayat._akhir}} ";" untuk baris selain terakhir, "." untuk yang terakhir
{{?syarat}}         paragraf hanya muncul bila nilainya ada
{{@foto}}           foto lapangan dilampirkan di halaman baru pada akhir dokumen
{{*panitia.nama}}   di dalam sel tabel: baris tabelnya yang diulang
{{*nazhir._romawi}} i, ii, iii - penomoran anak butir a.i, a.ii (Risalah wakaf)
{{#panitia}} …
{{/panitia}}        semua paragraf/baris tabel di antaranya diulang per anggota;
                    {{?panitia.nip}} membuang baris itu untuk anggota tanpa NIP
```

### Varian dirakit, bukan disalin

`ref_jenis_hak` menyimpan atribut tiap jenis hak (jangka waktu, subjek yang boleh,
kegiatan yang berlaku, dasar hukum). `ref_klausa` menyimpan blok kalimat yang dipilih
berdasarkan jenis hak, jenis kegiatan, dan jenis subjek — yang paling khusus menang.
Menambah jenis hak berarti menambah baris di dua tabel itu, bukan menyalin template.

### Validasi sebelum cetak

Tombol cetak mati selama masih ada kesalahan. Yang diperiksa antara lain:

| Pemeriksaan | Dasar |
|---|---|
| Subjek yang boleh memegang jenis hak ini | Pasal 52, 85, 111 Permen ATR/BPN 18/2021 |
| Jangka waktu wajib disebut untuk HGB dan Hak Pakai | Pasal 139 ayat (4) |
| Jumlah anggota Panitia A ganjil, paling kurang 3 | Pasal 138 ayat (1) |
| Alasan wajib ada bila anggota tidak setuju atau tidak menandatangani | Pasal 139 ayat (4) dan (7) |
| Tenggat 14 hari kerja sejak surat tugas | Pasal 136 ayat (1) |
| Kelengkapan dokumen permohonan | Pasal 54 |
| NIK 16 digit, urutan tanggal, konsistensi luas | — |
| Foto lapangan paling sedikit 4 | lampiran BAP |

### Kata penyambung di kanan bawah halaman

Tata naskah dinas menuliskan kata pertama halaman berikutnya di pojok kanan bawah
halaman sebelumnya — SK yang halaman 2-nya dimulai dengan diktum KELIMA diberi tulisan
`KELIMA…` di kanan bawah halaman 1 — supaya ketahuan kalau ada lembar yang hilang.

Di mana halaman berganti baru diketahui sesudah dokumen ditata, dan yang bisa menata
hanyalah pengolah kata. Karena itu `penyambung.py` menyerahkannya ke Microsoft Word
sesudah DOCX-nya dirakit: Word yang menghitung halaman, kata penyambungnya ditaruh
sebagai kotak teks mengambang satu baris di bawah baris terakhir halaman itu — tidak ada
satu baris pun yang bergeser dan jumlah halamannya tetap. Halaman yang teksnya berhenti
lebih awal (karena paragraf berikutnya sudah tidak muat) ikut naik penyambungnya, jadi
tidak ada yang menggantung sendirian di pojok bawah. Hurufnya mengikuti huruf teks di
sekitarnya, dan perakitan ulang menimpa kata penyambung lama, tidak menumpuknya.

Yang ditulis adalah apa yang benar-benar tercetak duluan di halaman berikutnya,
termasuk nomor daftarnya: halaman yang dimulai dengan butir "7. Peraturan Pemerintah …"
menghasilkan `7. Peraturan…`, bukan `Peraturan…`. Nomor itu diambil dari penomoran
otomatis Word, yang bukan bagian dari teks paragraf. Daftar berbutir (•) tidak diikutkan
karena lambangnya berasal dari huruf Symbol.

Dokumen mana yang diberi kata penyambung diatur di menu **Pengaturan** → *Kata
Penyambung* (bawaannya `sk`; isi `bap, risalah, sk` untuk ketiganya, kosongkan untuk
mematikan). Di komputer tanpa Microsoft Word langkah ini dilewati diam-diam —
dokumennya tetap terbit, hanya tanpa kata penyambung.

---

### Penomoran otomatis

Nomor Risalah dan SK diberikan saat pertama kali dicetak, berurutan per jenis hak
per tahun, dan tidak bisa terduplikasi:

```
Risalah  12/2026
SK       33/HGB/BPN.75.03/III/2026
SK       1/HW/BPN.75.03/IX/2026      (tanah wakaf)
```

Kode di tengah nomor SK diambil dari kolom *kode SK* pada matriks jenis hak, bukan dari
kode jenis haknya — tanah wakaf bernomor `HW` sedangkan kode jenis haknya `WAKAF`.
Nomornya berjalan sendiri-sendiri per kode.

Setiap cetakan tercatat di tabel `dokumen_terbit` — nomor, nama berkas, waktu, dan
siapa yang mencetak.

---

## Batas yang perlu diketahui

- **HM Satuan Rumah Susun** sudah ada di matriks jenis hak, tetapi belum punya
  template dan blok klausa sendiri. Perlu dasar hukumnya lebih dulu.
- **Batas kewenangan penetapan** (kantah/kanwil/menteri) baru dicatat, belum
  divalidasi terhadap luas. Perlu Permen ATR/BPN 5/2025 jo. 9/2025.
- **Keluaran hanya DOCX.** Untuk PDF, buka di Word lalu simpan sebagai PDF.
- Aplikasi berjalan di satu komputer (`localhost`). Untuk dipakai bersama lewat
  jaringan kantor, alamat di `server.py` perlu diubah dan hak akses per peran
  ditambahkan.

## Penyimpanan

Tiga tempat yang isinya menumpuk sejalan dengan pemakaian, dan semuanya terlihat di
menu **Pengaturan → Penyimpanan** lengkap dengan ukurannya:

| Isi | Bisa dibuat ulang? | Cara dirapikan |
|---|---|---|
| `pratinjau/` — PDF pratinjau | ya, dari DOCX-nya | **otomatis**: disisakan 40 berkas terakhir atau 100 MB |
| `keluaran/` — DOCX tercetak | ya, dari basis data | tombol *Rapikan keluaran*, sesuai umur dokumen |
| `data/berkas.db.bak-*` | tidak — ini justru cadangannya | tombol *Buang cadangan basis data lama* (sisa 3 terbaru) |
| `templates/cadangan/` | tidak | sudah dibatasi sendiri, 15 versi terakhir |

Yang membuat folder `keluaran/` aman dirapikan: dokumen yang dibuang **dirakit ulang
sendiri** begitu tautan unduh atau pratinjaunya dibuka lagi — datanya masih lengkap di
basis data, nomornya sudah tersimpan, jadi hasilnya sama. Karena itu pula yang dirapikan
hanya yang benar-benar bisa dibuat ulang; tiga hal selalu dilewati:

- dokumen yang **disunting tangan di Word** sesudah dicetak (ketahuan dari waktu ubah
  berkasnya yang lebih baru daripada waktu cetaknya) — misalnya yang fotonya ditempel manual;
- dokumen yang tidak tercatat di arsip cetak, jadi tidak diketahui asalnya;
- dokumen yang berkasnya sudah dihapus dari basis data.

Ukuran satu berkas kira-kira 0,8 MB DOCX + 0,7 MB PDF. Yang paling menentukan adalah
gambar di dalam template: setiap salinan BAP membawa gambar templatenya, jadi
memperkecil gambar di template sekali akan memperkecil semua cetakan berikutnya.
`data/berkas.db`, `data/foto/`, dan folder `templates/` tidak pernah disentuh.

---

## Menjalankan di server Ubuntu

Bisa. Seluruh aplikasinya Python biasa — pustaka bawaan + `python-docx` + `openpyxl`,
basis datanya SQLite, tidak ada kerangka kerja dan tidak ada kode khusus Windows kecuali
dua modul yang menyetir Microsoft Word.

```bash
sudo apt install python3 python3-pip libreoffice-writer
python3 -m pip install python-docx openpyxl Pillow
# salin folder app/ berikut data/berkas.db, data/foto/, dan templates/ dari komputer lama
./jalankan.sh 8000 0.0.0.0
```

Layanan tetap (systemd), berjalan sebagai pengguna sendiri:

```ini
# /etc/systemd/system/panitia-a.service
[Unit]
Description=Berkas Panitia A
After=network.target

[Service]
User=panitia
WorkingDirectory=/opt/panitia-a/app
Environment=ALAMAT=127.0.0.1 PORTA=8000 HTTPS=1
ExecStart=/usr/bin/python3 server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Lalu nginx di depannya untuk HTTPS (`proxy_pass http://127.0.0.1:8000;`). `ALAMAT`
menentukan antarmuka yang didengarkan — biarkan `127.0.0.1` kalau ada nginx, isi
`0.0.0.0` kalau langsung dipakai sejaringan. `HTTPS=1` menandai kuki sesi sebagai
`Secure`; kuki sesinya sendiri sudah `HttpOnly` + `SameSite=Lax`, dan kata sandi
disimpan sebagai PBKDF2-SHA256 200.000 putaran.

Yang perlu diketahui sebelum pindah:

- **Kata penyambung tidak jalan di Linux.** Yang menghitung halaman adalah Microsoft
  Word; tanpa Word langkah itu dilewati diam-diam dan dokumennya tetap terbit. Kalau
  fitur ini wajib ada di server, perlu ditulis ulang memakai LibreOffice UNO
  (`python3-uno`) — logikanya sama, hanya cara bertanya ke pengolah katanya yang beda.
- **Pratinjau PDF memakai LibreOffice** — sudah didukung `pdf.py` dan otomatis dipilih
  kalau Word tidak ada.
- **Pasang hurufnya.** Template memakai Bookman Old Style dan Times New Roman. Tanpa
  huruf itu LibreOffice mengganti sendiri dan pergantian halamannya bisa bergeser:
  `sudo apt install ttf-mscorefonts-installer`, lalu salin berkas huruf Bookman-nya ke
  `/usr/share/fonts/` dan jalankan `fc-cache -f`.
- `jalankan.bat`, `impor.bat`, dan `siapkan_template.bat` hanya untuk Windows; padanan
  Linux-nya `./jalankan.sh` atau langsung `python3 <berkas>.py`.
- Sistem berkas Linux membedakan huruf besar-kecil. Salin folder apa adanya, jangan
  ubah nama `templates/`, `static/`, atau nama berkas template.
- Backup: `data/berkas.db` dan `data/foto/` (plus `templates/` kalau tata naskahnya
  sudah disunting sendiri).

---

## Backup

Salin berkas `data/berkas.db` dan folder `data/foto/` secara berkala. Seluruh isi
aplikasi ada di situ — basis datanya menyimpan data berkas, folder foto menyimpan
gambar lampiran BAP.
