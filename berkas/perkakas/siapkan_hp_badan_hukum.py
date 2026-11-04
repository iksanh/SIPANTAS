# -*- coding: utf-8 -*-
"""Bangun tata naskah Hak Pakai Badan Hukum (risalah-hpbh, sk-hpbh).

Sumbernya contoh dokumen Kantah Bone Bolango di folder `hak_pakai_badan_hukum/`
(di samping folder app/): Risalah dan Konsep SK pemberian Hak Pakai dengan jangka
waktu. Kop, dasar hukum, diktum KESATU sampai KELIMABELAS, dan tembusannya dipakai
apa adanya; nilai berkas contoh — nama, luas, letak, nomor PBT, riwayat, susunan
panitia, dan tanggal — diganti penanda.

Pemohon pada contoh itu perorangan, jadi bagian subjeknya (Uraian mengenai
Pemohon, telaah subjek, analisis, Menimbang huruf a, KESATU, alamat penerima)
ditulis ulang untuk badan hukum: akta pendirian, pengesahan, NIB, bidang usaha,
dengan dasar UUPA Pasal 42 huruf c, PP 18/2021 Pasal 49 ayat (2) huruf b, dan
Permen ATR/BPN 18/2021 Pasal 111 ayat (2) huruf b — sama dengan tata naskah Hak
Pakai yang sudah ada. Alasan khusus contoh (tanah di sempadan sungai) jadi isian
«pertimbangan lapangan» yang boleh kosong. Kalimat «dimohon … direkomendasikan
Hak Pakai» hanya tercetak bila jenis hak yang dimohon bukan Hak Pakai.

BAP-nya tidak dibangun: berkas Hak Pakai Badan Hukum memakai BAP baku (bap.docx).

Setiap perubahan mencari kalimat jangkarnya di dokumen contoh. Kalau tidak ketemu
(contohnya diganti dokumen lain), perkakas berhenti dan menyebut kalimat mana —
template yang terpasang tidak disentuh. Template lama dicadangkan dulu ke
templates/cadangan/, jadi bisa dipulihkan dari menu Template.

    python -m berkas.perkakas.siapkan_hp_badan_hukum [folder-contoh]
"""
import copy
import os
import re
import shutil
import sys
import tempfile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .. import jalur
from ..dokumen import templat
from .siapkan_hak_pakai import JangkarHilang, _sel, _setel, _setel_sel, _teks
from .siapkan_hak_pakai_pemerintah import (
    _awal, _batas, _buang, _buang_di_antara, _buang_gambar_yatim, _cari, _cari_contoh,
    _ganti, _mulai, _persis, _sebagai_docx, _semua, _sisip_sesudah)
from .siapkan_hgb_badan_hukum import _buang_penyambung

FOLDER_CONTOH = os.path.join(jalur.INDUK, "hak_pakai_badan_hukum")
NAMA_CONTOH = "Reagen Hulukati, S.T"
SEBUTAN = "Hak Pakai dengan Jangka Waktu"

# Penanda yang sama dipakai berulang di kedua dokumen
LETAK = ("{{jenis_desa}} {{nama_desa}}, Kecamatan {{kecamatan}}, Kabupaten Bone Bolango, "
         "Provinsi Gorontalo")
RIWAYAT = "{{*riwayat.uraian}}{{*riwayat._akhir}}"
PERTIMBANGAN = "{{*hpbh_pertimbangan.uraian}};"
PERDA_RTRW = ("Peraturan Daerah Kabupaten Bone Bolango Nomor 5 Tahun 2021 Tentang Rencana "
              "Tata Ruang Wilayah Kabupaten Bone Bolango Tahun 2021-2041")
PAPT = ("Peta Analisis Penatagunaan Tanah Tanggal {{tanggal_peta_analisis}} yang "
        "ditandatangani oleh Kepala Seksi Penataan dan Pemberdayaan Kantor Pertanahan "
        "Kabupaten Bone Bolango")
