# -*- coding: utf-8 -*-
"""Ubah dokumen Word ber-MERGEFIELD menjadi template sistem.

Dijalankan sekali (atau setiap kali tata naskah berubah):

    python siapkan_template.py

Tiga hal yang dikerjakan:
  1. Setiap MERGEFIELD diganti penanda {{...}} sesuai PEMETAAN.
  2. Slot berulang (Jenis_Alas_Hak_1..10, tambahan_surat_1..54, Surat_1..10)
     diciutkan jadi satu paragraf berulang - ini yang menghapus baris ";" menggantung.
  3. Nilai yang selama ini diketik tetap di dalam template (NIK, nomor SK, tahun,
     sapaan Sdr./Sdri., nama jenis hak) diubah jadi penanda.

Format aslinya tidak disentuh: kop, gaya huruf, penomoran, tabel, dan gambar tetap.
"""
import copy
import os
import re
import shutil

from docx import Document
from docx.oxml.ns import qn
from .. import jalur

DIR_TEMPLATE = jalur.TEMPLATE
DIR_INDUK = jalur.INDUK
SUMBER = os.path.join(DIR_INDUK, "RAHMA WONTOGIA")

# Satu set dokumen contoh per tata naskah. Keluarannya bernama `<jenis>-<varian>.docx`
# (varian kosong = set baku), sama dengan nama yang dicari templat.py dan terbitkan.py.
SET = {
    "": {
        "nama": "Hak Milik & hak lainnya",
        "dir": os.path.join(DIR_INDUK, "RAHMA WONTOGIA"),
        "asal": {
            "bap": "1. BAP RAHMA WANTOGIA.docx",
            "risalah": "2. RISALAH WANTOGIA.docx",
            "sk": "3. SK RAHMA WANTOGIA.docx",
        },
    },
    "wakaf": {
        "nama": "Hak Wakaf",
        "dir": os.path.join(DIR_INDUK, "wakaf"),
        "asal": {
            "bap": "1. BAP_3099.2025 awin m. talib.docx",
            "risalah": "2. RISALAH_3099 awin m. talib.docx",
            "sk": "3. KONSEP_3099 awin m.talib.docx",
        },
    },
}

ASAL = SET[""]["asal"]

# ------------------------------------------------------- pemetaan nama field
PEMETAAN = {
    "Atas_Nama": "nama_penerima",
    "Nama_Pemohon": "nama_pemohon",
    "Alamat": "alamat_penerima",
    "NIK": "nik_penerima",
    "TTL": "ttl_penerima",
    "Pekerjaan": "pekerjaan_penerima",
    "Jenis_Kelamin": "jenis_kelamin",
    "KTP_Sebelumnya": "pemilik_sebelumnya",
    "Pemilik_Sebelumnya_2": "pemilik_sebelumnya_2",

    "Desa__Kelurahan": "jenis_desa",
    "Desa": "nama_desa",
    "Kecamatan": "kecamatan",
    "Pejabat_Kelurahan_desa": "jabatan_pejabat",
    "Nama_Kepala_Desa": "nama_pejabat",

    "Nomor_PBT": "nomor_pbt",
    "Tgl_PBT": "tanggal_pbt",
    "NIB": "nib",
    "Luas": "luas_teks",
    "Luas_Text": "luas_terbilang",
    "Luas_Surat_tanah": "luas_surat_teks",
    "selisih_luas": "selisih_teks",
    "tgl_Peta_analisis": "tanggal_peta_analisis",

    "Penggunaan_Tanah": "penggunaan_sekarang",
    "rencana_penggunaan": "rencana_penggunaan",
    "RTRW": "rtrw",
    "Kesesuaian_penggunaan_tanah": "kesesuaian",
    "Penggunaan_Tanah_di_SK": "penggunaan_sk",
    "Batas_Utara": "batas_utara",
    "Batas_Timur": "batas_timur",
    "Batas_Selatan": "batas_selatan",
    "Batas_Barat": "batas_barat",

    "Surat_Penguasaan_Fisik": "penguasaan_fisik",
    "jenis_sppf": "sppf",
    "Validasi_pph": "validasi_pph",
    "surat_kuasa": "surat_kuasa",

    "Tgl_Surat_Permohonan": "tanggal_permohonan",
    "Tgl_BAP": "tgl_bap", "Tgl_BAP_1": "tgl_bap_pendek",
    "Hari_BAP": "hari_bap", "Tgl_BAP_Text": "tgl_bap_terbilang",
    "Bulan_BAP_Text": "bulan_bap",
    "No_Risalah": "nomor_risalah",
    "Tgl_Risalah": "tgl_risalah", "Tgl_Risalah_1": "tgl_risalah_pendek",
    "Hari_Risalah": "hari_risalah", "Tgl_Risalah_Text": "tgl_risalah_terbilang",
    "Bulan_Risalah_Text": "bulan_risalah",
    "No_SK": "nomor_sk", "Tgl_SK": "tgl_sk",
}

