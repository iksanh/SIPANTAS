# -*- coding: utf-8 -*-
"""Bangun tata naskah Hak Pakai Tanah Pemerintah (bap-, risalah-, sk-hptp).

Sumbernya contoh dokumen Kantah Bone Bolango di folder `hak_pakai_tanah_pemerintah/`
(di samping folder app/): Berita Acara, Risalah, dan Konsep SK pemberian Hak Pakai
selama dipergunakan kepada Pemerintah Daerah Kabupaten Bone Bolango. Kop, susunan
diktum KESATU sampai KELIMABELAS, dasar hukum, dan tembusannya dipakai apa adanya;
yang diganti hanya nilai berkas contoh itu — nama instansi, pejabatnya, luas, letak,
nomor PBT, riwayat per bidang, susunan panitia, dan tanggal — dengan penanda.

Bedanya dengan Hak Pakai biasa (siapkan_hak_pakai.py) yang dirakit dari template
Hak Milik: kerangka dokumen pemerintah memang lain (Peraturan Pendirian Instansi,
tanpa jangka waktu, tanpa BPHTB, diktum «tidak dapat dijadikan jaminan utang»),
jadi dirakit dari contohnya sendiri.

Setiap perubahan mencari kalimat jangkarnya di dokumen contoh. Kalau tidak ketemu
(contohnya diganti dokumen lain), perkakas berhenti dan menyebut kalimat mana —
template yang terpasang tidak disentuh. Template lama dicadangkan dulu ke
templates/cadangan/, jadi bisa dipulihkan dari menu Template.

    python -m berkas.perkakas.siapkan_hak_pakai_pemerintah [folder-contoh]

Contoh berformat .doc (Word 97-2003) dibuka lewat Microsoft Word.
"""
import copy
import os
import shutil
import sys
import tempfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Length
from docx.table import Table
from docx.text.paragraph import Paragraph

from .. import jalur
from ..dokumen import templat
from .siapkan_hak_pakai import (JangkarHilang, _baris_penanda, _ganti_run, _sel, _setel,
                                _setel_sel, _teks)

FOLDER_CONTOH = os.path.join(jalur.INDUK, "hak_pakai_tanah_pemerintah")
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

# Penanda yang sama dipakai berulang di ketiga dokumen
LETAK = ("{{jenis_desa}} {{nama_desa}}, Kecamatan {{kecamatan}}, Kabupaten Bone Bolango, "
         "Provinsi Gorontalo")
PBT = "Peta Bidang Tanah Nomor {{nomor_pbt}} Tanggal {{tanggal_pbt}} NIB. {{nib}}"
RIWAYAT = "{{*riwayat.uraian}}{{*riwayat._akhir}}"
PERDA_RTRW = ("Peraturan Daerah Kabupaten Bone Bolango Nomor 5 Tahun 2021 tentang Rencana "
              "Tata Ruang Wilayah Kabupaten Bone Bolango Tahun 2021-2041")
PAPT = ("Peta Analisis Penatagunaan Tanah tanggal {{tanggal_peta_analisis}} yang "
        "ditandatangani oleh Kepala Seksi Penataan dan Pemberdayaan Kantor Pertanahan "
        "Kabupaten Bone Bolango")


# ------------------------------------------------------------ cari paragraf
def _cari(dok, jangkar, ke=0):
    ketemu = [p for p in dok.paragraphs if jangkar in _teks(p)]
    if len(ketemu) <= ke:
        raise JangkarHilang(jangkar)
    return ketemu[ke]


def _semua(dok, jangkar):
    return [p for p in dok.paragraphs if jangkar in _teks(p)]


def _awal(dok, awal, memuat=""):
    """Paragraf yang teksnya diawali `awal` (dan memuat `memuat`)."""
    for p in dok.paragraphs:
        t = _teks(p).strip()
        if t.startswith(awal) and memuat in t:
            return p
    raise JangkarHilang(f"paragraf berawalan «{awal}»" + (f" memuat «{memuat}»" if memuat else ""))


def _persis(dok, teks):
    for p in dok.paragraphs:
        if _teks(p).strip() == teks:
            return p
    raise JangkarHilang(f"paragraf «{teks}»")


