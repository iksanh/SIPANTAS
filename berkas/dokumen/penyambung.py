# -*- coding: utf-8 -*-
"""Kata penyambung di pojok kanan bawah halaman.

Tata naskah dinas menuliskan kata pertama halaman berikutnya di kanan bawah halaman
sebelumnya - misalnya "KELIMA…" - supaya pembaca tahu lembarannya belum habis dan
tidak ada halaman yang hilang.

Letak pergantian halaman baru diketahui setelah dokumen ditata, dan yang bisa
menatanya hanya pengolah kata. Jadi langkah ini dikerjakan Microsoft Word sesudah
DOCX-nya dirakit: Word yang menghitung halaman, kata penyambungnya ditaruh sebagai
kotak teks mengambang satu baris di bawah baris terakhir halaman itu, sehingga tidak
ada satu baris pun yang bergeser dan jumlah halamannya tetap.

Tanpa Word di komputer ini (mis. hanya ada LibreOffice) langkah ini dilewati -
dokumennya tetap terbit, hanya tanpa kata penyambung.
"""
import os

from . import pdf

# Konstanta Word yang dipakai, ditulis apa adanya supaya tidak perlu pustaka konstanta.
_GOTO_HALAMAN, _GOTO_MUTLAK = 1, 1
_HITUNG_HALAMAN = 2                  # wdStatisticPages
_TEKS_MENDATAR = 1                   # msoTextOrientationHorizontal
_RATA_KANAN = 2                      # wdAlignParagraphRight
_TANPA_LIPATAN = 3                   # wdWrapNone
_RELATIF_HALAMAN = 1                 # wdRelative(Horizontal|Vertical)PositionPage
_POSISI_VERTIKAL = 6                 # wdVerticalPositionRelativeToPage

NAMA_KOTAK = "penyambung"            # penanda kotak buatan kita, supaya bisa dibarui
LEBAR = 190.0                        # titik (± 6,7 cm), cukup untuk satu kata panjang
TINGGI = 16.0
JARAK = 2.0                          # turun sedikit dari baris terakhir
TINGGI_BARIS = 1.25                  # perkiraan tinggi satu baris terhadap besar huruf


class TidakAdaWord(RuntimeError):
    """Microsoft Word tidak ada di komputer ini."""


def tersedia():
    return pdf.mesin_tersedia() == "Microsoft Word"


def _nomor_daftar(dok, mulai):
    """Nomor daftar yang tercetak di awal halaman, mis. "7." atau "b.".

    Penomoran otomatis Word bukan bagian dari teks paragraf, jadi harus diambil
    sendiri - tanpa ini kata penyambungnya berbunyi "Peraturan…" padahal yang
    tercetak di halaman berikutnya "7. Peraturan …". Hanya dipakai bila halamannya
    memang dimulai dari paragraf itu: kalau paragrafnya sudah mulai di halaman
    sebelumnya, nomornya pun tercetak di sana.
    """
    try:
        par = dok.Range(mulai, mulai).Paragraphs(1)
        if par.Range.Start != mulai or not par.Range.ListFormat.ListType:
            return ""
        nomor = (par.Range.ListFormat.ListString or "").strip()
        # daftar berbutir (•) tidak menambah keterangan apa pun, dan lambangnya
        # berasal dari huruf Symbol - kalau ikut ditulis hasilnya kotak kosong
        return nomor if any(x.isalnum() for x in nomor) else ""
    except Exception:                                              # noqa: BLE001
        return ""


def _kata_pertama(dok, mulai):
    """Kata pertama yang tercetak mulai dari posisi `mulai`, lengkap nomor daftarnya."""
    r = dok.Range(mulai, min(mulai + 400, dok.Content.End))
    teks = (r.Text or "").replace("\x07", " ").replace("\v", " ")
    kata = ""
    for potong in teks.split():
        if potong.strip():
            kata = potong.strip()
            break
    if not kata:
        return ""
    nomor = _nomor_daftar(dok, mulai)
    return f"{nomor} {kata}" if nomor else kata


def _bersihkan(dok):
    """Buang kata penyambung dari perakitan sebelumnya."""
    for i in range(dok.Shapes.Count, 0, -1):
        s = dok.Shapes(i)
        try:
            nama = s.Name or ""
        except Exception:                                          # noqa: BLE001
            continue
        if nama.startswith(NAMA_KOTAK):
            s.Delete()


