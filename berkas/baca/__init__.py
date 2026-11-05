# -*- coding: utf-8 -*-
"""Membaca dokumen unggahan: teks per halaman, tebakan jenis, dan penguraian.

    ocr.py      file PDF/gambar -> teks per halaman (dan gambar halaman)
    pilah.py    teks per halaman -> jenis dokumen, halaman sejenis digabung
    jenis/      pola pengenal dan pengurai, satu berkas per jenis
    periksa.py  pemeriksaan silang (NIK dengan tanggal lahir/jenis kelamin)
    ekstrak.py  jenis + teks -> usulan isian formulir

Tidak ada yang ditulis ke tabel berkas di sini; penyimpanan unggahan ada di
berkas/unggah.py, penerapan usulannya lewat tombol Simpan biasa.
"""