# ------------------------------------------------------------ ubah paragraf
def _ganti(p, lama, baru):
    if not _ganti_run(p, lama, baru):
        raise JangkarHilang(f"{lama!r} di paragraf «{_teks(p)[:60]}…»")


def _mulai(p, jangkar, baru):
    """Ganti teks paragraf mulai dari `jangkar` sampai akhir; format run di awal
    jangkar yang dipakai, jadi label dan tab di depannya tetap utuh."""
    t = _teks(p)
    i = t.find(jangkar)
    if i < 0:
        raise JangkarHilang(f"{jangkar!r} di paragraf «{t[:60]}…»")
    _ganti(p, t[i:], baru)


def _buang(p):
    el = p._p if isinstance(p, Paragraph) else p
    if el.getparent() is not None:
        el.getparent().remove(el)


def _buang_di_antara(awal, akhir):
    """Buang semua elemen badan dokumen di antara dua paragraf (keduanya tetap)."""
    el = awal._p.getnext()
    while el is not None and el is not akhir._p:
        lanjut = el.getnext()
        el.getparent().remove(el)
        el = lanjut


def _sisip_sesudah(p, teks):
    salinan = copy.deepcopy(p._p)
    p._p.addnext(salinan)
    baru = Paragraph(salinan, p._parent)
    _setel(baru, teks)
    return baru


def _riwayat(dok):
    """Bidang I … VII pada contoh jadi satu paragraf berulang per mata rantai riwayat."""
    pertama = _cari(dok, "Bidang I seluas")
    for jangkar in ("Bidang II seluas", "Bidang III seluas", "Bidang IV seluas",
                    "Bidang V seluas", "Bidang VI seluas", "Bidang Tanah VII"):
        for p in _semua(dok, jangkar):
            _buang(p)
    _setel(pertama, RIWAYAT)
    return pertama


def _batas(dok, ke=0):
    for arah in ("Utara", "Timur", "Selatan", "Barat"):
        ps = [p for p in dok.paragraphs
              if _teks(p).strip().startswith(arah) and "berbatasan dengan" in _teks(p)]
        if len(ps) <= ke:
            raise JangkarHilang(f"batas {arah}")
        _mulai(ps[ke], "berbatasan dengan",
               f"berbatasan dengan {{{{batas_{arah.lower()}}}}}")


# ------------------------------------------------------------ kotak teks
def _teks_kotak(el):
    tb = next(el.iter(qn("w:txbxContent")), None)
    return "".join(x.text or "" for x in tb.iter(qn("w:t"))) if tb is not None else ""


def _run_berkotak(dok):
    """Run di badan dokumen yang memuat kotak teks: (run, isi kotaknya)."""
    for r in dok.element.body.iter(qn("w:r")):
        if r.find(MC + "AlternateContent") is not None or r.find(qn("w:pict")) is not None:
            yield r, _teks_kotak(r)


def _buang_penyambung(dok):
    """Kata penyambung contoh («tersebut ...», «Saud, ...») ditulis tangan per halaman;
    aplikasi menambahkannya sendiri lewat Word sesudah dokumen dirakit."""
    n = 0
    for r, isi in list(_run_berkotak(dok)):
        if isi.strip().endswith("..."):
            r.getparent().remove(r)
            n += 1
    return n


def _tanda_tangan_jadi_paragraf(dok, geser_twip, lebar_twip):
    """Blok «Ditetapkan di … NIP» pada contoh SK ada di dalam kotak teks, padahal
    penanda di kotak teks tidak diisi mesin template. Isinya dipindah jadi paragraf
    biasa yang digeser ke kanan, setempat dan selebar kotaknya semula."""
    sek = dok.sections[0]
    lebar_teks = Length(sek.page_width - sek.left_margin - sek.right_margin).twips
    kanan = min(0, lebar_teks - geser_twip - lebar_twip)     # kotaknya melewati margin
    for r, isi in list(_run_berkotak(dok)):
        if "Ditetapkan di" not in isi:
            continue
        p_induk = r.getparent()
        kotak = next(r.iter(qn("w:txbxContent")))
        sebelum = p_induk
        for p_el in kotak.findall(qn("w:p")):
            baru = copy.deepcopy(p_el)
            ppr = baru.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                baru.insert(0, ppr)
            ind = ppr.find(qn("w:ind"))
            if ind is None:
                ind = OxmlElement("w:ind")
                ppr.append(ind)
            kiri = int(ind.get(qn("w:left")) or ind.get(qn("w:start")) or 0)
            ind.set(qn("w:left"), str(kiri + geser_twip))
            for x in (qn("w:right"), qn("w:end")):
                if x in ind.attrib:
                    del ind.attrib[x]
            ind.set(qn("w:right"), str(kanan))
            sebelum.addnext(baru)
            sebelum = baru
        p_induk.remove(r)
        return Paragraph(sebelum, dok._body)
    raise JangkarHilang("kotak teks tanda tangan «Ditetapkan di»")


