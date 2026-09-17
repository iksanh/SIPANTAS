# -*- coding: utf-8 -*-
"""Ubah DOCX menjadi PDF untuk pratinjau.

Dua mesin, dicoba berurutan:
  1. Microsoft Word lewat COM  - hasilnya sama persis dengan "Save as PDF" di Word
  2. LibreOffice headless      - bila Word tidak ada di komputer ini

Hasil konversi disimpan di folder `pratinjau/` dan dipakai ulang selama DOCX-nya
belum berubah, sehingga membuka pratinjau kedua kali langsung tampil.
"""
import os
import subprocess
import sys
import threading

import pemeliharaan

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_PRATINJAU = os.path.join(DIR, "pratinjau")

# Word tidak aman dipakai dua permintaan sekaligus - antrekan. Dipakai bersama oleh
# modul lain yang juga menyetir Word (lihat penyambung.py).
KUNCI_WORD = threading.Lock()

_LOKASI_LIBREOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/usr/bin/libreoffice",
]


class TidakAdaMesin(RuntimeError):
    """Tidak ada Word maupun LibreOffice di komputer ini."""


def _libreoffice():
    for j in _LOKASI_LIBREOFFICE:
        if os.path.exists(j):
            return j
    return None


def mesin_tersedia():
    """Kembalikan nama mesin yang bisa dipakai, atau None."""
    if sys.platform == "win32":
        try:
            import win32com.client  # noqa: F401
            import winreg
            winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application")
            return "Microsoft Word"
        except Exception:                                          # noqa: BLE001
            pass
    if _libreoffice():
        return "LibreOffice"
    return None


def _via_word(sumber, tujuan):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    word = None
    try:
        # DispatchEx: instance terpisah, tidak mengganggu Word yang sedang dibuka pengguna
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        dok = word.Documents.Open(sumber, ReadOnly=True, AddToRecentFiles=False,
                                  Visible=False)
        try:
            dok.ExportAsFixedFormat(OutputFileName=tujuan, ExportFormat=17,
                                    OpenAfterExport=False, OptimizeFor=0,
                                    CreateBookmarks=0, DocStructureTags=True)
        finally:
            dok.Close(SaveChanges=0)
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:                                      # noqa: BLE001
                pass
        pythoncom.CoUninitialize()


def _via_libreoffice(sumber, tujuan):
    exe = _libreoffice()
    keluaran = os.path.dirname(tujuan)
    subprocess.run([exe, "--headless", "--norestore", "--convert-to", "pdf",
                    "--outdir", keluaran, sumber],
                   check=True, timeout=180,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bawaan = os.path.join(keluaran, os.path.splitext(os.path.basename(sumber))[0] + ".pdf")
    if bawaan != tujuan and os.path.exists(bawaan):
        os.replace(bawaan, tujuan)


def ke_pdf(jalur_docx, paksa=False):
    """Kembalikan jalur PDF dari `jalur_docx`. Konversi dilewati bila PDF masih baru."""
    if not os.path.isfile(jalur_docx):
        raise FileNotFoundError(jalur_docx)
    os.makedirs(DIR_PRATINJAU, exist_ok=True)
    nama = os.path.splitext(os.path.basename(jalur_docx))[0] + ".pdf"
    tujuan = os.path.join(DIR_PRATINJAU, nama)

    if not paksa and os.path.exists(tujuan) and \
            os.path.getmtime(tujuan) >= os.path.getmtime(jalur_docx):
        return tujuan

    mesin = mesin_tersedia()
    if mesin is None:
        raise TidakAdaMesin(
            "Pratinjau PDF memerlukan Microsoft Word atau LibreOffice di komputer ini. "
            "Dokumen DOCX-nya tetap bisa diunduh dan dibuka seperti biasa.")

    with KUNCI_WORD:
        # periksa lagi: mungkin permintaan lain sudah selesai saat menunggu antrean
        if not paksa and os.path.exists(tujuan) and \
                os.path.getmtime(tujuan) >= os.path.getmtime(jalur_docx):
            return tujuan
        sementara = tujuan + ".tmp.pdf"
        for j in (sementara, tujuan):
            if os.path.exists(j):
                try:
                    os.remove(j)
                except OSError:
                    pass
        if mesin == "Microsoft Word":
            _via_word(os.path.abspath(jalur_docx), os.path.abspath(sementara))
        else:
            _via_libreoffice(os.path.abspath(jalur_docx), os.path.abspath(sementara))
        if not os.path.exists(sementara):
            raise RuntimeError(f"{mesin} tidak menghasilkan berkas PDF.")
        os.replace(sementara, tujuan)
    # singgahan tidak boleh menumpuk terus: sisakan yang terbaru saja
    pemeliharaan.bersihkan_pratinjau()
    return tujuan


if __name__ == "__main__":
    print("Mesin tersedia:", mesin_tersedia() or "tidak ada")
    if len(sys.argv) > 1:
        print("->", ke_pdf(sys.argv[1], paksa=True))
