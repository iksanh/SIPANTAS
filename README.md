# SIPANTAS

**Sistem Panitia A Terpadu.**

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

**Menu di sisi kiri**, tetap di tempatnya seperti KKP. Tombol `‹` di sebelah nama
aplikasi menguncupkannya jadi ikon saja kalau perlu ruang lebih — pilihan itu
diingat peramban. Di layar sempit menunya jadi laci yang dibuka lewat tombol di
bilah atas, dan menutup sendiri begitu salah satu menunya ditekan.

Halaman **Berkas baru** dituntun per langkah, bukan bertab: petugas yang baru
pertama kali memakai aplikasi ini tidak perlu menebak harus mulai dari mana.
Tab Sidang dan Cetak sengaja tidak muncul saat membuat — keduanya baru berarti
setelah berkasnya ada. Begitu tersimpan, berkasnya terbuka sebagai delapan tab
biasa supaya pengisian lanjutannya bisa melompat ke mana saja.

Tiap halaman lain **dipecah per tab**, tidak memanjang ke bawah. Tab yang terakhir
dipakai diingat peramban, dan tautan yang menunjuk ke dalam salah satu tab
(misalnya sesudah menyimpan) membuka tab itu sendiri.

Lima menu, dan tiap halaman hanya menampilkan yang sedang dipakai:

| Menu | Bentuknya |
|---|---|
| **Pradaftar** | Satu tabel, disaring kotak cari dan tombol keadaan (Semua / Belum lengkap / Siap diterima / Diterima / Dikembalikan / Batal) yang berikut jumlahnya. Pemeriksaan kelengkapan berkas **sebelum** didaftar di loket. |
| **Pradaftar baru** | Dituntun tiga langkah: Pemohon → Letak tanah → Kelengkapan berkas. Sesudah tersimpan, pradaftarnya terbuka sebagai empat tab. |
| **Berkas** | Satu tabel berhalaman (10/25/50/100 per halaman), disaring kotak cari dan dropdown Jenis hak (HM, WAKAF, …), Status, Kegiatan, dan Kecamatan — tiap pilihan berikut jumlahnya. Saringan tersimpan di alamat (`/berkas?hak=WAKAF&hal=2`), jadi bisa ditandai atau dibagikan. |
| **Berkas baru** | Dituntun enam langkah bernomor: Jenis permohonan → Pihak → Bidang tanah → Riwayat tanah → Dokumen → Foto lapangan. Tiga terakhir bertanda **boleh nanti** dan ada tombol **Lewati**. Simpan hanya ada satu, di ujung langkah terakhir. Sesudah tersimpan, berkasnya langsung terbuka sebagai delapan tab biasa. |
| **Berkas yang dibuka** | Delapan tab. Judul, tombol Simpan, dan bilah tabnya menempel di atas, jadi tetap terjangkau sampai bawah. Tab **Cetak** memakai angka: merah kalau ada yang menghalangi pencetakan, kuning kalau cuma peringatan, centang hijau kalau bersih. |
| **Data referensi** | Lima tab: **Jenis hak**, **Klausa**, **Kelengkapan** (daftar persyaratan yang dipakai Pradaftar), **Wilayah** (daftar induk Kemendagri, kecamatan, desa/kelurahan), **Panitia A** (satu kartu per SK). Di dalam tab Wilayah dan Panitia A isinya tetap kartu lipat — jumlah SK panitia bertambah terus, jadi tidak mungkin dijadikan tab sendiri-sendiri. |
| **Template** | Lima tab: **Hak Milik & hak lain**, **Hak Wakaf**, **Hak Pakai**, **Cetakan loket**, dan **Penanda & cara pakai**. Tiap template satu kartu lipat. |
| **Pengaturan** | Tiga tab: Kantor, Penyimpanan, Pengguna. |

Kartu lipat berarti isi kartunya baru diambil dari server saat kartunya diklik —
halaman referensi dan template tidak pernah memuat semua isinya sekaligus. Kartu yang
terakhir dibuka dan tab yang terakhir dipakai diingat peramban. Kalau JavaScript mati,
kepala kartunya tetap tautan biasa yang membuka bagian itu lewat server.

## Pradaftar: memeriksa kelengkapan di loket

Menu **Pradaftar**, di atas menu Berkas — karena di situlah urutan kerjanya:

```
pemohon datang ke loket
  → Pradaftar baru: pemohon, letak tanah, lalu centang daftar kelengkapannya
      → lengkap      → Terima di loket → jadi Berkas → Panitia A seperti biasa
      → belum lengkap → cetak surat pengembalian, pemohon melengkapi, datang lagi
```

Yang dicentang adalah **Daftar Kelengkapan Persyaratan Permohonan Hak Milik**,
salinan Lampiran Permen ATR/BPN 18/2021 angka 2 halaman 184–185 — delapan butir
bernomor, sebagian punya anak butir berhuruf. Bunyi butirnya disalin apa adanya
supaya cetakannya sama persis dengan formulir resminya.

Empat sifat formulir itu ikut dibawa ke aplikasi, bukan diratakan jadi daftar
centang biasa:

