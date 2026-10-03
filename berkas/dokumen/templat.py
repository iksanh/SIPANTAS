# -*- coding: utf-8 -*-
"""Pengelolaan berkas template DOCX: unduh, unggah, cadangkan, pulihkan.

Alur yang dipakai petugas:

    1. Unduh template dari halaman Template.
    2. Sunting di Microsoft Word seperti dokumen biasa - penanda {{...}}
       adalah teks biasa, boleh dipindah, dihapus, atau ditambah.
    3. Unggah lagi. Template lama otomatis disalin ke `templates/cadangan/`
       sebelum ditimpa, jadi selalu bisa dikembalikan.

Berbeda dengan `siapkan_template.py` yang membangun ulang template dari dokumen
ber-MERGEFIELD di folder `RAHMA WONTOGIA`. Yang itu dipakai kalau tata naskahnya
dirombak dari sumber aslinya; yang ini untuk perubahan sehari-hari.
"""
import datetime as dt
import io
import os
import re
import shutil
import zipfile

from . import docxgen
from .. import jalur

DIR_TEMPLATE = jalur.TEMPLATE
DIR_CADANGAN = jalur.CADANGAN

# Tiga dokumen x satu set template per tata naskah. Set baku dipakai Hak Milik dan
# hak-hak lain; set 'wakaf' dipakai berkas yang jenis haknya memilih varian itu di
# Data referensi -> Matriks jenis hak. Set baru cukup ditambahkan di sini.
DOKUMEN = {
    "bap": ("BAP", "Berita Acara Pemeriksaan Lapang"),
    "risalah": ("Risalah", "Risalah Panitia Pemeriksaan Tanah A"),
    "sk": ("SK", "Surat Keputusan Penetapan Hak"),
}
VARIAN = {
    "": "Hak Milik & hak lainnya",
    "wakaf": "Hak Wakaf",
    # perorangan dan badan hukum dalam satu set; bagian yang berbeda bersyarat
    "hp": "Hak Pakai",
}
# Bukan tata naskah, jadi tidak ikut perkalian DOKUMEN x VARIAN di _susun_jenis.
VARIAN_LOKET = "loket"
NAMA_VARIAN = dict(VARIAN, **{VARIAN_LOKET: "Cetakan loket"})

# Cetakan loket punya sumbu varian sendiri — per formulir lampiran Permen
# (184 untuk Hak Milik), bukan per tata naskah (Hak Milik / wakaf) seperti
# ketiga dokumen di atas. Karena itu tidak ikut perkalian DOKUMEN x VARIAN.
KELENGKAPAN = {
    "checklist": ("Daftar Kelengkapan", "Formulir kelengkapan persyaratan di loket"),
    "pengembalian": ("Pengembalian Berkas", "Surat pengembalian berkas yang belum lengkap"),
}


def _susun_jenis():
    hasil = {}
    for varian, label_varian in VARIAN.items():
        for dok, (nama, uraian) in DOKUMEN.items():
            kunci = f"{dok}-{varian}" if varian else dok
            hasil[kunci] = (f"{nama} · {label_varian}", f"{kunci}.docx",
                            f"{uraian} — {label_varian}", dok, varian)
    for dok, (nama, uraian) in KELENGKAPAN.items():
        # varian "loket": bukan tata naskah Hak Milik maupun wakaf, melainkan
        # formulir loket yang berlaku untuk semua jenis hak. Halaman Template
        # memakainya untuk menaruhnya di tabnya sendiri.
        hasil[dok] = (nama, f"{dok}.docx", uraian, dok, VARIAN_LOKET)
    return hasil


# kunci -> (nama tampil, nama berkas, uraian, jenis dokumen, varian)
JENIS = _susun_jenis()