# --------------------------------------------------------------------- BAP
def ubah_bap(dok):
    p = _cari(dok, "Pada hari ini")
    _mulai(p, "Kamis", "{{hari_bap}}, tanggal {{tgl_bap_terbilang}} {{bulan_bap}} tahun "
                       "{{tahun_bap_terbilang}} ({{tgl_bap}}) kami yang bertandatangan di "
                       "bawah ini:")

    # Susunan panitia: tiga baris (Nama, NIP, Jabatan) diulang per anggota
    t = next((Table(el, dok) for el in dok.element.body.iterchildren()
              if el.tag == qn("w:tbl") and "Jabatan" in "".join(
                  x.text or "" for x in el.iter(qn("w:t")))), None)
    if t is None:
        raise JangkarHilang("tabel susunan panitia")
    baris = t._tbl.findall(qn("w:tr"))
    nama, nip, jab = baris[0], baris[1], baris[2]
    for tr in baris[3:]:
        t._tbl.remove(tr)
    for tr, isi in ((nama, ["{{*panitia._nomor}}.", None, None, "{{*panitia.nama}}"]),
                    (nip, ["{{?panitia.nip}}", None, None, "{{*panitia.nip}}"]),
                    (jab, [None, None, None, "{{*panitia.jabatan_lengkap}}"])):
        for tc, teks in zip(_sel(tr), isi):
            if teks is not None:
                _setel_sel(tc, teks)
    nama.addprevious(_baris_penanda(nama, "{{#panitia}}"))
    jab.addnext(_baris_penanda(nama, "{{/panitia}}"))

    _mulai(_cari(dok, "Dengan ini kami telah melakukan pemeriksaan lapang"), "permohonan dari",
           f"permohonan dari {{{{ins_pemohon_bertindak}}}} atas sebidang tanah seluas "
           f"{{{{luas_teks}}}} sesuai dengan {PBT} terletak di {LETAK}, dengan hasil sebagai "
           "berikut:")
    _mulai(_cari(dok, "Bahwa bidang tanah yang dimohon dikuasai oleh"), "dikuasai oleh",
           "dikuasai oleh {{nama_penerima}}{{ins_asal_bidang}} dengan riwayat:")
    _riwayat(dok)
    _setel(_cari(dok, "Bahwa bidang tanah yang dimohon dipergunakan untuk"),
           f"Bahwa bidang tanah yang dimohon dipergunakan untuk {{{{penggunaan_sekarang}}}} "
           f"dan berdasarkan {PERDA_RTRW} bidang tanah yang dimohonkan Hak Pakai tersebut "
           "terletak di {{rtrw}} dan telah {{ins_kesesuaian_kecil}} dengan Rencana Tata Ruang "
           f"Wilayah Kabupaten Bone Bolango tahun 2021-2041 berdasarkan {PAPT};")
    _setel(_cari(dok, "Bahwa keadaan tanah yang dimohon"),
           "{{?ins_keadaan_kalimat}}{{ins_keadaan_kalimat}}")
    _batas(dok)

    # Foto: tabel kosong contoh diganti lampiran foto yang disusun aplikasi
    foto = _cari(dok, "Berikut bukti dokumentasi")
    el = foto._p.getnext()
    while el is not None and el.tag in (qn("w:tbl"), qn("w:p")):
        lanjut = el.getnext()
        if el.tag == qn("w:p") and "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
            break
        el.getparent().remove(el)
        el = lanjut
    _sisip_sesudah(foto, "{{@foto}}")