| Sifat formulir | Di aplikasi |
|---|---|
| **Bertingkat** — grup dan anak butir | Baris berindentasi; kepala kelompok tidak dicentang, keadaannya disimpulkan dari anaknya |
| **Alternatif** — «a … atau b …», «b …; dan/atau c …» | Grup terpenuhi begitu salah satunya ada. Alternatif yang tidak dipakai **tidak** ditandai kurang |
| **Bersyarat** — grup Badan Hukum, butir h/i untuk HPL, butir 6 untuk Tanah Negara | Ditentukan jenis subjek pemohon dan asal tanahnya. Butir yang tidak berlaku tetap tampil, hanya diredupkan — petugas perlu melihat bahwa butir itu sengaja dilewati, bukan hilang |
| **Isian bebas** — butir yang berakhir titik-titik | Ada kotak isian di sebelahnya untuk menulis nama suratnya |

**Ada, tapi perlu koreksi.** Tiap butir punya tiga pilihan: *Ada*, *Perlu koreksi*,
*Tidak Ada*. *Perlu koreksi* dipakai bila suratnya dibawa tetapi ada yang salah
(belum dilegalisir, NIK beda, kedaluwarsa). Saat dipilih, muncul kotak catatan
yang bisa diisi dari **catatan koreksi baku** (Data referensi → Kelengkapan →
Catatan koreksi baku) atau diketik sendiri. Butir koreksi:

- menahan penerimaan seperti butir yang kurang — terima bersyarat tetap bisa
  dengan alasan tertulis, dan catatannya ikut tersalin ke dokumen pendukung berkas;
- tercetak di kolom **Ada** pada formulir 184, dengan catatannya di belakang bunyi butir;
- muncul di surat pengembalian dengan keterangan «Perlu diperbaiki: …», terpisah
  dari yang «Belum ada».

Yang disimpan pada pradaftar adalah **teks** catatannya, bukan rujukan ke daftar
baku — menyunting atau menghapus catatan baku tidak mengubah pemeriksaan yang
sudah lewat. Catatan baku boleh berlaku untuk semua butir atau khusus satu butir.

**Lengkap atau tidak, dihitung — bukan disimpan.** Kolom `status` hanya menyimpan
`baru`, `diterima`, `dikembalikan`, atau `batal`. Keadaan kelengkapannya dihitung
ulang dari centangannya setiap kali dibutuhkan, sama seperti terbilang dan luas
berhuruf. Kalau disimpan, akan ada baris bertanda "lengkap" yang centangannya
sudah berubah.

**Nomor agenda loket** diberi saat pradaftar dibuat — `PD-0012/2026`, berjalan per
tahun lewat mekanisme penomoran yang sama dengan Risalah dan SK, jadi tidak bisa
terduplikasi. Nomor berkas baru keluar kalau berkasnya benar-benar diterima.

### Terima di loket

Tombolnya di tab **Kesimpulan & cetak**. Yang terjadi: berkas baru dibuat, lalu
isian pradaftar disalin ke sana — inilah alasan pradaftar ada di aplikasi yang
sama, bukan di buku tersendiri.

| Dari pradaftar | Masuk ke berkas |
|---|---|
| Jenis hak, jenis kegiatan, asal tanah | kolom `berkas` yang sama |
| Pemohon | pihak berperan *penerima hak* |
| Penerima kuasa | pihak berperan *kuasa* |
| Desa, luas menurut surat, nomor PBT | bidang tanah |
| Butir bercentang yang punya padanan slot baku | slot dokumen baku, mis. butir 6 → *Jenis SPPF* |
| Butir bercentang di bawah *Dasar Penguasaan atau Alas Hak* | baris dokumen berkategori *Bukti alas hak* |
| Butir bercentang lainnya | baris *Dokumen tambahan* |

Yang disalin hanya **nama suratnya**. Nomor, tanggal, dan pejabatnya tetap diisi
petugas Panitia A — loket memang tidak mencatat itu.

Sesudah diterima, pradaftarnya **terkunci jadi baca-saja** dan tidak bisa diterima
dua kali: nomor berkas yang telanjur keluar tidak bisa ditarik, dan berkas kembar
berarti satu permohonan disidangkan dua kali. Di tab **Dokumen** berkasnya muncul
tautan balik ke pradaftar asalnya.

Berkas yang belum lengkap **tetap bisa diterima**, tetapi alasannya wajib ditulis
dan ikut tersimpan — praktiknya ada berkas yang diterima bersyarat.

### Cetakannya

Dua, keduanya dari tab **Kesimpulan & cetak**:

| Cetakan | Isinya |
|---|---|
| **Daftar Kelengkapan Persyaratan** | Formulir 184 terisi, lengkap dengan kolom Ada / Tidak Ada — untuk arsip berkas |
| **Surat pengembalian berkas** | Hanya butir yang masih kurang atau perlu koreksi, dengan kolom keterangan — diserahkan ke pemohon. Mati kalau kelengkapannya sudah terpenuhi |

Keduanya membuka **pratinjau PDF**, bukan unduhan: formulir loket dibaca sebentar
lalu dicetak, tidak disunting, jadi mengunduh DOCX dulu cuma menambah satu
langkah. Dari halaman pratinjaunya ada **Cetak** (membuka dialog cetak peramban
langsung dari PDF yang tampil), **Unduh PDF**, **Unduh DOCX** untuk yang perlu
menyuntingnya dulu, dan **Buat ulang** kalau datanya baru diubah.