def _atas(dok, akhir, ukuran, font_ukuran):
    """Posisi tegak kata penyambung: tepat di bawah baris terakhir halaman itu.

    Halaman yang teksnya berhenti lebih awal - karena paragraf berikutnya tidak
    muat lagi - kata penyambungnya ikut naik, jadi tidak ada halaman yang
    penyambungnya menggantung sendirian jauh di bawah baris terakhir.
    """
    bawah = ukuran["tinggi"] - ukuran["bawah"] + JARAK          # batas bidang cetak
    try:
        y = float(akhir.Information(_POSISI_VERTIKAL))
    except Exception:                                              # noqa: BLE001
        return bawah
    if y <= 0:                                                  # Word tidak tahu posisinya
        return bawah
    return min(y + (font_ukuran or 11) * TINGGI_BARIS + JARAK, bawah)


def _tulis(dok, hal, teks, ukuran, atas, font_nama, font_ukuran):
    """Satu kotak teks di kanan bawah halaman `hal`."""
    awal = dok.GoTo(_GOTO_HALAMAN, _GOTO_MUTLAK, hal)
    jangkar = dok.Range(awal.Start, awal.Start)
    kotak = dok.Shapes.AddTextbox(_TEKS_MENDATAR, 0, 0, LEBAR, TINGGI, jangkar)
    kotak.Name = f"{NAMA_KOTAK}{hal}"
    kotak.Line.Visible = False
    kotak.Fill.Visible = False
    kotak.WrapFormat.Type = _TANPA_LIPATAN
    kotak.RelativeHorizontalPosition = _RELATIF_HALAMAN
    kotak.RelativeVerticalPosition = _RELATIF_HALAMAN
    kotak.Left = ukuran["lebar"] - ukuran["kanan"] - LEBAR
    kotak.Top = atas
    bingkai = kotak.TextFrame
    bingkai.MarginLeft = bingkai.MarginRight = 0
    bingkai.MarginTop = bingkai.MarginBottom = 0
    isi = bingkai.TextRange
    isi.Text = teks
    isi.ParagraphFormat.Alignment = _RATA_KANAN
    isi.ParagraphFormat.SpaceBefore = 0
    isi.ParagraphFormat.SpaceAfter = 0
    if font_nama:
        isi.Font.Name = font_nama
    if font_ukuran:
        isi.Font.Size = font_ukuran


def tambahkan(jalur_docx, sisipan="…"):
    """Tulis kata penyambung di setiap halaman kecuali halaman terakhir.

    Kembalikan jumlah kata penyambung yang ditulis.
    """
    if not os.path.isfile(jalur_docx):
        raise FileNotFoundError(jalur_docx)
    if not tersedia():
        raise TidakAdaWord(
            "Kata penyambung memerlukan Microsoft Word di komputer ini.")

    import pythoncom
    import win32com.client

    with pdf.KUNCI_WORD:
        pythoncom.CoInitialize()
        word = None
        jumlah = 0
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            dok = word.Documents.Open(os.path.abspath(jalur_docx),
                                      AddToRecentFiles=False, Visible=False)
            try:
                _bersihkan(dok)
                dok.Repaginate()
                halaman = int(dok.ComputeStatistics(_HITUNG_HALAMAN))
                tata = dok.Sections(1).PageSetup
                ukuran = {"lebar": tata.PageWidth, "tinggi": tata.PageHeight,
                          "kanan": tata.RightMargin, "bawah": tata.BottomMargin}
                for hal in range(1, halaman):
                    mulai = dok.GoTo(_GOTO_HALAMAN, _GOTO_MUTLAK, hal + 1).Start
                    kata = _kata_pertama(dok, mulai)
                    if not kata:                       # halaman berikutnya kosong
                        continue
                    # huruf terakhir halaman ini: menentukan besar huruf sekaligus
                    # sampai di mana barisnya turun
                    akhir = dok.Range(max(mulai - 1, 0), mulai)
                    huruf = akhir.Font
                    besar = huruf.Size if huruf.Size and huruf.Size > 0 else None
                    _tulis(dok, hal, kata + sisipan, ukuran,
                           _atas(dok, akhir, ukuran, besar), huruf.Name, besar)
                    jumlah += 1
                dok.Save()
            finally:
                dok.Close(SaveChanges=0)
        finally:
            if word is not None:
                try:
                    word.Quit()
                except Exception:                                  # noqa: BLE001
                    pass
            pythoncom.CoUninitialize()
    return jumlah


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(tambahkan(sys.argv[1]), "kata penyambung ditulis")
    else:
        print("Word tersedia:", tersedia())