def kunci(jenis_dokumen, varian=""):
    """Kunci template untuk satu jenis dokumen pada satu varian tata naskah.

    Jatuh kembali ke set baku bila varian itu belum punya berkasnya sendiri, jadi
    menambah varian tidak mengharuskan ketiga dokumennya disalin sekaligus.
    """
    k = f"{jenis_dokumen}-{varian}" if varian else jenis_dokumen
    if k in JENIS and os.path.isfile(os.path.join(DIR_TEMPLATE, JENIS[k][1])):
        return k
    return jenis_dokumen


def kunci_kelengkapan(jenis_dokumen, varian=""):
    """Kunci template cetakan loket, dengan aturan jatuh-kembali yang sama.

    `varian` datang dari ref_kelengkapan.varian_template, jadi formulir jenis
    hak lain cukup menambah satu berkas checklist-<varian>.docx; selama belum
    ada, yang dipakai template bakunya.
    """
    k = f"{jenis_dokumen}-{varian}" if varian else jenis_dokumen
    if k in JENIS and os.path.isfile(os.path.join(DIR_TEMPLATE, JENIS[k][1])):
        return k
    return jenis_dokumen


MAKS_UKURAN = 30 * 1024 * 1024      # 30 MB - template BAP saja sudah 1,3 MB


class Ditolak(Exception):
    """Berkas yang diunggah tidak layak dipakai sebagai template."""


def jalur(jenis):
    return os.path.join(DIR_TEMPLATE, JENIS[jenis][1])