# ----------------------------------------------------------------- Risalah
def ubah_risalah(dok):
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_risalah}}")
    _mulai(_cari(dok, "Pada hari ini"), "Kamis",
           "{{hari_risalah}}, tanggal {{tgl_risalah_terbilang}} {{bulan_risalah}} tahun "
           "{{tahun_risalah_terbilang}} ({{tgl_risalah}}) kami yang bertanda tangan di "
           "bawah ini:")

    # Panitia: «NAMA <tab><tab> Jabatan, sebagai …;» diulang per anggota
    p = _cari(dok, "BAHMID KASIM")
    t = _teks(p)
    i = t.index("\t")
    j = i
    while j < len(t) and t[j] == "\t":
        j += 1
    jabatan = t[j:]
    _ganti(p, t[:i], "{{*panitia.nama}}")
    _ganti(p, jabatan, "{{*panitia.jabatan_lengkap}}{{*panitia._akhir}}")
    for jangkar in ("SEP HAMDAN", "ASDA ICHSANTO", "ISWAN B. PADU", "INDRAWATY"):
        _buang(_cari(dok, jangkar))

    p = _cari(dok, "Secara bersama-sama merupakan Panitia")
    _ganti(p, "Bone Bolango 156.1/SK-75.03.HP.01/VIII/2026", "Bone Bolango Nomor "
                                                            "{{panitia_nomor_sk}}")
    _ganti(p, "31 Agustus 2026", "{{panitia_tanggal_sk}}")
    _ganti(p, "5 (lima)", "{{panitia_jumlah}} ({{panitia_jumlah_terbilang}})")
    _ganti(p, "terletak di Ulanta, Kecamatan Suwawa, Kabupaten Bone Bolango, Provinsi Gorontalo",
           f"terletak di {LETAK}")
    _mulai(p, "Dr. Iwan Mustapa", "{{ins_pemohon_bertindak}}.")

    # I. Uraian mengenai pemohon
    _mulai(_awal(dok, "Nama Pemohon"), "Pemerintah", "{{nama_penerima}}")
    _mulai(_awal(dok, "Domisili/Tempat Kedudukan"), "Desa Ulanta", "{{ins_kedudukan}}")
    _buang(_persis(dok, "Bolango"))
    _mulai(_awal(dok, "c. Peraturan Pendirian Instansi"), "Undang-undang", "{{ins_dasar}}")
    _buang(_persis(dok, "tentang Pembentukan Kabupaten Bonebolango"))
    _buang(_persis(dok, "dan Kabupaten Pohuwato di Provinsi Gorontalo"))

    # II. Uraian mengenai tanah
    _mulai(_awal(dok, "Desa", "Inomata"), "Inomata", "{{nama_desa}}")
    _mulai(_awal(dok, "Kecamatan", "Bone Raya"), "Bone Raya", "{{kecamatan}}")
    _mulai(_awal(dok, "Luas", "31.475"), "31.475", "{{luas_teks}}")
    _mulai(_awal(dok, "Peta Bidang Tanah", "191/2026"), "Nomor", "Nomor : {{nomor_pbt}} NIB. {{nib}}")
    _mulai(_awal(dok, "Tanggal 15 Oktober 2026"), "15 Oktober 2026", "{{tanggal_pbt}}")
    # III. Uraian atas hak: «Jenis Hak : Hak Pakai», «Jangka Waktu : Selama Dipergunakan» tetap
    _mulai(_awal(dok, "Penggunaan Saat Ini"), "RSUD", "{{penggunaan_sekarang}}")
    _mulai(_awal(dok, "Rencana Penggunaan"), "RSUD", "{{rencana_penggunaan}}")

    # IV. Data pendukung: dokumen berkas (termasuk KIB) + SPPF + KTP pejabat + butir tetap
    awal = _cari(dok, "Asli Formulir permohonan Pemberian Hak Pakai")
    pbt = _cari(dok, "Asli Peta Bidang Tanah Nomor")
    _buang_di_antara(awal, pbt)
    _setel(awal, "{{*dokumen.uraian}};")
    # disisipkan terbalik supaya urutannya: dokumen, SPPF, KTP pejabat
    _sisip_sesudah(awal, "{{?ins_wakil}}Fotokopi KTP atas nama {{ins_wakil}};")
    _sisip_sesudah(awal, "{{?sppf}}Asli {{sppf}};")
    _setel(pbt, f"Asli {PBT} dengan luas {{{{luas_teks}}}};")
    _setel(_cari(dok, "Asli Peta Analisis Penatagunaan Tanah"),
           "Asli Peta Analisis Penatagunaan Tanah tanggal {{tanggal_peta_analisis}} yang "
           "ditandatangani oleh a.n Kepala Kantor Pertanahan Kabupaten Bone Bolango Kepala Seksi "
           "Penataan dan Pemberdayaan Kantor Pertanahan Kabupaten Bone Bolango "
           "{{kasi_pgt_nama}};")
    # tanda batas sudah ikut daftar dokumen (slot baku)
    _buang(_cari(dok, "Asli Surat Pernyataan Pemasangan Tanda Batas"))
    _setel(_cari(dok, "Asli Berita Acara Pemeriksaan Lapang"),
           "Asli Berita Acara Pemeriksaan Lapang Tanggal {{tgl_bap}} oleh Anggota Panitia "
           "Pemeriksaan Tanah A yang telah ditandatangani.")

    # V. Dasar hukum: hanya SK susunan panitianya yang mengikuti berkas
    _ganti(_cari(dok, "Tentang Susunan Tim Panitia Pemeriksaan Tanah"),
           "156.1/SK-75.03.HP.01/VIII/2026 Tanggal 30 Agustus 2026",
           "{{panitia_nomor_sk}} Tanggal {{panitia_tanggal_sk}}")

    # VI. Telaah subjek
    _setel(_cari(dok, "Bahwa Pemohon yaitu"),
           "Bahwa Pemohon yaitu {{nama_penerima}} berkedudukan di {{ins_kedudukan}}"
           "{{ins_dibentuk}};")
    _ganti(_cari(dok, "pemohon memenuhi syarat sebagai Subjek Hak"), "huruf b",
           "huruf {{ins_huruf}}")

    # VII. Telaah objek
    _setel(_cari(dok, "belum dilekati dengan sesuatu hak yang dikuasai oleh"),
           "Bahwa bidang tanah yang dimohon merupakan tanah negara yang belum dilekati dengan "
           "sesuatu hak yang dikuasai oleh {{nama_penerima}} seluas {{luas_teks}};")
    _setel(_cari(dok, "telah dikuasai oleh pemohon yang berasal dari"),
           "Bahwa bidang tanah yang dimohon merupakan tanah Negara yang telah dikuasai oleh "
           "pemohon{{ins_asal_bidang}} dengan riwayat perolehan sebagai berikut:")
    _riwayat(dok)
    _setel(_cari(dok, "sebagaimana yang dimuat dalam Surat Pernyataan Penguasaan Fisik"),
           "{{?sppf}}Bahwa bidang tanah yang dimohon seluas {{luas_teks}} merupakan Tanah "
           "Negara yang dikuasai oleh {{nama_penerima}} sebagaimana yang dimuat dalam {{sppf}}.")
    _setel(_cari(dok, "belum pernah dilekati dengan sesuatu hak"),
           "Bahwa tanah yang dimohon berasal dari Tanah Negara yang belum pernah dilekati "
           "dengan sesuatu hak yang dikuasai oleh {{nama_penerima}}.")
    _setel(_cari(dok, "tersebut dimanfaatkan dan digunakan oleh"),
           "Bahwa bidang tanah yang dimohonkan Hak Pakai tersebut dimanfaatkan dan digunakan "
           "oleh {{nama_penerima}};")
    _setel(_cari(dok, "tersebut digunakan oleh pemohon untuk"),
           "Bahwa bidang tanah yang dimohonkan Hak Pakai tersebut digunakan oleh pemohon untuk "
           f"{{{{penggunaan_sekarang}}}} dan berdasarkan {PERDA_RTRW} berada di {{{{rtrw}}}}.")
    _setel(_cari(dok, "Tanah yang dimohonkan hak pakai digunakan dan dimanfaatkan"),
           "Tanah yang dimohonkan hak pakai digunakan dan dimanfaatkan oleh pemohon untuk "
           "{{penggunaan_sekarang}};")
    _setel(_cari(dok, "Bahwa bidang tanah yang dimohon dipergunakan untuk"),
           "Bahwa bidang tanah yang dimohon dipergunakan untuk {{penggunaan_sekarang}} dan "
           f"berdasarkan {PERDA_RTRW} bidang tanah yang dimohonkan Hak Pakai tersebut terletak "
           "di {{rtrw}} dan penggunaan tanah tersebut {{ins_kesesuaian_kecil}} dengan Rencana "
           f"Tata Ruang Wilayah Kabupaten Bone Bolango Tahun 2021-2041 berdasarkan {PAPT};")
    _setel(_cari(dok, "berdasarkan hasil pengukuran kadasteral"),
           "Bahwa berdasarkan hasil pengukuran kadasteral oleh Kantor Pertanahan Kabupaten "
           f"Bone Bolango yang hasilnya dituangkan dalam {PBT}, tanah yang dimohon terletak di "
           f"{LETAK} seluas {{{{luas_teks}}}} dengan batas-batas sebagai berikut:")
    _batas(dok)

    # VIII. Analisa
    p = _cari(dok, "telah   memenuhi  syarat  sebagai  pemegang")
    _ganti(p, "Pemerintah Daerah Kabupaten Bone Bolango", "{{nama_penerima}}")
    _ganti(p, "huruf b", "huruf {{ins_huruf}}")
    _setel(_cari(dok, "sebagaimana dituangkan dalam Peta Bidang Tanah"),
           f"Bahwa bidang tanah yang dimohon seluas {{{{luas_teks}}}} sebagaimana dituangkan "
           f"dalam {PBT}, tanah yang dimohon terletak di {LETAK};")
    _ganti(_cari(dok, "Lapang tanggal 22 Oktober 2026"), "22 Oktober 2026", "{{tgl_bap}}")
    _setel(_cari(dok, "Bahwa penggunaan tanah yang dimohon telah sesuai"),
           "Bahwa penggunaan tanah yang dimohon telah {{ins_kesesuaian_kecil}} dengan Rencana "
           f"Tata Ruang Wilayah Kabupaten Bone Bolango tahun 2021-2041 berdasarkan {PAPT};")

    # X. Kesimpulan
    _setel(_cari(dok, "Bahwa tanah yang dimohon seluas 31.475"),
           f"Bahwa tanah yang dimohon seluas {{{{luas_teks}}}} sesuai {PBT};")
    _ganti(_cari(dok, "Berdasarkan uraian tersebut di atas, permohonan Hak Pakai atas nama"),
           "Pemerintah Daerah Kabupaten Bone Bolango", "{{nama_penerima}}")


