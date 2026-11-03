# -*- coding: utf-8 -*-
"""Bangun tata naskah HGB Badan Hukum (risalah-hgbbh, sk-hgbbh).

Sumbernya contoh dokumen Kantah Bone Bolango di folder
`hak_guna_bangunan_badan_hukum/` (di samping folder app/): Risalah dan Konsep SK
pemberian Hak Guna Bangunan kepada sebuah PT. Kop, dasar hukum, diktum KESATU
sampai KELIMABELAS, dan tembusannya dipakai apa adanya; yang diganti hanya nilai
berkas contoh itu — nama PT, akta dan pengesahannya, luas, letak, nomor PBT,
riwayat, susunan panitia, dan tanggal — dengan penanda.

BAP-nya tidak dibangun: berkas HGB Badan Hukum memakai BAP baku (bap.docx).

Setiap perubahan mencari kalimat jangkarnya di dokumen contoh. Kalau tidak ketemu
(contohnya diganti dokumen lain), perkakas berhenti dan menyebut kalimat mana —
template yang terpasang tidak disentuh. Template lama dicadangkan dulu ke
templates/cadangan/, jadi bisa dipulihkan dari menu Template.

    python -m berkas.perkakas.siapkan_hgb_badan_hukum [folder-contoh]
"""
import copy
import os
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
    _ganti, _mulai, _run_berkotak, _sebagai_docx, _semua, _sisip_sesudah)

FOLDER_CONTOH = os.path.join(jalur.INDUK, "hak_guna_bangunan_badan_hukum")
NAMA_CONTOH = "PT. Sinar Berkah Tinelo"

# Penanda yang sama dipakai berulang di kedua dokumen
LETAK = ("{{jenis_desa}} {{nama_desa}}, Kecamatan {{kecamatan}}, Kabupaten Bone Bolango, "
         "Provinsi Gorontalo")
RIWAYAT = "{{*riwayat.uraian}}{{*riwayat._akhir}}"
PERDA_RTRW = ("Peraturan Daerah Kabupaten Bone Bolango Nomor 5 Tahun 2021 Tentang Rencana "
              "Tata Ruang Wilayah Kabupaten Bone Bolango Tahun 2021-2041")
PAPT = ("Peta Analisis Penatagunaan Tanah Tanggal {{tanggal_peta_analisis}} yang "
        "ditandatangani oleh Kepala Seksi Penataan dan Pemberdayaan Kantor Pertanahan "
        "Kabupaten Bone Bolango")
# «Bahwa bidang tanah yang dimohon sampai dengan saat ini dikuasai … oleh pemohon,
# yang diperoleh pemohon dari … berdasarkan … dan tidak dijadikan …»
KUASAI = ("Bahwa bidang tanah yang dimohon sampai dengan saat ini dikuasai terus menerus oleh "
          "pemohon{{hgb_diperoleh}} dan tidak dijadikan ataupun menjadi jaminan sesuatu hutang "
          "serta tidak dalam sengketa{{hgb_sesuai_sppf}}")
GUNA = ("Bahwa penggunaan dan pemanfaatan bidang tanah tersebut {{penggunaan_sekarang}} "
        f"berdasarkan {PAPT}, bidang tanah yang dimohon berada dalam {{{{rtrw}}}}, sehingga "
        f"bidang tanah tersebut {{{{kesesuaian}}}} dengan {PERDA_RTRW}{{{{hgb_tata_ruang_frasa}}}}. "
        "Sehingga penggunaan tanahnya untuk {{hgb_jenis_tanah}};")
UKUR = ("Bahwa atas bidang tanah yang dimohon Hak Guna Bangunan oleh {{nama_penerima}} telah "
        "dilaksanakan pengukuran secara kadastral oleh Seksi Survei dan Pemetaan Kantor "
        "Pertanahan Kabupaten Bone Bolango seluas {{luas_teks}} sesuai Peta Bidang Tanah Nomor "
        f"{{{{nomor_pbt}}}} tanggal {{{{tanggal_pbt}}}}, NIB. {{{{nib}}}} terletak di {LETAK}")