Mencetak selalu boleh, termasuk pada pradaftar yang sudah diterima atau sudah
ditutup — formulirnya justru dibutuhkan sebagai lampiran arsip berkas, dan
mencetak tidak mengubah apa pun.

Keduanya memakai template DOCX biasa (`templates/checklist.docx` dan
`pengembalian.docx`), jadi tata naskahnya bisa diubah lewat menu **Template** →
tab *Cetakan loket* seperti BAP, Risalah, dan SK. Kalau templatenya perlu
dikembalikan ke bentuk awal: `python -m berkas.perkakas.siapkan_checklist`
(**menimpa** hasil suntingan).

Berbeda dengan BAP/Risalah/SK, cetakan loket **tidak disimpan** ke folder
`keluaran/` dan tidak dicatat di arsip cetak: isinya bisa dirakit ulang persis
dari pradaftarnya kapan saja. DOCX dan PDF-nya menumpang di folder `pratinjau/`
sebagai singgahan biasa, dan ikut dipangkas sendiri di 40 berkas terakhir.
Siapa yang memeriksa dan kapan sudah tercatat di baris pradaftarnya sendiri.

Singgahannya tidak perlu dicatat di mana pun: **waktu ubah DOCX-nya disetel ke
waktu ubah pradaftarnya**, jadi perbandingan mtime yang sudah dipakai
`pdf.ke_pdf()` otomatis tahu kapan PDF-nya basi. Cetakan yang datanya tidak
berubah langsung tampil tanpa memanggil Word lagi.

Di komputer tanpa Microsoft Word maupun LibreOffice, halaman pratinjaunya
mengatakan begitu dan tetap menawarkan unduhan DOCX — sama seperti pratinjau
dokumen Panitia A.

### Mengubah daftar kelengkapannya

Menu **Data referensi** → tab **Kelengkapan**. Yang bisa disunting admin dua hal
yang memang berbeda antar kantor:

- **bunyi butirnya**, dan
- **wajib atau tidaknya** — butir yang tidak wajib tetap tercetak dan tetap bisa
  dicentang, hanya tidak menahan penerimaan berkas di loket.

Tiga butir sudah tidak wajib sejak awal karena keluaran Kantor Pertanahan sendiri,
bukan dokumen yang dibawa pemohon: **Peta Bidang Tanah** (terbit sesudah
pengukuran), **Risalah Pemeriksaan Tanah A** (sesudah sidang Panitia A), dan
**Surat Pengantar dari Kantor Pertanahan**. Kantor yang alurnya berbeda tinggal
menyalakan wajibnya di sini.

Susunan nomor, huruf, dan tingkatannya sengaja **tidak** bisa diubah dari layar —
kalau bisa, cetakannya tidak lagi sama dengan formulir resminya.

### Menambah formulir untuk jenis hak lain

Yang terpasang: Hak Milik (`184-HM`) dan Hak Pakai dengan jangka waktu
(`190-HP`, Lampiran angka 5 huruf a, hlm. 190-191). Lampiran Permen 18/2021 memuat format
serupa untuk HGB, Hak Pakai selama dipergunakan, HPL, perubahan hak, dan izin peralihan. Menambahkannya
**tidak mengubah kode**, cukup dua hal di `berkas/db.py`:

1. satu baris di `KELENGKAPAN` — kode, judul, jenis hak, dan varian templatenya;
2. satu daftar butir di `KELENGKAPAN_BUTIR`, memakai penolong `_butir()`.

Kalau tata naskah cetakannya juga berbeda, tambahkan `templates/checklist-<varian>.docx`;
selama berkas itu belum ada, yang dipakai template bakunya. Formulir yang dipakai
sebuah pradaftar dipilih dari jenis haknya, yang paling khusus menang — pola yang
sama dengan pemilihan blok klausa.

Formulir resmi dipasang sekali sebagai satu kesatuan, dikenali dari `kode`-nya.
Sesudah terpasang ia jadi milik kantor: suntingan admin tidak akan tertimpa saat
aplikasi diperbarui.

---

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
| `bap-hp.docx`, `risalah-hp.docx`, `sk-hp.docx` | Hak Pakai (perorangan dan badan hukum) |

### Yang diisi pada berkas wakaf

Semuanya diisi sekali, di tempat yang sudah ada — tidak ada isian kembar:

| Yang dicetak dokumen | Diisi di |
|---|---|
| Nama seluruh Nazhir di judul SK dan Risalah | tab **Pihak**: Nazhir pertama di kartu *Penerima hak*, sisanya baris *Pihak lain* berperan **Nazhir** |
| Nama, NIK, TTL, domisili, pekerjaan tiap Nazhir (Risalah mencetaknya per orang, a.i/a.ii/a.iii) | baris Nazhir itu juga — barisnya bertambah sendiri sesuai jumlah Nazhir |
| Nama Wakif di Menimbang SK dan di DATA PENDUKUNG | baris *Pihak lain* berperan **Wakif** |
| Nama, domisili, NIK, pekerjaan tiap Wakif (Risalah, *Uraian mengenai Pemohon* nomor 2, a.i/a.ii/…) | baris Wakif itu juga |
| Akta Ikrar Wakaf yang dirujuk Menimbang SK | tab **Dokumen** → slot *Akta Ikrar Wakaf* |
| Pengesahan Nazhir oleh PPAIW | tab **Dokumen** → slot *Pengesahan Nazhir oleh PPAIW* |
| Bentuk Nazhir (perseorangan / organisasi / badan hukum) | *Jenis subjek* penerima hak |

