# -*- coding: utf-8 -*-
"""File unggahan (PDF/JPG/PNG) -> teks per halaman, dan gambar satu halaman.

PDF yang punya lapisan teks dibaca langsung lewat pypdfium2. Halaman tanpa
teks (hasil scan) dan foto dibaca RapidOCR — model PaddleOCR yang dijalankan
onnxruntime di CPU, tanpa internet dan tanpa GPU.

Kedua paket itu opsional, seperti Pillow di foto.py: tanpa keduanya aplikasi
tetap jalan, hanya fitur unggah dokumen yang menampilkan PESAN_PASANG.
"""
import io
import logging
import threading
from dataclasses import dataclass

try:
    import pypdfium2 as pdfium
except ImportError:                     # pragma: no cover - paket opsional
    pdfium = None
try:
    from rapidocr import RapidOCR
except ImportError:                     # pragma: no cover - paket opsional
    RapidOCR = None
try:
    from PIL import Image, ImageOps
except ImportError:                     # pragma: no cover - Pillow tidak wajib
    Image = None

log = logging.getLogger(__name__)

TERSEDIA = pdfium is not None and RapidOCR is not None and Image is not None
PESAN_PASANG = ("Fitur unggah dokumen perlu paket tambahan: "
                "python -m pip install -r requirements.txt")

BATAS_BITA = 20 * 1024 * 1024
BATAS_HALAMAN = 30
DPI_OCR = 300
MIN_TEKS = 20          # karakter non-spasi; kurang dari ini dianggap halaman gambar


class GalatBaca(Exception):
    """File tidak bisa dibaca. Pesannya siap ditampilkan ke petugas."""


@dataclass
class Halaman:
    no: int
    teks: str
    gagal: bool = False


_mesin = None
_kunci = threading.Lock()
# PDFium tidak aman dipakai beberapa utas sekaligus, bahkan untuk dokumen yang
# berbeda (dokumentasi pypdfium2), sedangkan waitress melayani beberapa
# permintaan bersamaan. Semua panggilan PDFium lewat kunci ini, dipegang per
# halaman supaya OCR berkas tebal tidak menahan permintaan gambar orang lain.
_KUNCI_PDF = threading.Lock()
MAKS_PIKSEL = 40_000_000     # ±A3 pada 300 dpi; halaman lebih besar diturunkan resolusinya


def _skala(lebar_pt, tinggi_pt, dpi=DPI_OCR):
    """Skala render PDF: dpi/72, diturunkan bila hasilnya melebihi MAKS_PIKSEL
    (peta A0 pada 300 dpi butuh lebih dari 1 GB memori)."""
    s = dpi / 72
    piksel = lebar_pt * s * tinggi_pt * s
    if piksel > MAKS_PIKSEL:
        s *= (MAKS_PIKSEL / piksel) ** 0.5
    return s


def _ocr(gambar):
    """Teks satu gambar PIL, baris demi baris dari atas ke bawah."""
    global _mesin
    with _kunci:
        if _mesin is None:
            _mesin = RapidOCR()
            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        hasil = _mesin(gambar)
    if hasil.txts is None:
        return ""
    return _susun_baris(hasil.boxes, hasil.txts)


def _susun_baris(kotak, teks):
    """Potongan teks OCR -> baris. Kotak yang titik tengah tegaknya berdekatan
    (kurang dari setengah tinggi kotak) dianggap satu baris, diurut kiri-kanan."""
    potongan = []
    for k, t in zip(kotak, teks):
        ys = [float(p[1]) for p in k]
        potongan.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), float(k[0][0]), t))
    potongan.sort()
    baris, kini, y_kini = [], [], None
    for y, tinggi, x, t in potongan:
        if kini and abs(y - y_kini) > max(tinggi, 1) / 2:
            baris.append(kini)
            kini = []
        if not kini:
            y_kini = y
        kini.append((x, t))
    if kini:
        baris.append(kini)
    return "\n".join(" ".join(t for _, t in sorted(b)) for b in baris)


def _jenis(isi):
    if isi.startswith(b"%PDF"):
        return "pdf"
    if isi.startswith(b"\x89PNG"):
        return "png"
    if isi.startswith(b"\xff\xd8"):
        return "jpg"
    return None