# Slot berulang: (pola nama field, nama daftar di konteks, kolom)
CIUTKAN = [
    (re.compile(r"^Jenis_Alas_Hak_\d+$", re.I), "riwayat", "uraian"),
    (re.compile(r"^jenis_alas_hak_\d+$"), "riwayat", "uraian"),
    (re.compile(r"^(Surat_\d+|tambahan_surat_\d+|surat_\d+)$"), "dokumen", "uraian"),
    (re.compile(r"^(Formulir_permohonan|Surat_Pernyataan.*|Surat_Keterangan.*|"
                r"surat_pemasangan_tanda_batas|surat_pernyataan_selisih_luas)$"), "dokumen", "uraian"),
]

# Pada berkas wakaf «KTP Sebelumnya» adalah Wakif, bukan bekas pemilik biasa.
PEMETAAN_VARIAN = {
    "wakaf": {"KTP_Sebelumnya": "nama_wakif"},
}

# Nilai yang selama ini di-hardcode -> jadi penanda. Ditulis eksplisit supaya bisa diperiksa.
GANTI_TEKS = {
    "bap": [
        (r"tahun dua ribu dua puluh enam", "tahun {{tahun_bap_terbilang}}"),
        (r"\bSdri\.\s*(?=\{\{nama_penerima\}\})", "{{sapaan}} "),
        (r"\bSdr\.\s*(?=\{\{nama_penerima\}\})", "{{sapaan}} "),
        (r"Ichsandy Masloman, S\.H\. NIP\. 197506212002121004", "{{kasi_pgt_nama}} NIP. {{kasi_pgt_nip}}"),
    ],
    "risalah": [
        (r"tahun dua ribu dua puluh enam", "tahun {{tahun_risalah_terbilang}}"),
        (r"\s*lebih tiga ratus empat puluh sembilan meter persegi\)", ""),
        (r"Nomor 02/SK-75\.03\.HP\.01/I/2026 Tanggal 01 Januari 2026",
         "Nomor {{panitia_nomor_sk}} Tanggal {{panitia_tanggal_sk}}"),
        (r"\b\d+\s*\(\s*[a-z]+\s*\)\s*orang anggota",
         "{{panitia_jumlah}} ({{panitia_jumlah_terbilang}}) orang anggota"),
        (r"Permohonan Hak Milik atas Nama", "Permohonan {{nama_hak}} atas Nama"),
        (r"Jenis hak\s*:\s*Hak Milik", "Jenis hak : {{nama_hak}}"),
    ],
    "sk": [
        (r"NIK\s*7503161510730001", "NIK {{nik_penerima}}"),
        (r"NOMOR\s*:\s*33/HM/BPN\.75\.03/XII/2025", "NOMOR : {{nomor_sk}}"),
        (r"pada tanggal\s+Agustus 2026", "pada tanggal {{tgl_sk}}"),
        (r"PEMBERIAN HAK MILIK", "PEMBERIAN {{nama_hak_kapital}}"),
        (r"\bHAK MILIK\b", "{{nama_hak_kapital}}"),
        (r"pemberian Hak Milik ini", "pemberian {{nama_hak}} ini"),
        (r"Pemberian Hak Milik sebagaimana", "Pemberian {{nama_hak}} sebagaimana"),
        (r"diberikan Hak Milik", "diberikan {{nama_hak}}"),
        (r"Sertipikat Hak Milik", "Sertipikat {{nama_hak}}"),
        (r"subjek Hak Milik", "subjek {{nama_hak}}"),
        (r"permohonan Hak Milik", "permohonan {{nama_hak}}"),
        (r"\(non pertanian\)", "({{rencana_penggunaan}})"),
        (r"untuk rumah tinggal \(", "untuk {{rencana_penggunaan}} ("),
        (r"ILKHAM MOODUTO, S\.H", "{{pejabat_nama}}"),
        (r"NIP\.\s*19821006 200604 1 002", "NIP. {{pejabat_nip}}"),
    ],
}

