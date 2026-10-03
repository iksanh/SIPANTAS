# -*- coding: utf-8 -*-
"""Menjalankan aplikasi Flask dengan waitress.

    python jalankan.py            buka di komputer ini saja
    python jalankan.py 8000 0.0.0.0   bisa dibuka dari perangkat sejaringan

Bisa juga lewat lingkungan: PORTA=8000 ALAMAT=0.0.0.0

Waitress dipakai sejak di meja sendiri, bukan cuma di server, supaya yang
diuji sehari-hari sama persis dengan yang dipakai di production. Server
bawaan Flask sengaja tidak dipakai.
"""
import os
import sys
import threading
import webbrowser

from waitress import serve

from berkas import db, pemeliharaan
from berkas.aplikasi import buat_aplikasi
from berkas.dokumen import pdf, terbitkan

# Sepuluh pengguna, satu proses. Utasnya dilebihkan sedikit karena mencetak
# DOCX/PDF menahan satu utas beberapa detik.
UTAS = int(os.environ.get("UTAS", 8))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORTA", 8000))
    alamat = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ALAMAT", "127.0.0.1")
    sendiri = alamat in ("127.0.0.1", "localhost")

    k = db.siapkan()
    jumlah = k.execute("SELECT COUNT(*) FROM berkas").fetchone()[0]
    k.close()
    # hanya singgahan yang dipangkas sendiri; cadangan basis data menunggu perintah
    pemeliharaan.bersihkan_pratinjau()
    if not os.path.exists(os.path.join(terbitkan.DIR_TEMPLATE, "sk.docx")):
        print("  ! Template belum dibuat. Jalankan dulu: python siapkan_template.py")
    if not os.environ.get("KUNCI_RAHASIA"):
        print("  ! KUNCI_RAHASIA belum disetel - dibuatkan acak tiap kali mulai.")

    print(f"""
  SIPANTAS
  ------------------------------------------------
  Alamat    : http://{"localhost" if sendiri else alamat}:{port}
  Basis data: {db.BERKAS_DB}
  Berkas    : {jumlah}
  Keluaran  : {terbitkan.DIR_KELUARAN}
  PDF       : {pdf.mesin_tersedia() or "tidak tersedia (perlu Word / LibreOffice)"}
  Server    : waitress, {UTAS} utas

  Tekan Ctrl+C untuk berhenti.
""")

    if sendiri:
        # Dibuka setelah waitress sempat mengikat porta, supaya tab pertamanya
        # tidak mendarat di "tidak bisa dihubungi".
        threading.Timer(1.0, _buka, (port,)).start()
    try:
        serve(buat_aplikasi(), host=alamat, port=port, threads=UTAS,
              ident="SIPANTAS")
    except KeyboardInterrupt:
        print("\n  Berhenti.")


def _buka(port):
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:                                                 # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