GUNA = ("Bahwa penggunaan dan pemanfaatan bidang tanah tersebut {{penggunaan_sekarang}} "
        f"berdasarkan {PAPT}, bidang tanah yang dimohon berada dalam {{{{rtrw}}}}, sehingga "
        f"bidang tanah tersebut {{{{kesesuaian}}}} dengan {PERDA_RTRW}{{{{hpbh_tata_ruang_frasa}}}}. "
        "Sehingga penggunaan tanahnya untuk {{hpbh_jenis_tanah}}")
UKUR = ("Bahwa atas bidang tanah yang dimohon {{hpbh_hak_dimohon}} oleh {{nama_penerima}} telah "
        "dilaksanakan pengukuran secara kadastral oleh Seksi Survei dan Pemetaan Kantor "
        "Pertanahan Kabupaten Bone Bolango seluas {{luas_teks}} sesuai Peta Bidang Tanah Nomor "
        f"{{{{nomor_pbt}}}} tanggal {{{{tanggal_pbt}}}}, NIB. {{{{nib}}}} terletak di {LETAK}")
# Dasar subjek Hak Pakai badan hukum, sama dengan tata naskah Hak Pakai (risalah-hp)
DASAR_SUBJEK = ("Undang-Undang Nomor 5 Tahun 1960 tentang Peraturan Dasar Pokok-Pokok Agraria "
                "Pasal 42 huruf c, Peraturan Pemerintah Nomor 18 Tahun 2021 tentang Hak "
                "Pengelolaan, Hak atas Tanah, Satuan Rumah Susun, dan Pendaftaran Tanah Pasal 49 "
                "ayat (2) huruf b, dan Peraturan Menteri Agraria dan Tata Ruang/Kepala Badan "
                "Pertanahan Nasional Nomor 18 Tahun 2021 Tentang Tata Cara Penetapan Hak "
                "Pengelolaan Dan Hak Atas Tanah Pasal 111 ayat (2) huruf b")
PENGUASAAN = "dikuasai terus menerus oleh pemohon, belum bersertipikat"


def _ganti_pola(p, pola, baru):
    """Seperti _ganti, tetapi `pola` regex: contoh SK meratakan teks dengan deretan
    spasi, jadi jumlah spasinya tidak bisa ditulis persis."""
    m = re.search(pola, _teks(p))
    if not m:
        raise JangkarHilang(f"pola {pola!r} di paragraf «{_teks(p)[:60]}…»")
    _ganti(p, m.group(0), baru)


def _ganti_nama(p):
    _ganti(p, NAMA_CONTOH, "{{nama_penerima}}")


def _baris_isian(p, label, nilai):
    """Baris «Label : nilai» Uraian mengenai Pemohon; penomoran paragrafnya tetap."""
    _setel(p, f"{label}\t\t: {nilai}")


def _riwayat(dok):
    """Mata rantai riwayat contoh (paragraf «Bahwa sebelumnya …», «Bahwa selanjutnya
    …», dan «;» sisa mail merge) jadi satu paragraf berulang. Yang diubah selalu
    kelompok pertama yang belum diubah, jadi dipanggil sekali per kelompok."""
    pertama = _cari(dok, "Bahwa sebelumnya bidang tanah yang dimohon dikuasai oleh")
    el = pertama._p.getnext()
    while el is not None and el.tag == qn("w:p"):
        isi = "".join(x.text or "" for x in el.iter(qn("w:t"))).strip()
        if not (isi.startswith("Bahwa selanjutnya") or isi == ";"):
            break
        lanjut = el.getnext()
        el.getparent().remove(el)
        el = lanjut
    _setel(pertama, RIWAYAT)
    return pertama


def _pertimbangan(dok, jumlah):
    """Pasangan kalimat sempadan sungai pada contoh jadi satu paragraf berulang per
    baris isian pertimbangan lapangan."""
    awal = [p for p in dok.paragraphs if _teks(p).strip().startswith(
        "Bahwa berdasarkan hasil pemeriksaan tanah di lapangan bidang tanah yang dimohon "
        "berbatasan")]
    if len(awal) != jumlah:
        raise JangkarHilang(f"{jumlah} kalimat pemeriksaan lapangan (ketemu {len(awal)})")
    for p in awal:
        berikut = p._p.getnext()
        isi = "".join(x.text or "" for x in berikut.iter(qn("w:t"))).strip()
        if not isi.startswith("Bahwa berdasarkan Peraturan Menteri Pekerjaan Umum"):
            raise JangkarHilang("kalimat Permen PUPR sesudah kalimat pemeriksaan lapangan")
        berikut.getparent().remove(berikut)
        _setel(p, PERTIMBANGAN)