# ---------------------------------------------------------------------- SK
# Kotak tanda tangan contoh SK: 2.536.190 EMU dari margin kiri = ±3.994 twip,
# lebarnya 4.133.215 EMU = ±6.509 twip (1 twip = 635 EMU)
GESER_TANDA_TANGAN = 3994
LEBAR_TANDA_TANGAN = 6509


def ubah_sk(dok):
    _buang_penyambung(dok)
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_sk}}")

    # Judul (lima baris pada contoh)
    _mulai(_cari(dok, "PEMBERIAN HAK PAKAI ATAS NAMA"), "PEMBERIAN HAK PAKAI ATAS NAMA",
           "PEMBERIAN HAK PAKAI ATAS NAMA {{ins_nama_kapital}}")
    _setel(_cari(dok, "ATAS TANAH SELUAS"), "ATAS TANAH SELUAS {{ins_luas_kapital}}")
    _buang(_cari(dok, "(TIGA PULUH SATU RIBU"))
    _setel(_cari(dok, "TERLETAK DI Desa"),
           "TERLETAK DI {{ins_desa_kapital}} KECAMATAN {{ins_kecamatan_kapital}}")

    _mulai(_cari(dok, "Surat permohonan Hak Pakai tanggal"), "Surat permohonan",
           "Surat permohonan Hak Pakai tanggal {{tanggal_permohonan}}{{ins_nomor_berkas_frasa}} "
           "dari {{ins_pemohon_mewakili}};")
    # Menimbang
    _mulai(_cari(dok, "sehingga telah memenuhi syarat sebagai subjek Hak Pakai"), "Bahwa",
           "Bahwa {{nama_penerima}} berkedudukan di {{ins_kedudukan}}{{ins_dibentuk}} sehingga "
           "telah memenuhi syarat sebagai subjek Hak Pakai;")
    _setel(_cari(dok, "telah dilakukan pengukuran secara kadastral"),
           "Bahwa tanah yang dimohon telah dilakukan pengukuran secara kadastral oleh Kantor "
           f"Pertanahan Kabupaten Bone Bolango seluas {{{{luas_teks}}}} terletak di {LETAK} "
           "sebagaimana diuraikan dalam Peta Bidang Tanah Nomor : {{nomor_pbt}} Tanggal "
           "{{tanggal_pbt}} NIB. {{nib}};")
    _setel(_cari(dok, "Bahwa pemohon menyatakan menguasai"),
           f"Bahwa pemohon menyatakan menguasai sebidang tanah yang terletak di {LETAK}, "
           "dipergunakan untuk {{penggunaan_sekarang}} yang dikuasai secara terus menerus, dan "
           "sampai dengan saat ini tanah tersebut belum dilekati Hak Atas Tanah"
           "{{ins_sesuai_sppf}};")
    _setel(_cari(dok, "dilakukan pemeriksaan oleh Panitia"),
           "Bahwa tanah yang dimohon telah dilakukan pemeriksaan oleh Panitia Pemeriksaan "
           "Tanah A yang hasilnya dituangkan dalam Risalah Panitia Pemeriksaan Tanah A Kantor "
           "Pertanahan Kabupaten Bone Bolango Nomor {{nomor_risalah}} tanggal {{tgl_risalah}} "
           "antara lain dinyatakan:")
    _setel(_cari(dok, "Bahwa sebelumnya bidang tanah yang dimohon berasal dari"),
           "Bahwa status bidang tanah yang dimohon merupakan tanah negara yang dikuasai oleh "
           "pemohon{{ins_asal_bidang}} dengan riwayat perolehan sebagai berikut :")
    _riwayat(dok)
    _setel(_cari(dok, "akan dipergunakan untuk"),
           "Bahwa tanah yang dimohon akan dipergunakan untuk {{rencana_penggunaan}};")
    _setel(_cari(dok, "Rencana Penggunaan Tanah yang dimohon"),
           "Bahwa rencana penggunaan tanah yang dimohon untuk {{rencana_penggunaan}} telah "
           "{{ins_kesesuaian_kecil}} dengan Rencana Tata Ruang Wilayah Kabupaten Bone Bolango "
           "berdasarkan Peraturan Daerah Kabupaten Bone Bolango No.05 tahun 2021 tentang "
           "Rencana Tata Ruang Wilayah (RTRW) Kabupaten Bone Bolango Tahun 2021–2041;")
    # Mengingat: hanya SK susunan panitianya yang mengikuti berkas
    _ganti(_cari(dok, "Tentang Susunan Tim Panitia Pemeriksaan Tanah"),
           "156.1/SK-75.03.HP.01/VIII/2026 Tanggal 30 Agustus 2026",
           "{{panitia_nomor_sk}} Tanggal {{panitia_tanggal_sk}}")

    # Memutuskan
    _mulai(_cari(dok, "Menetapkan"), "PEMBERIAN HAK",
           "PEMBERIAN HAK PAKAI ATAS NAMA {{ins_nama_kapital}} ATAS TANAH SELUAS "
           "{{ins_luas_kapital}} TERLETAK DI {{ins_desa_kapital}} KECAMATAN "
           "{{ins_kecamatan_kapital}} KABUPATEN BONE BOLANGO PROVINSI GORONTALO.")
    _mulai(_cari(dok, "KESATU"), "Memberikan",
           "Memberikan {{nama_penerima}} berkedudukan di {{ins_kedudukan}} Hak Pakai Selama "
           "Dipergunakan atas sebidang tanah{{ins_jenis_tanah_frasa}} sejak didaftarkan pada "
           "Kantor Pertanahan Kabupaten Bone Bolango atas Tanah Negara seluas {{luas_teks}}, "
           f"terletak di {LETAK} sebagaimana diuraikan dalam Peta Bidang Tanah Nomor : "
           "{{nomor_pbt}} Tanggal {{tanggal_pbt}} NIB. {{nib}} yang diterbitkan oleh Kantor "
           "Pertanahan Kabupaten Bone Bolango;")

    # Tanda tangan, lalu baris kosong pengganjal kotak teksnya dibuang
    akhir = _tanda_tangan_jadi_paragraf(dok, GESER_TANDA_TANGAN,
                                       LEBAR_TANDA_TANGAN)
    _ganti(_cari(dok, "Pada Tanggal"), "       Oktober 2026", " {{tgl_sk}}")
    kepada = _awal(dok, "Kepada")
    el = akhir._p.getnext()
    kosong = []
    while el is not None and el is not kepada._p:
        if el.tag == qn("w:p") and not "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
            kosong.append(el)
        el = el.getnext()
    for el in kosong[1:]:                      # sisakan satu baris jarak
        el.getparent().remove(el)

    _setel(_persis(dok, "Pemerintah Daerah Kabupaten Bone Bolango"), "{{nama_penerima}}")
    _setel(_cari(dok, "Desa Ulantah"), "{{ins_kedudukan}}.")


