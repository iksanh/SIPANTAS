# -*- coding: utf-8 -*-
"""Bahan uji unggah dokumen: PDF dan gambar yang dirakit di dalam uji.

Tidak ada dokumen pemohon asli di sini. PDF-nya dirakit tangan (satu font
Helvetica, teks per baris) supaya uji tidak bergantung pada pustaka pembuat PDF.
"""
import io


def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_teks(halaman):
    """halaman: daftar teks (satu teks per halaman, baris dipisah \\n) -> bita PDF."""
    n = len(halaman)
    obj = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
           3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    anak = []
    for i, teks in enumerate(halaman):
        no_hal, no_isi = 4 + 2 * i, 5 + 2 * i
        anak.append(f"{no_hal} 0 R")
        baris = [f"({_esc(b)}) Tj T*" for b in teks.split("\n")]
        isi = ("BT /F1 14 Tf 16 TL 50 800 Td " + " ".join(baris) + " ET").encode("latin-1")
        obj[no_hal] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {no_isi} 0 R >>").encode()
        obj[no_isi] = b"<< /Length %d >>\nstream\n" % len(isi) + isi + b"\nendstream"
    obj[2] = f"<< /Type /Pages /Kids [{' '.join(anak)}] /Count {n} >>".encode()

    keluar = io.BytesIO()
    keluar.write(b"%PDF-1.4\n")
    letak = {}
    for no in sorted(obj):
        letak[no] = keluar.tell()
        keluar.write(b"%d 0 obj\n" % no + obj[no] + b"\nendobj\n")
    xref = keluar.tell()
    jumlah = max(obj) + 1
    keluar.write(b"xref\n0 %d\n0000000000 65535 f \n" % jumlah)
    for no in range(1, jumlah):
        keluar.write(b"%010d 00000 n \n" % letak[no])
    keluar.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (jumlah, xref))
    return keluar.getvalue()


def png_teks(teks, ukuran=(1200, 400), huruf=64):
    """Gambar PNG putih bertulisan hitam (tiap baris teks satu baris gambar)."""
    from PIL import Image, ImageDraw, ImageFont
    gambar = Image.new("RGB", ukuran, "white")
    gores = ImageDraw.Draw(gambar)
    f = ImageFont.load_default(size=huruf)
    for i, b in enumerate(teks.split("\n")):
        gores.text((40, 40 + i * int(huruf * 1.4)), b, fill="black", font=f)
    keluar = io.BytesIO()
    gambar.save(keluar, "PNG")
    return keluar.getvalue()