def _penguasaan(dok, jumlah):
    ps = _semua(dok, PENGUASAAN)
    if len(ps) != jumlah:
        raise JangkarHilang(f"{jumlah} kalimat penguasaan fisik (ketemu {len(ps)})")
    for p in ps:
        akhir = "." if _teks(p).rstrip().endswith(".") else ";"
        _setel(p, "{{penguasaan_fisik}}" + akhir)


def _selisih(dok, jumlah):
    ps = _semua(dok, "Bahwa terdapat selisih seluas")
    if len(ps) != jumlah:
        raise JangkarHilang(f"{jumlah} kalimat selisih luas (ketemu {len(ps)})")
    for p in ps:
        _setel(p, "{{?selisih_teks}}{{selisih_teks}};")


def _panitia_sk(p):
    _ganti(p, "02/SK-75.03.HP.01/I/2026", "{{panitia_nomor_sk}}")
    _ganti(p, "05 Januari 2026", "{{panitia_tanggal_sk}}")


# ----------------------------------------------------------------- Risalah
def _pendapat(dok):
    """Pendapat anggota: satu pasang paragraf (nama, pendapat) diulang per anggota."""
    pertama = _cari(dok, "sebagai Ketua Panitia Merangkap Anggota:")
    pendapat = pertama._p.getnext()
    akhir = _cari(dok, "Bahwa kami seluruh anggota berpendapat")
    p_pendapat = Paragraph(pendapat, pertama._parent)
    _buang_di_antara(p_pendapat, akhir)
    _setel(pertama, "{{*panitia.nama}}, sebagai {{*panitia.peran}}:")
    _setel(p_pendapat, "{{*panitia.pendapat}}")
    buka = copy.deepcopy(pendapat)
    tutup = copy.deepcopy(pendapat)
    pertama._p.addprevious(buka)
    pendapat.addnext(tutup)
    _setel(Paragraph(buka, pertama._parent), "{{#panitia}}")
    _setel(Paragraph(tutup, pertama._parent), "{{/panitia}}")
    _setel(akhir, "Bahwa kami seluruh anggota berpendapat permohonan {{hpbh_hak_dimohon}} atas "
                  "nama pemohon {{hpbh_dapat_diberikan}}, namun apabila di atas bidang tanah yang "
                  "diberikan Hak Pakai terdapat keberatan, permasalahan, penguasaan dan/atau "
                  "pemilikan hak lain yang timbul dikemudian hari, maka penerima hak wajib "
                  "menyelesaikan permasalahan tersebut tanpa melibatkan Panitia A Kantor "
                  "Pertanahan Kabupaten Bone Bolango dan Surat Keputusan Haknya yang akan "
                  "diterbitkan batal demi hukum.")


