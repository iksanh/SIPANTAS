# -*- coding: utf-8 -*-
"""SIPANTAS (Sistem Panitia A Terpadu) — penerbitan BAP, Risalah, dan SK Penetapan Hak.

Susunannya:

    jalur.py      letak tiap folder, dihitung sekali
    db.py         skema SQLite dan data referensi awal
    aplikasi.py   pabrik Flask; rutenya di rute/
    web.py        perakit HTML
    rute/         satu berkas per kelompok halaman
    dokumen/      perakitan DOKUMEN docx - tidak tahu soal HTTP
    perkakas/     skrip sekali jalan

Berkas ini sengaja dibiarkan kosong: perkakas baris perintah seperti
`python -m berkas.perkakas.siapkan_template` jadi tidak ikut menarik Flask.
Pabrik aplikasinya diambil dari berkas.aplikasi.
"""