def _periksa(nama, isi):
    if len(isi) > BATAS_BITA:
        raise GalatBaca(f"{nama}: lebih dari {BATAS_BITA // (1024 * 1024)} MB.")
    jenis = _jenis(isi)
    if jenis is None:
        raise GalatBaca(f"{nama}: bukan PDF, JPG, atau PNG.")
    if jenis == "pdf" and pdfium is None:
        raise GalatBaca(PESAN_PASANG)
    if jenis != "pdf" and Image is None:
        raise GalatBaca(PESAN_PASANG)
    return jenis


def _buka_pdf(nama, isi):
    try:
        dok = pdfium.PdfDocument(isi)
    except pdfium.PdfiumError as g:
        raise GalatBaca(f"{nama}: PDF rusak atau terkunci sandi.") from g
    if len(dok) > BATAS_HALAMAN:
        n = len(dok)
        dok.close()
        raise GalatBaca(f"{nama}: {n} halaman, paling banyak {BATAS_HALAMAN} per file. "
                        "Pecah dulu PDF-nya.")
    return dok


def _buka_gambar(nama, isi):
    try:
        g = Image.open(io.BytesIO(isi))
        g.load()
        return ImageOps.exif_transpose(g).convert("RGB")
    except Exception as e:                                         # noqa: BLE001
        raise GalatBaca(f"{nama}: gambar rusak.") from e


def _baca_gambar(no, gambar):
    if RapidOCR is None:
        return Halaman(no, "", gagal=True)
    try:
        return Halaman(no, _ocr(gambar))
    except Exception:                                              # noqa: BLE001
        log.exception("OCR halaman %s gagal", no)
        return Halaman(no, "", gagal=True)


def baca(nama, isi):
    """Teks tiap halaman. GalatBaca untuk file yang tidak bisa dibaca sama sekali;
    halaman yang OCR-nya gagal dikembalikan dengan gagal=True."""
    jenis = _periksa(nama, isi)
    if jenis != "pdf":
        return [_baca_gambar(1, _buka_gambar(nama, isi))]
    with _KUNCI_PDF:
        dok = _buka_pdf(nama, isi)
        n = len(dok)
    try:
        hasil = []
        for i in range(n):
            # Satu halaman rusak (atau kehabisan memori) tidak menggagalkan
            # halaman lain: halaman itu saja yang "tidak terbaca".
            try:
                with _KUNCI_PDF:
                    hal = dok[i]
                    teks = hal.get_textpage().get_text_range()
                    gambar_hal = None
                    if len("".join(teks.split())) < MIN_TEKS:
                        gambar_hal = hal.render(scale=_skala(*hal.get_size())).to_pil().convert("RGB")
            except Exception:                                      # noqa: BLE001
                log.exception("Halaman %s dari %s tidak bisa dibaca PDFium", i + 1, nama)
                hasil.append(Halaman(i + 1, "", gagal=True))
                continue
            if gambar_hal is None:
                hasil.append(Halaman(i + 1, teks.replace("\r\n", "\n").replace("\r", "\n")))
            else:
                hasil.append(_baca_gambar(i + 1, gambar_hal))      # OCR di luar kunci PDFium
        return hasil
    finally:
        with _KUNCI_PDF:
            dok.close()


def gambar(nama, isi, no, lebar=900):
    """PNG satu halaman (no mulai 1), dikecilkan selebar `lebar` piksel."""
    jenis = _periksa(nama, isi)
    if jenis == "pdf":
        with _KUNCI_PDF:
            dok = _buka_pdf(nama, isi)
            try:
                if not 1 <= no <= len(dok):
                    raise GalatBaca(f"{nama}: tidak ada halaman {no}.")
                hal = dok[no - 1]
                g = hal.render(scale=lebar / hal.get_width()).to_pil().convert("RGB")
            except pdfium.PdfiumError as e:
                raise GalatBaca(f"{nama}: halaman {no} tidak bisa digambar.") from e
            finally:
                dok.close()
    else:
        g = _buka_gambar(nama, isi)
        if g.width > lebar:
            g = g.resize((lebar, round(g.height * lebar / g.width)))
    keluar = io.BytesIO()
    g.save(keluar, "PNG", optimize=True)
    return keluar.getvalue()