# Dokumen contoh wakaf dipakai apa adanya dari berkas yang sudah dicetak, jadi masih
# memuat nama panitia, nomor SK, dan sisa nama pemohon berkas lain. Semua itu diganti
# penanda di sini; kalimat tata naskahnya sendiri tidak disentuh.
GANTI_VARIAN = {
    "wakaf": {
        "bap": [
            (r"tahun dua ribu dua puluh (?:lima|enam)", "tahun {{tahun_bap_terbilang}}"),
        ],
        "risalah": [
            (r"tahun dua ribu dua puluh (?:lima|enam)", "tahun {{tahun_risalah_terbilang}}"),
            # nomor SK susunan panitia, baik di pembuka maupun di DASAR HUKUM
            (r"Nomor:?\s*[0-9][0-9.]*/SK-75\.03[^\s]*\s*Tanggal\s+\d{1,2}\s+\w+\s+\d{4}",
             "Nomor {{panitia_nomor_sk}} Tanggal {{panitia_tanggal_sk}}"),
            (r"\b\d+\s*\(\s*[a-z]+\s*\)\s*orang anggota",
             "{{panitia_jumlah}} ({{panitia_jumlah_terbilang}}) orang anggota"),
            # nama Nazhir yang diketik tetap -> penanda; daftar identitasnya
            # dirakit dari baris Nazhir berkasnya, bukan diketik ulang
            (r"Awin M\. Talib tempat tanggal lahir .*?(?=dan Undang-Undang Nomor 12)",
             "{{nazhir_uraian}} "),
            (r"sehingga Awin M\. Talib, Ahmad Oktaviani Salihi, Ridwan Salihi memenuhi",
             "sehingga {{nama_nazhir}} memenuhi"),
            # sisa nama pemohon berkas lain yang ikut tersalin
            (r"\s*Hasan Umar, Sulastri Sahrain, Hasfiyani, S\.T\s*", " "),
            (r"Fotokopi KTP Awin M Talib, Ahmad Oktoviani Salihi, Ridwan Salihi \(Nazhir\)",
             "Fotokopi KTP {{nama_nazhir}} (Nazhir)"),
            # penanda yang tersangkut di tengah kata / di depan baris tetap
            (r"B\{\{Jenis_Alas_Hak_4\}\}ahwa", "Bahwa"),
            (r"\{\{tambahan_surat_8\}\}(?=Asli Peta)", ""),
            # baris surat kuasa: di dokumen contoh masih menumpang slot tambahan
            (r"Asli \{\{tambahan_surat_2\}\}kaf", "{{?surat_kuasa}}Asli {{surat_kuasa}}"),
            (r"(?<=\{\{tambahan_surat_2\}\})kaf", ""),
            (r"Permohonan Hak Wakaf atas Nama", "Permohonan {{nama_hak}} atas Nama"),
            (r"Jenis hak\s*:\s*Hak Wakaf", "Jenis hak : {{nama_hak}}"),
        ],
        "sk": [
            (r"NOMOR\s*:\s*\d+/HW/BPN-?75\.03/[IVX]+/\d{4}", "NOMOR : {{nomor_sk}}"),
            (r"adalah Nazhir\s+perorangan", "adalah Nazhir {{bentuk_nazhir}}"),
            # huruf b dan c Menimbang: format Permen ATR/BPN 2/2017, disusun dari rincian
            (r"\{\{luas_teks\}\} yang diwakafkan Kepada", "{{luas_teks}}, yang diwakafkan kepada"),
            (r"sesuai \{\{Surat_3\}\}", "sesuai {{akta_ikrar_sk}}"),
            (r"telah disahkan oleh Pejabat Pembuat Akta Ikrar Wakaf tanggal .*?Nomor\s*:\s*"
             r"WT\.[^\s;]+", "telah disahkan {{pengesahan_nazhir_sk}}"),
            (r"NIB\.\s*3005150800476", "NIB. {{nib}}"),
            (r"dipergunakan untuk Masjid dengan Nazhir", 
             "dipergunakan untuk {{penggunaan_sekarang}} dengan Nazhir"),
            (r"atas tanah non pertanian seluas", "atas tanah {{rencana_penggunaan}} seluas"),
            (r"Nomor:?\s*[0-9][0-9.]*/SK-75\.03[^\s]*\s*Tanggal\s+\d{1,2}\s+\w+\s+\d{4}",
             "Nomor {{panitia_nomor_sk}} Tanggal {{panitia_tanggal_sk}}"),
            (r"ILKHAM MOODUTO, S\.H", "{{pejabat_nama}}"),
            (r"NIP\.\s*19821006 200604 1 002", "NIP. {{pejabat_nip}}"),
        ],
    },
}

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# --------------------------------------------------------------- utilitas
def _teks(p):
    return "".join(r.text for r in p.runs)