UBAH = {"bap": ubah_bap, "risalah": ubah_risalah, "sk": ubah_sk}


def _buang_gambar_yatim(dok):
    """Gambar yang tak lagi dirujuk badan dokumen ikut dibuang dari berkasnya.

    Tabel foto contoh BAP dibuang, tetapi foto lapangnya — foto pemeriksaan
    sungguhan — masih menumpang di paket .docx (±4 MB). Kop di header tidak
    terkena: gambarnya milik bagian header, bukan badan dokumen.
    """
    xml = dok.element.xml
    yatim = [rid for rid, rel in dok.part.rels.items()
             if rel.reltype.endswith("/image") and f'"{rid}"' not in xml]
    for rid in yatim:
        del dok.part.rels[rid]
    return len(yatim)


# ------------------------------------------------------------ berkas contoh
def _cari_contoh(folder):
    """Berkas contoh per jenis dokumen, dari namanya: «… Acara …», «RISALAH», «SK»."""
    hasil = {}
    for nama in sorted(os.listdir(folder)):
        dasar, eks = os.path.splitext(nama)
        if eks.lower() not in (".doc", ".docx") or nama.startswith("~$"):
            continue
        n = dasar.lower()
        if "risalah" in n:
            jenis = "risalah"
        elif "acara" in n or "bap" in n:
            jenis = "bap"
        elif n.startswith("sk") or "konsep" in n:
            jenis = "sk"
        else:
            continue
        # .docx didahulukan bila keduanya ada
        if jenis not in hasil or eks.lower() == ".docx":
            hasil[jenis] = os.path.join(folder, nama)
    return hasil