Empat slot dokumen khusus wakaf — Akta Ikrar Wakaf, pengesahan Nazhir, kesediaan
menjadi Nazhir, dan kesediaan diaudit — hanya muncul pada berkas berjenis hak wakaf.

Yang diperiksa sebelum cetak, selain pemeriksaan yang berlaku umum:

| Pemeriksaan | Dasar |
|---|---|
| Nazhir perseorangan paling sedikit 3 orang — hanya peringatan, karena AIW lama ada yang Nazhirnya satu orang | Pasal 4 ayat (2) PP 42/2006 |
| Wakif wajib ada | Permen ATR/BPN 2/2017 |
| Akta Ikrar Wakaf wajib ada | Pasal 32 UU 41/2004 |
| Pengesahan Nazhir dari PPAIW | Pasal 14 PP 42/2006 |
| NIK dan TTL tiap Nazhir terisi | Risalah mencetaknya per orang |
| Domisili, NIK, pekerjaan tiap Wakif terisi (peringatan) | Risalah mencetaknya per orang |
| Hak Wakaf tidak berjangka waktu | UU 41/2004 |

## Tata naskah Hak Pakai: perorangan dan badan hukum

Pilih jenis hak `HP` di tab Berkas, dan ketiga dokumennya dirakit dari set Hak Pakai
(`bap-hp.docx`, `risalah-hp.docx`, `sk-hp.docx`). Satu set melayani **perorangan
maupun badan hukum** — yang menentukan adalah *Jenis subjek* penerima hak:

| Bagian | Perorangan | Badan hukum |
|---|---|---|
| Risalah I — Uraian mengenai Pemohon | 1. Perorangan: nama, domisili, kewarganegaraan, NIK, pekerjaan | 1. Badan Hukum: nama, tempat kedudukan, akta pendirian, pengesahan, NIB/TDP (Lampiran VII) |
| Risalah IV — Data Pendukung | KTP dan KK pemohon | fotokopi akta pendirian, akta perubahan, pengesahan, NIB, KTP pengurus, akta CSR — yang diisi saja |
| Risalah VI dan VIII — telaah subjek | UUPA Pasal 42 huruf a, Permen 18/2021 Pasal 111 ayat (2) huruf a | UUPA Pasal 42 huruf c, PP 18/2021 Pasal 49 ayat (2) huruf b, Permen 18/2021 Pasal 111 ayat (2) huruf b |
| SK Membaca a, KESATU | «bertempat tinggal di …» | «berkedudukan di …» |
| SK Menimbang a | WNI, alamat, NIK (Lampiran VI format A.1.a) | badan hukum, kedudukan, bidang usaha, akta pendirian + notaris, pengesahan, akta perubahan + persetujuannya, OSS/NIB (format A.1.b) |
| SK Menimbang — CSR | — | bila akta kesanggupan CSR diisi (Pasal 114 ayat (1) huruf f angka 9) |
| SK Mengingat | — | UU bentuk badannya: PT → UU 40/2007, Yayasan → UU 16/2001 jo. 28/2004, Koperasi → UU 25/1992 |
| BAP | «Sdr./Sdri. Nama» | nama badan hukumnya saja |

Yang sama untuk keduanya: sebutannya «Hak Pakai dengan jangka waktu», jangka
waktunya (isian *Jangka waktu* di tab Sidang, paling lama 30 tahun — Pasal 113)
disebut di Risalah III dan X serta di SK Menimbang d.6, Menetapkan, dan KESATU, dan
diktum KEDUA mendapat butir perpanjangan paling lama 20 tahun.

Di dalam template, paragraf `{{!badan_hukum}}` hanya tercetak untuk perorangan dan
`{{?badan_hukum}}` hanya untuk badan hukum; baris tabel Risalah dipilih lewat blok
`{{#pemohon_perorangan}}` / `{{#pemohon_badan_hukum}}`.

### Yang diisi pada berkas Hak Pakai badan hukum

Tab **Pihak** → kartu *Bila penerima hak adalah badan hukum*. Pada berkas Hak Pakai
kartu itu bertambah bagian **Rincian untuk SK Hak Pakai**: bidang usaha, kota
notaris, pejabat yang mengesahkan, NIK pengurus, akta perubahan terakhir berikut
persetujuannya, tanggal terdaftar di OSS, dan akta kesanggupan CSR. Semuanya
boleh kosong — kalimat SK disusun dari yang terisi saja, tanpa titik-titik. Pada
jenis hak lain bagian itu tidak tampak, tetapi isinya tetap tersimpan.

Seperti isian wakaf, bagian ini baru muncul **setelah** berkas disimpan dengan jenis
hak `HP`.

Yang diperiksa sebelum cetak, khusus Hak Pakai (semuanya peringatan):