def _ganti_regex(p, pola, pengganti):
    """Ganti pola pada teks paragraf, tetap menjaga format run di sekitarnya."""
    runs = p.runs
    if not runs:
        return False
    teks = "".join(r.text for r in runs)
    cocok = list(re.finditer(pola, teks))
    if not cocok:
        return False
    peta = []
    for i, r in enumerate(runs):
        for j in range(len(r.text)):
            peta.append((i, j))
    isi = [r.text for r in runs]
    for m in reversed(cocok):
        a, b = m.start(), m.end()
        if a == b:
            continue
        baru = m.expand(pengganti) if "\\" in pengganti else pengganti
        ra, oa = peta[a]
        rb, ob = peta[b - 1]
        if ra == rb:
            isi[ra] = isi[ra][:oa] + baru + isi[ra][ob + 1:]
        else:
            isi[ra] = isi[ra][:oa] + baru
            for i in range(ra + 1, rb):
                isi[i] = ""
            isi[rb] = isi[rb][ob + 1:]
    for r, s in zip(runs, isi):
        r.text = s
    return True


def _semua_paragraf(wadah):
    for p in wadah.paragraphs:
        yield p
    for t in getattr(wadah, "tables", []):
        for baris in t.rows:
            for sel in baris.cells:
                for p in _semua_paragraf(sel):
                    yield p


# --------------------------------------------------- langkah 1: MERGEFIELD
def _bongkar_field(dok, varian=""):
    """Ubah setiap konstruksi field MERGEFIELD menjadi satu run berisi {{nama}}."""
    peta = dict(PEMETAAN, **PEMETAAN_VARIAN.get(varian, {}))
    jumlah = 0
    for p in _semua_paragraf(dok):
        el = p._p
        anak = list(el)
        i = 0
        while i < len(anak):
            r = anak[i]
            if r.tag != W + "r" or r.find(W + "fldChar") is None:
                i += 1
                continue
            fc = r.find(W + "fldChar")
            if fc.get(W + "fldCharType") != "begin":
                i += 1
                continue
            # kumpulkan sampai fldChar end
            j, instr, tingkat = i, [], 0
            while j < len(anak):
                rr = anak[j]
                f = rr.find(W + "fldChar") if rr.tag == W + "r" else None
                if f is not None:
                    t = f.get(W + "fldCharType")
                    if t == "begin":
                        tingkat += 1
                    elif t == "end":
                        tingkat -= 1
                        if tingkat == 0:
                            break
                it = rr.find(W + "instrText") if rr.tag == W + "r" else None
                if it is not None and it.text:
                    instr.append(it.text)
                j += 1
            kode = "".join(instr)
            m = re.search(r'MERGEFIELD\s+"?([A-Za-z0-9_]+)', kode)
            if m:
                asli = m.group(1)
                nama = peta.get(asli, asli)
                # simpan format dari run hasil bila ada, jika tidak dari run pertama
                contoh = None
                for k in range(i, j + 1):
                    if anak[k].tag == W + "r" and anak[k].find(W + "t") is not None:
                        contoh = anak[k]
                        break
                baru = contoh if contoh is not None else anak[i]
                import copy as _c
                baru = _c.deepcopy(baru)
                for tag in (W + "fldChar", W + "instrText"):
                    for e in baru.findall(tag):
                        baru.remove(e)
                for e in baru.findall(W + "t"):
                    baru.remove(e)
                t = baru.makeelement(W + "t", {})
                t.text = "{{" + nama + "}}"
                t.set(qn("xml:space"), "preserve")
                baru.append(t)
                el.insert(list(el).index(anak[i]), baru)
                for k in range(i, j + 1):
                    if anak[k].getparent() is not None:
                        el.remove(anak[k])
                jumlah += 1
                anak = list(el)
                i = 0
                continue
            i = j + 1
    return jumlah


