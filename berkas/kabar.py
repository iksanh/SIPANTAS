# -*- coding: utf-8 -*-
"""Kabar singkat di atas halaman, dan cara membacanya dari alamat.

Alurnya: sesudah POST, rute mengalihkan ke halaman daftar dengan `?pesan=<kode>`
di belakangnya. Halamannya menerjemahkan kode itu jadi kalimat lewat PESAN di
bawah. Kalau kabarnya memuat angka atau nama yang tidak bisa ditulis di muka,
dipakai `?baik=<teks>` atau `?galat=<teks>` yang isinya langsung dipakai apa
adanya (setelah di-escape).

Pola alihkan-lalu-tampilkan ini disengaja: menyegarkan halaman sesudah menyimpan
tidak mengirim ulang formulirnya.
"""
import html

from flask import request

PESAN = {
    "tersimpan": ("baik", "<b>Tersimpan.</b> Perubahan sudah masuk ke basis data."),
    "dibuat": ("baik", "<b>Berkas dibuat.</b> Lengkapi tab berikutnya, lalu simpan lagi."),
    "dihapus": ("baik", "<b>Berkas dihapus.</b>"),
    "pradaftar_dibuat": ("baik", "<b>Pradaftar dibuat.</b> Centang dokumen yang "
                                 "diserahkan pemohon di bawah ini."),
    "pradaftar_hapus": ("baik", "<b>Pradaftar dihapus.</b> Berkas yang sudah terbit "
                                "darinya tidak ikut terhapus."),
    "sandi": ("baik", "<b>Kata sandi diubah.</b>"),
    "sandi_salah": ("galat", "<b>Kata sandi lama salah.</b>"),
    "pengguna": ("baik", "<b>Pengguna ditambahkan.</b>"),
    "pengguna_ada": ("galat", "<b>Username sudah dipakai.</b>"),
    "peran": ("baik", "<b>Peran diubah.</b> Berlaku saat pengguna itu memuat halaman "
                      "berikutnya."),
    "peran_salah": ("galat", "<b>Peran tidak dikenal.</b>"),
    "peran_sendiri": ("galat", "<b>Tidak bisa menurunkan peran sendiri.</b> Minta admin "
                               "lain yang melakukannya, supaya tidak ada keadaan tanpa "
                               "admin sama sekali."),
    "pengaturan": ("baik", "<b>Pengaturan disimpan.</b>"),
    "referensi": ("baik", "<b>Data referensi diperbarui.</b>"),
    "butir": ("baik", "<b>Butir disimpan.</b> Berlaku untuk pradaftar yang dibuka "
                      "sesudah ini."),
    "butir_hapus": ("baik", "<b>Butir dihapus</b> dari formulir."),
    "butir_nonaktif": ("baik", "<b>Butir dinonaktifkan.</b> Sudah pernah dicentang pada "
                               "pradaftar lama, jadi barisnya disimpan untuk riwayat — "
                               "pradaftar baru tidak lagi menampilkannya."),
    "butir_nomor": ("baik", "<b>Nomor dan huruf disusun ulang.</b>"),
    "formulir_baru": ("baik", "<b>Formulir dibuat.</b> Tambahkan atau susun butirnya di "
                              "bawah ini."),
    "formulir_hapus": ("baik", "<b>Formulir dihapus.</b>"),
    "formulir_nonaktif": ("baik", "<b>Formulir dinonaktifkan.</b> Sudah dipakai pradaftar, "
                                  "jadi tidak dihapus; pradaftar baru tidak lagi memakainya."),
    "catatan_koreksi": ("baik", "<b>Catatan koreksi disimpan.</b> Pemeriksaan yang sudah "
                                "tersimpan tidak ikut berubah."),
    "catatan_koreksi_hapus": ("baik", "<b>Catatan koreksi dihapus dari daftar.</b>"),
    "kecamatan": ("baik", "<b>Kecamatan disimpan.</b>"),
    "kecamatan_ada": ("galat", "<b>Nama kecamatan itu sudah ada.</b>"),
    "kecamatan_hapus": ("baik", "<b>Kecamatan dihapus.</b>"),
    "kecamatan_isi": ("galat", "<b>Tidak bisa dihapus.</b> Masih ada desa/kelurahan di "
                               "kecamatan ini. Pindahkan atau hapus desanya dulu."),
    "desa": ("baik", "<b>Desa/kelurahan disimpan.</b>"),
    "desa_ada": ("galat", "<b>Nama itu sudah ada</b> di kecamatan yang sama."),
    "desa_hapus": ("baik", "<b>Desa/kelurahan dihapus.</b>"),
    "desa_dipakai": ("galat", "<b>Tidak bisa dihapus.</b> Letak tanah pada berkas yang sudah "
                              "ada masih menunjuk ke sini."),
    "pejabat": ("baik", "<b>Kepala desa/lurah disimpan.</b>"),
    "pejabat_aktif": ("baik", "<b>Pejabat yang menjabat diganti.</b> Dokumen yang dicetak "
                              "setelah ini memakai nama yang baru."),
    "pejabat_hapus": ("baik", "<b>Pejabat dihapus dari riwayat.</b>"),
    "wilayah_selaras": ("baik", "<b>Daftar Kemendagri dimuat.</b>"),
    "wilayah_lengkap": ("baik", "<b>Sudah lengkap.</b> Semua kecamatan dan desa menurut "
                                "Kemendagri sudah ada."),
    "panitia": ("baik", "<b>Susunan Panitia A disimpan.</b>"),
    "panitia_hapus": ("baik", "<b>Susunan Panitia A dihapus.</b>"),
    "panitia_dipakai": ("galat", "<b>Tidak bisa dihapus.</b> Susunan ini masih dipakai "
                                 "berkas yang sudah ada. Hapus dulu rujukannya, atau biarkan "
                                 "sebagai arsip."),
    "panitia_salin": ("baik", "<b>Susunan disalin.</b> Ubah nomor SK dan anggotanya "
                              "seperlunya."),
    "anggota": ("baik", "<b>Anggota panitia disimpan.</b>"),
    "anggota_hapus": ("baik", "<b>Anggota panitia dihapus.</b>"),
    "template": ("baik", "<b>Template diganti.</b> Yang lama tersimpan sebagai cadangan."),
    "template_pulih": ("baik", "<b>Template dikembalikan</b> dari cadangan."),
    "galat_cetak": ("galat", "<b>Dokumen tidak bisa dicetak</b> karena masih ada kesalahan."),
    "bersih": ("baik", "<b>Penyimpanan dirapikan.</b>"),
    "bersih_kosong": ("baik", "<b>Tidak ada yang perlu dibuang.</b> Penyimpanannya "
                              "sudah rapi."),
}

# Batas aman teks kabar yang datang dari alamat, supaya tidak ada yang
# menjejalkan satu halaman penuh ke dalam bilah kabar.
MAKS_TEKS = 400


def pesan():
    """Kabar untuk halaman ini, dibaca dari query. None kalau tidak ada.

    Kembaliannya (jenis, teks-html) — sama seperti isi PESAN, karena web.py
    memperlakukan keduanya sama.
    """
    teks = request.args.get("galat")
    if teks:
        return ("galat", html.escape(teks[:MAKS_TEKS]))
    teks = request.args.get("baik")         # kabar berhasil yang memuat angka
    if teks:
        return ("baik", html.escape(teks[:MAKS_TEKS]))
    return PESAN.get(request.args.get("pesan"))


def buka():
    """Kunci kartu lipat yang diminta terbuka lewat ?buka= — jalur tanpa JavaScript."""
    return [b for b in request.args.getlist("buka") if b][:8]


def ke(alamat, tanya):
    """Sisipkan kabar ke alamat tujuan, di belakang query tapi di depan #jangkar."""
    jalan, _, jangkar = alamat.partition("#")
    jalan += ("&" if "?" in jalan else "?") + tanya
    return jalan + ("#" + jangkar if jangkar else "")