| Pemeriksaan | Dasar |
|---|---|
| Badan hukum: kedudukan, bidang usaha, tanggal akta, notaris, nomor pengesahan, NIB | Menimbang huruf a, Lampiran VI |
| Akta perubahan diisi tanpa persetujuan/pencatatannya | Lampiran VI format A.1.b |
| Pengurus yang mewakili belum diisi | — |
| Subjek *instansi* (Hak Pakai selama dipergunakan) belum punya tata naskah sendiri | Pasal 111 ayat (3) |

### Membangun ulang template Hak Pakai

Template Hak Pakai **dirakit dari template Hak Milik yang sedang terpasang** — kop,
susunan panitia, dasar hukum, dan diktumnya memang sama — lalu bagian yang
berbeda diganti oleh `python -m berkas.perkakas.siapkan_hak_pakai`. Perintah itu
**menimpa** `*-hp.docx`; jalankan hanya kalau template Hak Milik berubah banyak dan
set Hak Pakai mau diturunkan ulang darinya. Kalau kalimat jangkarnya sudah tidak
ada di template Hak Milik, perkakasnya berhenti dan menyebut kalimat mana.
Suntingan kecil cukup lewat menu **Template** → tab *Hak Pakai* seperti biasa.

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
- `Flask` dan `waitress` — kerangka web dan server WSGI
- `python-docx` dan `openpyxl` — perakit DOCX dan pembaca XLSX
- `Pillow` (dianjurkan) — untuk memutar tegak dan memperkecil foto lapangan

Semuanya dipasang otomatis oleh `jalankan.bat`. Versinya dipatok di
`requirements.txt`; untuk memasang sendiri:
`python -m pip install -r requirements.txt`

Tidak ada basis data server, tidak ada ORM, dan tidak perlu internet. HTML, CSS,
dan JavaScript tetap ditulis sendiri di `web.py` dan folder `static/`.

---

## Isi folder

| Berkas | Isi |
|---|---|
| `jalankan.py` | Titik masuk sehari-hari: siapkan basis data, lalu jalankan waitress |
| `wsgi.py` | Titik masuk WSGI untuk server production |
| **`berkas/`** | **Paket aplikasinya** |
| `berkas/jalur.py` | Letak tiap folder, dihitung sekali — satu-satunya yang memakai `__file__` |
| `berkas/aplikasi.py` | Pabrik Flask: koneksi per permintaan, penjagaan sesi, pendaftaran blueprint |
| `berkas/db.py` | Skema, data referensi awal, dan penolong kueri lintas-basis-data |
| `berkas/konfigurasi.py` | Setelan pemasangan: basis data, kunci rahasia, alamat |
| `berkas/basis.py` | Lapisan tipis di atas SQLite dan PostgreSQL |
| `berkas/sesi.py` | Sesi masuk — token di tabel `sesi`, kuki HttpOnly |
| `berkas/izin.py` | Peran, kepemilikan berkas, dan penjaga tiap rute |
| `berkas/kabar.py` | Kabar di atas halaman dan cara membacanya dari alamat |
| `berkas/formulir.py` | Penyimpanan formulir berkas ke sebelas tabel, dan kueri daftarnya |
| `berkas/pradaftar.py` | Pradaftar loket: centangan kelengkapan, hitungan lengkap/kurang, dan penaikannya jadi berkas |
| `berkas/referensi.py` | Kueri data referensi — tanpa HTTP, tanpa HTML |
| `berkas/wilayah.py` | Daftar induk kecamatan/desa Kemendagri dan riwayat kepala desa |
| `berkas/web.py` | Perakit halaman HTML |
| `berkas/pemeliharaan.py` | Hitung isi folder dan buang berkas yang bisa dibuat ulang |
| `berkas/util.py` | Terbilang, nama hari/bulan, luas, hari kerja |
| **`berkas/rute/`** | **Satu berkas per kelompok halaman** |
| `rute/auth.py` | Masuk, keluar, ganti sandi, tambah pengguna |
| `rute/pradaftar.py` | Daftar pradaftar, formulir empat tab, cetakan loket, dan terima di loket |
| `rute/berkas.py` | Daftar berkas, formulir delapan tab, dan pencetakan |
| `rute/referensi.py` | Halaman Data referensi dan seluruh penyimpanannya |
| `rute/template.py` | Halaman Template: unduh, ganti, kembalikan dari cadangan |
| `rute/pengaturan.py` | Identitas kantor dan perapian penyimpanan |
| `rute/unduhan.py` | Mengeluarkan DOCX, foto, dan PDF |
| **`berkas/dokumen/`** | **Perakitan dokumen — tidak tahu soal HTTP** |
| `dokumen/konteks.py` | Nilai turunan dan seluruh aturan validasi |
| `dokumen/docxgen.py` | Mesin perakit DOCX (perulangan, kondisi, lampiran foto) |
| `dokumen/templat.py` | Unduh, unggah, cadangkan, dan pulihkan template |
| `dokumen/terbitkan.py` | Penomoran otomatis dan pencatatan arsip cetak |
| `dokumen/penyambung.py` | Kata penyambung di kanan bawah halaman, lewat Microsoft Word |
| `dokumen/pdf.py` | Pratinjau PDF lewat Microsoft Word atau LibreOffice |
| `dokumen/foto.py` | Simpan, putar tegak, perkecil, dan buang foto lapangan |
| `dokumen/kelengkapan.py` | Rakit cetakan loket — tidak disimpan, langsung dikirim ke peramban |
| **`berkas/perkakas/`** | **Skrip sekali jalan, dipanggil dengan `python -m`** |
| `perkakas/siapkan_template.py` | Pengubah dokumen Word ber-MERGEFIELD jadi template sistem |
| `perkakas/siapkan_checklist.py` | Pembangun template daftar kelengkapan dan surat pengembalian |
| `perkakas/siapkan_hak_pakai.py` | Penurun set template Hak Pakai dari template Hak Milik |
| `perkakas/impor_excel.py` | Pemindah data dari Excel lama (rutin dan wakaf) |
| `perkakas/perbaiki_dokumen.py` | Perapian data hasil impor |
| `perkakas/pindah_ke_pg.py` | Pindahkan isi SQLite ke PostgreSQL, id dipertahankan |
| `static/` | style.css dan app.js |
| `templates/` | Template DOCX hasil konversi, satu set per tata naskah (`cadangan/` berisi versi sebelumnya) |
| `uji/` | Uji acuan: memastikan isi dokumen tidak berubah diam-diam |
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