# ------------------------------------------- langkah 2: ciutkan slot berulang
def _nama_penanda(p):
    return re.findall(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}", _teks(p))


def _cocok_grup(nama):
    for pola, daftar, kolom in CIUTKAN:
        if pola.match(nama):
            return daftar, kolom
    return None, None


def _ciutkan(dok):
    """Paragraf pertama tiap grup jadi paragraf berulang; sisanya dibuang."""
    sudah = set()
    dibuang = 0
    for p in list(_semua_paragraf(dok)):
        nama = _nama_penanda(p)
        if not nama:
            teks = _teks(p).strip()
            # baris sisa slot kosong: hanya ";" atau ";" berspasi
            if teks in (";", ";.", ".", "; ."):
                _hapus(p)
                dibuang += 1
            continue
        grup = {_cocok_grup(n)[0] for n in nama}
        grup.discard(None)
        if len(grup) != 1:
            continue
        daftar = grup.pop()
        if daftar in sudah:
            _hapus(p)
            dibuang += 1
            continue
        sudah.add(daftar)
        for n in nama:
            _, kolom = _cocok_grup(n)
            _ganti_regex(p, r"\{\{\s*" + re.escape(n) + r"\s*\}\}",
                         "{{*%s.%s}}" % (daftar, kolom))
        if daftar == "dokumen":
            # Keterangan asli/fotokopi dibawa tiap dokumen dari basis data, jadi kata
            # di depan penanda dibuang — kalau tidak, hasilnya "Asli Fotokopi KTP ...".
            _ganti_regex(p, r"^\s*(?:Asli|Fotokopi|Foto\s*Kopi|Fotocopy|Salinan)\s+(?=\{\{)", "")
        # akhiri baris dengan ; atau . otomatis
        if not _ganti_regex(p, r";\s*$", "{{*%s._akhir}}" % daftar):
            _ganti_regex(p, r"\.\s*$", "{{*%s._akhir}}" % daftar)
    return dibuang


def _hapus(p):
    el = p._p
    if el.getparent() is not None:
        el.getparent().remove(el)


# ---------------------------------------- langkah 3: nilai yang di-hardcode
def _ganti_hardcode(dok, jenis, varian=""):
    """Aturan set baku dulu, lalu aturan khusus varian tata naskahnya."""
    aturan = (GANTI_TEKS.get(jenis, []) if not varian
              else GANTI_VARIAN.get(varian, {}).get(jenis, []))
    n = 0
    for pola, ganti in aturan:
        for p in _semua_paragraf(dok):
            if _ganti_regex(p, pola, ganti):
                n += 1
    return n


# ------------------------------ langkah 4: baris opsional jadi bersyarat
# Paragraf yang isinya hanya satu penanda plus kata sambung ("Asli …;") akan
# menyisakan baris kosong bila nilainya tidak ada. Paragraf seperti itu ditandai
# bersyarat, sehingga hilang sendiri ketika nilainya kosong.
SISA_SEPELE = re.compile(r"^(asli|fotokopi|foto\s*kopi|salinan)?[\s;.,:\-]*$", re.I)


