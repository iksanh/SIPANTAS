# -*- coding: utf-8 -*-
"""Perakitan dokumen: dari baris basis data sampai berkas DOCX yang siap cetak.

Urutannya: konteks menyusun nilai tiap penanda, docxgen merakitnya ke dalam
template, terbitkan memberi nomor dan menyimpan arsipnya. templat mengurus
template itu sendiri, foto mengurus lampiran, penyambung dan pdf memanggil
Word atau LibreOffice untuk yang tidak bisa dikerjakan python-docx.

Tidak ada satu pun modul di sini yang tahu soal HTTP.
"""