def ubah_risalah(dok):
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_risalah}}")
    _mulai(_cari(dok, "Pada hari Ini"), "Selasa",
           "{{hari_risalah}} tanggal {{tgl_risalah_terbilang}} bulan {{bulan_risalah}} tahun "
           "{{tahun_risalah_terbilang}} ({{tgl_risalah_pendek}}), kami yang bertandatangan di "
           "bawah ini :")

    # Susunan panitia: satu baris tabel (nomor | nama | jabatan) diulang per anggota
    t = next((Table(el, dok) for el in dok.element.body.iterchildren()
              if el.tag == qn("w:tbl") and "sebagai Ketua" in "".join(
                  x.text or "" for x in el.iter(qn("w:t")))), None)
    if t is None:
        raise JangkarHilang("tabel susunan panitia")
    baris = t._tbl.findall(qn("w:tr"))
    for tr in baris[1:]:
        t._tbl.remove(tr)
    sel = _sel(baris[0])
    if len(sel) < 3:
        raise JangkarHilang("tiga kolom tabel susunan panitia")
    for tc, teks in zip(sel, ("{{*panitia._nomor}}.", "{{*panitia.nama}}",
                              "{{*panitia.jabatan_lengkap}}{{*panitia._akhir}}")):
        _setel_sel(tc, teks)

    p = _cari(dok, "Secara bersama-sama merupakan panitia")
    _panitia_sk(p)
    _ganti(p, "5 (lima)", "{{panitia_jumlah}} ({{panitia_jumlah_terbilang}})")
    _mulai(p, "terletak di", "terletak di {{jenis_desa}} {{nama_desa}}, Kecamatan "
                             "{{kecamatan}}, Kabupaten Bone Bolango, untuk mengadakan "
                             "pemeriksaan atas Permohonan {{hpbh_hak_dimohon}} atas Nama : "
                             "{{nama_penerima}}.")

    # I. Uraian mengenai pemohon: baris perorangan contoh jadi baris badan hukum
    _ganti(_awal(dok, "1.", "Perorangan"), "Perorangan", "Badan Hukum")
    _mulai(_awal(dok, "Nama Pemohon"), NAMA_CONTOH, "{{nama_penerima}}")
    _mulai(_awal(dok, "Domisili"), "Komp. Perum", "{{hpbh_kedudukan}}")
    _buang(_awal(dok, "009 Kelurahan Entrop"))
    _buang(_awal(dok, "Selatan Kota"))
    _baris_isian(_awal(dok, "Kewarganegaraan"), "Akta Pendirian Badan Hukum",
                 "Nomor : {{bh_akta_nomor}} tanggal {{bh_akta_tanggal}}")
    _baris_isian(_awal(dok, "NIK"), "Pengesahan Badan Hukum",
                 "Nomor : {{bh_pengesahan_nomor}} tanggal {{bh_pengesahan_tanggal}}")
    nib = _awal(dok, "Pekerjaan")
    _baris_isian(nib, "Nomor Induk Berusaha", "{{bh_nib}}")
    _sisip_sesudah(nib, "Bidang Usaha/Kegiatan\t\t: {{bh_bidang_usaha}}")

    # II. Uraian mengenai tanah
    _mulai(_awal(dok, "Jalan", ":"), "-", "{{hpbh_jalan}}")
    _mulai(_awal(dok, "Desa", "Molotabu"), "Molotabu", "{{nama_desa}}")
    _mulai(_awal(dok, "Kecamatan", "Kabila Bone"), "Kabila Bone", "{{kecamatan}}")
    _mulai(_awal(dok, "2", "Luas"), "171", "{{luas_teks}}")
    _mulai(_awal(dok, "3", "Peta Bidang Tanah"), "No.",
           "No. {{nomor_pbt}}, Tanggal {{tanggal_pbt}},")
    _mulai(_awal(dok, "NIB."), "NIB.", "NIB. {{nib}}")

    # III. Uraian atas hak yang akan ditetapkan
    _ganti(_awal(dok, "1.", "Jenis"), "Hak Milik", SEBUTAN)
    _mulai(_awal(dok, "2.", "Jangka Waktu"), "-", "{{jangka_tahun}} Tahun")
    _mulai(_awal(dok, "a.", "Penggunaan saat ini"), "Tanah Kosong", "{{penggunaan_sekarang}}")
    _mulai(_awal(dok, "b.", "Rencana penggunaan"), "Rumah Tinggal", "{{rencana_penggunaan}}")

    # IV. Data pendukung: dokumen berkas + SPPF + kuasa + PBT + PAPT + BAP
    awal = _cari(dok, "Asli Surat permohonan hak yang dibuat")
    pbt = _cari(dok, "Asli Peta Bidang Tanah Nomor")
    _buang_di_antara(awal, pbt)
    _setel(awal, "{{*dokumen.uraian}};")
    sppf = _sisip_sesudah(awal, "{{?sppf}}Asli {{sppf}};")
    _sisip_sesudah(sppf, "{{?surat_kuasa}}Asli {{surat_kuasa}};")
    _setel(pbt, "Asli Peta Bidang Tanah Nomor : {{nomor_pbt}}, Tanggal {{tanggal_pbt}}, "
                "NIB. {{nib}};")
    _setel(_cari(dok, "Asli Peta Analisis Penatagunaan Tanah"), f"Asli {PAPT};")
    # tanda batas dan perbedaan luas ikut daftar dokumen berkas
    _buang(_cari(dok, "Asli Surat Pernyataan Pemasangan Tanda Batas"))
    _buang(_cari(dok, "Asli Surat Pernyataan Perbedaan Luas"))
    _setel(_cari(dok, "Berita Acara Pemeriksaan Lapang Tanggal"),
           "Berita Acara Pemeriksaan Lapang Tanggal {{tgl_bap}} oleh anggota yang telah "
           "ditandatangani.")

    # V. Dasar hukum: hanya SK susunan panitianya yang mengikuti berkas
    _panitia_sk(_cari(dok, "Tentang Susunan Tim Panitia Pemeriksaan Tanah"))

    # VI. Telaah subjek: badan hukum, bukan perorangan
    _setel(_persis(dok, "Perorangan"), "Badan Hukum")
    _setel(_cari(dok, "tempat tanggal lahir Gorontalo"),
           "Bahwa pemohon yaitu {{nama_penerima}} yang berkedudukan di {{hpbh_kedudukan}}, "
           "adalah Badan Hukum yang didirikan berdasarkan {{hpbh_akta_pendirian}}"
           "{{hpbh_pengesahan_frasa}}{{bh_diwakili}};")
    _setel(_cari(dok, "Berdasarkan Undang-Undang Nomor 12 Tahun 2006"),
           "Berdasarkan uraian tersebut di atas dapat disimpulkan bahwa pemohon merupakan Badan "
           "Hukum Indonesia menurut {{hpbh_dasar_bentuk}}{{hpbh_nib_frasa}}. Berdasarkan hal "
           f"tersebut, sesuai dengan {DASAR_SUBJEK}, {{{{nama_penerima}}}} memenuhi syarat "
           f"sebagai subyek {SEBUTAN}.")

    # IX. Pendapat anggota (lebih dulu: kalimatnya ikut memuat kalimat sempadan sungai)
    _pendapat(dok)

    # VII. Telaah objek — data yuridis
    _setel(_cari(dok, "Bahwa tanah yang dimohon adalah Tanah Negara"),
           "Bahwa tanah yang dimohon adalah Tanah Negara{{hpbh_asal_frasa}} yang seluruhnya "
           f"seluas {{{{luas_teks}}}} yang terletak di {LETAK}.")
    _setel(_cari(dok, "Memperoleh Tanah Dengan Riwayat"),
           "Bahwa {{nama_penerima}} (Pemohon) Memperoleh Tanah Dengan Riwayat Sebagai Berikut:")
    _riwayat(dok)
    _penguasaan(dok, 4)
    _setel(_cari(dok, "Bahwa status tanah yang dimohon adalah Tanah Negara"),
           "Bahwa status tanah yang dimohon adalah Tanah Negara{{hpbh_status_frasa}} yang "
           f"seluruhnya seluas {{{{luas_teks}}}} yang terletak di {LETAK} yang kemudian telah "
           "dikuasai secara fisik secara terus menerus oleh {{nama_penerima}} selaku pemohon"
           "{{hpbh_berdasarkan_sppf}};")
    _setel(_cari(dok, "telah dimohonkan untuk diberikan"),
           "Bahwa tanah tersebut telah dimohonkan untuk diberikan {{hpbh_hak_dimohon}} Pada "
           "Kantor Pertanahan Kabupaten Bone Bolango sesuai Surat permohonan hak yang dibuat "
           "dan ditandatangani oleh {{hpbh_pemohon_bertindak}}.")
    _setel(_cari(dok, "saat ini dipergunakan untuk"),
           "Bahwa bidang tanah tersebut saat ini dipergunakan untuk {{penggunaan_sekarang}};")
    guna = [p for p in dok.paragraphs if _teks(p).strip().startswith(
        "Bahwa penggunaan dan pemanfaatan bidang tanah tersebut")]
    if len(guna) != 4:
        raise JangkarHilang(f"empat kalimat penggunaan dan pemanfaatan (ketemu {len(guna)})")
    for i, p in enumerate(guna):
        _setel(p, GUNA + ("." if i == 0 else ";"))

    # data fisik
    ukur = _semua(dok, "telah dilaksanakan pengukuran secara kadastral")
    if len(ukur) != 2:
        raise JangkarHilang(f"dua kalimat pengukuran kadastral (ketemu {len(ukur)})")
    _setel(ukur[0], UKUR + ". Dengan batas-batas bidang tanah tersebut:")
    _setel(ukur[1], UKUR + ";")
    _batas(dok)
    _selisih(dok, 2)
    _setel(_cari(dok, "saat turun lapangan dipergunakan untuk"),
           "Bahwa bidang tanah yang dimohon saat turun lapangan dipergunakan untuk "
           "{{penggunaan_sekarang}};")
    _pertimbangan(dok, 2)
    _setel(_cari(dok, "Bahwa semua data fisik yang diuraikan di atas"),
           "Bahwa semua data fisik yang diuraikan di atas {{hpbh_data_fisik}}.")

    # VIII. Analisis
    _setel(_cari(dok, "tempat tanggal lahir"),
           "Bahwa {{nama_penerima}} yang berkedudukan di {{hpbh_kedudukan}} sesuai dengan "
           "{{hpbh_dasar_bentuk}} dan yang bersangkutan telah memiliki Akta Pendirian Badan "
           "Hukum dari Notaris dan Pengesahan Badan Hukum, Bahwa pemohon memenuhi syarat sebagai "
           f"subyek hak sesuai {DASAR_SUBJEK}.")
    _ganti_nama(_cari(dok, "dengan riwayat;"))
    _riwayat(dok)
    _ganti(_cari(dok, "Sehubungan dengan poin 7"), "poin 7 (tujuh)", "hal tersebut")
    _setel(_cari(dok, "bahwa berdasarkan hal-hal tersebut di atas, permohonan"),
           "bahwa berdasarkan hal-hal tersebut di atas, permohonan {{hpbh_hak_dimohon}} yang di "
           "mohonkan oleh {{hpbh_pemohon_bertindak}}{{hpbh_rekomendasi_frasa}} telah memenuhi "
           "ketentuan peraturan perundang-undangan dan kebijakan. Sehingga dapat "
           "dipertimbangkan untuk dikabulkan.")

    # X. Kesimpulan
    _setel(_cari(dok, "Bahwa aspek Yuridis terkait permohonan"),
           "Bahwa aspek Yuridis terkait permohonan {{hpbh_hak_dimohon}} atas {{nama_penerima}} "
           "{{hpbh_aspek_yuridis}};")
    _setel(_cari(dok, "Bahwa Tanah yang dimohon seluas"),
           "Bahwa Tanah yang dimohon seluas {{luas_teks}} sesuai Peta Bidang Tanah Nomor "
           f"{{{{nomor_pbt}}}} tanggal {{{{tanggal_pbt}}}}, NIB. {{{{nib}}}} terletak di {LETAK};")
    _setel(_cari(dok, "(poin 1 sampai dengan poin 4)"),
           "Berdasarkan uraian tersebut di atas (poin 1 sampai dengan poin 4), permohonan "
           "pemberian {{hpbh_hak_dimohon}} yang dimohonkan oleh {{nama_penerima}} atas tanah yang "
           "terletak di {{jenis_desa}} {{nama_desa}}, Kecamatan {{kecamatan}}, Kabupaten Bone "
           f"Bolango Provinsi Gorontalo dapat dipertimbangkan untuk diberikan {SEBUTAN}.")