def _jadikan_bersyarat(dok):
    n = 0
    for p in _semua_paragraf(dok):
        teks = _teks(p)
        penanda = re.findall(r"\{\{\s*([*?!@]?)\s*([A-Za-z0-9_.]+)\s*\}\}", teks)
        if len(penanda) != 1 or penanda[0][0] != "":
            continue
        nama = penanda[0][1]
        sisa = re.sub(r"\{\{.*?\}\}", "", teks)
        if not SISA_SEPELE.match(sisa.strip()):
            continue
        r = p.runs[0]
        r.text = "{{?%s}}" % nama + r.text
        n += 1
    return n


# ------------------------- langkah 5: susunan panitia jadi daftar berulang
# Nama, NIP, jabatan, dan pendapat anggota Panitia A diketik tetap di dokumen asli.
# Semua itu sudah ada di basis data (Referensi -> Panitia A), jadi barisnya diciutkan
# menjadi satu baris contoh yang diulang sebanyak anggota panitia berkas bersangkutan.
def _sel_teks(sel, teks):
    p = sel.paragraphs[0]
    runs = list(p.runs)
    if runs:
        runs[0].text = teks
        for r in runs[1:]:
            r.text = ""
    else:
        p.add_run(teks)
    for lebih in sel.paragraphs[1:]:
        _hapus(lebih)


def _par_teks(p, teks):
    runs = list(p.runs)
    if runs:
        runs[0].text = teks
        for r in runs[1:]:
            r.text = ""
    else:
        p.add_run(teks)


def _baris_penanda(t, contoh, teks):
    """Baris tabel berisi penanda blok, disalin dari `contoh` supaya sah secara XML."""
    from docx.table import _Cell
    tr = copy.deepcopy(contoh._tr)
    for i, tc in enumerate(tr.findall(W + "tc")):
        _sel_teks(_Cell(tc, t), teks if i == 0 else "")
    return tr


def _tabel_panitia(dok, kolom_nama):
    """Tabel yang memuat susunan Panitia A: dikenali dari kata 'merangkap Anggota'."""
    for t in dok.tables:
        for b in t.rows:
            sel = b.cells
            if len(sel) > kolom_nama and "merangkap" in sel[-1].text.lower():
                return t
    return None


def _panitia_risalah(dok):
    n = 0
    t = _tabel_panitia(dok, 2)
    if t is not None and len(t.rows) > 1:
        baris = list(t.rows)
        _sel_teks(baris[0].cells[0], "{{*panitia._nomor}}.")
        _sel_teks(baris[0].cells[1], "{{*panitia.nama}}")
        _sel_teks(baris[0].cells[2], "{{*panitia.jabatan_lengkap}}{{*panitia._akhir}}")
        for b in baris[1:]:
            b._tr.getparent().remove(b._tr)
        n += 1

    # blok pendapat: dari judul sampai sebelum kalimat penutup panitia
    par = list(dok.paragraphs)
    awal = next((i for i, p in enumerate(par)
                 if "PENDAPAT ANGGOTA PANITIA" in _teks(p).upper()), None)
    if awal is None:
        return n
    akhir = next((i for i in range(awal + 1, len(par))
                  if _teks(par[i]).strip().lower().startswith("bahwa kami seluruh")), None)
    isi = par[awal + 1:akhir if akhir is not None else len(par)]
    isi = [p for p in isi if _teks(p).strip()]
    if len(isi) < 2:
        return n
    judul, uraian = isi[0], isi[1]
    _par_teks(judul, "{{*panitia.nama}}, sebagai {{*panitia.peran}}:")
    _par_teks(uraian, "{{*panitia.pendapat}}")
    _sisip_penanda(judul, "{{#panitia}}")
    _sisip_penanda(uraian, "{{/panitia}}", sesudah=True)
    for p in isi[2:]:
        _hapus(p)
    return n + 1


def _sisip_penanda(p, teks, sesudah=False):
    el = copy.deepcopy(p._p)
    pPr = el.find(W + "pPr")
    if pPr is not None:
        num = pPr.find(W + "numPr")
        if num is not None:                    # penanda tidak ikut menghabiskan nomor
            pPr.remove(num)
    from docx.text.paragraph import Paragraph
    _par_teks(Paragraph(el, p._parent), teks)
    p._p.addnext(el) if sesudah else p._p.addprevious(el)