## Uji acuan

Masalahnya begini: terbilang, luas berhuruf, selisih ukuran, penomoran a/i/romawi,
dan kalimat otomatis terlalu banyak untuk diperiksa satu per satu setiap kali kode
disentuh. Kesalahan kecil di situ tidak kelihatan sampai dokumennya telanjur
ditandatangani.

Jadi hasil yang sekarang dianggap benar direkam ke `uji/emas/`. Sesudah itu setiap
perubahan kode dibandingkan dengan rekaman tadi, dan yang berbeda ditampilkan baris
per baris.

| Perintah | Yang dikerjakan |
|---|---|
| `uji.bat` | Konteks seluruh berkas + lapisan web. Cepat (beberapa detik), dipakai sehari-hari. |
| `uji.bat penuh` | Ikut merakit DOCX untuk delapan berkas contoh. Sekitar satu menit. |
| `uji.bat rekam` | Merekam ulang acuan. **Hanya** bila perubahannya memang disengaja. |

Tiga lapis yang diperiksa:

- **Konteks** — nilai setiap penanda `{{...}}` berikut hasil `periksa()`, untuk semua
  berkas di basis data. Kalau ada yang berubah, selisihnya langsung menyebut nama
  penandanya.
- **Dokumen** — teks DOCX hasil rakitan. Yang dijaga di sini hal yang tidak kelihatan
  di konteks: paragraf berulang, paragraf bersyarat, baris `;` yang harus jadi `.` di
  ujung daftar, tabel kosong yang dibuang, dan ekor halaman kosong. Karena perakitan
  DOCX lambat, yang dipakai hanya satu berkas per bentuk — dipilih sendiri dari isi
  basis data, jadi jenis berkas baru ikut terwakili tanpa perlu diatur.
- **Hak Pakai** (`uji/uji_hak_pakai.py`) — satu berkas Hak Milik di salinan basis
  data dijadikan Hak Pakai, lalu ketiga dokumennya dirakit untuk pemohon perorangan
  dan badan hukum: kalimat yang harus berbeda diperiksa, dan tak boleh ada sisa
  «Hak Milik» atau penanda. Ikut menguji isian rincian badan hukum dan formulir 190-HP.
- **Web** (`uji/uji_web.py`) — kode jawaban, alamat tujuan, dan bentuk kuki sesi
  untuk tiap rute — 165 uji, meliputi seluruh blueprint, aturan peran,
  penjagaan CSRF, dan susunan langkah pada formulir berkas baru. Dijalankan
  di SQLite maupun PostgreSQL.
- **Konfigurasi dan dialek** (`uji/uji_basis.py`) — penguraian setelan dan
  penerjemahan SQL, termasuk penjaga yang menolak kembalinya dialek khas
  SQLite ke dalam kode.
  Tidak perlu rekaman acuan: harapannya ditulis langsung di dalam ujinya.

Basis datanya tidak pernah disentuh: uji selalu bekerja di salinan sementara, dan
dokumen hasil uji tidak masuk ke `keluaran/`.

Kalau uji gagal, **baca dulu selisihnya.** Merekam ulang supaya uji jadi hijau sama
saja dengan membuang jaring pengamannya — kesalahan yang baru muncul ikut terekam
sebagai kebenaran baru.

Rekaman di `uji/emas/` tidak dilacak git karena berisi data pemohon yang sebenarnya.
Di komputer baru, rekamannya dibuat sekali dengan `uji.bat rekam`.

---

## Batas yang perlu diketahui

- **HM Satuan Rumah Susun** sudah ada di matriks jenis hak, tetapi belum punya
  template dan blok klausa sendiri. Perlu dasar hukumnya lebih dulu.
- **Batas kewenangan penetapan** (kantah/kanwil/menteri) baru dicatat, belum
  divalidasi terhadap luas. Perlu Permen ATR/BPN 5/2025 jo. 9/2025.
- **Keluaran hanya DOCX.** Untuk PDF, buka di Word lalu simpan sebagai PDF.
- Aplikasi berjalan di satu komputer (`localhost`). Untuk dipakai bersama lewat
  jaringan kantor, setel `ALAMAT=0.0.0.0` (lihat `jalankan_jaringan.bat`).