# ------------------------------------------------------------------ periksa
def _periksa(data, nama_asal):
    if not nama_asal.lower().endswith(".docx"):
        raise Ditolak("Yang diunggah harus berkas Word .docx. "
                      "Kalau berkasnya .doc, buka di Word lalu simpan sebagai .docx.")
    if not data:
        raise Ditolak("Berkasnya kosong.")
    if len(data) > MAKS_UKURAN:
        raise Ditolak(f"Berkasnya terlalu besar ({len(data) // 1024 // 1024} MB). "
                      f"Batasnya {MAKS_UKURAN // 1024 // 1024} MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise Ditolak("Isinya bukan dokumen Word.")
    except zipfile.BadZipFile:
        raise Ditolak("Berkasnya rusak atau bukan .docx yang sah.")
    try:
        return docxgen.daftar_penanda(io.BytesIO(data))
    except Exception as ex:                                        # noqa: BLE001
        raise Ditolak(f"Dokumennya tidak bisa dibaca python-docx: {ex}")


# -------------------------------------------------------------------- info
def penanda(jenis_atau_jalur):
    """Daftar penanda sebuah template: [(tipe, nama), ...]."""
    p = jalur(jenis_atau_jalur) if jenis_atau_jalur in JENIS else jenis_atau_jalur
    if not os.path.isfile(p):
        return []
    try:
        return docxgen.daftar_penanda(p)
    except Exception:                                              # noqa: BLE001
        return []


def info(jenis):
    p = jalur(jenis)
    nama, berkas, uraian, dokumen, varian = JENIS[jenis]
    d = {"jenis": jenis, "nama": nama, "berkas": berkas, "uraian": uraian,
         "dokumen": dokumen, "varian": varian, "varian_nama": NAMA_VARIAN.get(varian, varian),
         "jalur": p, "ada": os.path.isfile(p), "ukuran": 0, "diubah": "",
         "penanda": [], "cadangan": cadangan(jenis)}
    if d["ada"]:
        st = os.stat(p)
        d["ukuran"] = st.st_size
        d["diubah"] = dt.datetime.fromtimestamp(st.st_mtime).strftime("%d-%m-%Y %H:%M")
        d["penanda"] = penanda(jenis)
    return d


# --------------------------------------------------------------- cadangan
def cadangan(jenis):
    """Salinan lama, terbaru lebih dulu."""
    if not os.path.isdir(DIR_CADANGAN):
        return []
    hasil = []
    pola = re.compile(r"^" + re.escape(jenis) + r"-\d{8}-\d{6}(-\d+)?\.docx$")
    for nama in os.listdir(DIR_CADANGAN):
        if not pola.match(nama):
            continue
        p = os.path.join(DIR_CADANGAN, nama)
        st = os.stat(p)
        hasil.append({
            "nama": nama,
            "ukuran": st.st_size,
            "waktu": dt.datetime.fromtimestamp(st.st_mtime).strftime("%d-%m-%Y %H:%M"),
        })
    return sorted(hasil, key=lambda x: x["nama"], reverse=True)


def _cadangkan(jenis):
    p = jalur(jenis)
    if not os.path.isfile(p):
        return None
    os.makedirs(DIR_CADANGAN, exist_ok=True)
    cap = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tujuan = os.path.join(DIR_CADANGAN, f"{jenis}-{cap}.docx")
    urut = 1
    while os.path.exists(tujuan):          # dua penggantian dalam detik yang sama
        urut += 1
        tujuan = os.path.join(DIR_CADANGAN, f"{jenis}-{cap}-{urut}.docx")
    shutil.copy2(p, tujuan)
    _pangkas(jenis)
    return tujuan


def _pangkas(jenis, simpan=15):
    """Sisakan `simpan` cadangan terbaru saja, sisanya dibuang."""
    lama = cadangan(jenis)[simpan:]
    for c in lama:
        try:
            os.remove(os.path.join(DIR_CADANGAN, c["nama"]))
        except OSError:
            pass


# ---------------------------------------------------------------- simpan
def simpan(jenis, data, nama_asal):
    """Ganti template `jenis` dengan `data`. Template lama dicadangkan dulu.

    Mengembalikan (jalur_cadangan, daftar_penanda).
    """
    if jenis not in JENIS:
        raise Ditolak("Jenis template tidak dikenal.")
    tanda = _periksa(data, nama_asal)
    lama = _cadangkan(jenis)
    os.makedirs(DIR_TEMPLATE, exist_ok=True)
    sementara = jalur(jenis) + ".baru"
    with open(sementara, "wb") as fh:
        fh.write(data)
    os.replace(sementara, jalur(jenis))
    return lama, tanda


def pulihkan(jenis, nama):
    """Kembalikan template dari salinan `nama` di folder cadangan."""
    nama = os.path.basename(nama)
    if jenis not in JENIS or nama not in [c["nama"] for c in cadangan(jenis)]:
        raise Ditolak("Cadangan tidak cocok dengan jenis templatenya.")
    asal = os.path.join(DIR_CADANGAN, nama)
    if not os.path.isfile(asal):
        raise Ditolak("Cadangannya sudah tidak ada.")
    _cadangkan(jenis)                       # yang sekarang ikut disimpan dulu
    shutil.copy2(asal, jalur(jenis))
    return jalur(jenis)


# --------------------------------------------------------------- pemeriksa
def bandingkan(tanda, kunci):
    """Pisahkan penanda template menjadi yang dikenali konteks dan yang tidak.

    `kunci` adalah dict konteks contoh. Penanda berulang `{{*daftar.kolom}}`
    dicek nama daftarnya; kolomnya bebas karena berasal dari baris basis data.
    """
    dikenal, asing = [], []
    for tipe, nama in dict.fromkeys(tanda):        # unik, urutan tetap
        pokok = nama.split(".")[0]
        if tipe == "@":
            (dikenal if pokok in kunci or pokok == "foto" else asing).append((tipe, nama))
        elif pokok in kunci:
            dikenal.append((tipe, nama))
        else:
            asing.append((tipe, nama))
    return dikenal, asing


def uji_rakit(jenis, konteks_contoh):
    """Coba rakit template dengan konteks contoh. Mengembalikan pesan galat atau ''."""
    if not konteks_contoh:
        return ""
    import tempfile
    tujuan = os.path.join(tempfile.gettempdir(), f"uji-{jenis}.docx")
    try:
        docxgen.render(jalur(jenis), konteks_contoh, tujuan)
    except Exception as ex:                                        # noqa: BLE001
        return f"{type(ex).__name__}: {ex}"
    finally:
        try:
            os.remove(tujuan)
        except OSError:
            pass
    return ""