def _panitia_bap(dok):
    t = _tabel_panitia(dok, 3)
    if t is None or len(t.rows) < 3:
        return 0
    baris = list(t.rows)
    label = [b.cells[1].text.strip().lower() for b in baris[:3]]
    if label != ["nama", "nip", "jabatan"]:
        return 0
    _sel_teks(baris[0].cells[0], "{{*panitia._nomor}}.")
    _sel_teks(baris[0].cells[3], "{{*panitia.nama}}")
    _sel_teks(baris[1].cells[0], "{{?panitia.nip}}")   # dilewati bila NIP kosong
    _sel_teks(baris[1].cells[3], "{{*panitia.nip}}")
    _sel_teks(baris[2].cells[0], "")
    _sel_teks(baris[2].cells[3], "{{*panitia.jabatan_lengkap}}")
    baris[0]._tr.addprevious(_baris_penanda(t, baris[0], "{{#panitia}}"))
    baris[2]._tr.addnext(_baris_penanda(t, baris[0], "{{/panitia}}"))
    for b in baris[3:]:
        b._tr.getparent().remove(b._tr)
    return 1


def _panitia(dok, jenis):
    if jenis == "risalah":
        return _panitia_risalah(dok)
    if jenis == "bap":
        return _panitia_bap(dok)
    return 0


# ------------------------- langkah 6: daftar Nazhir jadi daftar berulang (wakaf)
# Pada berkas wakaf penerima haknya Nazhir, dan Nazhir perseorangan paling sedikit
# tiga orang. Di dokumen contoh ketiganya diketik satu per satu (a.i, a.ii, a.iii).
# Yang diketik itu diciutkan jadi satu kelompok berulang, sehingga jumlah Nazhir
# mengikuti isi berkas - bukan mengikuti berapa banyak baris yang tersedia.
LABEL_NAZHIR = [
    (re.compile(r"nama", re.I), "nama"),
    (re.compile(r"domisili|tempat\s+kedudukan|alamat", re.I), "alamat"),
    (re.compile(r"kewarganegaraan", re.I), None),          # selalu Indonesia
    (re.compile(r"\bNIK\b", re.I), "nik"),
    (re.compile(r"pekerjaan", re.I), "pekerjaan"),
]
BUTIR_NAZHIR = re.compile(r"^\s*([a-z])\.(i+|\d+)(?=[\s:])", re.I)


def _kolom_nazhir(teks):
    for pola, kolom in LABEL_NAZHIR:
        if pola.search(teks.split(":")[0]):
            return kolom
    return None


def _butir(p):
    """(huruf, urutan) bila paragraf ini butir 'a.i', atau None."""
    m = BUTIR_NAZHIR.match(_teks(p))
    if not m:
        return None
    urut = m.group(2)
    return m.group(1).lower(), (len(urut) if set(urut.lower()) == {"i"} else int(urut))


def _rentang(par, judul, batas):
    """Indeks paragraf antara judul dan judul berikutnya."""
    awal = next((i for i, p in enumerate(par) if judul in _teks(p).upper()), None)
    if awal is None:
        return None, None
    akhir = next((i for i in range(awal + 1, len(par))
                  if any(b in _teks(par[i]).upper() for b in batas)), len(par))
    return awal, akhir


def _nazhir_uraian(par, awal, akhir):
    """Blok 'URAIAN MENGENAI PEMOHON': lima baris identitas per orang."""
    butir = [(i, _butir(par[i])) for i in range(awal + 1, akhir)]
    butir = [(i, b) for i, b in butir if b]
    if not butir:
        return 0
    pertama = [i for i, (_, n) in butir if n == 1]
    lain = [i for i, (_, n) in butir if n != 1]
    if not pertama or not lain:
        return 0
    for i in pertama:
        p = par[i]
        kolom = _kolom_nazhir(_teks(p))
        _ganti_regex(p, r"^(\s*[a-zA-Z])\.(?:i+|\d+)", r"\1.{{*nazhir._romawi}}")
        if kolom:
            _ganti_regex(p, r"(:\s*).*$", r"\1{{*nazhir." + kolom + "}}")
    _sisip_penanda(par[pertama[0]], "{{#nazhir}}")
    _sisip_penanda(par[pertama[-1]], "{{/nazhir}}", sesudah=True)
    for i in lain:
        _hapus(par[i])
    return 1