## Peran dan hak akses

Dua peran, disimpan di kolom `pengguna.peran` dan diatur admin lewat menu
**Pengaturan → Pengguna**.

| | Admin | Petugas |
|---|---|---|
| Tambah pradaftar | ✓ | ✓ |
| Lihat pradaftar | semua | miliknya sendiri |
| Terima di loket & cetak | semua | miliknya sendiri |
| Hapus pradaftar | ✓ | — |
| Tambah berkas | ✓ | ✓ |
| Lihat berkas | semua | miliknya sendiri + arsip impor |
| Ubah berkas | semua | miliknya sendiri |
| Cetak dokumen | semua | miliknya sendiri |
| Hapus berkas | ✓ | — |
| Unduh DOCX / PDF / foto | semua | berkas yang boleh dilihatnya |
| Data referensi | ubah | **lihat saja** |
| Template | ✓ | — (menunya tidak muncul) |
| Identitas kantor & penyimpanan | ✓ | — |
| Tambah pengguna & ubah peran | ✓ | — |
| Ganti kata sandi sendiri | ✓ | ✓ |

**Kepemilikan berkas** ada di kolom `berkas.dibuat_oleh`, diisi otomatis saat
berkas dibuat. Petugas hanya melihat berkas yang dibuatnya sendiri.

**Berkas hasil impor Excel** kolom itu kosong — tidak ada yang mengetiknya lewat
aplikasi ini. Arsip tersebut sengaja dibiarkan terlihat semua orang supaya
pekerjaan yang sedang berjalan tidak terputus, tetapi **hanya admin yang boleh
mengubahnya**: tidak ada cara memastikan siapa yang berhak atas berkas yang
pemiliknya tidak tercatat. Di daftar, berkas seperti ini bertanda `arsip impor`,
dan formulirnya terbuka dalam mode baca-saja.

Admin tidak bisa menurunkan perannya sendiri. Kalau itu admin terakhir, tidak
akan ada lagi yang bisa menaikkan siapa pun dan aplikasinya terkunci tanpa jalan
masuk selain menyunting basis datanya langsung.

### Token anti-CSRF

Tiap permintaan yang mengubah data (POST) wajib membawa token; yang tidak
membawa ditolak sebelum menyentuh basis data. Tanpa ini, satu halaman jahat di
tab sebelah cukup memuat formulir tersembunyi untuk menyuruh peramban petugas —
lengkap dengan kukinya — menghapus berkas atau menaikkan peran seseorang.

| | |
|---|---|
| Yang sudah masuk | token di kolom `sesi.csrf`, satu per sesi, mati sendiri saat keluar |
| Yang belum masuk | token di kuki `csrf_tamu`, menjaga formulir masuk itu sendiri |

Formulir masuk ikut dijaga karena tanpa itu penyerang bisa memaksa korban masuk
ke akun miliknya, lalu menunggu korban mengetik data ke sana.

Tokennya **disisipkan otomatis** ke tiap `<form method="post">` sesudah
halamannya dirakit (`aplikasi.py`), bukan ditulis satu per satu di `web.py`.
Alasannya: formulir baru yang lupa memanggilnya akan lolos tanpa penjagaan, dan
itu tidak kelihatan sampai ada yang memanfaatkannya. Dengan penyisipan terpusat
tidak ada yang bisa terlewat — termasuk potongan kartu lipat yang tidak melewati
`layout()`. Uji `test_tiap_form_di_tiap_halaman_bertoken` menyapu seluruh halaman
dan memastikannya.

Kedua kukinya `HttpOnly` + `SameSite=Lax`: tidak terbaca JavaScript, dan tidak
ikut terkirim pada permintaan lintas situs.

Penjagaan masuk berjalan **sebelum** pemeriksaan token. Sesi yang habis di tengah
pengisian formulir jadi berakhir di halaman masuk, bukan di halaman galat yang
buntu. Token yang basi menghasilkan halaman "Formulir kedaluwarsa" yang menyuruh
memuat ulang, bukan omelan.

Aturan peran ada di satu berkas, `berkas/izin.py`, dan dipakai dua kali untuk tiap
halaman: sekali oleh rute untuk menolak permintaan, sekali oleh `web.py` untuk
menyembunyikan tombolnya. **Yang menjaga adalah penolakan di rute** —
menyembunyikan tombol saja tidak menghalangi siapa pun yang mengetik alamatnya
langsung, dan uji di `uji/uji_web.py` memang menembak rutenya, bukan memeriksa
tombolnya.

---

## Basis data: SQLite atau PostgreSQL

Bawaannya SQLite di `data/berkas.db` — tanpa setelan apa pun, tanpa server
tambahan. Untuk pindah ke PostgreSQL, salin `.env.contoh` jadi `.env` lalu isi:

```
DB_URL=postgresql://panitia:ganti-sandinya@127.0.0.1:5432/panitia_a
```

Kata sandi yang memuat `@ : / ?` harus disandikan di dalam URL; kalau
merepotkan, pakai bentuk per bagian (`DB_JENIS`, `DB_HOST`, `DB_PASSWORD`, …)
yang menerimanya apa adanya. Variabel lingkungan sungguhan mengalahkan isi
`.env`, jadi satu setelan bisa ditimpa sekali jalan tanpa menyunting berkas.

