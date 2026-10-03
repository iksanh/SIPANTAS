# -*- coding: utf-8 -*-
"""Titik masuk WSGI untuk server production.

    waitress-serve --listen=127.0.0.1:8000 wsgi:aplikasi     (Windows)
    gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 wsgi:aplikasi  (Linux)

Satu proses saja. SQLite tidak suka ditulisi banyak proses sekaligus, dan
untuk sepuluh pengguna satu proses dengan beberapa utas sudah lebih dari
cukup. Yang menaikkan jumlah utas, bukan jumlah pekerja.

Untuk menjalankan sehari-hari di komputer kantor, pakai jalankan.py yang
sekalian menyiapkan basis data dan membuka peramban.
"""
from berkas import db, pemeliharaan
from berkas.aplikasi import buat_aplikasi

db.siapkan().close()
pemeliharaan.bersihkan_pratinjau()

aplikasi = buat_aplikasi()