def _nazhir_telaah(par, awal, akhir):
    """Blok 'URAIAN DAN TELAAH ATAS SUBYEK HAK': satu kalimat per orang."""
    butir = [(i, _butir(par[i])) for i in range(awal + 1, akhir)]
    butir = [(i, b) for i, b in butir if b]
    if not butir:
        return 0
    pertama = [i for i, (_, n) in butir if n == 1]
    if not pertama:
        return 0
    p = par[pertama[0]]
    _par_teks(p, "a.{{*nazhir._romawi}} {{*nazhir.nama}} tempat tanggal lahir "
                 "{{*nazhir.ttl}} Kewarganegaraan Indonesia, bertempat tinggal di "
                 "{{*nazhir.alamat}}, pekerjaan {{*nazhir.pekerjaan}}{{*nazhir._akhir}}")
    for i, _ in butir:
        if i != pertama[0]:
            _hapus(par[i])
    return 1


def _nazhir(dok):
    par = list(dok.paragraphs)
    n = 0
    awal, akhir = _rentang(par, "URAIAN MENGENAI PEMOHON", ("URAIAN MENGENAI TANAH",))
    if awal is not None:
        n += _nazhir_uraian(par, awal, akhir)
    awal, akhir = _rentang(par, "TELAAH ATAS SUBYEK HAK", ("TELAAH ATAS OBYEK HAK",
                                                           "URAIAN DAN TELAAH ATAS OBYEK"))
    if awal is not None:
        n += _nazhir_telaah(par, awal, akhir)
    return n


# --------------------------------------------------------------- penanda foto
def _tambah_penanda_foto(dok):
    for p in _semua_paragraf(dok):
        if "Lampiran Dokumentasi" in _teks(p):
            baru = p.insert_paragraph_before("{{@foto}}")
            return True
    return False


# --------------------------------------------------------------------- utama
def siapkan(jenis, jalur_asal, jalur_tujuan, varian=""):
    dok = Document(jalur_asal)
    n_field = _bongkar_field(dok, varian)
    n_hard = _ganti_hardcode(dok, jenis, varian)
    n_naz = _nazhir(dok) if varian == "wakaf" and jenis == "risalah" else 0
    n_buang = _ciutkan(dok)
    n_syarat = _jadikan_bersyarat(dok)
    n_pan = _panitia(dok, jenis)
    if jenis == "bap":
        _tambah_penanda_foto(dok)
    os.makedirs(os.path.dirname(jalur_tujuan), exist_ok=True)
    dok.save(jalur_tujuan)
    return n_field, n_hard, n_buang, n_syarat, n_pan, n_naz


def main(hanya=None):
    """Bangun ulang template dari dokumen contoh. `hanya` = nama varian tertentu."""
    os.makedirs(DIR_TEMPLATE, exist_ok=True)
    for varian, setel in SET.items():
        if hanya is not None and varian != hanya:
            continue
        print(f"\n{setel['nama']}  ({os.path.basename(setel['dir'])}/)")
        for jenis, berkas in setel["asal"].items():
            asal = os.path.join(setel["dir"], berkas)
            nama_keluaran = f"{jenis}-{varian}" if varian else jenis
            if not os.path.exists(asal):
                print(f"  ! lewati {jenis}: tidak ditemukan {asal}")
                continue
            tujuan = os.path.join(DIR_TEMPLATE, f"{nama_keluaran}.docx")
            f, h, b, y, pn, nz = siapkan(jenis, asal, tujuan, varian)
            naz = f" | {nz} blok nazhir jadi berulang" if nz else ""
            print(f"  {jenis:<8} {f:>3} field -> penanda | {h:>2} nilai hardcode diperbaiki | "
                  f"{b:>2} baris slot kosong dibuang | {y:>2} baris jadi bersyarat | "
                  f"{pn} bagian panitia jadi berulang{naz}"
                  f"  -> templates/{nama_keluaran}.docx")


if __name__ == "__main__":
    # tanpa argumen: semua set. Dengan argumen: hanya varian itu ("" untuk set baku),
    # supaya memperbarui tata naskah wakaf tidak ikut menimpa template Hak Milik.
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
