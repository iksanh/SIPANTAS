# -*- coding: utf-8 -*-
"""Letak setiap folder, dihitung sekali di sini.

Dulu sembilan modul masing-masing memancangkan jalurnya sendiri dengan
`os.path.dirname(os.path.abspath(__file__))`. Begitu berkasnya dipindah ke
dalam paket, sembilan pancang itu ikut bergeser dan folder data dicari di
tempat yang salah. Sekarang hanya berkas ini yang tahu di mana AKAR berada;
yang lain tinggal membacanya.

AKAR adalah folder app/, yaitu induk dari paket ini — bukan folder paketnya.
Semua folder kerja (data, templates, keluaran) tetap di sana, di samping
jalankan.bat, supaya orang kantor masih bisa menemukannya.
"""
import os

# .../app/berkas/jalur.py -> .../app/berkas -> .../app
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folder di atas app/, tempat berkas Word dan Excel yang masih mentah.
# Dipakai perkakas impor dan penyiap template, bukan aplikasinya.
INDUK = os.path.dirname(AKAR)

DATA = os.path.join(AKAR, "data")
FOTO = os.path.join(DATA, "foto")
BASIS_DATA = os.path.join(DATA, "berkas.db")

TEMPLATE = os.path.join(AKAR, "templates")
CADANGAN = os.path.join(TEMPLATE, "cadangan")

KELUARAN = os.path.join(AKAR, "keluaran")
PRATINJAU = os.path.join(AKAR, "pratinjau")
STATIS = os.path.join(AKAR, "static")


def siapkan(*folder):
    """Buat folder kalau belum ada, lalu kembalikan jalurnya."""
    for f in folder:
        os.makedirs(f, exist_ok=True)
    return folder[0] if len(folder) == 1 else folder