def _ganti_nama(p):
    _ganti(p, NAMA_CONTOH, "{{nama_penerima}}")


def _riwayat(dok, jangkar_awal, jangkar_kedua, ke=0):
    """Dua mata rantai riwayat pada contoh jadi satu paragraf berulang; paragraf
    «;» sisa mail merge sesudahnya ikut dibuang."""
    pertama = _cari(dok, jangkar_awal, ke)
    kedua = _cari(dok, jangkar_kedua, ke)
    sisa = kedua._p.getnext()
    _setel(pertama, RIWAYAT)
    _buang(kedua)
    if sisa is not None and "".join(x.text or "" for x in sisa.iter(qn("w:t"))).strip() == ";":
        sisa.getparent().remove(sisa)
    return pertama


# ----------------------------------------------------------------- Risalah
def ubah_risalah(dok):
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_risalah}}")
    _mulai(_cari(dok, "Pada hari Ini"), "Rabu",
           "{{hari_risalah}}, tanggal {{tgl_risalah_terbilang}} bulan {{bulan_risalah}} tahun "
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
    _ganti(p, "02/SK-75.03.HP.01/I/2026", "{{panitia_nomor_sk}}")
    _ganti(p, "05 Januari 2026", "{{panitia_tanggal_sk}}")
    _ganti(p, "5 (lima)", "{{panitia_jumlah}} ({{panitia_jumlah_terbilang}})")
    _mulai(p, "terletak di", "terletak di {{jenis_desa}} {{nama_desa}}, Kecamatan "
                             "{{kecamatan}}, Kabupaten Bone Bolango, untuk mengadakan "
                             "pemeriksaan atas Permohonan Hak Guna Bangunan atas Nama : "
                             "{{nama_penerima}}.")

    # I. Uraian mengenai pemohon
    _mulai(_awal(dok, "Nama Pemohon"), NAMA_CONTOH, "{{nama_penerima}}")
    _mulai(_awal(dok, "Domisili/Tempat Kedudukan"), "Kabupaten Bone Bolango",
           "{{hgb_kedudukan}}")
    _mulai(_awal(dok, "Akta Pendirian Badan Hukum"), "Nomor",
           "Nomor : {{bh_akta_nomor}} tanggal {{bh_akta_tanggal}}")
    _mulai(_awal(dok, "Pengesahan Badan Hukum"), "Nomor",
           "Nomor : {{bh_pengesahan_nomor}} tanggal {{bh_pengesahan_tanggal}}")
    _buang(_awal(dok, "Tahun 2025 tanggal 20 Juni 2025"))
    _mulai(_awal(dok, "Nomor Induk Berusaha"), "3007250003557", "{{bh_nib}}")
    _mulai(_awal(dok, "Bidang Usaha/Kegiatan"), "Real Estat", "{{bh_bidang_usaha}}")
    _buang(_awal(dok, "Atau Kontrak"))

    # II. Uraian mengenai tanah
    _mulai(_awal(dok, "Jalan", ":"), "-", "{{hgb_jalan}}")
    _mulai(_awal(dok, "Desa", "Dutohe"), "Dutohe", "{{nama_desa}}")
    _mulai(_awal(dok, "Kecamatan", "Kabila"), "Kabila", "{{kecamatan}}")
    _mulai(_awal(dok, "2.  Luas"), "4421", "{{luas_teks}}")
    _buang(_awal(dok, "satu meter persegi)"))
    _mulai(_awal(dok, "3.\tPeta Bidang Tanah"), "No.59/2025",
           "No.{{nomor_pbt}}, Tanggal {{tanggal_pbt}},")
    _mulai(_awal(dok, "NIB. 30.05"), "NIB.", "NIB. {{nib}}")

    # III. Uraian atas hak: «Jenis hak : Hak Guna Bangunan» tetap
    _mulai(_awal(dok, "2.\tJangka Waktu"), "30 Tahun", "{{jangka_tahun}} Tahun")
    _mulai(_awal(dok, "a.\tPenggunaan saat ini"), "Perumahan", "{{penggunaan_sekarang}}")
    _mulai(_awal(dok, "b. Rencana penggunaan"), "Perumahan", "{{rencana_penggunaan}}")

    # IV. Data pendukung: dokumen berkas + SPPF + PBT + kuasa + PAPT + BAP
    awal = _cari(dok, "Asli Surat permohonan hak yang dibuat")
    pbt = _cari(dok, "Asli Peta Bidang Tanah Nomor")
    _buang_di_antara(awal, pbt)
    _setel(awal, "{{*dokumen.uraian}};")
    _sisip_sesudah(awal, "{{?sppf}}Asli {{sppf}};")
    _setel(pbt, "Asli Peta Bidang Tanah Nomor : {{nomor_pbt}}, Tanggal {{tanggal_pbt}}, "
                "NIB. {{nib}};")
    _setel(_cari(dok, "Asli Surat kuasa mengurus"), "{{?surat_kuasa}}Asli {{surat_kuasa}};")
    # bukti PPh dan tanda batas ikut daftar dokumen berkas
    _buang(_cari(dok, "Asli Surat Keterangan Penelitian Formal"))
    _buang(_cari(dok, "Asli Surat Pernyataan Pemasangan Tanda Batas"))
    _setel(_cari(dok, "Asli Peta Analisis Penatagunaan Tanah"), f"Asli {PAPT};")
    _setel(_cari(dok, "Berita Acara Pemeriksaan Lapang Tanggal"),
           "Berita Acara Pemeriksaan Lapang Tanggal {{tgl_bap}} oleh anggota yang telah "
           "ditandatangani.")

    # V. Dasar hukum: hanya SK susunan panitianya yang mengikuti berkas
    p = _cari(dok, "Tentang Susunan Tim Panitia Pemeriksaan Tanah")
    _ganti(p, "02/SK-75.03.HP.01/I/2026", "{{panitia_nomor_sk}}")
    _ganti(p, "05 Januari 2026", "{{panitia_tanggal_sk}}")

    # VI. Telaah subjek
    _setel(_cari(dok, "Bahwa pemohon yaitu"),
           "Bahwa pemohon yaitu {{nama_penerima}} yang berkedudukan di {{hgb_kedudukan}}, "
           "adalah Badan Hukum yang didirikan berdasarkan {{hgb_akta_pendirian}}"
           "{{hgb_pengesahan_frasa}};")
    p = _cari(dok, "dapat disimpulkan bahwa pemohon merupakan Badan Hukum Indonesia")
    _ganti(p, "Undang-undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas",
           "{{hgb_dasar_bentuk}}")
    _ganti(p, "3007250003557", "{{bh_nib}}")
    _ganti_nama(_cari(dok, "memenuhi syarat sebagai Subyek Hak"))

    # VII. Telaah objek — data yuridis
    _setel(_cari(dok, "Bahwa tanah yang dimohon adalah Tanah Negara"),
           "Bahwa tanah yang dimohon adalah Tanah Negara{{hgb_asal_frasa}} seluruhnya seluas "
           f"{{{{luas_teks}}}} yang terletak di {LETAK}.")
    _setel(_cari(dok, "Memperoleh Tanah Dengan Riwayat"),
           "Bahwa {{nama_penerima}} (Pemohon) Memperoleh Tanah Dengan Riwayat Sebagai Berikut:")
    _riwayat(dok, "sebelumnya dikuasai oleh", "selanjutnya bidang tanah yang dimohon beralih")
    kuasai = [p for p in _semua(dok, "dikuasai terus menerus oleh pemohon, yang diperoleh")]
    if len(kuasai) != 3:
        raise JangkarHilang(f"tiga kalimat penguasaan tanah (ketemu {len(kuasai)})")
    _setel(kuasai[0], KUASAI + ".")
    for p in kuasai[1:]:
        _setel(p, KUASAI + ";")
    _setel(_cari(dok, "Bahwa status tanah yang dimohon adalah Tanah Negara"),
           "Bahwa status tanah yang dimohon adalah Tanah Negara{{hgb_asal_frasa}} yang "
           f"seluruhnya seluas {{{{luas_teks}}}} yang terletak di {LETAK} yang kemudian telah "
           "dikuasai secara fisik secara terus menerus oleh {{nama_penerima}} selaku pemohon"
           "{{hgb_berdasarkan_sppf}};")
    _ganti_nama(_cari(dok, "telah dimohonkan untuk diberikan Hak Guna Bangunan"))
    _setel(_cari(dok, "saat ini dipergunakan untuk"),
           "Bahwa bidang tanah tersebut saat ini dipergunakan untuk {{penggunaan_sekarang}};")
    guna = [p for p in dok.paragraphs if _teks(p).strip().startswith(
        "Bahwa penggunaan dan pemanfaatan bidang tanah tersebut")]
    if len(guna) != 4:
        raise JangkarHilang(f"empat kalimat penggunaan dan pemanfaatan (ketemu {len(guna)})")
    for p in guna:
        _setel(p, GUNA)

    # data fisik
    _setel(_cari(dok, "telah dilaksanakan pengukuran secara kadastral", 0),
           UKUR + ". Dengan batas-batas bidang tanah tersebut:")
    _batas(dok)
    _ganti(_cari(dok, "saat turun lapangan dipergunakan untuk"), "Non Pertanian",
           "{{hgb_jenis_tanah}}")
    _ganti_nama(_cari(dok, "semua data fisik yang diuraikan diatas"))

    # VIII. Analisis
    p = _cari(dok, "sesuai dengan Undang-Undang Nomor 40 Tahun 2007")
    _ganti_nama(p)
    _ganti(p, "berkedudukan di Kabupaten Bone Bolango", "berkedudukan di {{hgb_kedudukan}}")
    _ganti(p, "Undang-Undang Nomor 40 Tahun 2007 Tentang Perseroan Terbatas",
           "{{hgb_dasar_bentuk}}")
    _ganti_nama(_cari(dok, "dengan riwayat;"))
    _riwayat(dok, "sebelumnya dikuasai oleh", "selanjutnya bidang tanah yang dimohon beralih")
    _setel(_cari(dok, "belum bersertipikat dan tidak dijadikan"), "{{penguasaan_fisik}}.")
    _setel(_cari(dok, "telah dilaksanakan pengukuran secara kadastral", 1), UKUR + ";")
    _ganti(_cari(dok, "permohonan Hak Guna Bangunan yang di mohonkan oleh"),
           f"Zulkifli Abaidata bertindak untuk dan atas nama {NAMA_CONTOH}",
           "{{hgb_pemohon_bertindak}}")

    # IX. Pendapat anggota: satu pasang paragraf diulang per anggota panitia
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

    # X. Kesimpulan
    _ganti_nama(_cari(dok, "Bahwa aspek Yuridis terkait permohonan"))
    _setel(_cari(dok, "Bahwa Tanah yang dimohon seluas"),
           "Bahwa Tanah yang dimohon seluas {{luas_teks}} sesuai Peta Bidang Tanah Nomor "
           f"{{{{nomor_pbt}}}} tanggal {{{{tanggal_pbt}}}}, NIB. {{{{nib}}}} terletak di {LETAK};")
    _setel(_cari(dok, "(poin 1 sampai dengan poin 4)"),
           "Berdasarkan uraian tersebut di atas (poin 1 sampai dengan poin 4), permohonan "
           "pemberian Hak Guna Bangunan yang dimohonkan oleh {{nama_penerima}} atas tanah yang "
           "terletak di {{jenis_desa}} {{nama_desa}}, Kecamatan {{kecamatan}}, Kabupaten Bone "
           "Bolango Provinsi Gorontalo dapat dipertimbangkan untuk diberikan Hak Guna Bangunan.")


# ---------------------------------------------------------------------- SK
def _buang_penyambung(dok):
    """Kata penyambung contoh («yang …», «Kepala …») ditulis tangan per halaman di
    kotak teks; aplikasi menambahkannya sendiri lewat Word sesudah dokumen dirakit.
    Kotak label «Membaca :», «Menimbang :», «Mengingat:» tetap."""
    n = 0
    for r, isi in list(_run_berkotak(dok)):
        if isi.strip().endswith(("...", "…")):
            r.getparent().remove(r)
            n += 1
    return n


def ubah_sk(dok):
    _buang_penyambung(dok)
    _mulai(_awal(dok, "NOMOR"), "NOMOR", "NOMOR : {{nomor_sk}}")

    # Judul. Huruf besar-kecilnya mengikuti contoh: nama dan desa apa adanya.
    _ganti_nama(_awal(dok, "PEMBERIAN HAK GUNA BANGUNAN ATAS NAMA"))
    _setel(_awal(dok, "ATAS TANAH SELUAS"),
           "ATAS TANAH SELUAS {{luas_teks}} TERLETAK DI {{jenis_desa}} {{nama_desa}} KECAMATAN "
           "{{kecamatan}} KABUPATEN BONE BOLANGO PROVINSI GORONTALO")

    # Membaca
    _setel(_cari(dok, "Surat Permohonan Hak Guna Bangunan tanggal"),
           "Surat Permohonan Hak Guna Bangunan tanggal {{tanggal_permohonan}} dari "
           "{{nama_penerima}} berkedudukan di {{hgb_kedudukan_lengkap}};")
    # Menimbang
    _setel(_cari(dok, "sehingga telah memenuhi syarat sebagai subjek Hak Guna Bangunan"),
           "Bahwa {{nama_penerima}}, berkedudukan di {{hgb_kedudukan_lengkap}}, sehingga telah "
           "memenuhi syarat sebagai subjek Hak Guna Bangunan;")
    _setel(_cari(dok, "telah dilakukan pengukuran secara kadastral"),
           "Bahwa tanah yang dimohon telah dilakukan pengukuran secara kadastral oleh Kantor "
           f"Pertanahan Kabupaten Bone Bolango, Seluas {{{{luas_teks}}}}, terletak di {LETAK}, "
           "sebagaimana telah diuraikan dalam Peta Bidang Tanggal {{tanggal_pbt}} Nomor "
           "{{nomor_pbt}} NIB {{nib}};")
    _setel(_cari(dok, "telah dilakukan pemeriksaan oleh Panitia A"),
           "Bahwa tanah yang dimohon telah dilakukan pemeriksaan oleh Panitia A yang hasilnya "
           "dituangkan dalam Risalah Panitia Pemeriksaan Tanah A Kantor Pertanahan Kabupaten "
           "Bone Bolango Tanggal {{tgl_risalah}} Nomor {{nomor_risalah}}, antara lain "
           "dinyatakan:")
    _setel(_cari(dok, "Bahwa status tanah yang dimohon merupakan Tanah Negara"),
           "Bahwa status tanah yang dimohon merupakan Tanah Negara{{hgb_asal_frasa}} yang "
           "diperoleh dari :")
    _riwayat(dok, "sebelumnya bidang tanah yang dimohon dikuasai oleh",
             "selanjutnya bidang tanah yang dimohon beralih")
    _setel(_cari(dok, "dikuasai terus menerus oleh pemohon, yang diperoleh"), KUASAI + ";")
    _setel(_cari(dok, "Bahwa bidang tanah tersebut dipergunakan untuk"),
           "Bahwa bidang tanah tersebut dipergunakan untuk {{penggunaan_sekarang}};")
    _setel(_cari(dok, "Bahwa penggunaan tanah di lapangan adalah"),
           "Bahwa penggunaan tanah di lapangan adalah {{penggunaan_sekarang}} dan rencana "
           "penggunaan tanah berupa {{rencana_penggunaan}}. Berdasarkan Peta Analisis "
           "Penatagunaan Tanah tanggal {{tanggal_peta_analisis}} yang ditandatangani oleh "
           "Kepala Seksi Penataan dan Pemberdayaan Kantor Pertanahan Kabupaten Bone Bolango, "
           "bidang tanah yang dimohon berada dalam {{rtrw}}, sehingga penggunaan tanah bidang "
           f"tanah tersebut {{{{kesesuaian}}}} dengan {PERDA_RTRW}{{{{hgb_tata_ruang_frasa}}}} "
           "sehingga penggunaan tanahnya untuk {{hgb_jenis_tanah}};")
    _setel(_cari(dok, "Berkesimpulan permohonan tersebut"),
           "Berkesimpulan permohonan tersebut dapat dipertimbangkan untuk diberikan Hak Guna "
           "Bangunan kepada {{nama_penerima}}, Seluas {{luas_teks}} karena telah memenuhi "
           "persyaratan teknis, yuridis dan administratif.")

    # Mengingat: hanya SK susunan panitianya yang mengikuti berkas
    p = _cari(dok, "tentang Susunan Tim Panitia Pemeriksaan Tanah")
    _ganti(p, "02/SK-75.03.HP.01/I/2026", "{{panitia_nomor_sk}}")
    _ganti(p, "05 Januari 2026", "{{panitia_tanggal_sk}}")
    _ganti(p, "Tahun 2025.", "Tahun {{hgb_panitia_tahun}}.")

    # Memutuskan: nilai diganti di tempatnya supaya cetak tebalnya tetap
    p = _awal(dok, "Menetapkan")
    _ganti_nama(p)
    _ganti(p, "2116 m² (dua ribu seratus enam belas meter persegi)", "{{luas_teks}}")
    _ganti(p, "Desa Dutohe Barat KECAMATAN Kabila",
           "{{jenis_desa}} {{nama_desa}} KECAMATAN {{kecamatan}}")
    p = _awal(dok, "KESATU")
    _ganti_nama(p)
    _ganti(p, "Kabupaten Bone Bolango, Provinsi Gorontalo,", "{{hgb_kedudukan_lengkap}},")
    _ganti(p, "tanah Non Pertanian", "tanah {{hgb_jenis_tanah}}")
    _ganti(p, "2116 m² (dua ribu seratus enam belas meter persegi)", "{{luas_teks}}")
    _ganti(p, "Desa Dutohe Barat, Kecamatan Kabila, Kabupaten Bone Bolango, Provinsi Gorontalo",
           LETAK)
    _ganti(p, "tanggal 20 September 2025 Nomor 58/2025 NIB.30.05.02.12.02020",
           "tanggal {{tanggal_pbt}} Nomor {{nomor_pbt}} NIB.{{nib}}")

    # Tanda tangan dan alamat penerima di bawahnya
    _ganti(_cari(dok, "Pada Tanggal"), "23 Februari 2026", "{{tgl_sk}}")
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
    _setel(berikut[1], "{{hgb_kedudukan_lengkap}}")


UBAH = {"risalah": ubah_risalah, "sk": ubah_sk}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[0] if argv else FOLDER_CONTOH
    contoh = _cari_contoh(folder)
    kurang = [j for j in UBAH if j not in contoh]
    if kurang:
        print(f"  ! contoh {', '.join(kurang)} tidak ditemukan di {folder}")
        return 1
    sarang = tempfile.mkdtemp(prefix="hgbbh_")
    gagal = False
    try:
        for jenis, fungsi in UBAH.items():
            tujuan = os.path.join(jalur.TEMPLATE, f"{jenis}-hgbbh.docx")
            try:
                dok = Document(_sebagai_docx(contoh[jenis], sarang))
                fungsi(dok)
                _buang_gambar_yatim(dok)
            except JangkarHilang as ex:
                gagal = True
                print(f"  ! {jenis}: kalimat jangkar tidak ditemukan di "
                      f"{os.path.basename(contoh[jenis])}: {ex}")
                continue
            cadangan = templat._cadangkan(f"{jenis}-hgbbh")
            if cadangan:
                print(f"  cadangan {cadangan}")
            dok.save(tujuan)
            print(f"  dibuat  {tujuan}")
    finally:
        shutil.rmtree(sarang, ignore_errors=True)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