### Pindah dari SQLite yang sudah terisi

```bash
python -m berkas.db                            # buat skemanya di PostgreSQL
python -m berkas.perkakas.pindah_ke_pg --lihat # lihat rencananya dulu
python -m berkas.perkakas.pindah_ke_pg         # jalankan
```

Nomor id dipertahankan apa adanya — dokumen yang sudah terbit menyebut nomor
berkas, dan riwayat cetak menunjuk id; kalau id bergeser, tautan antar-tabel
putus tanpa ada yang kelihatan salah. Seluruh pemindahan satu transaksi: satu
baris gagal, semuanya dibatalkan. Jumlah baris tiap tabel diperiksa sebelum
transaksinya ditutup, dan tujuan yang sudah dipakai ditolak kecuali `--paksa`.

**Folder `data/foto/` dan `keluaran/` tidak ikut pindah** — keduanya berkas
biasa di cakram, bukan isi basis data. Salin sendiri.

### Bagaimana satu kode melayani dua basis data

Kuerinya sendiri ditulis dalam dialek yang dimengerti keduanya: `ON CONFLICT`
untuk upsert (bukan `INSERT OR REPLACE` yang khas SQLite), `RETURNING id`
(bukan `cursor.lastrowid`), dan waktu dihitung di Python (bukan
`datetime('now','localtime')`). Yang benar-benar tidak bisa disamakan cuma
empat hal, dan semuanya diurus `basis.py`:

| | SQLite | PostgreSQL |
|---|---|---|
| Penampung nilai | `?` | `%s` |
| Bentuk baris | `sqlite3.Row` | dibuatkan yang setara |
| Kolom id otomatis | `INTEGER PRIMARY KEY` | `GENERATED ALWAYS AS IDENTITY` |
| Nama galat bentrok | `sqlite3.IntegrityError` | `psycopg.errors.IntegrityError` |

Sengaja bukan ORM: seluruh kueri aplikasi ini SQL tulis tangan yang sudah
terbukti, dan menggantinya dengan ORM berarti menulis ulang semuanya sekaligus
membuang uji acuan yang menjaganya.

Kolom waktu tetap TEXT `YYYY-MM-DD HH:MM:SS` di PostgreSQL, bukan `timestamp`,
supaya data berpindah apa adanya dan perbandingan `<` `>` berperilaku sama.

Rangkaian uji yang sama dijalankan di kedua basis data:

```bash
python -m unittest uji.uji_web
DB_URL=postgresql://panitia:sandi@127.0.0.1:5432/panitia_a_uji     python -m unittest uji.uji_web
```

---

## Memasang pembaruan

Salin berkas yang berubah, lalu **nyalakan ulang layanannya**. Dua hal ikut
bergantung pada itu:

- Kode Python baru hanya terbaca saat proses dimulai.
- `style.css` dan `app.js` dipanggil dengan `?v=<waktu ubah berkas>`, dan angka
  itu dihitung sekali saat modul dimuat. Menyalakan ulang membuat alamatnya
  berubah, sehingga peramban mengambil yang baru alih-alih memakai singgahan
  lamanya. Tanpa itu, halaman baru bisa berjalan dengan JavaScript lama —
  setengah rusak, dan sulit dikenali sebagai masalah singgahan.

---

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

Bisa. Seluruh aplikasinya Python biasa — Flask + waitress + `python-docx` +
`openpyxl`, basis datanya SQLite, dan tidak ada kode khusus Windows kecuali dua modul
yang menyetir Microsoft Word.

```bash
sudo apt install python3 python3-pip libreoffice-writer
python3 -m pip install -r requirements.txt
# salin folder app/ berikut data/berkas.db, data/foto/, dan templates/ dari komputer lama
./jalankan.sh 8000 0.0.0.0
```

Layanan tetap (systemd), berjalan sebagai pengguna sendiri:

```ini
# /etc/systemd/system/panitia-a.service
[Unit]
Description=SIPANTAS
After=network.target

[Service]
User=panitia
WorkingDirectory=/opt/panitia-a/app
Environment=ALAMAT=127.0.0.1 PORTA=8000 HTTPS=1
Environment=KUNCI_RAHASIA=ganti-dengan-teks-acak-panjang
ExecStart=/usr/bin/python3 jalankan.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Lalu nginx di depannya untuk HTTPS (`proxy_pass http://127.0.0.1:8000;`). `ALAMAT`
menentukan antarmuka yang didengarkan — biarkan `127.0.0.1` kalau ada nginx, isi
`0.0.0.0` kalau langsung dipakai sejaringan. `HTTPS=1` menandai kuki sesi sebagai
`Secure`; kuki sesinya sendiri sudah `HttpOnly` + `SameSite=Lax`, dan kata sandi
disimpan sebagai PBKDF2-SHA256 200.000 putaran. `KUNCI_RAHASIA` diisi teks acak
panjang dan tetap — kalau dibiarkan kosong, kunci dibuat baru tiap kali layanan
dinyalakan ulang.

Satu proses sudah cukup; yang dinaikkan kalau terasa lambat adalah jumlah utas
(`UTAS=8`), bukan jumlah pekerja — SQLite tidak suka ditulisi banyak proses
sekaligus.

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