# ---------------------------------------------------------------------- SK
def ubah_sk(dok):
    _buang_penyambung(dok)
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_sk}}")

    # Judul. Huruf besar-kecilnya mengikuti contoh: nama dan desa apa adanya.
    _mulai(_awal(dok, "PEMBERIAN"), "ATAS NAMA",
           "ATAS NAMA {{nama_penerima}} ATAS TANAH SELUAS {{luas_teks}} TERLETAK DI "
           "{{jenis_desa}} {{nama_desa}} KECAMATAN {{kecamatan}}")

    # Membaca
    _setel(_cari(dok, "Surat Permohonan Hak Milik tanggal"),
           "Surat Permohonan {{hpbh_hak_dimohon}} tanggal {{tanggal_permohonan}} dari "
           "{{nama_penerima}} berkedudukan di {{hpbh_kedudukan_lengkap}};")
    # Menimbang huruf a: uraian badan hukum lengkap (Lampiran VI Permen ATR/BPN 18/2021)
    _setel(_cari(dok, "sehingga telah memenuhi syarat sebagai subjek Hak Pakai"),
           "Bahwa {{bh_uraian_subjek}}{{bh_diwakili}}, sehingga telah memenuhi syarat sebagai "
           "subjek Hak Pakai Dengan Jangka Waktu;")
    _setel(_cari(dok, "telah dilakukan pengukuran secara kadastral"),
           "Bahwa tanah yang dimohon telah dilakukan pengukuran secara kadastral oleh Kantor "
           f"Pertanahan Kabupaten Bone Bolango, Seluas {{{{luas_teks}}}}, terletak di {LETAK}, "
           "sebagaimana telah diuraikan dalam Peta Bidang Tanggal {{tanggal_pbt}} Nomor "
           "{{nomor_pbt}} NIB. {{nib}};")
    _setel(_cari(dok, "telah dilakukan pemeriksaan oleh Panitia A"),
           "Bahwa tanah yang dimohon telah dilakukan pemeriksaan oleh Panitia A yang hasilnya "
           "dituangkan dalam Risalah Panitia Pemeriksaan Tanah A Kantor Pertanahan Kabupaten "
           "Bone Bolango Tanggal {{tgl_risalah}} Nomor {{nomor_risalah}}:")
    _setel(_cari(dok, "Bahwa status tanah yang dimohon merupakan Tanah Negara"),
           "Bahwa status tanah yang dimohon merupakan Tanah Negara{{hpbh_asal_frasa}} yang "
           "dikuasai pemohon, diperoleh dari :")
    _riwayat(dok)
    _penguasaan(dok, 1)
    _setel(_cari(dok, "Bahwa bidang tanah tersebut dipergunakan untuk"),
           "Bahwa bidang tanah tersebut dipergunakan untuk {{penggunaan_sekarang}};")
    _pertimbangan(dok, 1)
    _setel(_cari(dok, "Berdasarkan Peta Analisis Penatagunaan Tanah yang ditandatangani"),
           "Berdasarkan Peta Analisis Penatagunaan Tanah tanggal {{tanggal_peta_analisis}} yang "
           "ditandatangani oleh Kepala Seksi Penataan dan Pemberdayaan Kantor Pertanahan "
           "Kabupaten Bone Bolango, bidang tanah yang dimohon berada dalam {{rtrw}}, sehingga "
           f"bidang tanah tersebut {{{{kesesuaian}}}} dengan {PERDA_RTRW}"
           "{{hpbh_tata_ruang_frasa}}. Sehingga penggunaan tanahnya untuk {{hpbh_jenis_tanah}};")
    _selisih(dok, 1)
    _setel(_cari(dok, "Berkesimpulan permohonan tersebut"),
           "Berkesimpulan permohonan tersebut dapat dipertimbangkan untuk diberikan Hak Pakai "
           "Dengan Jangka Waktu kepada {{nama_penerima}}, Seluas {{luas_teks}} karena telah "
           "memenuhi persyaratan teknis, yuridis dan administratif.")

    # Mengingat: undang-undang bentuk badan hukumnya, lalu SK susunan panitia
    _sisip_sesudah(_cari(dok, "Undang-Undang Nomor 11 Tahun 2020 tentang Cipta Kerja"),
                   "{{?bh_dasar_bentuk}}{{bh_dasar_bentuk}};")
    _panitia_sk(_cari(dok, "Tentang Susunan Tim Panitia Pemeriksaan Tanah"))

    # Memutuskan: nilai diganti di tempatnya supaya cetak tebalnya tetap
    p = _awal(dok, "Menetapkan")
    _ganti(p, "SELAMA 30 (TIGA PULUH TAHUN)",
           "SELAMA {{jangka_tahun}} ({{jangka_terbilang_kapital}} TAHUN)")
    _ganti_pola(p, r"ATAS NAMA\s+Reagen Hulukati, S\.T ATAS TANAH SELUAS .*? TERLETAK DI\s+"
                   r"Desa Molotabu KECAMATAN Kabila Bone\s+",
                "ATAS NAMA {{nama_penerima}} ATAS TANAH SELUAS {{luas_teks}} TERLETAK DI "
                "{{jenis_desa}} {{nama_desa}} KECAMATAN {{kecamatan}} ")
    p = _awal(dok, "KESATU")
    _ganti_pola(p, r"Reagen Hulukati, S\.T bertempat tinggal di\s+Komp\..*?Papua,\s+",
                "{{nama_penerima}} berkedudukan di {{hpbh_kedudukan_lengkap}}, ")
    _ganti(p, "tanah Non Pertanian", "tanah {{hpbh_jenis_tanah}}")
    _ganti_pola(p, r"seluas 171 m. \(seratus tujuh puluh satu meter persegi\)\s+terletak di "
                   r"Desa Molotabu,\s+Kecamatan Kabila Bone, Kabupaten Bone Bolango Provinsi "
                   r"Gorontalo",
                f"seluas {{{{luas_teks}}}} terletak di {LETAK}")
    _ganti_pola(p, r"Peta Bidang tanggal 10 Juli 2024 Nomor 37/2024\s+NIB\. 30\.05\.08\.02\.00320",
                "Peta Bidang tanggal {{tanggal_pbt}} Nomor {{nomor_pbt}} NIB. {{nib}}")

    # Tanda tangan dan alamat penerima di bawahnya
    _ganti(_cari(dok, "Pada Tanggal"), "20 Februari 2026", "{{tgl_sk}}")
    nip = _awal(dok, "NIP.")
    berikut = []
    el = nip._p.getnext()
    while el is not None and len(berikut) < 2:
        if el.tag == qn("w:p") and "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
            berikut.append(Paragraph(el, nip._parent))
        el = el.getnext()
    if len(berikut) < 2 or _teks(berikut[0]).strip() != NAMA_CONTOH:
        raise JangkarHilang("alamat penerima di bawah tanda tangan")
    _setel(berikut[0], "{{nama_penerima}}")
    _setel(berikut[1], "{{hpbh_kedudukan_lengkap}}")


UBAH = {"risalah": ubah_risalah, "sk": ubah_sk}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[0] if argv else FOLDER_CONTOH
    contoh = _cari_contoh(folder)
    kurang = [j for j in UBAH if j not in contoh]
    if kurang:
        print(f"  ! contoh {', '.join(kurang)} tidak ditemukan di {folder}")
        return 1
    sarang = tempfile.mkdtemp(prefix="hpbh_")
    gagal = False
    try:
        for jenis, fungsi in UBAH.items():
            tujuan = os.path.join(jalur.TEMPLATE, f"{jenis}-hpbh.docx")
            try:
                dok = Document(_sebagai_docx(contoh[jenis], sarang))
                fungsi(dok)
                _buang_gambar_yatim(dok)
            except JangkarHilang as ex:
                gagal = True
                print(f"  ! {jenis}: kalimat jangkar tidak ditemukan di "
                      f"{os.path.basename(contoh[jenis])}: {ex}")
                continue
            cadangan = templat._cadangkan(f"{jenis}-hpbh")
            if cadangan:
                print(f"  cadangan {cadangan}")
            dok.save(tujuan)
            print(f"  dibuat  {tujuan}")
    finally:
        shutil.rmtree(sarang, ignore_errors=True)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