def _sebagai_docx(jalur_asal, sarang):
    """.doc dibuka dan disimpan ulang sebagai .docx lewat Microsoft Word."""
    if jalur_asal.lower().endswith(".docx"):
        return jalur_asal
    import win32com.client                                  # hanya di Windows ber-Word
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        d = word.Documents.Open(os.path.abspath(jalur_asal), ReadOnly=True)
        tujuan = os.path.join(sarang, os.path.splitext(os.path.basename(jalur_asal))[0] + ".docx")
        d.SaveAs2(tujuan, FileFormat=16)                    # wdFormatXMLDocument
        d.Close(False)
        return tujuan
    finally:
        word.Quit()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[0] if argv else FOLDER_CONTOH
    contoh = _cari_contoh(folder)
    kurang = [j for j in UBAH if j not in contoh]
    if kurang:
        print(f"  ! contoh {', '.join(kurang)} tidak ditemukan di {folder}")
        return 1
    sarang = tempfile.mkdtemp(prefix="hptp_")
    gagal = False
    try:
        for jenis, fungsi in UBAH.items():
            tujuan = os.path.join(jalur.TEMPLATE, f"{jenis}-hptp.docx")
            try:
                dok = Document(_sebagai_docx(contoh[jenis], sarang))
                fungsi(dok)
                _buang_gambar_yatim(dok)
            except JangkarHilang as ex:
                gagal = True
                print(f"  ! {jenis}: kalimat jangkar tidak ditemukan di "
                      f"{os.path.basename(contoh[jenis])}: {ex}")
                continue
            cadangan = templat._cadangkan(f"{jenis}-hptp")
            if cadangan:
                print(f"  cadangan {cadangan}")
            dok.save(tujuan)
            print(f"  dibuat  {tujuan}")
    finally:
        shutil.rmtree(sarang, ignore_errors=True)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
