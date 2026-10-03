# -*- coding: utf-8 -*-
"""Perakit HTML. Semua halaman dibangun di sini sebagai teks biasa."""
import datetime as dt
import html
import json
import os
import re
import urllib.parse as up

from . import db, izin, jalur, pemeliharaan, pradaftar, util, wilayah
from . import susun_kelengkapan as SUSUN
from .dokumen import foto as foto_lapang, konteks, templat

KEGIATAN = [("baru", "Pemberian hak baru"), ("perpanjangan", "Perpanjangan jangka waktu"),
            ("pembaruan", "Pembaruan hak"), ("peningkatan", "Peningkatan hak")]
ASAL_TANAH = [("tanah_negara", "Tanah Negara"), ("hak_pengelolaan", "Tanah Hak Pengelolaan")]
KEWENANGAN = [("kantah", "Kepala Kantor Pertanahan"), ("kanwil", "Kepala Kantor Wilayah"),
              ("menteri", "Menteri ATR/BPN")]
SUBJEK = [("perorangan", "Perorangan"), ("badan_hukum", "Badan hukum"),
          ("instansi", "Instansi / BUMN / BUMD")]
STATUS = [("draf", "Draf"), ("diperiksa", "Diperiksa"), ("selesai", "Selesai"), ("ditolak", "Ditolak")]
KESIMPULAN = [("dikabulkan", "Dapat dikabulkan"), ("ditolak", "Ditolak"),
              ("dilengkapi", "Perlu dilengkapi")]
PERAN_LAIN = [("pemilik_sebelumnya", "Pemilik sebelumnya"), ("ahli_waris", "Ahli waris"),
              ("saksi", "Saksi"), ("wakif", "Wakif"), ("nazhir", "Nazhir")]


def e(v):
    return html.escape("" if v is None else str(v), quote=True)


def pilih(nama, daftar, terpilih, kosong=None, atribut=""):
    o = []
    if kosong:
        o.append(f'<option value="">{e(kosong)}</option>')
    for nilai, label in daftar:
        s = " selected" if str(nilai) == str(terpilih or "") else ""
        o.append(f'<option value="{e(nilai)}"{s}>{e(label)}</option>')
    return f'<select name="{e(nama)}" {atribut}>{"".join(o)}</select>'


def bidang(label, nama, nilai="", tipe="text", petunjuk="", wajib=False, atribut=""):
    w = ' <span class="wajib">*</span>' if wajib else ""
    p = f'<div class="petunjuk">{e(petunjuk)}</div>' if petunjuk else ""
    return (f'<div><label for="f_{e(nama)}">{e(label)}{w}</label>'
            f'<input type="{tipe}" id="f_{e(nama)}" name="{e(nama)}" value="{e(nilai)}" {atribut}>{p}</div>')


def area(label, nama, nilai="", petunjuk="", baris=3):
    p = f'<div class="petunjuk">{e(petunjuk)}</div>' if petunjuk else ""
    return (f'<div><label for="f_{e(nama)}">{e(label)}</label>'
            f'<textarea id="f_{e(nama)}" name="{e(nama)}" rows="{baris}">{e(nilai)}</textarea>{p}</div>')


def kotak(label, nama, daftar, terpilih, kosong=None, petunjuk="", atribut=""):
    p = f'<div class="petunjuk">{e(petunjuk)}</div>' if petunjuk else ""
    s = pilih(nama, daftar, terpilih, kosong, f'id="f_{e(nama)}" ' + atribut)
    return f'<div><label for="f_{e(nama)}">{e(label)}</label>{s}{p}</div>'


def _rincian_bh_hak_pakai(d, bh):
    """Rincian badan hukum yang dicetak Menimbang huruf a SK Hak Pakai.

    Hanya tampil pada berkas Hak Pakai — tata naskah lain tidak memakainya. Pada
    jenis hak lain isinya tetap ikut terkirim sebagai medan tersembunyi, supaya
    menyimpan berkas yang jenis haknya sempat diganti tidak menghapusnya.
    """
    nilai = {kol: bh.get(kol) or "" for kol, *_ in db.KOLOM_BH_RINCIAN}
    if not konteks.hak_pakai(d):
        return "".join(f'<input type="hidden" name="bh_{e(kol)}" value="{e(v)}">'
                       for kol, v in nilai.items())
    kolom = [bidang(label, "bh_" + kol, nilai[kol], tipe or "text", petunjuk)
             for kol, label, tipe, petunjuk in db.KOLOM_BH_RINCIAN]
    baris = lambda a, b: f'<div class="grid g4" style="margin-top:.75rem">{"".join(kolom[a:b])}</div>'
    return f"""<h3 style="margin:1.1rem 0 .2rem">Rincian untuk SK Hak Pakai</h3>
<p class="petunjuk" style="margin:0">Dicetak di Menimbang huruf a SK sesuai format
Lampiran VI Permen ATR/BPN 18/2021. Yang dikosongkan dilewati, tidak dicetak
sebagai titik-titik.</p>
{baris(0, 4)}{baris(4, 8)}{baris(8, 11)}{baris(11, 15)}"""


# Urutan pengisian berkas baru. Tiga langkah pertama wajib supaya berkasnya
# berarti; tiga sisanya boleh menyusul, dan itu dikatakan terang-terangan
# supaya petugas baru tidak merasa harus melengkapi semuanya sekaligus.
LANGKAH_BARU = [
    ("p-berkas", "Jenis permohonan", False,
     "Hak apa yang dimohon dan untuk kegiatan apa. Pilihan ini menentukan template "
     "dokumen yang dipakai serta isian yang muncul di langkah berikutnya."),
    ("p-pihak", "Pihak", False,
     "Siapa yang memohon dan menerima haknya. Untuk perorangan, NIK-nya 16 digit; "
     "kalau dikuasakan, isi juga nama penerima kuasa."),
    ("p-tanah", "Bidang tanah", False,
     "Letak, luas, dan batas tanahnya — disalin dari Peta Bidang Tanah hasil "
     "pengukuran. Desa/kelurahan menentukan kepala desa yang ikut jadi anggota Panitia A."),
    ("p-asal", "Riwayat tanah", True,
     "Asal usul penguasaan tanahnya, atau data hak lama untuk perpanjangan dan "
     "pembaruan."),
    ("p-dokumen", "Dokumen", True,
     "Surat-surat yang dilampirkan permohonan. Slot bakunya sudah disiapkan; "
     "yang belum ada boleh dibiarkan kosong."),
    ("p-foto", "Foto lapangan", True,
     f"Foto pemeriksaan lapang untuk lampiran BAP, paling sedikit "
     f"{foto_lapang.MINIMAL} buah. Bisa juga diunggah belakangan."),
]


def _bilah_langkah(butir):
    """Bilah langkah bernomor. Tombolnya tetap tombol tab yang sama — app.js
    tidak perlu tahu bedanya, hanya gayanya yang lain."""
    tombol = []
    for i, (panel, label, opsional, _) in enumerate(butir, 1):
        cap = '<span class="cap abu">boleh nanti</span>' if opsional else ""
        tombol.append(
            f'<button type="button" role="tab" id="t-{e(panel)}" aria-controls="{e(panel)}"'
            f' aria-selected="false" tabindex="-1" data-panel="{e(panel)}">'
            f'<span class="tahap-no">{i}</span>'
            f'<span class="tahap-teks">{e(label)}{cap}</span></button>')
    return (f'<div class="tab tahap" role="tablist" data-tab="berkas-baru"'
            f' data-tahap="1" aria-label="Langkah pengisian">{"".join(tombol)}</div>')


def _kaki_langkah(i, n, petunjuk):
    """Petunjuk singkat di atas panel, dan tombol maju/mundur di bawahnya."""
    kembali = ('<button type="button" class="btn" data-tahap-mundur>&larr; Kembali</button>'
               if i > 1 else '<a class="btn" href="/berkas">&larr; Batal</a>')
    maju = ('<button type="button" class="btn utama" data-tahap-maju>Lanjut &rarr;</button>'
            if i < n else
            '<button class="btn utama" type="submit" form="form-berkas">Simpan berkas</button>')
    lewati = ('<button type="button" class="btn sunyi" data-tahap-maju>Lewati</button>'
              if i < n else "")
    return (f'<p class="tahap-petunjuk"><b>Langkah {i} dari {n}.</b> {petunjuk}</p>',
            f'<div class="tahap-kaki">{kembali}<span class="tahap-isi"></span>'
            f'{lewati}{maju}</div>')


def _tab(nama, butir):
    """Bilah tab. butir = (id_panel, label) atau (id_panel, label, lencana HTML).
    Peran ARIA dan panelnya dijodohkan app.js saat halaman dibuka."""
    tombol = "".join(
        f'<button type="button" role="tab" id="t-{e(b[0])}" aria-controls="{e(b[0])}"'
        f' aria-selected="false" tabindex="-1" data-panel="{e(b[0])}">{e(b[1])}'
        f'{b[2] if len(b) > 2 else ""}</button>' for b in butir)
    return (f'<div class="tab" role="tablist" data-tab="{e(nama)}"'
            f' aria-label="Bagian halaman">{tombol}</div>')


# --------------------------------------------------------- penanda berkas statis
def _cap_statis(nama):
    """Waktu ubah berkas, dilekatkan ke alamatnya sebagai ?v=.

    Tanpa ini, peramban yang sudah menyinggah style.css atau app.js lama tetap
    memakainya sampai singgahannya kedaluwarsa — dan halaman baru dengan
    JavaScript lama adalah halaman yang setengah rusak. Dihitung sekali saat
    modul dimuat; memasang pembaruan berarti menyalakan ulang layanannya,
    dan di situlah nilainya ikut berubah.
    """
    try:
        return str(int(os.path.getmtime(os.path.join(jalur.STATIS, nama))))
    except OSError:
        return ""


CAP_CSS = _cap_statis("style.css")
CAP_JS = _cap_statis("app.js")


# ------------------------------------------------------------------- ikon
# Satu sprite SVG di awal halaman; sisanya cuma menunjuk ke <symbol> ini,
# jadi tidak ada permintaan tambahan ke server dan ikonnya ikut warna teks.
SPRITE = """<svg class="sprite" aria-hidden="true" focusable="false"><defs>
<symbol id="i-pradaftar" viewBox="0 0 24 24"><path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z"/>
  <path d="M8 6H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2"/>
  <path d="M8.5 12.5l1.7 1.7 3.3-3.4M15 17H9"/></symbol>
<!-- Bentuk menu sengaja dibuat berbeda satu sama lain (map, tabung data,
     petak tata letak, roda gigi) supaya tetap bisa dibedakan saat menu
     kuncup dan tinggal ikon. -->
<symbol id="i-berkas" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
  <path d="M3 10h18"/></symbol>
<symbol id="i-referensi" viewBox="0 0 24 24"><ellipse cx="12" cy="5.5" rx="8" ry="2.8"/>
  <path d="M4 5.5v13c0 1.55 3.58 2.8 8 2.8s8-1.25 8-2.8v-13"/><path d="M4 12c0 1.55 3.58 2.8 8 2.8s8-1.25 8-2.8"/></symbol>
<symbol id="i-template" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="7" rx="1.5"/>
  <rect x="3" y="14" width="9" height="7" rx="1.5"/><rect x="16" y="14" width="5" height="7" rx="1.5"/></symbol>
<symbol id="i-pengaturan" viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
  <circle cx="12" cy="12" r="3"/></symbol>
<symbol id="i-keluar" viewBox="0 0 24 24"><path d="M15 17l5-5-5-5"/><path d="M20 12H9"/>
  <path d="M12 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></symbol>
<symbol id="i-kuncup" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></symbol>
<symbol id="i-tambah" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
<symbol id="i-pegang" viewBox="0 0 24 24"><circle cx="9" cy="6" r=".6"/><circle cx="15" cy="6" r=".6"/>
  <circle cx="9" cy="12" r=".6"/><circle cx="15" cy="12" r=".6"/><circle cx="9" cy="18" r=".6"/>
  <circle cx="15" cy="18" r=".6"/></symbol>
<symbol id="i-layar" viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></symbol>
</defs></svg>"""


def ikon(nama, kelas=""):
    k = f" {kelas}" if kelas else ""
    return (f'<svg class="ikon{k}" aria-hidden="true" focusable="false">'
            f'<use href="#i-{nama}"></use></svg>')


# ------------------------------------------------------------------ layout
MENU = [("/pradaftar", "Pradaftar", "pradaftar"),
        ("/berkas", "Berkas", "berkas"),
        ("/referensi", "Data referensi", "referensi"),
        ("/template", "Template", "template"),
        ("/pengaturan", "Pengaturan", "pengaturan")]


def _menu_samping(pengguna, aktif):
    """Menu samping. Template disembunyikan dari petugas — lihat izin.py."""
    butir = []
    for alamat, label, gbr in MENU:
        if alamat == "/template" and not izin.admin(pengguna):
            continue
        kelas = " aktif" if aktif == alamat else ""
        butir.append(f'<a href="{alamat}" class="samping-butir{kelas}" '
                     f'title="{e(label)}">{ikon(gbr)}<span>{e(label)}</span></a>')
    peran = "admin" if izin.admin(pengguna) else "petugas"
    awal = e((pengguna["nama"] or "?").strip()[:1].upper())
    return f"""<aside class="samping" id="samping">
<div class="samping-kepala">
  <a class="merek" href="/berkas"><span class="tanda">S</span>
    <span class="nama-panjang">SIPANTAS</span></a>
  <button type="button" class="ikon-btn kuncup-btn" id="kuncup"
          aria-label="Kuncupkan menu" title="Kuncupkan menu">{ikon("kuncup")}</button>
</div>
<nav class="samping-menu" aria-label="Menu utama">{"".join(butir)}</nav>
<div class="samping-kaki">
  <div class="siapa" title="{e(pengguna["nama"])} · {peran}">
    <span class="awal">{awal}</span>
    <span class="siapa-teks"><b>{e(pengguna["nama"])}</b>
      <span class="cap {'aksen' if peran == 'admin' else 'abu'}">{peran}</span></span>
  </div>
  <a class="samping-butir" href="/keluar" title="Keluar">{ikon("keluar")}<span>Keluar</span></a>
</div>
</aside>"""


def layout(judul, isi, pengguna=None, aktif="", pesan=None, fokus=False):
    """Kerangka tiap halaman.

    Sudah masuk  -> menu samping tetap + bilah atas yang hanya muncul di layar
                    sempit, tempat tombol pembuka lacinya.
    Belum masuk  -> tanpa kerangka sama sekali; halaman masuk berdiri sendiri
                    di tengah layar.
    fokus=True   -> sudah masuk, tetapi tanpa menu samping dan selebar layar:
                    halaman kerja yang ditinggalkan lewat tombol Kembali-nya
                    sendiri (periksa kelengkapan layar penuh).
    """
    blok_pesan = ""
    if pesan:
        jenis, teks = pesan
        blok_pesan = f'<div class="pesan {e(jenis)}">{teks}</div>'

    if not pengguna:
        badan = f"<main>{blok_pesan}{isi}</main>"
    elif fokus:
        badan = f'<main class="fokus">{blok_pesan}{isi}</main>'
    else:
        badan = f"""<div class="kerangka">{_menu_samping(pengguna, aktif)}
<div class="wadah">
  <header class="atas">
    <button type="button" class="ikon-btn" id="buka-nav"
            aria-label="Buka menu" aria-expanded="false">{ikon("menu")}</button>
    <a class="merek" href="/berkas"><span class="tanda">S</span>
      <span class="nama-panjang">SIPANTAS</span></a>
  </header>
  <main>{blok_pesan}{isi}</main>
</div>
<div class="tabir" id="tabir" hidden></div>
</div>"""

    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(judul)} · SIPANTAS</title>
<link rel="stylesheet" href="/static/style.css?v={CAP_CSS}">
<script>/* dipasang sebelum halaman digambar supaya menu tak berkedip lebar
  dulu baru menguncup */
  try{{if(localStorage.getItem("menu-kuncup")==="1")
    document.documentElement.classList.add("menu-kuncup");}}catch(e){{}}</script>
</head><body>{SPRITE}{badan}
<script src="/static/app.js?v={CAP_JS}"></script></body></html>"""


# ------------------------------------------------------------------- masuk
def halaman_masuk(galat=None):
    p = f'<div class="pesan galat">{e(galat)}</div>' if galat else ""
    isi = f"""<div class="masuk">
  <div class="merek"><span class="tanda">S</span> SIPANTAS</div>
  <div class="kartu"><div class="badan">
    {p}
    <form method="post" action="/masuk" class="grid">
      {bidang("Nama pengguna", "username", "", atribut="autofocus autocomplete=username")}
      {bidang("Kata sandi", "sandi", "", tipe="password", atribut="autocomplete=current-password")}
      <button class="btn utama" type="submit">Masuk</button>
    </form>
  </div></div>
  <p class="petunjuk" style="text-align:center;margin-top:.8rem">
    Kantor Pertanahan Kabupaten Bone Bolango</p>
</div>"""
    return layout("Masuk", isi)


# ------------------------------------------------------------- daftar berkas
def _cap_pemilik(b):
    """Siapa yang menginput, dan apakah baris ini bisa disunting pembacanya.

    Berkas hasil impor Excel tidak punya pemilik; ditandai "arsip impor"
    supaya jelas kenapa tidak bisa diubah petugas.
    """
    if b["dibuat_oleh"] is None:
        nama = '<span class="cap abu">arsip impor</span>'
    else:
        nama = f'<span class="petunjuk">{e(b["pemilik"] or "-")}</span>'
    if b.get("boleh_ubah"):
        return nama
    return nama + ' <span class="cap abu" title="hanya bisa dilihat">lihat</span>'


PER_HALAMAN = (10, 25, 50, 100)
PER_BAWAAN = 25
# Kunci query string -> judul yang tampil di cap "saringan aktif".
SARINGAN = [("hak", "Jenis hak"), ("status", "Status"), ("kegiatan", "Kegiatan"),
            ("kec", "Kecamatan"), ("q", "Cari")]


def _alamat_daftar(saringan, **ubah):
    """Alamat /berkas dengan saringan yang sama, kecuali yang diubah. Nilai
    kosong dan nilai bawaan dibuang supaya alamatnya tetap pendek."""
    p = {**saringan, **ubah}
    p = {kunci: v for kunci, v in p.items() if v not in ("", None)}
    if p.get("per") == PER_BAWAAN:
        del p["per"]
    if p.get("hal") == 1:
        del p["hal"]
    return "/berkas" + ("?" + up.urlencode(p) if p else "")


def _nomor_halaman(kini, akhir):
    """1 … 4 5 6 … 12 — halaman pertama, terakhir, dan tetangga halaman kini.
    None berarti elipsis. Celah selebar satu halaman diisi nomornya saja,
    karena "1 … 3" lebih membingungkan daripada "1 2 3"."""
    tampil = sorted(n for n in {1, 2, kini - 1, kini, kini + 1, akhir - 1, akhir}
                    if 1 <= n <= akhir)
    hasil, sebelum = [], 0
    for n in tampil:
        if n - sebelum == 2:
            hasil.append(sebelum + 1)
        elif n - sebelum > 2:
            hasil.append(None)
        hasil.append(n)
        sebelum = n
    return hasil


def _paging(saringan, kini, akhir, awal, ujung, jumlah):
    if not jumlah:
        return ""
    nomor = []
    for n in _nomor_halaman(kini, akhir):
        if n is None:
            nomor.append('<span class="halaman-elipsis" aria-hidden="true">…</span>')
        elif n == kini:
            nomor.append(f'<span class="btn kecil halaman-no aktif" aria-current="page">{n}</span>')
        else:
            nomor.append(f'<a class="btn kecil halaman-no" href="{e(_alamat_daftar(saringan, hal=n))}"'
                         f' aria-label="Halaman {n}">{n}</a>')

    def panah(n, teks, rel):
        if 1 <= n <= akhir and n != kini:
            return f'<a class="btn kecil" rel="{rel}" href="{e(_alamat_daftar(saringan, hal=n))}">{teks}</a>'
        return f'<span class="btn kecil" aria-disabled="true">{teks}</span>'

    per = "".join(f'<option value="{n}"{" selected" if n == saringan["per"] else ""}>{n}</option>'
                  for n in PER_HALAMAN)
    return f"""<nav class="halaman" aria-label="Halaman daftar berkas">
  <p class="halaman-info">Menampilkan <b>{awal}–{ujung}</b> dari <b>{jumlah}</b> berkas</p>
  <div class="halaman-nomor">{panah(kini - 1, "&lsaquo; Sebelumnya", "prev")}
    {"".join(nomor)}{panah(kini + 1, "Berikutnya &rsaquo;", "next")}</div>
  <label class="halaman-per">Tampilkan
    <select name="per" form="form-saring" aria-label="Jumlah berkas per halaman">{per}</select>
    per halaman</label>
</nav>"""


def _form_saring(k, baris, saringan):
    """Kotak cari + empat dropdown. Setiap pilihan menyebut jumlah berkasnya,
    supaya pengguna tahu sebelum memilih apakah hasilnya bakal kosong."""
    def hitung(kunci):
        n = {}
        for b in baris:
            n[b[kunci] or ""] = n.get(b[kunci] or "", 0) + 1
        return n

    n_hak = hitung("kode_hak")
    nama_hak = {r["kode"]: r["nama"] for r in k.execute(
        "SELECT kode, nama FROM ref_jenis_hak WHERE aktif=1 ORDER BY urut")}
    # Kode lama yang tak aktif lagi di referensi tapi masih dipakai berkas tetap
    # bisa dipilih — kalau tidak, berkasnya tak terjangkau saringan.
    for kode in n_hak:
        if kode and kode not in nama_hak:
            nama_hak[kode] = kode
    opsi_hak = [(kode, f"{kode} — {nama} ({n_hak.get(kode, 0)})") for kode, nama in nama_hak.items()]

    n_status = hitung("status")
    opsi_status = [(v, f"{l} ({n_status.get(v, 0)})") for v, l in STATUS]

    n_keg = hitung("jenis_kegiatan")
    opsi_keg = [(v, f"{l} ({n_keg.get(v, 0)})") for v, l in KEGIATAN]

    n_kec = hitung("kecamatan")
    opsi_kec = [(v, f"{v} ({n_kec[v]})") for v in sorted(x for x in n_kec if x)]

    return f"""<form class="saringan" id="form-saring" method="get" action="/berkas" role="search"
      data-saring-otomatis>
  <div class="saringan-cari">
    <label for="cari-berkas">Cari berkas</label>
    <div class="cari-kotak">
      <input type="search" id="cari-berkas" name="q" value="{e(saringan['q'])}"
             placeholder="Nama penerima, kuasa, desa, nomor risalah / SK…" autocomplete="off">
      <button class="btn utama" type="submit">Cari</button>
    </div>
  </div>
  <div class="saringan-pilih">
    {kotak("Jenis hak", "hak", opsi_hak, saringan["hak"], "Semua jenis hak")}
    {kotak("Status", "status", opsi_status, saringan["status"], "Semua status")}
    {kotak("Kegiatan", "kegiatan", opsi_keg, saringan["kegiatan"], "Semua kegiatan")}
    {kotak("Kecamatan", "kec", opsi_kec, saringan["kec"], "Semua kecamatan")}
  </div>
  <noscript><button class="btn" type="submit">Terapkan saringan</button></noscript>
</form>"""


def _saringan_aktif(saringan):
    """Cap untuk tiap saringan yang terpasang; klik × untuk melepas satu."""
    label = {"hak": {}, "status": dict(STATUS), "kegiatan": dict(KEGIATAN)}
    cap = []
    for kunci, judul in SARINGAN:
        v = saringan.get(kunci)
        if not v:
            continue
        teks = label.get(kunci, {}).get(v, v)
        cap.append(f'<a class="saring-cap" href="{e(_alamat_daftar(saringan, **{kunci: "", "hal": 1}))}"'
                   f' title="Lepas saringan ini">{e(judul)}: <b>{e(teks)}</b>'
                   f'<span class="saring-x" aria-label="lepas">×</span></a>')
    if not cap:
        return ""
    bersih = _alamat_daftar({"per": saringan["per"]})
    return (f'<div class="saringan-aktif"><span class="petunjuk">Saringan aktif:</span>'
            f'{"".join(cap)}<a class="btn hantu kecil" href="{e(bersih)}">Hapus semua</a></div>')


def halaman_daftar(k, pengguna, baris, ringkasan, pesan=None, tersaring=None, saringan=None):
    """baris = semua berkas yang boleh dilihat (untuk ringkasan dan hitungan
    dropdown); tersaring = yang lolos saringan, lalu dipotong per halaman."""
    saringan = {"q": "", "hak": "", "status": "", "kegiatan": "", "kec": "",
                "per": PER_BAWAAN, "hal": 1, **(saringan or {})}
    tersaring = baris if tersaring is None else tersaring
    per = saringan["per"]
    akhir = max(1, -(-len(tersaring) // per))
    kini = min(saringan["hal"], akhir)
    saringan["hal"] = kini
    potong = tersaring[(kini - 1) * per: kini * per]
    awal, ujung = (kini - 1) * per + 1, (kini - 1) * per + len(potong)

    r = ringkasan
    kotak_ringkas = f"""<div class="ringkas">
  <div><b>{r['total']}</b><span>berkas</span></div>
  <div><b>{r['draf']}</b><span>draf</span></div>
  <div><b>{r['selesai']}</b><span>selesai</span></div>
  <div><b>{r['dokumen']}</b><span>dokumen tercetak</span></div>
  <div><b>{r['desa']}</b><span>desa terdaftar</span></div>
</div>"""

    tr = []
    for b in potong:
        warna = {"selesai": "hijau", "ditolak": "merah", "diperiksa": "kuning"}.get(b["status"], "abu")
        tr.append(f"""<tr>
  <td class="nomor">{b['id']:04d}</td>
  <td><a href="/berkas/{b['id']}"><b>{e(b['penerima'] or '(tanpa nama)')}</b></a>
      {'<div class="petunjuk">a.n. kuasa ' + e(b['kuasa']) + '</div>' if b['kuasa'] else ''}</td>
  <td><span class="cap aksen">{e(b['kode_hak'])}</span>
      <div class="petunjuk">{e(b['jenis_kegiatan'])}</div></td>
  <td>{e(b['desa'] or '-')}<div class="petunjuk">{e(b['kecamatan'] or '')}</div></td>
  <td class="angka">{util.format_angka(b['luas_pbt']) if b['luas_pbt'] else '-'}</td>
  <td class="nomor">{e(b['nomor_risalah'] or '-')}</td>
  <td class="nomor">{e(b['nomor_sk'] or '-')}</td>
  <td><span class="cap {warna}">{e(b['status'])}</span></td>
  <td>{_cap_pemilik(b)}</td>
</tr>""")

    ada_saringan = any(saringan[x] for x, _ in SARINGAN)
    if tr:
        tabel = f"""<div class="kartu"><div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr>
  <th>No</th><th>Penerima hak</th><th>Hak</th><th>Letak</th>
  <th style="text-align:right">Luas m²</th><th>Risalah</th><th>SK</th><th>Status</th>
  <th>Pemilik</th>
</tr></thead><tbody>{''.join(tr)}</tbody></table></div>
{_paging(saringan, kini, akhir, awal, ujung, len(tersaring))}</div></div>"""
    elif baris:
        tabel = (f'<div class="kartu"><div class="kosong"><b>Tidak ada berkas yang cocok</b>'
                 f'<span>Coba kata cari lain, atau longgarkan saringannya.</span>'
                 f'<div class="aksi"><a class="btn" href="{e(_alamat_daftar({"per": per}))}">'
                 f'Hapus semua saringan</a></div></div></div>')
    else:
        tabel = ('<div class="kartu"><div class="kosong"><b>Belum ada berkas</b>'
                 '<span>Klik "Berkas baru" untuk memulai, atau jalankan impor Excel.</span></div></div>')

    keterangan = (f"{len(tersaring)} dari {len(baris)} berkas cocok dengan saringan"
                  if ada_saringan else f"{len(baris)} berkas")
    isi = f"""<div class="judul">
  <div><h1>Daftar berkas</h1>
  <p>{keterangan}</p></div>
  <div class="aksi"><a class="btn utama" href="/berkas/baru">+ Berkas baru</a></div>
</div>
{kotak_ringkas}
{_form_saring(k, baris, saringan) if baris else ""}
{_saringan_aktif(saringan)}
{tabel}"""
    return layout("Berkas", isi, pengguna, "/berkas", pesan)


# --------------------------------------------------------------- form berkas
def _baris_dinamis(nama, indeks, isi_html):
    return f"""<div class="baris">
  <div class="no"><button type="button" class="pegang" aria-label="Pindahkan baris {indeks}"
    title="Seret untuk memindah — atau fokuskan lalu tekan ↑ / ↓">{ikon("pegang")}</button>
    <span class="nomor">{indeks}</span></div>
  <div class="isi">{isi_html}</div>
  <div class="alat">
    <button type="button" class="btn kecil bahaya" data-aksi="hapus" title="Hapus">×</button>
  </div></div>"""


def _isi_riwayat(r=None):
    r = r or {}
    return (f'<textarea name="riwayat_uraian" rows="3" placeholder="Bahwa bidang tanah yang dimohon '
            f'sebelumnya dikuasai oleh …">{e(r.get("uraian"))}</textarea>'
            f'<textarea name="riwayat_bukti" rows="2" placeholder="Dokumen bukti (opsional)">'
            f'{e(r.get("dokumen_bukti"))}</textarea>')


KATEGORI_BEBAS = [("tambahan", "Dokumen tambahan"), ("alas_hak", "Bukti alas hak")]


def _isi_dokumen(d=None):
    d = d or {}
    return (f'<div class="grid g2">'
            f'{pilih("dokumen_keaslian", KEASLIAN, d.get("keaslian"))}'
            f'{pilih("dokumen_kategori", KATEGORI_BEBAS, d.get("kategori") or "tambahan")}</div>'
            f'<textarea name="dokumen_uraian" rows="2" placeholder="Uraian dokumen">'
            f'{e(d.get("uraian"))}</textarea>')


# Dikosongkan = tercetak "Asli", ikut kebiasaan naskah Data Pendukung.
KEASLIAN = [("", "Asli (bawaan)"), ("Asli", "Asli"), ("Fotokopi", "Fotokopi"),
            ("Salinan", "Salinan")]


def _isian_baku(d, otomatis):
    """Surat baku + dua kalimat telaah: masing-masing satu isian tetap, bukan baris
    yang bisa ditambah-kurang. Slot khusus jenis hak (mis. Akta Ikrar Wakaf) hanya
    muncul pada berkas jenis hak itu."""
    punya = {}
    for x in d["dokumen"]:
        punya.setdefault(x["kategori"] or "", x)
    blok = []
    for kategori, label, kolom, petunjuk in db.dokumen_baku(d.get("jenis_hak_dimohon")):
        x = punya.get(kategori, {})
        ket = petunjuk + (" · " if petunjuk else "") + f"kolom Excel «{kolom}»"
        if kategori in db.RINCIAN_BAKU:
            blok.append(_isian_rincian(kategori, label, x, ket))
            continue
        blok.append(
            f'<div class="baku"><div class="baku-kepala">'
            f'<label for="f_baku_{kategori}">{e(label)}</label>'
            f'{pilih("baku_asli_" + kategori, KEASLIAN, x.get("keaslian"))}</div>'
            f'<textarea id="f_baku_{kategori}" name="baku_{kategori}" rows="2" '
            f'placeholder="Kosongkan bila surat ini tidak ada">{e(x.get("uraian"))}</textarea>'
            f'<div class="petunjuk">{e(ket)}</div></div>')
    for kolom, label, kolom_xl, petunjuk in db.URAIAN_BAKU:
        blok.append(
            f'<div class="baku"><label for="f_{kolom}">{e(label)}</label>'
            f'<textarea id="f_{kolom}" name="{kolom}" rows="3" '
            f'placeholder="{e(otomatis.get(kolom) or "")}">{e(d["tanah"].get(kolom))}</textarea>'
            f'<div class="petunjuk">{e(petunjuk)} · kolom Excel «{e(kolom_xl)}»</div></div>')
    return "".join(blok)


# Kalimat Menimbang SK yang dipratinjau di bawah isian rincian; bagian «___»
# diganti app.js dengan frasa yang disusun dari isian (sama dengan konteks.py).
KALIMAT_SK = {
    "akta_ikrar": ("b. … yang diwakafkan kepada Nazhir sesuai ", ";"),
    "pengesahan_nazhir": ("c. bahwa Nazhir tanah wakaf tersebut telah disahkan ", ";"),
}


def _isian_rincian(kategori, label, x, ket):
    """Akta Ikrar Wakaf / Pengesahan Nazhir: diisi per unsur mengikuti format
    Menimbang SK Permen ATR/BPN 2/2017, dengan pratinjau kalimatnya."""
    unsur = []
    tebak = konteks.tebak_rincian(x)
    for kolom, judul, contoh in db.RINCIAN_BAKU[kategori]:
        nama = f"baku_{kolom}_{kategori}"
        nilai = x.get(kolom) or tebak.get(kolom) or ""
        if kolom == "jenis":
            masukan = pilih(nama, db.JENIS_AKTA_IKRAR, nilai or "AIW",
                            atribut=f'id="f_{nama}" data-rincian="{kolom}"')
        else:
            tipe = "date" if kolom == "tanggal" else "text"
            masukan = (f'<input type="{tipe}" id="f_{nama}" name="{nama}" value="{e(nilai)}" '
                       f'placeholder="{e(contoh)}" data-rincian="{kolom}">')
        salin = ""
        if kategori == "pengesahan_nazhir" and kolom in ("pejabat", "wilayah_pejabat"):
            salin = ' data-salin-dari="akta_ikrar"'
        unsur.append(f'<div{salin}><label for="f_{nama}">{e(judul)}</label>{masukan}</div>')
    awal, akhir = KALIMAT_SK[kategori]
    frasa = (konteks.frasa_akta_ikrar(x) if kategori == "akta_ikrar"
             else konteks.frasa_pengesahan_nazhir(x)) if x else ""
    tombol = ""
    if kategori == "pengesahan_nazhir":
        tombol = ('<button type="button" class="btn kecil" data-salin-ppaiw>'
                  'Salin PPAIW dari Akta Ikrar Wakaf</button>')
    catatan = ('<div class="petunjuk">Sebagian isian diambil dari uraian lama — '
               'periksa, lengkapi, lalu Simpan.</div>') if tebak else ""
    return (
        f'<div class="baku rincian" data-rincian-baku="{kategori}">'
        f'<div class="baku-kepala"><label>{e(label)}</label>'
        f'{pilih("baku_asli_" + kategori, KEASLIAN, x.get("keaslian"))}</div>'
        f'<div class="rincian-isi">{"".join(unsur)}</div>{tombol}{catatan}'
        f'<div class="pratinjau-sk"><span class="petunjuk">Tercetak di Menimbang SK:</span>'
        f'<p>{e(awal)}<b data-frasa>{e(frasa) or "…"}</b>{e(akhir)}</p></div>'
        f'<label for="f_baku_{kategori}" class="sub-label">Uraian di DATA PENDUKUNG '
        f'<span class="petunjuk">(boleh dikosongkan — disusun dari isian di atas)</span></label>'
        f'<textarea id="f_baku_{kategori}" name="baku_{kategori}" rows="2" '
        f'placeholder="{e((konteks.uraian_rincian(x) if x else "") or "Kosongkan bila surat ini tidak ada")}">'
        f'{e(x.get("uraian_tulis", x.get("uraian")))}</textarea>'
        f'<div class="petunjuk">{e(ket)}</div></div>')


def _isi_pihak(p=None):
    """Satu pihak selain penerima hak dan kuasa.

    Identitasnya ikut diisi di sini karena Risalah wakaf mencetak nama, TTL, NIK,
    domisili, dan pekerjaan tiap Nazhir - satu orang satu baris, tidak diketik lagi
    sebagai kalimat di tempat lain.
    """
    p = p or {}
    return (f'<div class="grid g3">{pilih("lain_peran", PERAN_LAIN, p.get("peran"))}'
            f'<input name="lain_nama" value="{e(p.get("nama"))}" placeholder="Nama">'
            f'<input name="lain_nik" value="{e(p.get("nik"))}" placeholder="NIK (16 digit)">'
            f'</div>'
            f'<div class="grid g3" style="margin-top:.5rem">'
            f'<input name="lain_ttl" value="{e(p.get("ttl"))}" '
            f'placeholder="Tempat, tanggal lahir">'
            f'<input name="lain_pekerjaan" value="{e(p.get("pekerjaan"))}" '
            f'placeholder="Pekerjaan">'
            f'<input name="lain_alamat" value="{e(p.get("alamat"))}" placeholder="Alamat">'
            f'</div>')


def _isi_foto(f):
    """Satu baris foto: gambar kecil + keterangan. Urutan baris = urutan di lampiran."""
    fid = e(f["id"])
    gambar = (f'<a href="/foto/{fid}" target="_blank" rel="noopener">'
              f'<img src="/foto/{fid}" alt="Foto lapangan" loading="lazy"></a>'
              if f.get("ada") else '<span class="foto-hilang">berkas foto hilang</span>')
    return (f'<div class="foto-baris">{gambar}<div>'
            f'<input type="hidden" name="foto_id" value="{fid}">'
            f'<label>Keterangan <span class="petunjuk">(opsional)</span></label>'
            f'<input name="foto_ket" value="{e(f.get("keterangan"))}" '
            f'placeholder="mis. Batas sebelah utara, tampak dari jalan desa"></div></div>')


def _panel_foto(d):
    ada = [f for f in d["foto"] if f.get("ada")]
    n, minimal = len(ada), foto_lapang.MINIMAL
    if n >= minimal:
        status = (f'<div class="pesan baik" style="margin:0 0 .8rem"><b>{n} foto.</b> '
                  f'Sudah memenuhi syarat minimal {minimal} foto.</div>')
    else:
        status = (f'<div class="pesan ingat" style="margin:0 0 .8rem"><b>{n} dari minimal '
                  f'{minimal} foto.</b> Dokumen belum bisa dicetak sebelum fotonya lengkap.</div>')
    daftar = "".join(_baris_dinamis("foto", i + 1, _isi_foto(f))
                     for i, f in enumerate(d["foto"]))
    return f"""<div class="kartu"><h2>Foto lapangan</h2><div class="badan">
{status}
<p class="petunjuk" style="margin-top:0">Dilampirkan pada halaman terakhir BAP, dua foto per
baris, sesuai urutan di bawah. Seret pegangan ⠿ untuk mengatur urutan dan × untuk membuang foto —
perubahannya berlaku setelah <b>Simpan</b>.</p>
<input type="hidden" name="foto_ada" value="1">
<div class="baris-dinamis" data-dinamis="foto">{daftar}</div>
{'' if daftar else '<div class="kosong" style="padding:1rem"><b>Belum ada foto</b></div>'}
</div></div>

<div class="kartu"><h2>Tambah foto</h2><div class="badan">
<label for="f_foto_baru">Pilih foto</label>
<input type="file" id="f_foto_baru" name="foto_baru" accept="image/*" multiple
       data-pratinjau-foto="pratinjau-foto">
<div class="petunjuk">Boleh beberapa sekaligus. Di ponsel bisa langsung memotret. Foto
diputar tegak dan diperkecil otomatis, lalu terunggah saat <b>Simpan</b> ditekan.</div>
<div id="pratinjau-foto" class="foto-pilihan"></div>
</div></div>"""


def _isi_pendapat(p=None):
    p = p or {}
    ya_tidak = [("1", "Setuju"), ("0", "Tidak setuju")]
    ttd = [("1", "Menandatangani"), ("0", "Tidak menandatangani")]
    return (f'<div class="grid g2">'
            f'<input name="pendapat_nama" value="{e(p.get("nama"))}" placeholder="Nama anggota">'
            f'<input name="pendapat_peran" value="{e(p.get("peran"))}" placeholder="Peran">'
            f'</div>'
            f'<textarea name="pendapat_alasan" rows="2" placeholder="Pendapat / alasan">'
            f'{e(p.get("alasan"))}</textarea>'
            f'<div class="grid g3">'
            f'{pilih("pendapat_setuju", ya_tidak, "1" if p.get("setuju", 1) else "0")}'
            f'{pilih("pendapat_ttd", ttd, "1" if p.get("menandatangani", 1) else "0")}'
            f'<input name="pendapat_diwakili" value="{e(p.get("diwakili_oleh"))}" '
            f'placeholder="Diwakili oleh (Ps. 139 ayat 3)"></div>')


def halaman_form(k, pengguna, d, ref, masalah=None, terbit=None, pesan=None,
                 boleh_ubah=True):
    """d = dict berkas hasil konteks.muat, atau None untuk berkas baru.

    boleh_ubah=False merakit halaman yang sama dalam mode baca-saja: seluruh
    isian dibungkus <fieldset disabled> sehingga peramban mematikannya
    sekaligus, dan tombol Simpan serta Cetak ditiadakan. Ini tampilan saja —
    yang menolak penyimpanan tetap rute/berkas.py.
    """
    baru = d is None
    if baru:
        d = {"id": None, "jenis_hak_dimohon": "HM", "jenis_kegiatan": "baru",
             "asal_tanah": "tanah_negara", "kewenangan": "kantah", "status": "draf",
             "pihak": [], "tanah": {}, "desa": {}, "riwayat": [], "dokumen": [],
             "hak_asal": {}, "pemeriksaan": {}, "pendapat": [], "risalah": {}, "sk": {},
             "foto": [], "panitia_anggota": []}
    t, ris, sk_, pem = d["tanah"], d["risalah"], d["sk"], d["pemeriksaan"]
    penerima = konteks.penerima_hak(d) if not baru else {}
    kuasa = konteks.pihak_peran(d, "kuasa") if not baru else {}
    bh = (penerima.get("badan_hukum") or {}) if penerima else {}
    lain = [p for p in d["pihak"] if p["peran"] not in ("penerima_hak", "pemohon", "kuasa")]

    aksi = "/berkas/baru" if baru else f"/berkas/{d['id']}"
    hak_pilihan = [(r["kode"], f"{r['kode']} — {r['nama']}") for r in ref["jenis_hak"]]
    kec_pilihan = [(r["id"], r["nama"]) for r in ref["kecamatan"]]
    pan_pilihan = [(r["id"], f"{r['nomor_sk']} ({util.tanggal_panjang(r['tanggal_sk'])})")
                   for r in ref["panitia"]]

    # ---- panel: berkas
    p_berkas = f"""<div class="kartu"><h2>Identitas berkas</h2><div class="badan">
<div class="grid g3">
  {kotak("Jenis hak dimohon", "jenis_hak_dimohon", hak_pilihan, d["jenis_hak_dimohon"],
         petunjuk="menentukan template yang dipakai; isian khusus jenis hak "
                  "(mis. Nazhir dan Akta Ikrar Wakaf) muncul setelah disimpan")}
  {kotak("Jenis hak direkomendasikan Panitia", "jenis_hak_rekomendasi", hak_pilihan,
         d.get("jenis_hak_rekomendasi"), "(sama dengan yang dimohon)",
         "Pasal 139 ayat (5): Panitia A boleh merekomendasikan jenis hak yang berbeda")}
  {kotak("Jenis kegiatan", "jenis_kegiatan", KEGIATAN, d["jenis_kegiatan"])}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {kotak("Asal tanah", "asal_tanah", ASAL_TANAH, d["asal_tanah"])}
  {kotak("Kewenangan penetapan", "kewenangan", KEWENANGAN, d["kewenangan"])}
  {kotak("Status berkas", "status", STATUS, d["status"])}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Nomor berkas", "nomor_berkas", d.get("nomor_berkas"))}
  {bidang("Tanggal surat permohonan", "tanggal_permohonan", d.get("tanggal_permohonan"), "date")}
</div>
{area("Catatan", "catatan", d.get("catatan"), baris=2)}
</div></div>"""

    # ---- panel: pihak
    # Pada berkas wakaf penerima haknya Nazhir: yang pertama diisi di kartu ini,
    # selebihnya jadi baris "Pihak lain" berperan Nazhir - identitasnya sekalian.
    ini_wakaf = (d.get("jenis_hak_rekomendasi") or d.get("jenis_hak_dimohon")) == "WAKAF"
    judul_penerima = "Penerima hak — Nazhir pertama" if ini_wakaf else "Penerima hak"
    petunjuk_wakaf = (
        '<div class="pesan ingat" style="margin:0 0 .8rem"><b>Berkas wakaf.</b> '
        'Nazhir kedua dan seterusnya ditambahkan di sini dengan peran <b>Nazhir</b>, '
        'dan pemilik yang mewakafkan tanahnya dengan peran <b>Wakif</b>. '
        'Nazhir perseorangan paling sedikit 3 orang (Pasal 4 ayat (2) PP 42/2006); '
        'kalau Akta Ikrar Wakaf lama hanya menyebut satu Nazhir, isi sesuai aktanya.'
        '</div>' if ini_wakaf else "")
    p_pihak = f"""<div class="kartu"><h2>{judul_penerima}</h2><div class="badan">
<div class="grid g3">
  {kotak("Jenis subjek", "penerima_jenis_subjek", SUBJEK, penerima.get("jenis_subjek", "perorangan"))}
  {bidang("Nama", "penerima_nama", penerima.get("nama"), wajib=True)}
  {bidang("NIK", "penerima_nik", penerima.get("nik"), petunjuk="16 digit angka")}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Tempat, tanggal lahir", "penerima_ttl", penerima.get("ttl"))}
  {kotak("Jenis kelamin", "penerima_jenis_kelamin",
         [("Laki-laki", "Laki-laki"), ("Perempuan", "Perempuan")],
         penerima.get("jenis_kelamin"), "- pilih -", "menentukan sapaan Sdr./Sdri.")}
  {bidang("Pekerjaan", "penerima_pekerjaan", penerima.get("pekerjaan"))}
</div>
{area("Alamat", "penerima_alamat", penerima.get("alamat"), baris=2)}
</div></div>

<div class="kartu"><h2>Bila penerima hak adalah badan hukum</h2><div class="badan">
<div class="grid g3">
  {bidang("Bentuk badan", "bh_bentuk", bh.get("bentuk"), petunjuk="PT, Yayasan, Koperasi, …")}
  {bidang("Kedudukan", "bh_kedudukan", bh.get("kedudukan"))}
  {bidang("NPWP", "bh_npwp", bh.get("npwp"))}
</div>
<div class="grid g4" style="margin-top:.75rem">
  {bidang("Akta pendirian nomor", "bh_akta_nomor", bh.get("akta_nomor"))}
  {bidang("Tanggal akta", "bh_akta_tanggal", bh.get("akta_tanggal"), "date")}
  {bidang("Notaris", "bh_notaris", bh.get("notaris"))}
  {bidang("NIB / OSS", "bh_nib", bh.get("nib"))}
</div>
<div class="grid g4" style="margin-top:.75rem">
  {bidang("Pengesahan nomor", "bh_pengesahan_nomor", bh.get("pengesahan_nomor"))}
  {bidang("Tanggal pengesahan", "bh_pengesahan_tanggal", bh.get("pengesahan_tanggal"), "date")}
  {bidang("Pengurus yang mewakili", "bh_wakil_nama", bh.get("wakil_nama"))}
  {bidang("Jabatan pengurus", "bh_wakil_jabatan", bh.get("wakil_jabatan"))}
</div>
{_rincian_bh_hak_pakai(d, bh)}
</div></div>

<div class="kartu"><h2>Kuasa</h2><div class="badan">
<div class="grid g2">
  {bidang("Nama penerima kuasa", "kuasa_nama", kuasa.get("nama"),
          petunjuk="kosongkan bila permohonan diajukan sendiri")}
  {bidang("NIK penerima kuasa", "kuasa_nik", kuasa.get("nik"))}
</div></div></div>

<div class="kartu"><h2>Pihak lain</h2><div class="badan">
{petunjuk_wakaf}
<div class="baris-dinamis" data-dinamis="lain">
  {''.join(_baris_dinamis("lain", i + 1, _isi_pihak(p)) for i, p in enumerate(lain))}
  <template>{_baris_dinamis("lain", 0, _isi_pihak())}</template>
</div>
<button type="button" class="btn kecil" data-tambah="lain" style="margin-top:.5rem">
  + Tambah pihak</button>
</div></div>"""

    # ---- panel: tanah
    opsi_desa = '<option value="">- pilih desa/kelurahan -</option>' + "".join(
        f'<option value="{r["id"]}"'
        f'{" selected" if str(r["id"]) == str(t.get("desa_id") or "") else ""}>'
        f'{e(r["jenis"])} {e(r["nama"])}'
        f'{"  (" + e(r["nama_pejabat"]) + ")" if r["nama_pejabat"] else ""}</option>'
        for r in ref["desa"])
    desa_json = json.dumps([{"id": r["id"], "nama": r["nama"], "jenis": r["jenis"],
                             "kecamatan_id": r["kecamatan_id"], "pejabat": r["nama_pejabat"] or ""}
                            for r in ref["desa"]], ensure_ascii=False)
    p_tanah = f"""<div class="kartu"><h2>Letak</h2><div class="badan">
<div class="grid g2">
  {kotak("Kecamatan", "kecamatan", kec_pilihan, d["desa"].get("kecamatan_id"), "- pilih kecamatan -")}
  <div><label for="f_desa">Desa / Kelurahan <span class="wajib">*</span></label>
    <select id="f_desa" name="desa_id" data-terpilih="{e(t.get('desa_id'))}">{opsi_desa}</select>
    <div class="petunjuk">Nama dan jabatan pejabat desa ikut terisi dari daftar induk</div></div>
</div></div></div>

<div class="kartu"><h2>Bidang tanah</h2><div class="badan">
<div class="grid g3">
  {bidang("Nomor Peta Bidang Tanah", "nomor_pbt", t.get("nomor_pbt"), wajib=True)}
  {bidang("Tanggal PBT", "tanggal_pbt", t.get("tanggal_pbt"), "date")}
  {bidang("NIB", "nib", t.get("nib"), wajib=True)}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Luas hasil ukur (m²)", "luas_pbt", t.get("luas_pbt"), "number", wajib=True,
          petunjuk="angka saja — terbilang dihitung otomatis")}
  {bidang("Luas menurut surat (m²)", "luas_surat", t.get("luas_surat"), "number")}
  <div><label for="f_selisih">Selisih</label>
    <input id="f_selisih" readonly><div class="petunjuk">dihitung, tidak disimpan</div></div>
</div>
<div class="grid g4" style="margin-top:.75rem">
  {bidang("Batas utara", "batas_utara", t.get("batas_utara"))}
  {bidang("Batas timur", "batas_timur", t.get("batas_timur"))}
  {bidang("Batas selatan", "batas_selatan", t.get("batas_selatan"))}
  {bidang("Batas barat", "batas_barat", t.get("batas_barat"))}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Penggunaan saat ini", "penggunaan_sekarang", t.get("penggunaan_sekarang"))}
  {bidang("Rencana penggunaan", "rencana_penggunaan", t.get("rencana_penggunaan"))}
  {bidang("Tanggal peta analisis", "tanggal_peta_analisis", t.get("tanggal_peta_analisis"), "date")}
</div>
<div class="grid g2" style="margin-top:.75rem">
  {bidang("Kawasan RTRW", "rtrw", t.get("rtrw"))}
  {kotak("Kesesuaian", "kesesuaian",
         [("Sesuai", "Sesuai"), ("Sesuai Bersyarat", "Sesuai Bersyarat"),
          ("Tidak Sesuai", "Tidak Sesuai")], t.get("kesesuaian"), "- pilih / ketik lain -")}
</div>
{area("Kesesuaian (uraian bila sebagian sesuai)", "kesesuaian_lain",
      t.get("kesesuaian") if t.get("kesesuaian") not in
      (None, "", "Sesuai", "Sesuai Bersyarat", "Tidak Sesuai") else "", baris=2,
      petunjuk="isi hanya bila kesesuaiannya terbagi per luasan")}
</div></div>"""

    # ---- panel: asal tanah
    ha = d["hak_asal"]
    p_asal = f"""<div class="kartu"><h2>Riwayat perolehan — untuk pemberian hak baru</h2>
<div class="badan">
<div class="baris-dinamis" data-dinamis="riwayat">
  {''.join(_baris_dinamis("riwayat", i + 1, _isi_riwayat(r)) for i, r in enumerate(d["riwayat"]))}
  <template>{_baris_dinamis("riwayat", 0, _isi_riwayat())}</template>
</div>
<button type="button" class="btn kecil" data-tambah="riwayat" style="margin-top:.5rem">
  + Tambah mata rantai</button>
<div class="petunjuk" style="margin-top:.5rem">Boleh 2 baris, boleh 10 — dokumen menyesuaikan
sendiri. Baris terakhir otomatis berakhir dengan titik.</div>
</div></div>

<div class="kartu"><h2>Hak asal — untuk perpanjangan, pembaruan, dan peningkatan</h2>
<div class="badan"><div class="grid g3">
  {bidang("Jenis hak lama", "asal_jenis_hak", ha.get("jenis_hak_lama"))}
  {bidang("Nomor sertipikat", "asal_sertipikat", ha.get("nomor_sertipikat"))}
  {bidang("Nomor SK asal", "asal_nomor_sk", ha.get("nomor_sk"))}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Tanggal SK asal", "asal_tanggal_sk", ha.get("tanggal_sk"), "date")}
  {bidang("Tanggal berakhir hak", "asal_tanggal_berakhir", ha.get("tanggal_berakhir"), "date")}
  {bidang("Luas menurut sertipikat (m²)", "asal_luas", ha.get("luas"), "number")}
</div></div></div>"""

    # ---- panel: dokumen
    # Berkas yang lahir dari loket menunjuk balik ke pradaftarnya: di situlah
    # tercatat siapa yang memeriksa kelengkapannya dan formulir 184-nya bisa
    # dicetak ulang. Tautannya satu arah — berkas tidak menyimpan kolomnya.
    asal = pradaftar.dari_berkas(k, d["id"]) if d.get("id") else None
    asal_pradaftar = (
        f'<div class="pesan ingat" style="margin:0 0 .8rem">Berkas ini berasal dari '
        f'<b>Pradaftar {e(asal["nomor"])}</b> '
        f'({e(util.tanggal_pendek(asal["tanggal"]) or asal["tanggal"])}) — '
        f'<a href="/pradaftar/{asal["id"]}">lihat daftar kelengkapannya</a>.</div>'
        if asal else "")
    syarat = ref["syarat"]
    punya = " | ".join((x["uraian"] or "").lower() for x in d["dokumen"])
    daftar_syarat = []
    for s in syarat:
        ada = any(w in punya for w in konteks._kata_kunci(s["nama"]))
        daftar_syarat.append(
            f'<li class="{"" if ada else "peringatan"}"><span class="ikon">'
            f'{"✓" if ada else "!"}</span><span>{e(s["nama"])}'
            f'<div class="petunjuk">{e(s["dasar"])}</div></span></li>')
    otomatis = konteks.kalimat_otomatis(d)
    slot_tampil = {x[0] for x in db.dokumen_baku(d.get("jenis_hak_dimohon"))}
    sisa = [x for x in d["dokumen"] if (x["kategori"] or "") not in slot_tampil]
    p_dok = f"""<div class="kartu"><h2>Dokumen baku</h2><div class="badan">
<p class="petunjuk">Satu kesatuan dengan formulir permohonan: slotnya tetap, tinggal diisi.
Yang dikosongkan tidak ikut tercetak.</p>
{_isian_baku(d, otomatis)}
</div></div>

<div class="kartu"><h2>Dokumen tambahan &amp; alas hak</h2><div class="badan">
<div class="baris-dinamis" data-dinamis="dokumen">
  {''.join(_baris_dinamis("dokumen", i + 1, _isi_dokumen(x)) for i, x in enumerate(sisa))}
  <template>{_baris_dinamis("dokumen", 0, _isi_dokumen())}</template>
</div>
<button type="button" class="btn kecil" data-tambah="dokumen" style="margin-top:.5rem">
  + Tambah dokumen</button>
</div></div>

<div class="kartu"><h2>Checklist syarat permohonan</h2><div class="badan">
{asal_pradaftar}
<ul class="daftar-periksa">{''.join(daftar_syarat)}</ul>
</div></div>"""

    # ---- panel: sidang
    p_sidang = f"""<div class="kartu"><h2>Pemeriksaan lapang (BAP)</h2><div class="badan">
<div class="grid g3">
  {bidang("Tanggal surat tugas", "tanggal_surat_tugas", pem.get("tanggal_surat_tugas"), "date",
          petunjuk="awal tenggat 14 hari kerja (Pasal 136)")}
  {bidang("Tanggal pemeriksaan lapang", "tanggal_bap", pem.get("tanggal_bap"), "date")}
  {kotak("Susunan Panitia A", "panitia_id", pan_pilihan, pem.get("panitia_id"), "- pilih -",
          petunjuk="daftarnya diisi di menu Data referensi, per SK penunjukan panitia")}
</div>
{area("Keberatan / sanggahan dan penyelesaiannya", "keberatan", pem.get("keberatan"), baris=2)}
</div></div>

<div class="kartu"><h2>Pendapat anggota panitia</h2><div class="badan">
<div class="baris-dinamis" data-dinamis="pendapat">
  {''.join(_baris_dinamis("pendapat", i + 1, _isi_pendapat(p)) for i, p in enumerate(d["pendapat"]))}
  <template>{_baris_dinamis("pendapat", 0, _isi_pendapat())}</template>
</div>
<button type="button" class="btn kecil" data-tambah="pendapat" style="margin-top:.5rem">
  + Tambah anggota</button>
</div></div>

<div class="kartu"><h2>Risalah</h2><div class="badan"><div class="grid g4">
  {bidang("Nomor Risalah", "risalah_nomor", ris.get("nomor"),
          petunjuk="kosongkan — diisi otomatis saat cetak")}
  {bidang("Tanggal Risalah", "risalah_tanggal", ris.get("tanggal"), "date")}
  {kotak("Kesimpulan", "risalah_kesimpulan", KESIMPULAN, ris.get("kesimpulan", "dikabulkan"))}
  {bidang("Jangka waktu (tahun)", "risalah_jangka", ris.get("jangka_waktu_tahun"), "number",
          petunjuk="wajib untuk HGB & Hak Pakai (Ps. 139 ayat 4)")}
</div>
{area("Alasan (bila ditolak atau perlu dilengkapi)", "risalah_alasan", ris.get("alasan"), baris=2)}
</div></div>

<div class="kartu"><h2>Surat Keputusan</h2><div class="badan"><div class="grid g3">
  {bidang("Nomor SK", "sk_nomor", sk_.get("nomor"), petunjuk="kosongkan — diisi otomatis saat cetak")}
  {bidang("Tanggal SK", "sk_tanggal", sk_.get("tanggal"), "date")}
  {bidang("Uang pemasukan (Rp)", "sk_uang", sk_.get("uang_pemasukan"), "number")}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Pejabat penanda tangan", "sk_pejabat_nama", sk_.get("pejabat_nama"))}
  {bidang("NIP", "sk_pejabat_nip", sk_.get("pejabat_nip"))}
  {bidang("Validasi PPh", "sk_validasi_pph", sk_.get("validasi_pph"))}
</div></div></div>"""

    # ---- panel: foto lapangan
    p_foto = _panel_foto(d)

    # ---- panel: terbitkan
    p_terbit = _panel_terbit(d, masalah, terbit, baru, boleh_ubah)

    # lencana di tab Cetak: berapa hal yang masih menghalangi pencetakan
    galat = [m for m in (masalah or []) if m[0] == "galat"]
    ingat = [m for m in (masalah or []) if m[0] != "galat"]
    if galat:
        lencana = f'<span class="lencana merah">{len(galat)}</span>'
    elif ingat:
        lencana = f'<span class="lencana kuning">{len(ingat)}</span>'
    else:
        lencana = "" if baru else '<span class="lencana hijau">✓</span>'
    n_foto = sum(1 for f in d["foto"] if f.get("ada"))
    warna_foto = "hijau" if n_foto >= foto_lapang.MINIMAL else "merah"
    lencana_foto = "" if baru else f'<span class="lencana {warna_foto}">{n_foto}</span>'
    isi_panel = {"p-berkas": p_berkas, "p-pihak": p_pihak, "p-tanah": p_tanah,
                 "p-asal": p_asal, "p-dokumen": p_dok, "p-foto": p_foto,
                 "p-sidang": p_sidang, "p-terbit": p_terbit}
    if baru:
        # Berkas baru dituntun selangkah demi selangkah. Tab Sidang dan Cetak
        # sengaja tidak ikut: keduanya baru berarti setelah berkasnya ada.
        tab = _bilah_langkah(LANGKAH_BARU)
        n = len(LANGKAH_BARU)
        panel = []
        for i, (kunci, _, _, petunjuk) in enumerate(LANGKAH_BARU, 1):
            kepala, kaki = _kaki_langkah(i, n, petunjuk)
            panel.append(f'<div class="panel" id="{kunci}">{kepala}'
                         f'{isi_panel[kunci]}{kaki}</div>')
        panel = chr(10).join(panel)
    else:
        tab = _tab("berkas", [
            ("p-berkas", "Berkas"), ("p-pihak", "Pihak"), ("p-tanah", "Bidang tanah"),
            ("p-asal", "Riwayat / hak asal"), ("p-dokumen", "Dokumen"),
            ("p-foto", "Foto lapangan", lencana_foto),
            ("p-sidang", "Sidang & dokumen terbit"), ("p-terbit", "Cetak", lencana)])
        panel = chr(10).join(f'<div class="panel" id="{k}">{v}</div>'
                              for k, v in isi_panel.items())

    # Form cetak harus berada DI LUAR form-berkas: peramban membuang form bersarang.
    form_cetak = ("" if baru or not boleh_ubah else
                  f'<form id="form-cetak" method="post" action="/berkas/{d["id"]}/cetak"></form>')
    nama_judul = penerima.get("nama") or "Berkas baru"
    buka_kunci = "" if boleh_ubah else '<fieldset disabled class="baca-saja">'
    tutup_kunci = "" if boleh_ubah else "</fieldset>"
    # Ctrl+S menyimpan formulir ini (app.js). Tidak dipasang pada tampilan
    # baca-saja, supaya pintasnya tidak berpura-pura menyimpan.
    pintas = " data-simpan-pintas" if boleh_ubah else ""
    if baru:
        # Tidak ada tombol Simpan di kepala: kalau ada, petugas baru cenderung
        # menekannya di langkah pertama dan mengira sudah selesai. Simpan ada
        # satu, di ujung langkah terakhir.
        aksi_kepala = '<a class="btn" href="/berkas">&larr; Batal</a>'
    elif boleh_ubah:
        aksi_kepala = ('<a class="btn" href="/berkas">&larr; Daftar</a>'
                       '<button class="btn utama" type="submit" form="form-berkas"'
                       ' title="Simpan (Ctrl+S)">Simpan'
                       '<kbd class="pintas" aria-hidden="true">Ctrl S</kbd></button>')
    else:
        aksi_kepala = '<a class="btn" href="/berkas">&larr; Daftar</a>'
    spanduk_baca = "" if boleh_ubah else (
        '<div class="pesan">Berkas ini <b>hanya bisa dilihat</b>. Yang boleh '
        'mengubahnya cuma petugas yang menginputnya, atau admin.</div>')
    isi = f"""<div class="lengket-atas">
<div class="judul">
  <div><h1>{e(nama_judul)}</h1>
  <p>{'Berkas baru' if baru else f"Berkas {d['id']:04d} · {e(d['jenis_hak_dimohon'])} · {e(d['jenis_kegiatan'])}"}</p></div>
  <div class="aksi">
    {aksi_kepala}
  </div>
</div>
{tab}
</div>
{spanduk_baca}
<form id="form-berkas" method="post" action="{aksi}"{pintas} enctype="multipart/form-data">
{buka_kunci}
{panel}
{tutup_kunci}
</form>
{form_cetak}
<script>window.DAFTAR_DESA = {desa_json};</script>"""
    return layout(nama_judul, isi, pengguna, "/berkas", pesan)


def _panel_terbit(d, masalah, terbit, baru, boleh_ubah=True):
    if baru:
        return ('<div class="kartu"><div class="kosong"><b>Simpan dulu</b>'
                'Dokumen bisa dicetak setelah berkas disimpan.</div></div>')
    masalah = masalah or []
    galat = [m for m in masalah if m[0] == "galat"]
    li = "".join(f'<li class="{e(t)}"><span class="ikon">{"×" if t == "galat" else "!"}</span>'
                 f'<span>{e(p)}</span></li>' for t, p in masalah)
    if not masalah:
        li = ('<li class=""><span class="ikon">✓</span>'
              '<span>Semua pemeriksaan lolos. Dokumen siap dicetak.</span></li>')
    nonaktif = " disabled" if galat else ""
    catatan = (f'<div class="pesan galat"><b>{len(galat)} hal harus diperbaiki</b> '
               f'sebelum dokumen bisa dicetak.</div>') if galat else ""

    riwayat = ""
    if d.get("_terbit"):
        baris = "".join(
            f'<tr><td>{e(x["jenis_dokumen"].upper())}</td><td class="nomor">{e(x["nomor"] or "-")}</td>'
            f'<td>{e(x["nama_file"])}</td>'
            f'<td class="petunjuk">{e(x["dicetak_pada"])}</td>'
            f'<td style="white-space:nowrap">'
            f'<a class="btn kecil" href="/pratinjau/{e(x["nama_file"])}">Pratinjau</a> '
            f'<a class="btn kecil" href="/unduh/{e(x["nama_file"])}">DOCX</a></td></tr>'
            for x in d["_terbit"])
        riwayat = f"""<div class="kartu"><h2>Riwayat cetak</h2><div class="badan rapat">
<div class="tabel-bungkus"><table><thead><tr><th>Dokumen</th><th>Nomor</th><th>Berkas</th>
<th>Dicetak</th><th>Buka</th></tr></thead><tbody>{baris}</tbody></table></div></div></div>"""

    hasil = ""
    if terbit:
        potong = []
        for j, jalur, err in terbit:
            if err:
                potong.append(f'<li class="galat"><span class="ikon">×</span>'
                              f'<span>{e(j.upper())}: {e(err)}</span></li>')
            else:
                nama = e(os.path.basename(jalur))
                potong.append(
                    f'<li><span class="ikon">✓</span><span>{e(j.upper())}: berhasil dirakit '
                    f'&nbsp;<a class="btn kecil" href="/pratinjau/{nama}">Pratinjau PDF</a> '
                    f'<a class="btn kecil" href="/unduh/{nama}">Unduh DOCX</a></span></li>')
        hasil = ('<div class="kartu"><h2>Hasil cetak</h2><div class="badan">'
                 f'<ul class="daftar-periksa">{"".join(potong)}</ul></div></div>')

    tombol_cetak = ("""<div class="kosong"><b>Hanya admin yang bisa mencetak berkas ini</b>
<span>Berkas tanpa pemilik berasal dari impor Excel, jadi nomor Risalah dan SK-nya
diberikan admin.</span></div>""" if not boleh_ubah else f"""
<div class="aksi" style="display:flex;gap:.5rem;flex-wrap:wrap">
  <button class="btn utama" type="submit" form="form-cetak" name="jenis" value="semua"{nonaktif}>
    Cetak semua dokumen</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="bap"{nonaktif}>BAP</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="risalah"{nonaktif}>Risalah</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="sk"{nonaktif}>SK</button>
</div>
<div class="petunjuk" style="margin-top:.6rem">Nomor Risalah dan SK diberikan otomatis saat
pertama kali dicetak, berurutan per jenis hak per tahun.</div>""")

    return f"""{catatan}{hasil}
<div class="kartu"><h2>Pemeriksaan sebelum cetak</h2><div class="badan">
<ul class="daftar-periksa">{li}</ul></div></div>

<div class="kartu"><h2>Cetak dokumen</h2><div class="badan">{tombol_cetak}</div></div>
{riwayat}"""


# ----------------------------------------------------------------- pradaftar
# Urutan pengisian pradaftar. Bentuknya sama dengan LANGKAH_BARU pada berkas:
# petugas loket yang baru memakai aplikasi ini dituntun, bukan dilepas ke
# formulir panjang.
LANGKAH_PRADAFTAR = [
    ("q-pemohon", "Pemohon", False,
     "Siapa yang datang dan hak apa yang dimohon. Jenis subjek menentukan butir "
     "kelengkapan mana yang berlaku — grup Badan Hukum hanya muncul untuk badan hukum."),
    ("q-tanah", "Letak tanah", True,
     "Letak dan luas tanah menurut surat yang dibawa pemohon. Boleh menyusul; "
     "yang menentukan kelengkapan bukan bagian ini."),
    ("q-periksa", "Kelengkapan berkas", False,
     "Centang tiap dokumen yang benar-benar diserahkan pemohon. Inilah daftar yang "
     "tercetak sebagai lampiran, dan yang menentukan berkas bisa diterima atau tidak."),
]

STATUS_PRADAFTAR_WARNA = {"diterima": "hijau", "dikembalikan": "kuning", "batal": "abu"}


def _cap_pradaftar(b):
    """Lencana status satu pradaftar: keadaan kelengkapannya, bukan cuma kolom status.

    Yang berstatus `baru` belum mengatakan apa pun sendiri — yang berarti bagi
    petugas loket adalah sudah lengkap atau belum, dan itu dihitung.
    """
    if b["status"] != "baru":
        label = dict(pradaftar.STATUS).get(b["status"], b["status"])
        return f'<span class="cap {STATUS_PRADAFTAR_WARNA.get(b["status"], "abu")}">{e(label)}</span>'
    if b["lengkap"]:
        return '<span class="cap hijau">siap diterima</span>'
    cap = []
    if b["kurang"]:
        cap.append(f'<span class="cap merah">kurang {len(b["kurang"])}</span>')
    if b["koreksi"]:
        cap.append(f'<span class="cap kuning">koreksi {len(b["koreksi"])}</span>')
    return " ".join(cap)


def halaman_pradaftar(pengguna, baris, ringkasan, pesan=None):
    r = ringkasan
    kotak_ringkas = f"""<div class="ringkas">
  <div><b>{r['total']}</b><span>pradaftar</span></div>
  <div><b>{r['siap']}</b><span>siap diterima</span></div>
  <div><b>{r['kurang']}</b><span>belum lengkap</span></div>
  <div><b>{r['diterima']}</b><span>sudah jadi berkas</span></div>
  <div><b>{r['dikembalikan']}</b><span>dikembalikan</span></div>
</div>"""

    tr = []
    for b in baris:
        cari = " ".join(str(x or "").lower() for x in
                        (b["nomor"], b["pemohon_nama"], b["desa"], b["kecamatan"],
                         b["jenis_hak"], b["nomor_pbt"]))
        # Disaring app.js memakai keadaan, bukan kolom status: "kurang" dan
        # "siap" adalah yang dicari petugas loket, dan keduanya berstatus baru.
        keadaan = (b["status"] if b["status"] != "baru"
                   else ("siap" if b["lengkap"] else "kurang"))
        tautan_berkas = (f'<a href="/berkas/{b["berkas_id"]}">{b["berkas_id"]:04d}</a>'
                         if b["berkas_id"] else "-")
        tr.append(f"""<tr data-cari="{e(cari)}" data-status="{e(keadaan)}">
  <td class="nomor">{e(b['nomor'] or '-')}</td>
  <td><a href="/pradaftar/{b['id']}"><b>{e(b['pemohon_nama'])}</b></a>
      {'<div class="petunjuk">a.n. kuasa ' + e(b['kuasa_nama']) + '</div>' if b['kuasa_nama'] else ''}</td>
  <td><span class="cap aksen">{e(b['jenis_hak'])}</span>
      <div class="petunjuk">{e(b['jenis_kegiatan'])}</div></td>
  <td>{e(b['desa'] or b['letak_lain'] or '-')}<div class="petunjuk">{e(b['kecamatan'] or '')}</div></td>
  <td>{e(util.tanggal_pendek(b['tanggal']) or b['tanggal'] or '-')}</td>
  <td>{_cap_pradaftar(b)}</td>
  <td class="nomor">{tautan_berkas}</td>
</tr>""")

    tabel = f"""<div class="kartu"><div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr>
  <th>Nomor</th><th>Pemohon</th><th>Hak</th><th>Letak</th><th>Tanggal</th>
  <th>Keadaan</th><th>Berkas</th>
</tr></thead><tbody>{''.join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada pradaftar yang cocok. Ubah kata cari atau
pilih tab <b>Semua</b>.</div></div></div>""" if tr else (
        '<div class="kartu"><div class="kosong"><b>Belum ada pradaftar</b>'
        '<span>Klik "Pradaftar baru" saat pemohon datang ke loket membawa berkasnya.'
        '</span></div></div>')

    keadaan = [("", "Semua"), ("kurang", "Belum lengkap"), ("siap", "Siap diterima"),
               ("diterima", "Diterima"), ("dikembalikan", "Dikembalikan"),
               ("batal", "Batal")]
    jumlah = {}
    for b in baris:
        n = b["status"] if b["status"] != "baru" else ("siap" if b["lengkap"] else "kurang")
        jumlah[n] = jumlah.get(n, 0) + 1
    tapis = "".join(
        f'<button type="button" data-status="{e(nilai)}" aria-pressed="false">{e(label)}'
        f'<span class="lencana">{jumlah.get(nilai, len(baris) if not nilai else 0)}</span>'
        f'</button>' for nilai, label in keadaan)

    isi = f"""<div class="judul">
  <div><h1>Pradaftar</h1>
  <p id="jumlah-tampil" data-satuan="pradaftar">{len(baris)} pradaftar</p></div>
  <div class="aksi"><a class="btn utama" href="/pradaftar/baru">+ Pradaftar baru</a></div>
</div>
{kotak_ringkas}
<div class="bar"><div class="tumbuh">
  <label for="saring">Cari nama pemohon, desa, atau nomor</label>
  <input id="saring" type="search" placeholder="ketik untuk menyaring…"></div></div>
<div class="tab tapis" role="group" aria-label="Saring menurut keadaan">{tapis}</div>
{tabel}"""
    return layout("Pradaftar", isi, pengguna, "/pradaftar", pesan)


# ------------------------------------------------------- daftar kelengkapan
# Dipakai dua tempat: tab Kelengkapan di halaman pradaftar, dan halaman periksa
# layar penuh (/pradaftar/<id>/periksa). Keduanya berbagi baris, bilah alat, dan
# ringkasan yang sama. app.js (pasangPeriksa) menghitung ulang keadaan tiap
# butir di peramban begitu pilihannya diganti — petugas tidak perlu menyimpan
# dulu untuk tahu apa yang masih kurang. Aturannya cermin pradaftar._nilai;
# keputusan yang mengikat tetap hitungan server saat disimpan.
def _baris_periksa(n, boleh_ubah=True, khusus=()):
    """Satu baris daftar kelengkapan: penanda, bunyi butirnya, dan pilihan
    Ada / Perlu koreksi / Tidak Ada.

    Butir bersifat `judul` tidak dicentang — keadaannya disimpulkan dari anaknya,
    jadi yang tampil di kolom kanan cuma ringkasan.

    Butir yang belum dijawab tampil tanpa pilihan tercentang (kelas `belum`),
    bukan otomatis "Tidak Ada": petugas harus bisa melihat mana yang belum
    ia periksa. Untuk keputusan terima, yang belum dijawab tetap dihitung
    tidak ada.

    Atribut data-* pada baris dibaca app.js untuk menyusun ulang pohonnya.

    Kotak catatan koreksi selalu ikut dirakit, tetapi baru tampil saat "Perlu
    koreksi" dipilih (CSS :has, tanpa JavaScript). Pilihan catatannya datang
    dari datalist: `koreksi-umum` untuk semua butir, atau datalist milik butir
    ini sendiri bila ada catatan baku yang khusus untuknya (`khusus`).
    """
    mati = "" if boleh_ubah else " disabled"
    dalam = min(n["tingkat"], 3)
    bisa_centang = n["berlaku"] and n["sifat"] != "judul"
    kelas = ["periksa-baris", f"dalam-{dalam}"]
    if not n["berlaku"]:
        kelas.append("lewat")
    if n["sifat"] == "judul":
        kelas.append("judul")
    if n["status"] in ("kurang", "koreksi"):
        kelas.append(n["status"])
    if bisa_centang and not n["dijawab"]:
        kelas.append("belum")

    label = (n["penanda"] + ". " if n["penanda"] else "") + n["nama"]
    data = (f' id="butir-{n["id"]}" data-butir="{n["id"]}"'
            f' data-induk="{n["induk_id"] or ""}" data-sifat="{e(n["sifat"] or "")}"'
            f' data-wajib="{1 if n["wajib"] else 0}" data-berlaku="{1 if n["berlaku"] else 0}"'
            f' data-label="{e(label)}"')

    penanda = f'<span class="periksa-no">{e(n["penanda"])}{"." if n["penanda"] else ""}</span>'
    # Bunyi butir, titik-titiknya, dan rujukan pasalnya jadi SATU sel — kalau
    # dipisah jadi saudara, masing-masing terhitung sel grid sendiri dan
    # rujukan pasalnya jatuh ke kolom nomor yang cuma selebar 2rem.
    isian = _isian_surat(n, mati)
    dasar = f'<span class="periksa-dasar">{e(n["dasar"])}</span>' if n["dasar"] else ""
    nama = f'<div class="periksa-nama">{e(n["nama"])}{isian}{dasar}</div>'

    if n["sifat"] == "judul":
        # Grup tidak dicentang sendiri — keadaannya disimpulkan dari anaknya.
        # Capnya dibungkus [data-cap] supaya app.js bisa menggantinya.
        cap = ('<span class="cap abu">tidak berlaku</span>' if not n["berlaku"]
               else _cap_grup(n["status"]))
        catatan = f'<span data-cap>{cap}</span>'
        if n.get("_pilihan") and n["berlaku"]:
            catatan += '<span class="petunjuk">cukup salah satu</span>'
        pilihan = f'<div class="periksa-pilih ringkas">{catatan}</div>'
    elif not n["berlaku"]:
        pilihan = ('<div class="periksa-pilih ringkas">'
                   '<span class="cap abu">tidak berlaku</span></div>')
    else:
        # KOREKSI di tengah: urutannya mengikuti keadaan suratnya, dari yang
        # beres sampai yang tidak dibawa sama sekali. Angka di tiap tombol
        # adalah tombol pintasnya (lihat pasangPeriksa di app.js).
        def pil(nilai, teks, jenis, kunci):
            cek = " checked" if n["dijawab"] and n["ada"] == nilai else ""
            return (f'<label class="pil {jenis}"><input type="radio" '
                    f'name="jawab_ada_{n["id"]}" value="{nilai}"{cek}{mati}>'
                    f'<span>{teks}</span><kbd aria-hidden="true">{kunci}</kbd></label>')
        pilihan = (f'<div class="periksa-pilih segmen" role="radiogroup" '
                   f'aria-label="{e(label)}">'
                   f'{pil(pradaftar.ADA, "Ada", "pil-ada", 1)}'
                   f'{pil(pradaftar.KOREKSI, "Perlu koreksi", "pil-koreksi", 2)}'
                   f'{pil(pradaftar.TIDAK_ADA, "Tidak Ada", "pil-tidak", 3)}</div>')
    koreksi = ""
    if bisa_centang:
        daftar = "koreksi-umum"
        pilihan_khusus = ""
        if khusus:
            daftar = f'koreksi-{n["id"]}'
            pilihan_khusus = (f'<datalist id="{daftar}">'
                              + "".join(f'<option value="{e(t)}">' for t in khusus)
                              + "</datalist>")
        koreksi = (f'<div class="periksa-koreksi"><label for="koreksi_{n["id"]}">'
                   f'Apa yang perlu diperbaiki</label>'
                   f'<input id="koreksi_{n["id"]}" type="text" '
                   f'name="jawab_catatan_{n["id"]}" value="{e(n["catatan_jawab"])}" '
                   f'list="{daftar}" maxlength="300" '
                   f'placeholder="pilih dari daftar atau ketik sendiri…"{mati}>'
                   f'{pilihan_khusus}</div>')
    sembunyi = (f'<input type="hidden" name="jawab_butir" value="{n["id"]}">'
                if bisa_centang else "")
    return (f'<div class="{" ".join(kelas)}"{data}>{sembunyi}'
            f'<div class="periksa-teks">{penanda}{nama}</div>{pilihan}{koreksi}</div>')


def _isian_surat(n, mati=""):
    """Kotak nama surat di bawah bunyi butir.

    Butir isian bebas biasa: satu kotak, seperti titik-titik pada formulirnya.
    Butir `jamak`: sederet kotak — satu surat satu kotak — dengan tombol
    "+ Tambah surat". Semuanya bernama sama (jawab_uraian_<id>), jadi server
    cukup membaca getlist(). Contoh yang sering: dua akta jual beli berantai,
    atau surat keterangan hibah plus surat keterangan waris sebagai bukti
    perolehan lainnya.
    """
    nama = f'jawab_uraian_{n["id"]}'
    if not n.get("jamak"):
        if not n["isian_bebas"]:
            return ""
        return (f'<input class="periksa-isian" type="text" name="{nama}" '
                f'value="{e("; ".join(n["uraian_daftar"]))}" '
                f'placeholder="sebutkan suratnya…"{mati}>')

    contoh = ("sebutkan suratnya, mis. Surat Keterangan Hibah No. 12/2019"
              if n["isian_bebas"] else "nomor & tanggal surat, mis. AJB No. 45/2018")

    def baris(nilai, i):
        hapus = ("" if mati else
                 '<button type="button" class="ikon-btn kecil" data-hapus-surat '
                 'title="Hapus surat ini" aria-label="Hapus surat ini">×</button>')
        return (f'<div class="surat-baris"><span class="surat-no">{i}.</span>'
                f'<input type="text" name="{nama}" value="{e(nilai)}" '
                f'placeholder="{e(contoh)}" aria-label="Surat ke-{i}"{mati}>{hapus}</div>')

    isi = n["uraian_daftar"] or ([""] if n["isian_bebas"] else [])
    tombol = ("" if mati else
              f'<button type="button" class="btn kecil hantu" data-tambah-surat>'
              f'+ {"Tambah surat" if isi else "Rincian surat"}</button>')
    return (f'<div class="periksa-surat" data-surat>'
            + "".join(baris(x, i) for i, x in enumerate(isi, 1))
            + f'<template>{baris("", 0)}</template>{tombol}</div>')


def _cap_grup(status):
    """Cap keadaan satu grup. Bunyinya harus sama dengan capGrup di app.js."""
    return {"ada": '<span class="cap hijau">terpenuhi</span>',
            "kurang": '<span class="cap merah">belum</span>',
            "koreksi": '<span class="cap kuning">perlu koreksi</span>'}.get(status, "")


def _daftar_periksa(d, boleh_ubah=True):
    """Seluruh baris daftar kelengkapan, berikut datalist catatan bakunya."""
    datar = pradaftar.ratakan(d["pohon"])
    # Grup yang anaknya bersifat alternatif diberi keterangan "cukup salah satu",
    # supaya petugas tidak mengira kesepuluh butirnya harus ada semua.
    anak_alternatif = set()
    for n in d["pohon"]:
        _tandai_alternatif(n, anak_alternatif)
    for n in datar:
        n["_pilihan"] = n["id"] in anak_alternatif

    umum, khusus = d.get("catatan_baku") or ([], {})
    baris = "".join(
        _baris_periksa(n, boleh_ubah,
                       khusus.get(n["id"], []) + umum if n["id"] in khusus else ())
        for n in datar)
    datalist = ('<datalist id="koreksi-umum">'
                + "".join(f'<option value="{e(t)}">' for t in umum) + '</datalist>')
    return f"""{datalist}
<div class="periksa">
  <div class="periksa-kepala"><div class="periksa-teks">Dokumen Persyaratan</div>
    <div class="periksa-pilih">Kelengkapan</div></div>
  {baris}
</div>
<div class="kosong periksa-kosong" data-periksa-kosong hidden><b>Tidak ada butir di sini</b>
<span>Pilih <b>Semua</b> untuk melihat seluruh daftar.</span></div>"""


def _belum_diperiksa(n):
    """Butir yang kurang karena memang belum disentuh, bukan dinyatakan Tidak Ada."""
    if n["anak"]:
        return not any(a["dijawab"] for a in n["anak"] if a["berlaku"])
    return not n["dijawab"]


def _ringkas_periksa(d):
    """Pesan kekurangan & koreksi. app.js merakit ulang bentuk yang sama
    (ringkasPeriksa) tiap kali pilihan diganti."""
    def _tautan(x, tambahan=""):
        nama = e(x["penanda"] + ". " if x["penanda"] else "") + e(x["nama"])
        return (f'<li><a href="#butir-{x["id"]}" data-lompat="{x["id"]}">{nama}</a>'
                f'{tambahan}</li>')

    kurang, koreksi = d["kurang"], d.get("koreksi", [])
    hasil = ""
    if kurang:
        daftar = "".join(
            _tautan(x, ' <span class="petunjuk">· belum diperiksa</span>'
                    if _belum_diperiksa(x) else "") for x in kurang)
        hasil += (f'<div class="pesan galat"><div class="teks"><b>{len(kurang)} belum '
                  f'lengkap.</b> Berkas belum bisa diterima di loket.'
                  f'<ul class="rapat">{daftar}</ul></div></div>')
    if koreksi:
        daftar = "".join(
            _tautan(x, f' — <i>{e(x["catatan_jawab"])}</i>' if x["catatan_jawab"]
                    else ' — <i>catatannya belum diisi</i>') for x in koreksi)
        hasil += (f'<div class="pesan ingat"><div class="teks"><b>{len(koreksi)} perlu '
                  f'koreksi.</b> Suratnya ada, tetapi harus diperbaiki pemohon dulu.'
                  f'<ul class="rapat">{daftar}</ul></div></div>')
    if not hasil:
        hasil = ('<div class="pesan baik"><div class="teks"><b>Kelengkapan terpenuhi.</b> '
                 'Berkas siap diterima di loket.</div></div>')
    return hasil


def _progres_periksa(d):
    sudah, semua = pradaftar.progres(d["pohon"])
    persen = round(100 * sudah / semua) if semua else 100
    return f"""<div class="periksa-progres" data-progres>
  <div class="periksa-progres-teks"><span><b data-progres-sudah>{sudah}</b> dari
    <b data-progres-semua>{semua}</b> butir sudah diperiksa</span>
    <span class="petunjuk" data-progres-persen>{persen}%</span></div>
  <div class="progres" role="progressbar" aria-label="Butir yang sudah diperiksa"
       aria-valuemin="0" aria-valuemax="{semua}" aria-valuenow="{sudah}">
    <span style="width:{persen}%"></span></div>
</div>"""


def _alat_periksa(d, tambahan=""):
    """Saringan tampilan dan lompat ke butir yang belum — di sisi peramban saja."""
    sudah, semua = pradaftar.progres(d["pohon"])
    masalah = len(d["kurang"]) + len(d.get("koreksi", []))
    return f"""<div class="periksa-alat">
  <div class="periksa-tapis" role="group" aria-label="Tampilkan butir">
    <button type="button" data-tapis="" aria-pressed="true" class="aktif">Semua</button>
    <button type="button" data-tapis="belum" aria-pressed="false">Belum diperiksa
      <span class="lencana" data-hitung="belum">{semua - sudah}</span></button>
    <button type="button" data-tapis="masalah" aria-pressed="false">Kurang &amp; koreksi
      <span class="lencana" data-hitung="masalah">{masalah}</span></button>
  </div>
  <button type="button" class="btn kecil" data-ke-belum
          title="Lompat ke butir berikutnya yang belum diperiksa">Berikutnya yang belum &darr;</button>
  {tambahan}
</div>"""


CATATAN_PERIKSA = """<p class="petunjuk">Butir yang redup tidak berlaku untuk
permohonan ini — menurut jenis subjek pemohon dan asal tanahnya. Butir itu tetap
ikut tercetak pada formulir, dengan kedua kolomnya dikosongkan.</p>
<p class="petunjuk"><b>Perlu koreksi</b> dipakai bila suratnya dibawa tetapi ada
yang salah. Tercetak di kolom Ada beserta catatannya, dan menahan penerimaan
berkas seperti butir yang kurang. Daftar catatan bakunya diatur di Data
referensi → Kelengkapan.</p>
<p class="petunjuk">Butir yang belum dijawab dihitung <b>Tidak Ada</b> saat berkas
diterima dan saat formulirnya dicetak.</p>"""

KOSONG_PERIKSA = ('<div class="kartu"><div class="kosong">'
                  '<b>Jenis hak ini belum punya daftar kelengkapan</b>'
                  '<span>Baru Hak Milik yang formulirnya terpasang. Tambahkan '
                  'formulirnya di Data referensi → Kelengkapan.</span></div></div>')


def _panel_periksa(d, boleh_ubah=True):
    """Tab Kelengkapan: daftar butir formulir, plus ringkasan kekurangannya."""
    if not d.get("kelengkapan_id"):
        return KOSONG_PERIKSA
    # Pindah ke layar penuh lewat tombol kirim, bukan tautan: centangan dan
    # isian lain yang belum tersimpan ikut disimpan dulu.
    penuh = (f'<button class="btn kecil" type="submit" form="form-pradaftar" '
             f'name="lanjut" value="periksa" '
             f'title="Simpan, lalu buka daftar ini selebar layar">'
             f'{ikon("layar")}Layar penuh</button>' if boleh_ubah else
             f'<a class="btn kecil" href="/pradaftar/{d["id"]}/periksa">'
             f'{ikon("layar")}Layar penuh</a>')
    return f"""<div class="kartu" data-periksa><h2>{e(d.get("judul_formulir") or "Daftar kelengkapan")}</h2>
<div class="badan">
<p class="petunjuk">{e(d.get("dasar_formulir") or "")}</p>
{_progres_periksa(d)}
<div data-periksa-ringkas>{_ringkas_periksa(d)}</div>
{_alat_periksa(d, penuh)}
{_daftar_periksa(d, boleh_ubah)}
<div style="margin-top:.8rem">{CATATAN_PERIKSA}</div>
</div></div>"""


def halaman_periksa(pengguna, d, pesan=None, boleh_ubah=True):
    """Periksa kelengkapan selebar layar: daftar di kiri, hasilnya menempel di kanan.

    Formulirnya hanya memuat centangan dan dikirim ke /periksa, yang menyimpan
    lewat pradaftar.simpan_jawab — data pemohon tidak ikut tertimpa.
    """
    pid = d["id"]
    judul = d.get("pemohon_nama") or "Pradaftar"
    subjek = dict(SUBJEK).get(d.get("pemohon_jenis_subjek"), d.get("pemohon_jenis_subjek"))
    asal = dict(ASAL_TANAH).get(d.get("asal_tanah"), d.get("asal_tanah"))
    bawah = " · ".join(e(x) for x in (d.get("nomor"), d.get("jenis_hak"), subjek, asal) if x)

    if boleh_ubah:
        kembali = ('<button class="btn" type="submit" form="form-periksa" name="lanjut" '
                   'value="kembali" title="Simpan, lalu kembali ke pradaftar">'
                   '&larr; Simpan &amp; kembali</button>')
        simpan = ('<button class="btn utama" type="submit" form="form-periksa"'
                  ' title="Simpan (Ctrl+S)">Simpan'
                  '<kbd class="pintas" aria-hidden="true">Ctrl S</kbd></button>')
    else:
        kembali = f'<a class="btn" href="/pradaftar/{pid}#q-periksa">&larr; Kembali</a>'
        simpan = ""
    cetak = (f'<a class="btn" href="/pradaftar/{pid}/pratinjau/kelengkapan">'
             f'Pratinjau cetak</a>')
    kepala = f"""<div class="fokus-atas">
  {kembali}
  <div class="fokus-judul"><h1>{e(judul)}</h1><p>{bawah}</p></div>
  <div class="aksi">{cetak}{simpan}</div>
</div>"""

    if not d.get("kelengkapan_id"):
        return layout(f"Periksa · {judul}", kepala + KOSONG_PERIKSA, pengguna,
                      "/pradaftar", pesan, fokus=True)

    spanduk = "" if boleh_ubah else (
        '<div class="pesan">Pradaftar ini <b>hanya bisa dilihat</b> — sudah diterima '
        'di loket, dibatalkan, atau bukan milik Anda.</div>')
    pintas = " data-simpan-pintas data-jaga-ubah" if boleh_ubah else ""
    petunjuk_kunci = """<div class="kunci-pintas"><b>Lebih cepat dengan papan ketik</b>
<span>Klik salah satu pilihan, lalu tekan <kbd>1</kbd> Ada, <kbd>2</kbd> Perlu
koreksi, atau <kbd>3</kbd> Tidak Ada — kursor pindah sendiri ke butir berikutnya.
<kbd>Ctrl</kbd> <kbd>S</kbd> menyimpan.</span></div>""" if boleh_ubah else ""

    isi = f"""{kepala}
{spanduk}
<form id="form-periksa" method="post" action="/pradaftar/{pid}/periksa"{pintas}>
<div class="fokus-grid" data-periksa>
  <div class="fokus-utama">
    <div class="kartu"><h2>{e(d.get("judul_formulir") or "Daftar kelengkapan")}
      <span class="petunjuk">{e(d.get("dasar_formulir") or "")}</span></h2>
    <div class="badan">
      {_alat_periksa(d)}
      {_daftar_periksa(d, boleh_ubah)}
    </div></div>
  </div>
  <aside class="fokus-samping">
    <div class="kartu"><h2>Hasil pemeriksaan</h2><div class="badan">
      {_progres_periksa(d)}
      <div data-periksa-ringkas>{_ringkas_periksa(d)}</div>
      {petunjuk_kunci}
    </div></div>
    <div class="kartu"><div class="badan">{CATATAN_PERIKSA}</div></div>
  </aside>
</div>
</form>"""
    return layout(f"Periksa · {judul}", isi, pengguna, "/pradaftar", pesan, fokus=True)


def _tandai_alternatif(n, keluar):
    """Kumpulkan id grup yang anaknya bersifat alternatif — sekali telusur."""
    if any(a["sifat"] == "alternatif" for a in n["anak"]):
        keluar.add(n["id"])
    for a in n["anak"]:
        _tandai_alternatif(a, keluar)


def _kartu_cetak(d, utama=True):
    """Dua tautan pratinjau PDF.

    Tautan, bukan tombol kirim: formulir loket dibaca sebentar lalu dicetak,
    bukan disunting, jadi mengunduh DOCX dulu cuma menambah satu langkah. Dari
    halaman pratinjaunya tersedia Cetak, Unduh PDF, dan Unduh DOCX.

    Selalu tersedia, termasuk pada pradaftar yang sudah diterima atau sudah
    ditutup: formulirnya justru dibutuhkan sebagai lampiran arsip berkas, dan
    mencetak tidak mengubah apa pun.
    """
    dasar = f'/pradaftar/{d["id"]}/pratinjau'
    kelas = "btn utama" if utama else "btn"
    pengembalian = (
        f'<a class="btn" href="{dasar}/pengembalian">Surat pengembalian berkas</a>'
        if not d["lengkap"] else
        '<span class="btn" aria-disabled="true" '
        'title="kelengkapannya sudah terpenuhi">Surat pengembalian berkas</span>')
    catatan = ('' if not d["lengkap"] else
               '<p class="petunjuk">Surat pengembalian tidak berlaku: '
               'kelengkapannya sudah terpenuhi.</p>')
    return f"""<div class="kartu"><h2>Cetak</h2><div class="badan">
<p class="petunjuk">Formulir kelengkapan dicetak untuk arsip berkas; surat
pengembalian diserahkan kepada pemohon yang berkasnya belum lengkap. Keduanya
terbuka sebagai pratinjau PDF, tinggal ditekan Cetak.</p>
<div class="tahap-kaki">
  <a class="{kelas}" href="{dasar}/kelengkapan">Daftar Kelengkapan Persyaratan</a>
  {pengembalian}
</div>
{catatan}</div></div>"""


def _sebut_tertahan(d):
    """'2 yang kurang dan 1 yang perlu koreksi' — yang menahan penerimaan."""
    bagian = []
    if d["kurang"]:
        bagian.append(f'{len(d["kurang"])} yang kurang')
    if d.get("koreksi"):
        bagian.append(f'{len(d["koreksi"])} yang perlu koreksi')
    return " dan ".join(bagian)


def _panel_putusan(d, boleh_ubah=True):
    """Tab Kesimpulan: terima di loket, kembalikan, atau batalkan."""
    if d["status"] == "diterima":
        tautan = (f'<a class="btn utama" href="/berkas/{d["berkas_id"]}">'
                  f'Buka berkas {d["berkas_id"]:04d} &rarr;</a>'
                  if d["berkas_id"] else "")
        catatan = (f'<p class="petunjuk">Diterima walau belum lengkap, dengan alasan: '
                   f'<b>{e(d["alasan_terima"])}</b></p>' if d.get("alasan_terima") else "")
        return (f'<div class="kartu"><h2>Sudah diterima di loket</h2><div class="badan">'
                f'<p>Pradaftar ini sudah jadi berkas dan tidak bisa diubah lagi. '
                f'Pengisian selanjutnya dilakukan di berkasnya.</p>{catatan}'
                f'<div class="tahap-kaki">{tautan}</div></div></div>'
                + _kartu_cetak(d, utama=False))

    if not boleh_ubah:
        return (_kartu_cetak(d)
                + '<div class="kartu"><div class="kosong"><b>Hanya bisa dilihat</b>'
                  '<span>Pradaftar ini sudah ditutup, atau bukan milik Anda. '
                  'Mencetaknya tetap boleh.</span></div></div>')

    cetak = _kartu_cetak(d, utama=False)

    if not d["lengkap"]:
        terima = f"""<div class="kartu"><h2>Terima di loket</h2><div class="badan">
<div class="pesan ingat"><b>Masih ada {_sebut_tertahan(d)}.</b>
Berkas yang belum lengkap tetap bisa diterima, tetapi alasannya wajib ditulis dan
ikut tersimpan pada berkasnya.</div>
{area("Alasan menerima berkas yang belum lengkap", "alasan_terima", "",
      "mis. kekurangannya menyusul paling lambat 3 hari kerja", 2)}
<div class="tahap-kaki">
  <button class="btn" type="submit" form="form-terima">Terima bersyarat</button>
</div></div></div>"""
    else:
        terima = """<div class="kartu"><h2>Terima di loket</h2><div class="badan">
<div class="pesan baik"><b>Kelengkapan terpenuhi.</b> Menerima berkas ini akan
membuat berkas baru berisi pemohon, letak tanah, dan seluruh dokumen yang tadi
dicentang — siap dilanjutkan Panitia A.</div>
<div class="tahap-kaki">
  <button class="btn utama" type="submit" form="form-terima">Terima di loket</button>
</div></div></div>"""

    tutup = """<div class="kartu"><h2>Tutup tanpa diterima</h2><div class="badan">
<p class="petunjuk">Dipakai bila berkasnya dikembalikan untuk dilengkapi, atau
pemohon membatalkan permohonannya. Isinya tetap tersimpan.</p>
<div class="tahap-kaki">
  <button class="btn" type="submit" form="form-status" name="status"
          value="dikembalikan">Tandai dikembalikan</button>
  <button class="btn sunyi" type="submit" form="form-status" name="status"
          value="batal">Tandai batal</button>
</div></div></div>"""
    return terima + cetak + tutup


def halaman_pradaftar_form(pengguna, d, ref, pesan=None, boleh_ubah=True):
    """d = hasil pradaftar.muat, atau None untuk pradaftar baru."""
    baru = d is None
    if baru:
        d = {"id": None, "nomor": None, "tanggal": dt.date.today().isoformat(),
             "jenis_hak": "HM", "jenis_kegiatan": "baru", "asal_tanah": "tanah_negara",
             "pemohon_jenis_subjek": "perorangan", "status": "baru",
             "pohon": [], "kurang": [], "koreksi": [], "lengkap": False,
             "kelengkapan_id": None}

    aksi = "/pradaftar/baru" if baru else f"/pradaftar/{d['id']}"
    hak_pilihan = [(r["kode"], f"{r['kode']} — {r['nama']}") for r in ref["jenis_hak"]]
    kec_pilihan = [(r["id"], r["nama"]) for r in ref["kecamatan"]]
    # Bentuknya persis sama dengan halaman berkas: app.js memakai satu penangan
    # untuk keduanya, dan mencarinya lewat id f_kecamatan / f_desa.
    desa_json = json.dumps([{"id": r["id"], "nama": r["nama"], "jenis": r["jenis"],
                             "kecamatan_id": r["kecamatan_id"],
                             "pejabat": r["nama_pejabat"] or ""}
                            for r in ref["desa"]], ensure_ascii=False)
    opsi_desa = '<option value="">- pilih desa/kelurahan -</option>' + "".join(
        f'<option value="{r["id"]}"'
        f'{" selected" if str(r["id"]) == str(d.get("desa_id") or "") else ""}>'
        f'{e(r["jenis"])} {e(r["nama"])}</option>' for r in ref["desa"])

    p_pemohon = f"""<div class="kartu"><h2>Permohonan</h2><div class="badan">
<div class="grid g3">
  {kotak("Jenis hak dimohon", "jenis_hak", hak_pilihan, d["jenis_hak"],
         petunjuk="menentukan daftar kelengkapan mana yang dipakai")}
  {kotak("Jenis kegiatan", "jenis_kegiatan", KEGIATAN, d["jenis_kegiatan"])}
  {kotak("Asal tanah", "asal_tanah", ASAL_TANAH, d["asal_tanah"],
         petunjuk="menentukan butir mana yang berlaku (Tanah Negara / Hak Pengelolaan)")}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Tanggal pradaftar", "tanggal", d.get("tanggal"), "date")}
  {bidang("Nomor agenda loket", "nomor_tampil", d.get("nomor") or "(diberi saat disimpan)",
          atribut="disabled")}
</div>
</div></div>

<div class="kartu"><h2>Pemohon</h2><div class="badan">
<div class="grid g3">
  {kotak("Jenis subjek", "pemohon_jenis_subjek", SUBJEK, d.get("pemohon_jenis_subjek"),
         petunjuk="badan hukum memunculkan butir c sampai g pada daftar kelengkapan")}
  {bidang("Nama pemohon", "pemohon_nama", d.get("pemohon_nama"), wajib=True)}
  {bidang("NIK", "pemohon_nik", d.get("pemohon_nik"), petunjuk="16 digit angka")}
</div>
<div class="grid g2" style="margin-top:.75rem">
  {area("Alamat", "pemohon_alamat", d.get("pemohon_alamat"), baris=2)}
  {bidang("Telepon yang bisa dihubungi", "pemohon_telepon", d.get("pemohon_telepon"),
          petunjuk="dipakai memberi tahu kalau berkasnya perlu dilengkapi")}
</div>
<div class="grid g2" style="margin-top:.75rem">
  {bidang("Nama penerima kuasa", "kuasa_nama", d.get("kuasa_nama"),
          petunjuk="diisi hanya bila permohonan diajukan lewat kuasa")}
  {bidang("NIK penerima kuasa", "kuasa_nik", d.get("kuasa_nik"))}
</div>
</div></div>"""

    p_tanah = f"""<div class="kartu"><h2>Letak tanah</h2><div class="badan">
<div class="grid g3">
  {kotak("Kecamatan", "kecamatan", kec_pilihan, d.get("kecamatan_id"), "- pilih kecamatan -")}
  <div><label for="f_desa">Desa / Kelurahan</label>
    <select id="f_desa" name="desa_id" data-terpilih="{e(d.get('desa_id'))}">{opsi_desa}</select>
    <div class="petunjuk">boleh menyusul; letak pasti diambil dari Peta Bidang Tanah</div></div>
  {bidang("Letak lain / dusun", "letak_lain", d.get("letak_lain"),
          petunjuk="diisi bila desanya belum terdaftar")}
</div>
<div class="grid g3" style="margin-top:.75rem">
  {bidang("Luas menurut surat (m²)", "luas_surat", d.get("luas_surat"), "number")}
  {bidang("Nomor Peta Bidang Tanah", "nomor_pbt", d.get("nomor_pbt"),
          petunjuk="kosongkan bila belum diukur")}
</div>
{area("Catatan loket", "catatan", d.get("catatan"), baris=2)}
</div></div>"""

    p_periksa = _panel_periksa(d, boleh_ubah) if not baru else f"""
<div class="kartu"><h2>Kelengkapan berkas</h2><div class="badan">
<div class="pesan ingat"><b>Simpan dulu.</b> Daftar kelengkapannya muncul setelah
jenis hak dipilih dan pradaftarnya tersimpan — butir mana yang berlaku ditentukan
jenis subjek pemohon dan asal tanahnya.</div>
</div></div>"""

    isi_panel = {"q-pemohon": p_pemohon, "q-tanah": p_tanah, "q-periksa": p_periksa}
    if baru:
        tab = _bilah_langkah(LANGKAH_PRADAFTAR)
        n = len(LANGKAH_PRADAFTAR)
        panel = []
        for i, (kunci, _, _, petunjuk) in enumerate(LANGKAH_PRADAFTAR, 1):
            kepala, kaki = _kaki_langkah(i, n, petunjuk)
            kaki = kaki.replace('form="form-berkas">Simpan berkas',
                                'form="form-pradaftar">Simpan pradaftar')
            kaki = kaki.replace('href="/berkas"', 'href="/pradaftar"')
            panel.append(f'<div class="panel" id="{kunci}">{kepala}'
                         f'{isi_panel[kunci]}{kaki}</div>')
        panel = chr(10).join(panel)
    else:
        isi_panel["q-putusan"] = _panel_putusan(d, boleh_ubah)
        if d["status"] == "baru":
            lencana = ('<span class="lencana hijau" data-lencana-periksa>✓</span>'
                       if d["lengkap"]
                       else f'<span class="lencana merah" data-lencana-periksa>'
                            f'{len(d["kurang"]) + len(d["koreksi"])}</span>')
        else:
            lencana = ""
        tab = _tab("pradaftar", [
            ("q-pemohon", "Pemohon"), ("q-tanah", "Letak tanah"),
            ("q-periksa", "Kelengkapan", lencana),
            ("q-putusan", "Kesimpulan & cetak")])
        panel = chr(10).join(f'<div class="panel" id="{k}">{v}</div>'
                             for k, v in isi_panel.items())

    # Ketiganya harus di LUAR form-pradaftar: peramban membuang form bersarang.
    form_luar = "" if baru or not boleh_ubah else (
        f'<form id="form-terima" method="post" action="/pradaftar/{d["id"]}/terima">'
        f'<input type="hidden" name="alasan" value=""></form>'
        f'<form id="form-status" method="post" action="/pradaftar/{d["id"]}/status"></form>')

    if baru:
        aksi_kepala = '<a class="btn" href="/pradaftar">&larr; Batal</a>'
    elif boleh_ubah:
        aksi_kepala = ('<a class="btn" href="/pradaftar">&larr; Daftar</a>'
                       '<button class="btn utama" type="submit" form="form-pradaftar"'
                       ' title="Simpan (Ctrl+S)">Simpan'
                       '<kbd class="pintas" aria-hidden="true">Ctrl S</kbd></button>')
    else:
        aksi_kepala = '<a class="btn" href="/pradaftar">&larr; Daftar</a>'

    spanduk = "" if boleh_ubah or baru else (
        '<div class="pesan">Pradaftar ini <b>hanya bisa dilihat</b> — sudah diterima '
        'di loket, dibatalkan, atau bukan milik Anda.</div>')
    buka_kunci = "" if boleh_ubah else '<fieldset disabled class="baca-saja">'
    tutup_kunci = "" if boleh_ubah else "</fieldset>"
    pintas = " data-simpan-pintas" if boleh_ubah else ""
    judul = d.get("pemohon_nama") or "Pradaftar baru"
    bawah = (f"{e(d['nomor'])} · {e(d['jenis_hak'])} · {e(d['jenis_kegiatan'])}"
             if not baru else "Pradaftar baru")

    isi = f"""<div class="lengket-atas">
<div class="judul">
  <div><h1>{e(judul)}</h1><p>{bawah}</p></div>
  <div class="aksi">{aksi_kepala}</div>
</div>
{tab}
</div>
{spanduk}
<form id="form-pradaftar" method="post" action="{aksi}"{pintas}>
{buka_kunci}
{panel}
{tutup_kunci}
</form>
{form_luar}
<script>window.DAFTAR_DESA = {desa_json};</script>"""
    return layout(judul, isi, pengguna, "/pradaftar", pesan)


# ------------------------------------------------------ susun formulir
# Halaman kerja satu formulir kelengkapan (/referensi/kelengkapan/<id>).
# Susunannya: daftar butir di kiri — bisa diseret, digeser dengan tombol
# panah, atau disunting di tempat — dan di kanan panel tambah butir serta
# pengaturan formulir. Semua tombol tetap formulir biasa; app.js
# (pasangSusun) hanya menambahkan seret-lepas di atasnya.

# Butir yang sering diminta Kantah di luar lampiran Permen. Hanya saran
# pengisian — bunyinya tetap bebas diketik.
SARAN_BUTIR = [
    "Peta Analisis Tata Ruang (PATR)",
    "Pertimbangan Teknis Pertanahan",
    "Surat Pernyataan tidak dalam sengketa",
    "Surat Keterangan Riwayat Tanah",
    "Surat Pernyataan Penguasaan Fisik Bidang Tanah",
    "Fotokopi Kartu Keluarga",
    "Fotokopi SPPT PBB tahun berjalan",
    "Bukti pembayaran BPHTB",
    "Bukti pembayaran PPh",
    "Surat Ukur / Gambar Situasi",
    "Surat kuasa bermeterai",
    "Persetujuan Kesesuaian Kegiatan Pemanfaatan Ruang (PKKPR)",
]

LABEL_SUBJEK = {"perorangan": "perorangan", "badan_hukum": "badan hukum",
                "instansi": "instansi"}
LABEL_ASAL = {"tanah_negara": "Tanah Negara", "hak_pengelolaan": "Hak Pengelolaan"}


def _cap_susun(n):
    """Keterangan singkat satu butir di daftar susun: sifat, syarat berlaku,
    dan kemana ia disalin saat pradaftar jadi berkas."""
    cap = []
    if not n["aktif"]:
        cap.append('<span class="cap abu">nonaktif</span>')
    if n["sifat"] == "judul":
        cap.append('<span class="cap abu tanpa-titik">kepala kelompok</span>')
    elif n["sifat"] == "alternatif":
        cap.append('<span class="cap aksen tanpa-titik">salah satu</span>')
    if n["sifat"] != "judul" and not n["wajib"]:
        cap.append('<span class="cap tanpa-titik">tidak wajib</span>')
    if n["isian_bebas"]:
        cap.append('<span class="cap tanpa-titik">isian ……</span>')
    if n["jamak"]:
        cap.append('<span class="cap hijau tanpa-titik">boleh lebih dari satu</span>')
    for nilai, label in (("subjek", LABEL_SUBJEK), ("asal_tanah", LABEL_ASAL)):
        if n[nilai] != "*":
            teks = ", ".join(label.get(x.strip(), x.strip()) for x in n[nilai].split(","))
            cap.append(f'<span class="cap kuning tanpa-titik">hanya {e(teks)}</span>')
    if n["slot_baku"]:
        cap.append(f'<span class="cap tanpa-titik" title="Disalin ke dokumen berkas '
                   f'kategori ini">→ {e(n["slot_baku"])}</span>')
    if n["dipakai"]:
        cap.append(f'<span class="petunjuk">dicentang di {n["dipakai"]} pradaftar</span>')
    return " ".join(cap)


def _pilihan_induk(butir, kecuali=None):
    """Pilihan "masuk ke kelompok": tingkat teratas, atau butir aktif mana pun.
    Butir itu sendiri dan keturunannya tidak ditawarkan."""
    opsi, lewati = [("", "— Tingkat teratas —")], set()
    for n in butir:
        if kecuali and (n["id"] == kecuali or n["induk_id"] in lewati):
            lewati.add(n["id"])
            continue
        if not n["aktif"]:
            continue
        label = f'{"    " * n["tingkat"]}{n["penanda"] + ". " if n["penanda"] else ""}{n["nama"]}'
        opsi.append((n["id"], label if len(label) <= 80 else label[:77] + "…"))
    return opsi


def _medan_butir(n, awalan, butir, otomatis, baru=False):
    """Isian satu butir. `awalan` membuat id tiap medan unik — satu halaman
    memuat puluhan formulir yang sama bentuknya."""
    n = n or {"id": None, "nama": "", "nama_dokumen": "", "sifat": "butir", "wajib": 1,
              "isian_bebas": 0, "jamak": 0, "subjek": "*", "asal_tanah": "*",
              "slot_baku": "", "dasar": "", "penanda": "", "induk_id": None}
    i = lambda x: f"{awalan}-{x}"
    cek = lambda x: " checked" if n.get(x) else ""
    slot = [("", "— tidak disalin khusus (tambahan) —")] + [(k, k) for k in db.KATEGORI_BAKU]
    penanda = (f'<div><label for="{i("penanda")}">No./huruf</label>'
               f'<input id="{i("penanda")}" name="penanda" value="{e(n["penanda"])}" '
               f'maxlength="8"{" disabled" if otomatis else ""}>'
               f'<div class="petunjuk">{"diatur otomatis" if otomatis else "mis. 4, b, c"}'
               f'</div></div>')
    atr_induk = f'id="{i("induk")}"'
    induk = (f'<div><label for="{i("induk")}">Letak</label>'
             f'{pilih("induk_id", _pilihan_induk(butir, n["id"]), n["induk_id"], atribut=atr_induk)}'
             f'<div class="petunjuk">jadikan anak dari butir/kelompok ini</div></div>')
    return f"""<div class="susun-medan">
  <div class="penuh"><label for="{i("nama")}">Bunyi butir <span class="wajib">*</span></label>
    <textarea id="{i("nama")}" name="nama" rows="2" required list="saran-butir"
      placeholder="mis. Peta Analisis Tata Ruang (PATR)">{e(n["nama"])}</textarea></div>
  {'<div class="penuh"><label for="' + i("saran") + '">Atau pilih dari yang sering dipakai</label><input id="' + i("saran") + '" list="saran-butir" data-salin-ke="' + i("nama") + '" placeholder="ketik untuk mencari…"></div>' if baru else ""}
  <div><label for="{i("sifat")}">Jenis baris</label>
    {pilih("sifat", SUSUN.SIFAT, n["sifat"], atribut=f'id="{i("sifat")}" data-sifat')}
    <div class="petunjuk">kepala kelompok tidak dicentang; "salah satu" = cukup satu
    di antara saudaranya</div></div>
  {induk}
  <div class="penuh susun-centang">
    <label class="centang-sebaris"><input type="checkbox" name="wajib" value="1"{cek("wajib")}>
      Wajib — menahan penerimaan bila tidak ada</label>
    <label class="centang-sebaris"><input type="checkbox" name="jamak" value="1"{cek("jamak")}>
      Boleh lebih dari satu surat</label>
    <label class="centang-sebaris"><input type="checkbox" name="isian_bebas" value="1"{cek("isian_bebas")}>
      Nama suratnya diketik petugas (……)</label>
  </div>
  <details class="penuh susun-lanjut"><summary>Pengaturan lanjutan</summary>
  <div class="susun-medan">
    <div><label for="{i("subjek")}">Berlaku untuk pemohon</label>
      {pilih("subjek", SUSUN.SUBJEK, n["subjek"], atribut=f'id="{i("subjek")}"')}</div>
    <div><label for="{i("asal")}">Berlaku untuk asal tanah</label>
      {pilih("asal_tanah", SUSUN.ASAL, n["asal_tanah"], atribut=f'id="{i("asal")}"')}</div>
    <div><label for="{i("dok")}">Nama surat di berkas</label>
      <input id="{i("dok")}" name="nama_dokumen" value="{e(n["nama_dokumen"] or "")}"
        placeholder="kosong = pakai bunyi butir"></div>
    <div><label for="{i("slot")}">Salin ke kategori dokumen</label>
      {pilih("slot_baku", slot, n["slot_baku"] or "", atribut=f'id="{i("slot")}"')}</div>
    <div><label for="{i("dasar")}">Dasar hukum</label>
      <input id="{i("dasar")}" name="dasar" value="{e(n["dasar"] or "")}"
        placeholder="mis. Pasal 54 ayat (1)"></div>
    {penanda}
  </div></details>
</div>"""


def _baris_susun(n, d, boleh_ubah, dibuka=None):
    fid = d["id"]
    dasar = f"/referensi/kelengkapan/{fid}/butir/{n['id']}"
    # "kepala", bukan "judul": .judul sudah dipakai bilah judul halaman.
    kelas = ["susun-baris", f"dalam-{min(n['tingkat'], 3)}"]
    if n["sifat"] == "judul":
        kelas.append("kepala")
    if not n["aktif"]:
        kelas.append("mati")
    nomor = (f'<span class="susun-no">{e(n["penanda"])}</span>' if n["penanda"]
             else '<span class="susun-no tanpa" aria-hidden="true">·</span>')
    dasar_hukum = (f'<span class="periksa-dasar">{e(n["dasar"])}</span>'
                   if n["dasar"] else "")
    kepala = f"""<div class="susun-isi">{nomor}
  <div class="susun-teks"><div class="susun-nama">{e(n["nama"])}</div>{dasar_hukum}
    <div class="susun-cap">{_cap_susun(n)}</div></div></div>"""
    if not boleh_ubah:
        return f'<li class="{" ".join(kelas)}" id="s-{n["id"]}">{kepala}</li>'

    if not n["aktif"]:
        aksi = (f'<form method="post" action="{dasar}/pulihkan" class="susun-aksi">'
                f'<button class="btn kecil">Pulihkan</button></form>')
        return f'<li class="{" ".join(kelas)}" id="s-{n["id"]}">{kepala}{aksi}</li>'

    geser = "".join(
        f'<button class="ikon-btn kecil" name="arah" value="{arah}" title="{judul}" '
        f'aria-label="{judul}">{panah}</button>'
        for arah, panah, judul in (("naik", "↑", "Naikkan"), ("turun", "↓", "Turunkan"),
                                   ("keluar", "←", "Keluarkan dari kelompok"),
                                   ("masuk", "→", "Masukkan ke butir di atasnya")))
    hapus_label = ("Nonaktifkan" if n["dipakai"] else "Hapus")
    hapus_tanya = ("Butir ini sudah dicentang di pradaftar lama, jadi hanya dinonaktifkan. "
                   "Lanjutkan?" if n["dipakai"] else
                   "Hapus butir ini" + (" berikut seluruh anaknya" if n["jml_anak"] else "")
                   + " dari formulir?")
    otomatis = d.get("nomor_otomatis", 1)
    # Panel sunting anak langsung <li>, supaya membentang selebar baris. Tanpa
    # JavaScript tombol Ubah adalah tautan ?ubah=<id> yang dijawab server
    # dengan panel ini sudah terbuka; app.js cukup membuka-tutupnya di tempat.
    buka = dibuka == n["id"]
    tombol_ubah = (f'<a class="btn kecil{" aktif" if buka else ""}" '
                   f'href="/referensi/kelengkapan/{fid}?ubah={n["id"]}#s-{n["id"]}" '
                   f'data-buka-sunting="u-{n["id"]}" '
                   f'aria-expanded="{"true" if buka else "false"}">Ubah</a>')
    sunting = f"""<div class="susun-panel" id="u-{n["id"]}"{"" if buka else " hidden"}>
<form method="post" action="/referensi/kelengkapan/{fid}/butir" class="susun-form">
<input type="hidden" name="id" value="{n["id"]}">
{_medan_butir(n, f"b{n['id']}", d["butir"], otomatis)}
<div class="aksi-baris">
  <button class="btn utama kecil">Simpan butir</button>
  <button class="btn kecil bahaya" formaction="{dasar}/hapus" formnovalidate
          data-konfirmasi="{e(hapus_tanya)}">{hapus_label}</button>
  <a class="btn kecil hantu" href="/referensi/kelengkapan/{fid}#s-{n["id"]}"
     data-buka-sunting="u-{n["id"]}">Batal</a>
</div></form></div>"""
    anak = (f'<a class="btn kecil hantu" href="/referensi/kelengkapan/{fid}?induk={n["id"]}#tambah"'
            f' title="Tambah butir di dalam kelompok ini">+ anak</a>')
    return (f'<li class="{" ".join(kelas)}" id="s-{n["id"]}" data-id="{n["id"]}" '
            f'data-judul="{1 if n["sifat"] == "judul" else 0}">'
            f'<span class="susun-pegang" title="Seret untuk memindah" aria-hidden="true">'
            f'⋮⋮</span>{kepala}'
            f'<div class="susun-aksi"><form method="post" action="{dasar}/geser" '
            f'class="susun-geser">{geser}</form>{anak}{tombol_ubah}</div>{sunting}</li>')


def halaman_susun_kelengkapan(pengguna, d, jenis_hak, pesan=None, boleh_ubah=True,
                              induk_pilih=None, dibuka=None):
    """d = susun_kelengkapan.muat()."""
    fid = d["id"]
    aktif = [n for n in d["butir"] if n["aktif"]]
    mati = [n for n in d["butir"] if not n["aktif"]]
    otomatis = d.get("nomor_otomatis", 1)
    hak = dict((r["kode"], r["nama"]) for r in jenis_hak)
    sasaran = ("semua jenis hak" if d["jenis_hak"] == "*"
               else f'{d["jenis_hak"]} — {hak.get(d["jenis_hak"], "")}')
    bawah = " · ".join(x for x in (
        e(d["kode"]), e(sasaran), f"{len(aktif)} butir",
        f'dipakai {d["jml_pradaftar"]} pradaftar' if d["jml_pradaftar"] else "belum dipakai",
        "" if d["aktif"] else "NONAKTIF") if x)

    baris = "".join(_baris_susun(n, d, boleh_ubah, dibuka) for n in aktif)
    riwayat = ""
    if mati:
        riwayat = (f'<details class="kartu susun-mati"><summary><b>{len(mati)} butir '
                   f'nonaktif</b> <span class="petunjuk">— sudah dihapus dari formulir, '
                   f'disimpan untuk pradaftar lama</span></summary><ol class="susun">'
                   + "".join(_baris_susun(n, d, boleh_ubah) for n in mati)
                   + '</ol></details>')
    kosong = ('<div class="kosong"><b>Formulir ini belum punya butir</b>'
              '<span>Tambahkan butir pertamanya dari panel di kanan.</span></div>'
              if not aktif else "")

    kembali = '<a class="btn" href="/referensi#r-lengkap">&larr; Data referensi</a>'
    aksi = ""
    if boleh_ubah:
        aksi = (("" if otomatis else
                 f'<form method="post" action="/referensi/kelengkapan/{fid}/nomori">'
                 f'<button class="btn">Nomori ulang</button></form>')
                + '<a class="btn utama" href="#tambah" data-fokus="f-tambah-nama">'
                  '+ Tambah butir</a>')
    kepala = f"""<div class="fokus-atas">
  {kembali}
  <div class="fokus-judul"><h1>{e(d["judul"])}</h1><p>{bawah}</p></div>
  <div class="aksi">{aksi}</div>
</div>"""

    petunjuk = ("""<p class="petunjuk susun-petunjuk">Seret <b>⋮⋮</b> untuk memindah butir, atau
pakai tombol panah: <b>↑ ↓</b> menukar urutan, <b>→</b> memasukkan butir ke dalam butir di
atasnya (jadi anaknya), <b>←</b> mengeluarkannya dari kelompok. """
                + ("Nomor dan huruf disusun ulang sendiri." if otomatis else
                   "Penomoran otomatis dimatikan — tekan <b>Nomori ulang</b> bila perlu.")
                + "</p>") if boleh_ubah else ""

    samping = ""
    if boleh_ubah:
        n_baru = {"id": None, "nama": "", "nama_dokumen": "", "sifat": "butir", "wajib": 1,
                  "isian_bebas": 0, "jamak": 0, "subjek": "*", "asal_tanah": "*",
                  "slot_baku": "", "dasar": "", "penanda": "", "induk_id": induk_pilih}
        tambah = f"""<section class="kartu" id="tambah"><h2>Tambah butir</h2><div class="badan">
<form method="post" action="/referensi/kelengkapan/{fid}/butir" class="susun-form">
{_medan_butir(n_baru, "f-tambah", d["butir"], otomatis, baru=True)}
<div class="aksi-baris"><button class="btn utama">Tambahkan</button>
<span class="petunjuk">masuk di akhir kelompok yang dipilih — pindahkan sesudahnya</span></div>
</form></div></section>"""
        kegiatan = SUSUN.KEGIATAN
        hak_pilihan = [("*", "Semua jenis hak")] + [(r["kode"], f'{r["kode"]} — {r["nama"]}')
                                                    for r in jenis_hak]
        hapus_tanya = ("Formulir ini sudah dipakai pradaftar, jadi hanya dinonaktifkan. "
                       "Lanjutkan?" if d["jml_pradaftar"] else
                       "Hapus formulir ini berikut seluruh butirnya?")
        atur = f"""<details class="kartu susun-atur"><summary><h2>Pengaturan formulir</h2></summary>
<div class="badan"><form method="post" action="/referensi/kelengkapan/{fid}" class="grid">
{bidang("Kode", "kode", d["kode"], wajib=True, petunjuk="unik, mis. 184-HM")}
{bidang("Judul", "judul", d["judul"], wajib=True)}
{kotak("Jenis hak", "jenis_hak", hak_pilihan, d["jenis_hak"],
       petunjuk="dipakai pradaftar dengan jenis hak ini")}
{kotak("Kegiatan", "kegiatan", kegiatan, d["kegiatan"])}
{bidang("Dasar / lampiran", "dasar", d["dasar"] or "")}
<label class="centang-sebaris"><input type="checkbox" name="aktif" value="1"
  {" checked" if d["aktif"] else ""}> Dipakai di loket</label>
<label class="centang-sebaris"><input type="checkbox" name="nomor_otomatis" value="1"
  {" checked" if otomatis else ""}> Nomor &amp; huruf disusun otomatis</label>
<div class="aksi-baris"><button class="btn utama kecil">Simpan pengaturan</button>
<button class="btn kecil bahaya" formaction="/referensi/kelengkapan/{fid}/hapus"
  formnovalidate data-konfirmasi="{e(hapus_tanya)}">Hapus formulir</button></div>
</form></div></details>"""
        samping = f'<aside class="fokus-samping susun-samping">{tambah}{atur}</aside>'

    saran = ('<datalist id="saran-butir">'
             + "".join(f'<option value="{e(x)}">' for x in SARAN_BUTIR) + "</datalist>")
    isi = f"""{kepala}
{saran}
<div class="fokus-grid{"" if boleh_ubah else " tunggal"}">
  <div class="fokus-utama">
    <section class="kartu"><h2>Susunan butir</h2><div class="badan">
      {petunjuk}
      <ol class="susun" data-susun="/referensi/kelengkapan/{fid}/butir/">{baris}</ol>
      {kosong}
    </div></section>
    {riwayat}
  </div>
  {samping}
</div>"""
    return layout(f"Susun · {d['judul']}", isi, pengguna, "/referensi", pesan, fokus=True)


def halaman_formulir_baru(pengguna, formulir, jenis_hak, pesan=None):
    hak_pilihan = [("*", "Semua jenis hak")] + [(r["kode"], f'{r["kode"]} — {r["nama"]}')
                                                for r in jenis_hak]
    salin = [(f["id"], f'{f["kode"]} — {f["judul"]} ({f["jml_butir"]} butir)')
             for f in formulir]
    isi = f"""<div class="fokus-atas">
  <a class="btn" href="/referensi#r-lengkap">&larr; Data referensi</a>
  <div class="fokus-judul"><h1>Formulir kelengkapan baru</h1>
    <p>Untuk jenis permohonan yang belum punya daftar kelengkapan sendiri</p></div>
</div>
<div class="kartu" style="max-width:46rem"><div class="badan">
<form method="post" action="/referensi/kelengkapan/baru" class="grid">
<div class="grid g2">
  {kotak("Jenis hak", "jenis_hak", hak_pilihan, "*",
         petunjuk="pradaftar dengan jenis hak ini memakai formulir ini")}
  {kotak("Kegiatan", "kegiatan", SUSUN.KEGIATAN, "*")}
</div>
<div class="grid g2">
  {bidang("Kode", "kode", "", wajib=True, petunjuk="unik, mis. HGB-BARU")}
  {bidang("Dasar / lampiran", "dasar", "", petunjuk="mis. Lampiran Permen ATR/BPN 18/2021")}
</div>
{bidang("Judul formulir", "judul", "Daftar Kelengkapan Persyaratan Permohonan ", wajib=True,
        petunjuk="tercetak di kepala formulir")}
{kotak("Mulai dari", "salin_dari", salin, "", "— formulir kosong —",
       petunjuk="salin seluruh butir formulir yang sudah ada, lalu sesuaikan")}
<input type="hidden" name="aktif" value="1">
<input type="hidden" name="nomor_otomatis" value="1">
<div class="aksi-baris"><button class="btn utama">Buat formulir</button></div>
</form></div></div>"""
    return layout("Formulir kelengkapan baru", isi, pengguna, "/referensi", pesan, fokus=True)


# ---------------------------------------------------------------- referensi
# Halaman referensi dirakit sebagai kartu yang bisa dibuka-tutup. Yang ikut
# terkirim saat halaman dibuka hanyalah kepala kartunya (judul + ringkasan);
# isi tabelnya baru diambil app.js dari /referensi/bagian/<kunci> ketika kartu
# itu dibuka, jadi satu halaman tidak pernah memuat seluruh data sekaligus.
# Tanpa JavaScript kepala kartu tetap tautan biasa (?buka=<kunci>) yang dijawab
# server dengan kartu tersebut sudah terbuka.

def _lipat(kunci, judul, ringkas, isi=None, cap="", terbuka=False, cari="",
           dasar="/referensi", kelas=""):
    """Satu kartu lipat. isi=None berarti isinya diambil belakangan dari
    <dasar>/bagian/<kunci>; kepalanya menaut ke <dasar>?buka=<kunci> sebagai
    jalan keluar bila JavaScript mati."""
    ident, sarang = f"b-{kunci}", f"i-{kunci}"
    muat = "" if isi is not None else f' data-muat="{dasar}/bagian/{e(kunci)}"'
    tanda = f' data-cari="{e(cari.lower())}"' if cari else ""
    kelas = f" {kelas}" if kelas else ""
    return f"""<section class="kartu lipat{kelas}{' terbuka' if terbuka else ''}" id="{ident}"{tanda}>
<h2 class="lipat-h"><a class="lipat-kepala" href="{dasar}?buka={e(kunci)}#{ident}"
   aria-controls="{sarang}" aria-expanded="{'true' if terbuka else 'false'}"{muat}>
  <span class="lipat-panah" aria-hidden="true"></span>
  <span class="lipat-teks"><span class="lipat-judul">{judul}</span>
    <span class="lipat-ringkas">{ringkas}</span></span>
  <span class="lipat-cap">{cap}</span>
  <span class="lipat-isyarat" aria-hidden="true"></span>
</a></h2>
<div class="lipat-isi" id="{sarang}"{'' if terbuka else ' hidden'}>{isi or ''}</div>
</section>"""


def _saring(target, petunjuk, jumlah, satuan):
    """Kotak cari yang menyaring baris di dalam satu kartu, di sisi klien saja."""
    return (f'<div class="saring-lipat"><input type="search" data-saring="{e(target)}"'
            f' placeholder="{e(petunjuk)}" aria-label="{e(petunjuk)}">'
            f'<span class="petunjuk" data-jumlah="{e(satuan)}">{jumlah} {e(satuan)}</span></div>')


def _kartu_tetap(kunci, judul, ringkas, isi):
    """Kartu yang selalu terbuka, untuk tab yang isinya cuma satu bagian —
    membuka tab lalu masih harus membuka kartunya hanya menambah satu klik."""
    return f"""<section class="kartu" id="b-{e(kunci)}">
<h2><span class="lipat-teks"><span class="lipat-judul">{judul}</span>
  <span class="lipat-ringkas">{ringkas}</span></span></h2>
{isi}
</section>"""


def _kunci(isi, boleh_ubah):
    """Matikan isian bila tak boleh mengubah; bagian di luarnya (cari, saring) tetap hidup."""
    return isi if boleh_ubah else _baca_saja(isi)


def _baca_saja(isi):
    """Matikan seluruh isian dan tombol di dalam satu potongan sekaligus.
    <a> tidak ikut mati, jadi kepala kartu lipat tetap bisa diklik."""
    return f'<fieldset disabled class="baca-saja">{isi or ""}</fieldset>'


def halaman_referensi(pengguna, ringkas, terbuka=None, pesan=None, boleh_ubah=True):
    """ringkas = angka tiap bagian + kepala tiap SK panitia.
    terbuka = {kunci: potongan HTML} untuk bagian yang diminta lewat ?buka=.

    boleh_ubah=False (petugas) tetap menampilkan seluruh isinya — nama kepala
    desa dan susunan panitia memang perlu dicek saat mengisi berkas — tetapi
    tiap formulirnya dimatikan dan kartu "tambah" disembunyikan.
    """
    # Potongan dari bagian_referensi() sudah dimatikan sendiri bila perlu.
    t = terbuka or {}
    r = ringkas
    ada = lambda kunci: kunci in t
    kurang = r["desa_kosong"]

    # Tab Jenis hak dan Klausa hanya berisi satu bagian yang kecil; kalau
    # isinya sudah dirakit server, tampilkan langsung tanpa kartu lipat.
    def _satu(kunci, judul, ringkas):
        if ada(kunci):
            return _kartu_tetap(kunci, judul, ringkas, t[kunci])
        return _lipat(kunci, judul, ringkas)

    bagian = [
        _satu("jenis_hak", "Matriks jenis hak",
              f'{r["jenis_hak"]} jenis hak aktif · jangka waktu, subjek yang boleh, '
              f'kegiatan, dan dasar hukumnya'),
        _satu("klausa", "Pustaka blok klausa",
              f'{r["klausa"]} blok kalimat baku yang disisipkan ke dokumen · '
              f'<code>{{{{isian}}}}</code> diganti data berkas saat dicetak'),
    ]

    sk = "".join(
        _lipat_panitia(p, t.get(f'panitia-{p["id"]}'), ada(f'panitia-{p["id"]}'))
        for p in r["panitia"])
    if not sk:
        sk = ('<div class="kartu"><div class="kosong"><b>Belum ada SK panitia</b>'
              '<span>Tambahkan SK penunjukan Panitia A lewat kartu di bawah.</span></div></div>')
    cari_sk = (_saring("daftar-sk", "Cari nomor SK, tahun, atau keterangan…",
                       len(r["panitia"]), "SK") if len(r["panitia"]) > 4 else "")

    cap_desa = (f'<span class="cap kuning">{kurang} belum ada pejabat</span>' if kurang
                else '<span class="cap hijau">pejabat lengkap</span>')
    if r.get("desa_pj"):
        cap_desa += f'<span class="cap aksen">{r["desa_pj"]} dijabat Pj./Plt.</span>'
    desa = _lipat("desa", "Desa dan kelurahan",
                  f'{r["desa"]} desa/kelurahan di {r["kecamatan"]} kecamatan'
                  + (f' · {kurang} belum ada nama pejabat' if kurang else ''),
                  t.get("desa"), cap=cap_desa, terbuka=ada("desa"))
    kecamatan = _lipat("kecamatan", "Kecamatan",
                       f'{r["kecamatan"]} kecamatan terdaftar · induk daftar desa di bawahnya',
                       t.get("kecamatan"), terbuka=ada("kecamatan"))
    kurang_kec = len(r["kurang"]["kecamatan"])
    kurang_desa = len(r["kurang"]["desa"])
    kemendagri = _lipat(
        "kemendagri", f"Daftar induk Kemendagri {wilayah.KODE_KABUPATEN}",
        (f'{kurang_kec} kecamatan dan {kurang_desa} desa/kelurahan belum terdaftar'
         if kurang_kec or kurang_desa else
         'Semua kecamatan dan desa menurut Kemendagri sudah terdaftar'),
        t.get("kemendagri"),
        cap=(f'<span class="cap kuning">{kurang_kec + kurang_desa} belum ada</span>'
             if kurang_kec or kurang_desa else '<span class="cap hijau">selaras</span>'),
        terbuka=ada("kemendagri"))

    kelengkapan = "".join(
        _lipat_kelengkapan(f, t.get(f'kelengkapan-{f["id"]}'), ada(f'kelengkapan-{f["id"]}'))
        for f in r.get("kelengkapan", []))
    if not kelengkapan:
        kelengkapan = ('<div class="kartu"><div class="kosong">'
                       '<b>Belum ada daftar kelengkapan</b><span>Jalankan '
                       '<code>python -m berkas.db</code> untuk memasangnya.</span>'
                       '</div></div>')
    kelengkapan += _lipat(
        "catatan_koreksi", "Catatan koreksi baku",
        "Pilihan catatan untuk butir yang ada tetapi perlu diperbaiki pemohon",
        t.get("catatan_koreksi"),
        cap=f'<span class="cap abu">{r.get("catatan_koreksi", 0)} aktif</span>',
        terbuka=ada("catatan_koreksi"))

    kartu_panitia_baru = (
        _lipat("panitia_baru", "+ Tambah SK susunan panitia",
               "Nomor dan masa berlaku SK baru; anggotanya diisi setelah tersimpan",
               _isi_panitia_baru(), terbuka=ada("panitia_baru"),
               kelas="tambah") if boleh_ubah else "")
    catatan_peran = "" if boleh_ubah else (
        '<div class="pesan">Halaman ini <b>hanya bisa dilihat</b>. Perubahan data '
        'referensi dilakukan admin, supaya dokumen yang sudah terbit tetap cocok '
        'dengan acuannya.</div>')
    # Empat tab menurut urusannya. Di dalam tab Wilayah dan Panitia A isinya
    # tetap kartu lipat: jumlah SK panitia bertambah terus, jadi tidak mungkin
    # dijadikan tab sendiri-sendiri.
    # Lencana tab: jumlah isinya, dan kuning bila ada yang perlu dilengkapi —
    # supaya kekurangan di tab Wilayah kelihatan tanpa harus membukanya.
    lencana = lambda n, warna="": f' <span class="lencana {warna}">{n}</span>'
    kurang_wil = kurang + kurang_kec + kurang_desa
    isi = f"""{catatan_peran}<div class="judul"><div><h1>Data referensi</h1>
<p>Yang berulang disimpan sekali di sini, bukan diketik ulang di tiap dokumen.</p></div></div>
{_tab("referensi", [
    ("r-hak", "Jenis hak", lencana(r["jenis_hak"])),
    ("r-klausa", "Klausa", lencana(r["klausa"])),
    ("r-lengkap", "Kelengkapan", lencana(len(r.get("kelengkapan", [])))),
    ("r-wilayah", "Wilayah",
     lencana(kurang_wil, "kuning") if kurang_wil else lencana(r["desa"])),
    ("r-panitia", "Panitia A", lencana(len(r["panitia"])))])}

<datalist id="peran-panitia">{"".join(f'<option value="{e(x)}">' for x in PERAN_PANITIA)}</datalist>

<div class="panel" id="r-hak">
<p class="pengantar">Hak yang bisa dimohonkan beserta batasannya. Pilihan jenis hak dan
kegiatan pada berkas diperiksa terhadap matriks ini.</p>
{bagian[0]}</div>
<div class="panel" id="r-klausa">
<p class="pengantar">Kalimat baku yang dipilih otomatis menurut jenis hak, kegiatan, dan
subjek berkas, lalu disisipkan ke slot yang sama namanya di template.</p>
{bagian[1]}</div>

<div class="panel" id="r-lengkap">
<div class="pengantar-aksi"><p class="pengantar">Daftar kelengkapan persyaratan yang
dipakai menu <b>Pradaftar</b> saat memeriksa berkas di loket. Satu formulir per jenis
permohonan; yang berlaku untuk sebuah pradaftar dipilih menurut jenis haknya.</p>
{'<a class="btn" href="/referensi/kelengkapan/baru">+ Formulir baru</a>' if boleh_ubah else ''}</div>
{kelengkapan}
</div>

<div class="panel" id="r-wilayah">
<p class="pengantar">Letak tanah pada berkas menunjuk ke daftar ini, dan kepala desa/lurah
yang sedang menjabat ikut tercetak sebagai anggota Panitia A. Kepala desa yang diganti tidak
ditimpa — yang lama tetap tersimpan sebagai riwayat supaya berkas lama masih bisa
ditelusuri.</p>
{kemendagri}
{kecamatan}
{desa}
</div>

<div class="panel" id="r-panitia">
<p class="pengantar" id="panitia">Diambil dari SK Kepala Kantor tentang penunjukan Panitia
Pemeriksaan Tanah A. Setiap kali susunannya berganti, tambah SK baru — jangan menimpa yang
lama, supaya berkas lama tetap merujuk susunan yang benar saat itu. Kepala desa/lurah letak
tanah ditambahkan otomatis sebagai anggota (Pasal 138 ayat (1) huruf c), jadi tidak perlu
didaftarkan di sini.</p>
{cari_sk}
<div id="daftar-sk">{sk}</div>
<div class="tak-cocok" hidden>Tidak ada SK yang cocok.</div>
{kartu_panitia_baru}
</div>"""
    return layout("Data referensi", isi, pengguna, "/referensi", pesan)


# --------------------------------------------------------- potongan bagian
def _isi_kelengkapan(d):
    """Satu formulir kelengkapan: sunting cepat bunyi butir dan wajibnya.

    Menambah butir, mengubah urutan, dan memindah butir ke kelompok lain
    dikerjakan di halaman Susun formulir (/referensi/kelengkapan/<id>) —
    kartu ini cuma pintu masuknya.
    """
    baris = []
    for n in d["butir"]:
        jorok = "padding-left:%.1frem" % (min(n["tingkat"], 3) * 1.1)
        sifat = {"judul": '<span class="cap abu">kepala</span>',
                 "alternatif": '<span class="cap aksen">salah satu</span>'}.get(
                     n["sifat"], "")
        syarat = []
        if n["subjek"] != "*":
            syarat.append(n["subjek"].replace("_", " "))
        if n["asal_tanah"] != "*":
            syarat.append(n["asal_tanah"])
        if n["isian_bebas"]:
            syarat.append("isian bebas")
        if n["slot_baku"]:
            syarat.append("→ " + n["slot_baku"])
        dasar = f'<div class="petunjuk">{e(n["dasar"])}</div>' if n["dasar"] else ""
        centang = " checked" if n["wajib"] else ""
        baris.append(
            f'<tr><td class="nomor">{e(n["penanda"])}</td>'
            f'<td style="{jorok}">'
            f'<input type="text" name="nama_{n["id"]}" value="{e(n["nama"])}">{dasar}</td>'
            f'<td>{sifat}<div class="petunjuk">{e(" · ".join(syarat))}</div></td>'
            f'<td><label class="centang-sebaris"><input type="checkbox" '
            f'name="wajib_{n["id"]}" value="1"{centang}> wajib</label></td></tr>')

    return f"""<div class="badan">
<div class="susun-pintu">
  <div><b>Tambah butir, ubah urutan, atau pindahkan ke kelompok lain</b>
  <span class="petunjuk">mis. Peta Analisis Tata Ruang, atau urutan yang mengikuti map
  berkas di loket</span></div>
  <a class="btn utama" href="/referensi/kelengkapan/{d["id"]}">Susun formulir &rarr;</a>
</div>
<p class="petunjuk" style="margin-bottom:.8rem">Sunting cepat: bunyi butir dan
wajib-tidaknya. Butir yang <b>tidak wajib</b> tetap tercetak dan tetap bisa dicentang,
hanya tidak menahan penerimaan berkas di loket.</p>
<form method="post" action="/referensi/kelengkapan">
<input type="hidden" name="id" value="{d["id"]}">
<div class="tabel-bungkus"><table class="tabel-isian"><thead><tr>
  <th style="width:3rem">No.</th><th>Bunyi butir</th><th style="width:11rem">Sifat</th>
  <th style="width:7rem">Kelengkapan</th>
</tr></thead><tbody>{"".join(baris)}</tbody></table></div>
<div class="aksi-baris lengket-bawah"><button class="btn utama">Simpan formulir</button>
<span class="petunjuk">Berlaku untuk pradaftar yang dibuka setelah ini; centangan
yang sudah tersimpan tidak berubah.</span></div>
</form></div>"""


def _lipat_kelengkapan(f, isi=None, terbuka=False):
    ringkas = " · ".join(x for x in (
        e(f["dasar"] or ""), f'{f["jml_butir"]} butir',
        f'jenis hak {e(f["jenis_hak"])}' if f["jenis_hak"] != "*" else "semua jenis hak",
    ) if x)
    cap = ('<span class="cap hijau">dipakai</span>' if f["aktif"]
           else '<span class="cap abu">nonaktif</span>')
    return _lipat(f'kelengkapan-{f["id"]}', e(f["judul"]), ringkas, isi, cap, terbuka,
                  cari=f'{f["kode"]} {f["judul"]} {f["jenis_hak"]}')


def bagian_referensi(kunci, data, boleh_ubah=True):
    """Potongan HTML satu bagian. Dipakai halaman /referensi maupun permintaan
    terpisah ke /referensi/bagian/<kunci> saat kartunya dibuka."""
    if data is None:
        return ""
    # Dua tabel ini tanpa isian sama sekali — tak perlu dimatikan, dan tombol
    # "Selengkapnya" di klausa harus tetap bisa ditekan petugas.
    if kunci == "jenis_hak":
        return _tabel_jenis_hak(data)
    if kunci == "klausa":
        return _tabel_klausa(data)
    # Desa dan kecamatan mematikan isiannya sendiri, supaya kotak cari dan
    # saringannya tetap bisa dipakai petugas.
    if kunci == "desa":
        return _tabel_desa(data, boleh_ubah)
    if kunci == "kecamatan":
        return _tabel_kecamatan(data, boleh_ubah)
    if kunci == "catatan_koreksi":
        return _tabel_catatan_koreksi(data, boleh_ubah)
    if not boleh_ubah:
        return _baca_saja(bagian_referensi(kunci, data))
    if kunci == "kemendagri":
        return _isi_kemendagri(data)
    if kunci.startswith("panitia-"):
        return _isi_panitia(data)
    if kunci.startswith("kelengkapan-"):
        return _isi_kelengkapan(data)
    return ""


def _daftar_cap(teks, warna="abu"):
    """'perorangan,badan_hukum' -> deretan label kecil. '*' berarti semua."""
    teks = (teks or "").strip()
    if not teks or teks == "*":
        return '<span class="petunjuk semua">semua</span>'
    return '<span class="chip">' + "".join(
        f'<span class="cap {warna} tanpa-titik">{e(x.strip().replace("_", " "))}</span>'
        for x in teks.split(",") if x.strip()) + "</span>"


def _tabel_jenis_hak(baris):
    def jangka(r):
        if not r["ada_jangka_waktu"]:
            return '<span class="petunjuk semua">tidak berjangka</span>'
        lanjut = (f'<div class="petunjuk">perpanjangan {r["perpanjangan_maks"]}&nbsp;th</div>'
                  if r["perpanjangan_maks"] else "")
        return f'paling lama <b>{r["jangka_maks"]}&nbsp;th</b>{lanjut}'
    tr = "".join(
        f'<tr><td><span class="cap aksen tanpa-titik kode">{e(r["kode"])}</span></td>'
        f'<td><b>{e(r["nama"])}</b></td><td>{jangka(r)}</td>'
        f'<td>{_daftar_cap(r["subjek_boleh"])}</td>'
        f'<td>{_daftar_cap(r["kegiatan_boleh"])}</td>'
        f'<td class="petunjuk">{e(r["dasar_subjek"])}</td></tr>' for r in baris)
    return f"""<div class="badan rapat"><div class="tabel-bungkus">
<table class="tabel-ref"><thead><tr><th>Kode</th><th>Nama</th><th>Jangka waktu</th>
<th>Subjek yang boleh</th><th>Kegiatan</th><th>Dasar</th></tr></thead>
<tbody>{tr}</tbody></table></div></div>"""


def _isi_klausa(teks):
    """Isi klausa utuh, dengan {{isian}} ditandai supaya kelihatan mana yang
    diganti data berkas. Yang panjang dipotong tiga baris dan bisa dibentangkan."""
    tanda = re.sub(r"\{\{\s*([\w.]+)\s*\}\}", r'<code class="isian">\1</code>', e(teks))
    if len(teks) <= 180:
        return f'<div class="klausa-isi">{tanda}</div>'
    return (f'<div class="klausa-isi potong">{tanda}</div>'
            '<button type="button" class="btn hantu kecil" data-bentang>Selengkapnya</button>')


def _tabel_klausa(baris):
    tr = "".join(
        f'<tr><td class="nomor">{e(r["slot"])}</td>'
        f'<td>{_daftar_cap(r["jenis_hak"], "aksen")}</td>'
        f'<td>{_daftar_cap(r["kegiatan"])}</td><td>{_daftar_cap(r["subjek"])}</td>'
        f'<td>{_isi_klausa(r["isi"])}</td></tr>' for r in baris)
    return f"""<div class="badan rapat"><div class="tabel-bungkus">
<table class="tabel-ref"><thead><tr><th>Slot</th><th>Jenis hak</th><th>Kegiatan</th>
<th>Subjek</th><th style="min-width:22rem">Isi</th></tr></thead>
<tbody>{tr}</tbody></table></div></div>"""


ASAL_DESA = "/referensi?buka=desa#b-desa"
ASAL_KECAMATAN = "/referensi?buka=kecamatan#b-kecamatan"


def _cap_jabatan(jabatan):
    """Jabatan sementara (Pj./Plt./Pjs.) ditandai supaya kelihatan sekilas."""
    j = (jabatan or "").strip()
    warna = "abu" if j in ("Kepala Desa", "Lurah") else "kuning"
    return f'<span class="cap {warna}">{e(j)}</span>'


def _pilih_pejabat(r):
    """Sel "yang menjabat sekarang" pada satu baris desa.

    Kalau riwayatnya sudah ada, yang ditawarkan adalah memilih salah satunya —
    itulah kejadian yang sering: kepala desa diganti Pj., lalu Pj. diganti kepala
    desa baru. Kalau belum ada satu pun, sel ini jadi isian nama supaya
    pendataan awal tetap secepat dulu.
    """
    desa = f'{r["jenis"]} {r["nama"]}'
    kepala = (f'<input type="hidden" name="desa_id" value="{r["id"]}">'
              f'<input type="hidden" name="asal" value="{e(ASAL_DESA)}">')
    if not r["pejabat"]:
        return (f'<form method="post" action="/referensi/desa/pejabat" class="simpan-baris">'
                f'{kepala}<input type="hidden" name="jenis" value="{e(r["jenis"])}">'
                f'<input name="nama" placeholder="nama {e(r["jabatan_pejabat"].lower())}"'
                f' aria-label="Nama pejabat {e(desa)}" required>'
                f'<button class="btn kecil">Simpan</button></form>')
    opsi = ['<option value="">— sedang kosong —</option>']
    for p in r["pejabat"]:
        s = " selected" if p["aktif"] else ""
        opsi.append(f'<option value="{p["id"]}"{s}>{e(p["jabatan"])} · {e(p["nama"])}</option>')
    return (f'<form method="post" action="/referensi/desa/pejabat/aktif" class="simpan-baris">'
            f'{kepala}<select name="pejabat_id" aria-label="Pejabat {e(desa)} yang menjabat">'
            f'{"".join(opsi)}</select>'
            f'<button class="btn kecil">Simpan</button></form>')


def _tabel_desa(data, boleh_ubah=True):
    baris, kecamatan = data["baris"], data["kecamatan"]
    tr = []
    hitung = {"kosong": 0, "pj": 0, "definitif": 0}
    for r in baris:
        desa = f'{r["jenis"]} {r["nama"]}'
        riwayat = len(r["pejabat"])
        cari = " ".join([r["kecamatan"], desa, r["nama_pejabat"] or "",
                         r["jabatan_pejabat"] or ""]
                        + [p["nama"] for p in r["pejabat"]])
        if r["nama_pejabat"]:
            jabatan = _cap_jabatan(r["jabatan_pejabat"])
            status = ("definitif" if r["jabatan_pejabat"] in ("Kepala Desa", "Lurah")
                      else "pj")
        else:
            jabatan = '<span class="cap kuning">belum diisi</span>'
            status = "kosong"
        hitung[status] += 1
        tr.append(
            f'<tr data-cari="{e(cari.lower())}" data-status="{status}">'
            f'<td class="redup">{e(r["kecamatan"])}</td>'
            f'<td><b>{e(desa)}</b></td><td>{jabatan}</td>'
            f'<td>{_pilih_pejabat(r)}</td>'
            f'<td class="nomor">{riwayat or "—"}</td>'
            f'<td><a class="btn kecil" href="/referensi/desa/{r["id"]}">Kelola</a></td></tr>')
    # Saringan keadaan: pendataan awal biasanya berarti mengisi yang kosong
    # satu per satu, jadi yang belum ada pejabatnya perlu bisa dipisahkan.
    tapis = "".join(
        f'<button type="button" data-status="{k}" aria-pressed="{"false" if k else "true"}"'
        f' class="{"" if k else "aktif"}">{label}'
        f' <span class="lencana {warna}">{n}</span></button>'
        for k, label, n, warna in (
            ("", "Semua", len(baris), ""),
            ("kosong", "Belum ada pejabat", hitung["kosong"], "kuning"),
            ("pj", "Pj./Plt.", hitung["pj"], ""),
            ("definitif", "Definitif", hitung["definitif"], "hijau"))
        if n or not k)
    tabel = f"""<div class="tabel-bungkus" id="tabel-desa"><table class="tabel-isian"><thead><tr>
<th>Kecamatan</th><th>Desa/Kelurahan</th><th>Jabatan</th><th>Yang menjabat sekarang</th>
<th>Riwayat</th><th></th></tr></thead>
<tbody>{"".join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada desa yang cocok.</div>"""
    return f"""<div class="badan rapat">
{_saring("tabel-desa", "Cari kecamatan, desa, atau nama pejabat…", len(baris), "desa")}
<div class="tapis-lipat" data-tapis="tabel-desa" role="group"
     aria-label="Saring menurut pejabat">{tapis}</div>
{_kunci(tabel, boleh_ubah)}
{_tambah_desa(kecamatan) if boleh_ubah else ""}</div>"""


def _tambah_desa(kecamatan):
    if not kecamatan:
        return ('<div class="badan"><p class="petunjuk">Daftarkan kecamatannya dulu — '
                'desa selalu menempel pada satu kecamatan.</p></div>')
    return f"""<div class="badan" style="border-top:1px solid var(--garis)">
<h3 class="sub">Tambah desa / kelurahan</h3>
<form method="post" action="/referensi/desa"><div class="grid g4">
  <div><label>Kecamatan <span class="wajib">*</span></label>
    {pilih("kecamatan_id", kecamatan, "", "- pilih kecamatan -", "required")}</div>
  {_isian("Nama", "nama", atribut="required placeholder='tanpa kata Desa/Kelurahan'")}
  <div><label>Jenis</label>
    {pilih("jenis", [(x, x) for x in wilayah.JENIS_DESA], "Desa")}</div>
  {_isian("Kode wilayah", "kode",
          petunjuk="kode Kemendagri, mis. 75.03.02.2001 — boleh dikosongkan")}
</div>
<div class="aksi-baris"><button class="btn utama">Tambah desa</button>
<span class="petunjuk">Kepala desanya diisi setelah tersimpan, lewat tombol Kelola.</span>
</div></form></div>"""


def _tabel_kecamatan(baris, boleh_ubah=True):
    tr = []
    for r in baris:
        tr.append(
            f'<tr data-cari="{e((r["nama"] + " " + (r["kode"] or "")).lower())}">'
            f'<td class="nomor">{e(r["kode"] or "—")}</td>'
            f'<td><form method="post" action="/referensi/kecamatan" class="simpan-baris">'
            f'<input type="hidden" name="id" value="{r["id"]}">'
            f'<input type="hidden" name="asal" value="{e(ASAL_KECAMATAN)}">'
            f'<input name="nama" value="{e(r["nama"])}" required'
            f' aria-label="Nama kecamatan {e(r["nama"])}">'
            f'<input name="kode" value="{e(r["kode"])}" placeholder="kode"'
            f' style="max-width:8rem" aria-label="Kode wilayah {e(r["nama"])}">'
            f'<button class="btn kecil">Simpan</button>'
            f'<button class="btn kecil bahaya" formaction="/referensi/kecamatan/hapus"'
            f' formnovalidate data-konfirmasi="Hapus kecamatan {e(r["nama"])}?">Hapus</button>'
            f'</form></td>'
            f'<td class="nomor">{r["jml_desa"]}</td></tr>')
    tabel = f"""<div class="tabel-bungkus" id="tabel-kecamatan"><table class="tabel-isian"><thead>
<tr><th>Kode</th><th>Nama kecamatan</th><th>Desa</th></tr></thead>
<tbody>{"".join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada kecamatan yang cocok.</div>"""
    return f"""<div class="badan rapat">
{_saring("tabel-kecamatan", "Cari nama atau kode kecamatan…", len(baris), "kecamatan")}
{_kunci(tabel, boleh_ubah)}
{_tambah_kecamatan() if boleh_ubah else ""}</div>"""


def _pilih_butir(butir, terpilih, label=""):
    """Pilihan butir tujuan sebuah catatan koreksi; kosong = semua butir."""
    opsi = [f'<option value=""{"" if terpilih else " selected"}>Semua butir</option>']
    opsi += [f'<option value="{bid}"{" selected" if bid == terpilih else ""}>{e(teks)}</option>'
             for bid, teks in butir]
    return (f'<select name="butir_id" aria-label="{e(label or "Berlaku untuk butir")}">'
            f'{"".join(opsi)}</select>')


def _tabel_catatan_koreksi(data, boleh_ubah=True):
    """Daftar catatan koreksi baku: satu formulir kecil per baris, seperti kecamatan.

    Menghapus atau menyunting di sini tidak menyentuh pemeriksaan yang sudah
    tersimpan — yang disimpan pada pradaftar adalah teks catatannya.
    """
    tr = []
    for r in data["baris"]:
        centang = " checked" if r["aktif"] else ""
        tr.append(
            f'<tr data-cari="{e(r["teks"].lower())}"><td>'
            f'<form method="post" action="/referensi/catatan-koreksi" class="simpan-baris">'
            f'<input type="hidden" name="id" value="{r["id"]}">'
            f'<input name="teks" value="{e(r["teks"])}" required maxlength="300"'
            f' aria-label="Bunyi catatan">'
            f'{_pilih_butir(data["butir"], r["butir_id"])}'
            f'<label class="centang-sebaris"><input type="checkbox" name="aktif" value="1"'
            f'{centang}> aktif</label>'
            f'<button class="btn kecil">Simpan</button>'
            f'<button class="btn kecil bahaya" formaction="/referensi/catatan-koreksi/hapus"'
            f' formnovalidate data-konfirmasi="Hapus catatan ini dari daftar?">Hapus</button>'
            f'</form></td></tr>')
    tabel = (f'<div class="tabel-bungkus" id="tabel-catatan-koreksi">'
             f'<table class="tabel-isian"><thead><tr><th>Catatan · berlaku untuk</th>'
             f'</tr></thead><tbody>{"".join(tr)}</tbody></table></div>'
             f'<div class="tak-cocok" hidden>Tidak ada catatan yang cocok.</div>'
             if tr else
             '<div class="kosong"><b>Belum ada catatan baku</b>'
             '<span>Petugas tetap bisa mengetik catatannya sendiri.</span></div>')
    tambah = f"""<div class="badan" style="border-top:1px solid var(--garis)">
<h3 class="sub">Tambah catatan</h3>
<form method="post" action="/referensi/catatan-koreksi"><div class="grid g2">
  {_isian("Bunyi catatan", "teks", atribut='required maxlength="300"',
          petunjuk="mis. SPPT PBB bukan tahun berjalan")}
  <div><label>Berlaku untuk</label>{_pilih_butir(data["butir"], None)}
    <div class="petunjuk">catatan khusus satu butir hanya ditawarkan pada butir itu</div></div>
</div>
<input type="hidden" name="aktif" value="1">
<div class="aksi-baris"><button class="btn utama">Tambah catatan</button></div>
</form></div>""" if boleh_ubah else ""
    return f"""<div class="badan rapat">
<p class="petunjuk">Pilihan cepat untuk kotak catatan pada butir yang <b>perlu
koreksi</b>. Petugas tetap boleh mengetik catatan sendiri. Yang nonaktif tidak
ditawarkan lagi, tetapi catatan yang sudah tersimpan pada pradaftar tidak berubah.</p>
{_saring("tabel-catatan-koreksi", "Cari bunyi catatan…", len(data["baris"]), "catatan")
 if tr else ""}
{_kunci(tabel, boleh_ubah)}
{tambah}</div>"""


def _tambah_kecamatan():
    return f"""<div class="badan" style="border-top:1px solid var(--garis)">
<h3 class="sub">Tambah kecamatan</h3>
<form method="post" action="/referensi/kecamatan"><div class="grid g2">
  {_isian("Nama kecamatan", "nama", atribut="required")}
  {_isian("Kode wilayah", "kode", petunjuk="kode Kemendagri, mis. 75.03.02")}
</div>
<input type="hidden" name="asal" value="{e(ASAL_KECAMATAN)}">
<div class="aksi-baris"><button class="btn utama">Tambah kecamatan</button></div>
</form></div>"""


def _isi_kemendagri(kurang):
    """Selisih daftar induk Kemendagri terhadap isi basis data, plus tombol memuatnya."""
    kec, desa = kurang["kecamatan"], kurang["desa"]
    if not (kec or desa):
        return f"""<div class="badan"><div class="kosong">
<b>Sudah selaras</b>
<span>Seluruh {len(wilayah.WILAYAH)} kecamatan dan desa/kelurahan {e(wilayah.NAMA_KABUPATEN)}
menurut daftar Kemendagri sudah ada di basis data.</span></div></div>"""
    daftar_kec = ", ".join(e(x) for x in kec)
    per_kec = {}
    for nama_kec, nama, jenis in desa:
        per_kec.setdefault(nama_kec, []).append(f"{jenis} {nama}")
    li = "".join(
        f'<li><span class="ikon">·</span><span><b>{e(nama_kec)}</b>'
        f'<div class="petunjuk">{e(", ".join(isi))}</div></span></li>'
        for nama_kec, isi in per_kec.items())
    return f"""<div class="badan">
<p>Daftar induk {e(wilayah.NAMA_KABUPATEN)} ({e(wilayah.KODE_KABUPATEN)}) berisi
{len(wilayah.WILAYAH)} kecamatan dan
{sum(len(x[2]) for x in wilayah.daftar_baku())} desa/kelurahan.
Yang belum ada di basis data: <b>{len(kec)} kecamatan</b> dan
<b>{len(desa)} desa/kelurahan</b>.</p>
{f'<p class="petunjuk">Kecamatan: {daftar_kec}</p>' if kec else ''}
<form method="post" action="/referensi/wilayah"><div class="aksi-baris" style="margin-top:0">
<button class="btn utama" data-konfirmasi="Tambahkan {len(kec)} kecamatan dan {len(desa)} desa/kelurahan yang belum ada?"
  >Tambahkan yang belum ada</button>
<span class="petunjuk">Hanya menambah. Nama, jenis, dan pejabat yang sudah tersimpan
tidak diubah, dan tidak ada baris yang dihapus.</span></div></form>
<h3 class="sub">Rincian yang akan ditambahkan</h3>
<ul class="daftar-periksa">{li}</ul></div>"""


# --------------------------------------------------- satu desa / kelurahan
def halaman_desa(pengguna, d, kecamatan, pesan=None):
    """Halaman satu desa: identitasnya, siapa yang menjabat, dan riwayatnya."""
    aktif = next((p for p in d["pejabat"] if p["aktif"]), None)
    nama = f'{d["jenis"]} {d["nama"]}'
    jabatan = wilayah.jabatan_untuk(d["jenis"])
    keterangan = (f'{_cap_jabatan(aktif["jabatan"])} {e(aktif["nama"])}' if aktif else
                  '<span class="cap kuning">belum ada yang menjabat</span>')
    dipakai = (f'<span class="cap abu">dipakai {d["dipakai"]} berkas</span>'
               if d["dipakai"] else "")
    riwayat = "".join(_baris_pejabat(d, p, jabatan) for p in d["pejabat"])
    if not riwayat:
        riwayat = ('<p class="petunjuk">Belum ada kepala desa/lurah yang didaftarkan. '
                   'Isi lewat formulir di bawah.</p>')
    isi = f"""<div class="judul"><div>
<h1>{e(nama)}</h1>
<p>Kecamatan {e(d["kecamatan"])} · {keterangan} {dipakai}</p></div>
<div class="aksi"><a class="btn" href="/referensi?buka=desa#b-desa">Kembali ke daftar</a></div>
</div>

<section class="kartu"><h2>Identitas wilayah</h2><div class="badan">
<form method="post" action="/referensi/desa">
<input type="hidden" name="id" value="{d["id"]}">
<div class="grid g4">
  <div><label>Kecamatan <span class="wajib">*</span></label>
    {pilih("kecamatan_id", kecamatan, d["kecamatan_id"], atribut="required")}</div>
  {_isian("Nama", "nama", d["nama"], atribut="required")}
  <div><label>Jenis</label>
    {pilih("jenis", [(x, x) for x in wilayah.JENIS_DESA], d["jenis"])}</div>
  {_isian("Kode wilayah", "kode", d["kode"] or "", petunjuk="kode Kemendagri")}
</div>
<div class="aksi-baris"><button class="btn utama">Simpan</button>
<button class="btn kecil bahaya" formaction="/referensi/desa/hapus" formnovalidate
  data-konfirmasi="Hapus {e(nama)} beserta riwayat pejabatnya?">Hapus desa</button>
<span class="petunjuk">Mengubah Desa jadi Kelurahan tidak mengubah nama pejabat yang
sudah tersimpan — jabatannya yang perlu disesuaikan di bawah.</span></div>
</form></div></section>

<section class="kartu"><h2>Kepala desa / lurah
<span class="petunjuk">Tandai satu yang menjabat sekarang; sisanya jadi riwayat</span></h2>
<div class="badan">
<h3 class="sub">Riwayat ({len(d["pejabat"])})</h3>
{riwayat}
<h3 class="sub">Tambah pejabat</h3>
{_baris_pejabat(d, None, jabatan)}
</div></section>"""
    return layout(nama, isi, pengguna, "/referensi", pesan)


def _baris_pejabat(d, p, jabatan):
    """Satu blok formulir pejabat — dipakai untuk baris riwayat maupun isian baru."""
    p = p or {}
    pid = p.get("id", "")
    cap = ('<span class="cap hijau">sedang menjabat</span>' if p.get("aktif") else
           '<span class="cap abu">riwayat</span>' if pid else "")
    if pid:
        tombol = (f'<button class="btn kecil utama">Simpan</button>'
                  f'<button class="btn kecil" formaction="/referensi/desa/pejabat/aktif"'
                  f' formnovalidate>Jadikan yang menjabat</button>'
                  if not p.get("aktif") else '<button class="btn kecil utama">Simpan</button>')
        tombol += (f'<button class="btn kecil bahaya" formaction="/referensi/desa/pejabat/hapus"'
                   f' formnovalidate data-konfirmasi="Hapus {e(p.get("nama", ""))}'
                   f' dari riwayat?">Hapus</button>')
        centang = ""
    else:
        tombol = '<button class="btn kecil utama">+ Tambah pejabat</button>'
        centang = ('<label class="pilihan"><input type="checkbox" name="aktif" value="1" checked>'
                   ' Jadikan yang menjabat sekarang</label>')
    return f"""<form method="post" action="/referensi/desa/pejabat" class="anggota">
<input type="hidden" name="desa_id" value="{d["id"]}">
<input type="hidden" name="pejabat_id" value="{e(pid)}">
<input type="hidden" name="jenis" value="{e(d["jenis"])}">
<div class="grid g4">
  {_isian("Nama dan gelar", "nama", p.get("nama", ""), atribut="required")}
  <div><label>Jabatan</label>
    {pilih("jabatan", [(x, x) for x in jabatan],
           p.get("jabatan") or wilayah.jabatan_baku(d["jenis"]))}</div>
  {_isian("Mulai menjabat", "mulai", p.get("mulai", ""), "date")}
  {_isian("Sampai", "sampai", p.get("sampai", ""), "date",
          petunjuk="kosongkan bila masih menjabat")}
  {_isian("Nomor SK pengangkatan", "sk_nomor", p.get("sk_nomor", ""))}
</div>
{_isian_panjang("Catatan", "catatan", p.get("catatan", ""), 2)}
<div class="aksi-baris">{tombol} {centang} {cap}</div>
</form>"""


# ------------------------------------------------------------ kartu panitia
PERAN_PANITIA = ["Ketua merangkap Anggota", "Sekretaris merangkap Anggota", "Anggota"]


def _isian(label, nama, nilai="", tipe="text", atribut="", petunjuk=""):
    """Seperti bidang(), tapi tanpa id — dipakai pada baris yang berulang."""
    p = f'<div class="petunjuk">{e(petunjuk)}</div>' if petunjuk else ""
    return (f'<div><label>{e(label)}</label>'
            f'<input type="{tipe}" name="{e(nama)}" value="{e(nilai)}" {atribut}>{p}</div>')


def _isian_panjang(label, nama, nilai="", baris=2, petunjuk=""):
    p = f'<div class="petunjuk">{e(petunjuk)}</div>' if petunjuk else ""
    return (f'<div><label>{e(label)}</label>'
            f'<textarea name="{e(nama)}" rows="{baris}">{e(nilai)}</textarea>{p}</div>')


def _baris_anggota(pid, a=None):
    a = a or {}
    aid = a.get("id", "")
    tombol = (f'<button class="btn kecil utama">Simpan</button>'
              f'<button class="btn kecil bahaya" formaction="/referensi/panitia/anggota/hapus"'
              f' formnovalidate data-konfirmasi="Hapus anggota ini dari susunan?">Hapus</button>'
              if aid else f'<button class="btn kecil utama">+ Tambah anggota</button>')
    return f"""<form method="post" action="/referensi/panitia/anggota" class="anggota">
<input type="hidden" name="panitia_id" value="{pid}">
<input type="hidden" name="anggota_id" value="{e(aid)}">
<div class="grid g-anggota">
  {_isian("Urut", "urut", a.get("urut", ""), "number", 'min="0"')}
  {_isian("Nama dan gelar", "nama", a.get("nama", ""), atribut="required")}
  {_isian("NIP", "nip", a.get("nip", ""))}
  {_isian("Jabatan", "jabatan", a.get("jabatan", ""),
          petunjuk="dipakai mengenali Kasi Penataan pada template")}
  {_isian("Kedudukan dalam panitia", "peran", a.get("peran", ""),
          atribut='list="peran-panitia"')}
</div>
{_isian_panjang("Pendapat baku di Risalah", "pendapat_baku", a.get("pendapat_baku", ""),
                petunjuk="dipakai bila pendapat anggota pada berkas dikosongkan")}
<div class="aksi-baris">{tombol}</div>
</form>"""


def _cap_masa(p):
    """Label masa berlaku SK, dibaca dari tanggal berlaku_sampai."""
    habis = util.tanggal(p.get("berlaku_sampai"))
    if not habis:
        return '<span class="cap aksen">masih berlaku</span>'
    if habis < dt.date.today():
        return f'<span class="cap abu">arsip · habis {e(util.tanggal_pendek(habis))}</span>'
    return f'<span class="cap hijau">berlaku s.d. {e(util.tanggal_pendek(habis))}</span>'


def _lipat_panitia(p, isi=None, terbuka=False):
    """Kepala kartu satu SK — cukup untuk memilih SK tanpa perlu membukanya."""
    jml = p.get("jml_anggota") or 0
    ganjil = jml + 1                      # + kepala desa/lurah letak tanah
    tgl = util.tanggal_panjang(p.get("tanggal_sk"))
    ringkas = " · ".join(x for x in (
        e(tgl) or "tanggal SK belum diisi",
        f"{jml} anggota terdaftar" if jml else "anggota belum diisi",
        e(p.get("keterangan") or "")) if x)
    cap = _cap_masa(p) + (
        f'<span class="cap hijau">{ganjil} orang · ganjil</span>' if ganjil % 2 else
        f'<span class="cap merah">{ganjil} orang · genap</span>')
    return _lipat(f'panitia-{p["id"]}', e(p["nomor_sk"]), ringkas, isi, cap, terbuka,
                  cari=f'{p["nomor_sk"]} {tgl} {p.get("keterangan") or ""}')


def _isi_panitia(p):
    anggota = "".join(_baris_anggota(p["id"], a) for a in p["anggota"])
    if not anggota:
        anggota = ('<p class="petunjuk">Belum ada anggota pada SK ini. Isi lewat formulir '
                   'di bawah, atau salin susunannya dari SK lama.</p>')
    jml = len(p["anggota"]) + 1
    catatan = ("" if jml % 2 else
               f'<span class="cap merah">{jml} orang — genap, Pasal 138 ayat (1) minta '
               f'ganjil. Kepala desa/lurah sudah ikut terhitung.</span>')
    return f"""<div class="badan">
<form method="post" action="/referensi/panitia">
<input type="hidden" name="id" value="{p["id"]}">
<div class="grid g-sk">
  {_isian("Nomor SK", "nomor_sk", p.get("nomor_sk", ""), atribut="required")}
  {_isian("Tanggal SK", "tanggal_sk", p.get("tanggal_sk", ""), "date")}
  {_isian("Berlaku dari", "berlaku_dari", p.get("berlaku_dari", ""), "date")}
  {_isian("Berlaku sampai", "berlaku_sampai", p.get("berlaku_sampai", ""), "date",
          petunjuk="kosongkan bila masih berlaku")}
  {_isian("Keterangan", "keterangan", p.get("keterangan", ""))}
</div>
<div class="aksi-baris">
  <button class="btn kecil utama">Simpan SK</button>
  <button class="btn kecil" formaction="/referensi/panitia/salin" formnovalidate
          title="Buat SK baru dengan anggota yang sama">Salin jadi SK baru</button>
  <button class="btn kecil bahaya" formaction="/referensi/panitia/hapus" formnovalidate
          data-konfirmasi="Hapus susunan ini beserta anggotanya?">Hapus</button>
  {catatan}
</div>
</form>
<h3 class="sub">Anggota ({len(p["anggota"])})</h3>
{anggota}
<h3 class="sub">Tambah anggota</h3>
{_baris_anggota(p["id"])}
</div>"""


def _isi_panitia_baru():
    return f"""<div class="badan">
<form method="post" action="/referensi/panitia"><div class="grid g-sk">
  {_isian("Nomor SK", "nomor_sk", atribut="required placeholder='02/SK-75.03.HP.01/I/2026'")}
  {_isian("Tanggal SK", "tanggal_sk", "", "date")}
  {_isian("Berlaku dari", "berlaku_dari", "", "date")}
  {_isian("Berlaku sampai", "berlaku_sampai", "", "date")}
  {_isian("Keterangan", "keterangan")}
</div>
<div class="aksi-baris"><button class="btn utama">Tambah SK</button>
<span class="petunjuk">Anggotanya diisi setelah SK tersimpan, atau salin dari SK lama.</span>
</div></form></div>"""


# ----------------------------------------------------------------- template
LABEL_TIPE = {"": ("nilai", "aksen"), "*": ("berulang", "hijau"),
              "?": ("bila ada", "kuning"), "!": ("bila kosong", "kuning"),
              "@": ("foto", "abu"), "#": ("awal blok", "hijau"),
              "/": ("akhir blok", "hijau")}


def _ukuran(b):
    return f"{b / 1024:.0f} KB" if b < 1024 * 1024 else f"{b / 1024 / 1024:.1f} MB"


def _kepala_template(t, kunci):
    """Ringkasan + cap untuk kepala kartu template, terbaca tanpa membukanya."""
    if not t["ada"]:
        return ("berkasnya tidak ada di folder templates/",
                '<span class="cap merah">hilang</span>')
    dikenal, asing = templat.bandingkan(t["penanda"], kunci)
    ringkas = (f'{e(t["uraian"])} · {e(t["berkas"])} · {_ukuran(t["ukuran"])} · '
               f'{len(dikenal) + len(asing)} penanda · diubah {e(t["diubah"])}')
    cap = (f'<span class="cap merah">{len(asing)} penanda asing</span>' if asing else
           '<span class="cap hijau">penanda cocok</span>')
    if t["cadangan"]:
        cap += f'<span class="cap abu">{len(t["cadangan"])} cadangan</span>'
    return ringkas, cap


def _isi_template(t, kunci):
    if not t["ada"]:
        return (f'<div class="badan">'
                f'<div class="pesan galat"><b>Berkasnya tidak ada</b> di folder templates/. '
                f'Jalankan siapkan_template.bat, atau unggah di bawah.</div>'
                f'{_form_unggah(t)}</div>')
    dikenal, asing = templat.bandingkan(t["penanda"], kunci)
    chip = []
    for tipe, nama in dikenal:
        label, warna = LABEL_TIPE.get(tipe, ("nilai", "abu"))
        chip.append(f'<span class="cap {warna}" title="{label}">{{{{{e(tipe + nama)}}}}}</span>')
    peringatan = ""
    if asing:
        daftar = " ".join(f'<span class="cap merah">{{{{{e(t_ + n_)}}}}}</span>'
                          for t_, n_ in asing)
        peringatan = (f'<div class="pesan ingat" style="margin:.7rem 0 0">'
                      f'<b>Penanda ini tidak dikenali</b> dan akan tercetak kosong: {daftar}'
                      f'<div class="petunjuk">Cocokkan namanya dengan daftar penanda di '
                      f'bagian "Penanda yang tersedia", atau hapus dari dokumen.</div></div>')
    cad = "".join(
        f"""<li><span class="ikon">·</span><span>{e(c["waktu"])}
<span class="petunjuk">{e(c["nama"])} · {_ukuran(c["ukuran"])}</span></span>
<form method="post" action="/template/pulihkan" style="margin-left:auto">
<input type="hidden" name="jenis" value="{e(t["jenis"])}">
<input type="hidden" name="nama" value="{e(c["nama"])}">
<button class="btn kecil" data-konfirmasi="Kembalikan template ke versi ini?"
  >Kembalikan</button></form></li>""" for c in t["cadangan"])
    blok_cadangan = (f'<h3 class="sub">Cadangan</h3><ul class="daftar-periksa">{cad}</ul>'
                     if cad else
                     '<p class="petunjuk">Belum ada cadangan — dibuat otomatis setiap kali '
                     'template diganti.</p>')
    return f"""<div class="badan">
<div class="aksi-baris" style="margin-top:0">
  <a class="btn utama" href="/template/unduh/{e(t["jenis"])}">Unduh untuk disunting</a>
</div>
{_form_unggah(t)}
{peringatan}
<h3 class="sub">Penanda yang dipakai dokumen ini</h3>
<div class="chip">{"".join(chip)}</div>
{blok_cadangan}
</div>"""


def _form_unggah(t):
    return f"""<form method="post" action="/template/unggah" enctype="multipart/form-data"
class="aksi-baris" style="margin-top:.6rem">
<input type="hidden" name="jenis" value="{e(t["jenis"])}">
<input type="file" name="berkas" accept=".docx" required>
<button class="btn">Ganti template {e(t["nama"])}</button>
</form>"""


# Blok penjelasan di halaman template dipakai sesekali saja, jadi ditutup
# secara bawaan. Katalog penandanya (puluhan baris) baru diambil dari
# /template/bagian/penanda ketika kartunya dibuka.
def bagian_template(k, kunci):
    if kunci == "cara":
        return _cara_template()
    if kunci == "arti":
        return _arti_penanda()
    if kunci == "penanda":
        return _katalog_penanda(k)
    if kunci.startswith("tpl-") and kunci[4:] in templat.JENIS:
        c, _ = konteks.konteks_contoh(k)
        return _isi_template(templat.info(kunci[4:]), c)
    return ""


def _cara_template():
    return """<div class="badan">
<ol class="langkah">
  <li><b>Unduh</b> template yang mau diubah.</li>
  <li><b>Sunting di Microsoft Word</b> seperti dokumen biasa. Penanda
      <code>{{nama_penerima}}</code> adalah teks biasa: boleh dipindah, disalin,
      dihapus, atau ditambah. Kop, tabel, gaya huruf, dan penomoran ikut apa adanya.</li>
  <li><b>Simpan sebagai .docx</b> (jangan .doc atau PDF).</li>
  <li><b>Unggah lagi</b> lewat tombol "Ganti template". Versi lama otomatis dicadangkan,
      dan sistem langsung mencoba merakit satu dokumen contoh untuk memastikan
      templatenya masih bisa dipakai.</li>
</ol>
<div class="pesan ingat" style="margin-top:.8rem"><b>Catatan:</b>
menjalankan <code>siapkan_template.bat</code> membangun ulang template dari dokumen
ber-MERGEFIELD di folder <code>RAHMA WONTOGIA</code> dan akan menimpa hasil unggahan di
sini. Pakai yang itu hanya kalau tata naskahnya dirombak dari sumber aslinya.</div>
</div>"""


def _arti_penanda():
    return """<div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr><th>Bentuk</th><th>Artinya</th></tr></thead><tbody>
<tr><td class="nomor">{{nama_penerima}}</td><td>diganti nilainya</td></tr>
<tr><td class="nomor">{{*riwayat.uraian}}</td>
    <td>paragrafnya diulang satu kali untuk tiap baris riwayat perolehan</td></tr>
<tr><td class="nomor">{{*riwayat._akhir}}</td>
    <td>";" untuk baris selain terakhir, "." untuk baris terakhir</td></tr>
<tr><td class="nomor">{{*dokumen._nomor}}</td><td>nomor urut baris: 1, 2, 3 …
    (<code>_huruf</code> untuk a, b, c …, <code>_romawi</code> untuk i, ii, iii …
    seperti butir a.i / a.ii pada Risalah wakaf)</td></tr>
<tr><td class="nomor">{{?ada_selisih}}</td>
    <td>paragrafnya hanya dicetak bila nilainya terisi</td></tr>
<tr><td class="nomor">{{!ada_selisih}}</td>
    <td>kebalikannya — hanya dicetak bila nilainya kosong</td></tr>
<tr><td class="nomor">{{@foto}}</td><td>foto lapangan dari tab <b>Foto lapangan</b>
    dilampirkan di halaman baru pada akhir dokumen; paragraf penandanya sendiri dibuang</td></tr>
<tr><td class="nomor">{{*panitia.nama}} di dalam tabel</td>
    <td>baris tabelnya yang diulang, satu baris untuk tiap anggota panitia</td></tr>
<tr><td class="nomor">{{#panitia}} … {{/panitia}}</td>
    <td>semua paragraf atau baris tabel di antara kedua penanda diulang untuk tiap
    anggota — dipakai bila satu anggota butuh lebih dari satu baris, seperti blok
    Nama/NIP/Jabatan di BAP dan pendapat anggota di Risalah</td></tr>
<tr><td class="nomor">{{?panitia.nip}} di dalam blok</td>
    <td>paragraf atau baris itu dilewati untuk anggota yang kolomnya kosong
    (mis. kepala desa yang tanpa NIP)</td></tr>
<tr><td class="nomor">{{#nazhir}} … {{/nazhir}}</td>
    <td>sama caranya untuk daftar Nazhir pada berkas wakaf — lima baris identitas
    tiap orang diulang sebanyak Nazhir yang terdaftar di tab Pihak</td></tr>
</tbody></table></div></div>"""


def _katalog_penanda(k):
    c, bid = konteks.konteks_contoh(k)
    daftar = konteks.katalog_penanda(c)
    tr = "".join(
        f'<tr data-cari="{e((p + " " + ket + " " + contoh).lower())}">'
        f'<td class="nomor">{e(p)}</td><td>{e(ket)}</td>'
        f'<td class="petunjuk">{e(contoh)}</td></tr>' for p, ket, contoh in daftar)
    sumber = (f"Contoh nilai diambil dari berkas nomor {bid:04d}." if bid else
              "Belum ada berkas yang bisa dijadikan contoh, jadi kolom contoh masih kosong.")
    return f"""<div class="badan rapat">
{_saring("tabel-penanda", "Cari penanda — misalnya luas, tanggal, atau nama",
         len(daftar), "penanda")}
<div class="petunjuk" style="padding:0 1rem .6rem">{e(sumber)}
Ketik salah satu penanda ini di dokumen Word, persis termasuk kurung kurawalnya.</div>
<div class="tabel-bungkus" id="tabel-penanda"><table><thead><tr><th>Penanda</th>
<th>Jenis</th><th>Contoh isi</th></tr></thead><tbody>{tr}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada penanda yang cocok.</div></div>"""


def halaman_template(k, pengguna, pesan=None, terbuka=None):
    t = terbuka or {}
    c, _ = konteks.konteks_contoh(k)
    lipat = lambda kunci, judul, ringkas, cap="": _lipat(
        kunci, judul, ringkas, t.get(kunci), cap, kunci in t, dasar="/template")

    # Dua tata naskah dipisah jadi dua tab; penjelasan penandanya jadi tab
    # ketiga supaya tidak ikut menumpuk di bawah daftar template.
    set_kartu = {"": [], "wakaf": [], "hp": [], templat.VARIAN_LOKET: []}
    for j in templat.JENIS:
        info = templat.info(j)
        ringkas, cap = _kepala_template(info, c)
        set_kartu[info.get("varian") or ""].append(
            lipat("tpl-" + j, info["nama"], ringkas, cap))

    isi = f"""<div class="judul"><div><h1>Template dokumen</h1>
<p>Tata naskah BAP, Risalah, SK, dan cetakan loket. Sunting di Word, bukan di kode.
Buka kartunya untuk mengunduh, mengganti, atau melihat penandanya.</p></div></div>
{_tab("template", [("t-hm", "Hak Milik & hak lain"), ("t-wakaf", "Hak Wakaf"),
                   ("t-hp", "Hak Pakai"),
                   ("t-loket", "Cetakan loket"),
                   ("t-penanda", "Penanda & cara pakai")])}
<div class="panel" id="t-hm">{"".join(set_kartu[""])}</div>
<div class="panel" id="t-wakaf">{"".join(set_kartu["wakaf"])}</div>
<div class="panel" id="t-hp">
<p class="petunjuk" style="margin:0 0 .8rem">Satu set untuk pemohon perorangan dan
badan hukum. Paragraf <code>{{{{!badan_hukum}}}}</code> hanya tercetak untuk
perorangan, <code>{{{{?badan_hukum}}}}</code> hanya untuk badan hukum.</p>
{"".join(set_kartu["hp"])}</div>
<div class="panel" id="t-loket">
<p class="petunjuk" style="margin:0 0 .8rem">Dipakai menu Pradaftar, berlaku untuk
semua jenis hak. Formulir jenis hak lain cukup ditambahkan sebagai
<code>checklist-&lt;varian&gt;.docx</code>; selama belum ada, yang dipakai yang ini.</p>
{"".join(set_kartu[templat.VARIAN_LOKET])}</div>
<div class="panel" id="t-penanda">
{lipat("cara", "Cara mengubah template",
       "Empat langkah: unduh, sunting di Word, simpan .docx, unggah lagi")}
{lipat("arti", "Arti penanda",
       "Bentuk {{nilai}}, {{*berulang}}, {{?bila ada}}, {{#blok}} dan kawan-kawannya")}
{lipat("penanda", "Penanda yang tersedia",
       "Daftar lengkap penanda beserta contoh isinya dari berkas sungguhan")}
</div>"""
    return layout("Template", isi, pengguna, "/template", pesan)


# --------------------------------------------------------------- pengaturan
PETUNJUK_PENGATURAN = {
    "kata_penyambung":
        "dokumen yang diberi kata penyambung di kanan bawah tiap halaman "
        "(kata pertama halaman berikutnya). Isi bap, risalah, sk — dipisah koma; "
        "kosongkan untuk mematikannya. Perlu Microsoft Word di komputer ini.",
}


def _kartu_penyimpanan(ringkas):
    baris = "".join(
        f'<tr><td>{e(b["nama"])}<div class="petunjuk">{e(b["catatan"])}</div></td>'
        f'<td class="nomor">{b["jumlah"]}</td>'
        f'<td class="nomor">{e(pemeliharaan.teks_ukuran(b["bita"]))}</td>'
        f'<td class="petunjuk">{e(b["folder"])}</td></tr>' for b in ringkas)
    total = pemeliharaan.teks_ukuran(sum(b["bita"] for b in ringkas))
    return f"""<div class="kartu" id="penyimpanan"><h2>Penyimpanan
<span class="petunjuk" style="font-weight:400">terpakai {e(total)}</span></h2>
<div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr><th>Isi</th><th>Berkas</th><th>Ukuran</th><th>Folder</th></tr></thead>
<tbody>{baris}</tbody></table></div>
<div class="badan">
<form method="post" action="/pemeliharaan" class="aksi-baris">
  <input type="hidden" name="aksi" value="pratinjau">
  <button class="btn">Kosongkan singgahan pratinjau</button>
  <span class="petunjuk">PDF-nya dibuat lagi sendiri saat dokumen dibuka.</span>
</form>
<form method="post" action="/pemeliharaan" class="aksi-baris" style="margin-top:.6rem">
  <input type="hidden" name="aksi" value="cadangan_db">
  <button class="btn">Buang cadangan basis data lama</button>
  <span class="petunjuk">Menyisakan {pemeliharaan.CADANGAN_DB_SIMPAN} salinan terbaru.</span>
</form>
<form method="post" action="/pemeliharaan" class="aksi-baris" style="margin-top:.6rem"
      onsubmit="return confirm('Buang DOCX lama dari folder keluaran? Dokumennya dirakit ulang otomatis kalau dibuka lagi.')">
  <input type="hidden" name="aksi" value="keluaran">
  <label for="f_umur_hari" style="align-self:center">Rapikan dokumen lebih lama dari</label>
  <input type="number" id="f_umur_hari" name="umur_hari" min="0" step="1"
         value="{pemeliharaan.KELUARAN_UMUR_HARI}" style="width:6rem"> hari
  <button class="btn">Rapikan keluaran</button>
</form>
<div class="pesan ingat" style="margin-top:.8rem"><b>Yang dirapikan hanya yang bisa
dibuat ulang.</b> DOCX yang dibuang akan dirakit lagi dari basis data begitu tautan
unduh atau pratinjaunya dibuka. Dokumen yang <b>disunting tangan di Word</b> sesudah
dicetak — misalnya yang fotonya ditempel manual — dikenali dari waktu ubahnya dan
selalu dilewati, begitu juga dokumen yang tidak tercatat di arsip cetak.</div>
</div></div></div>

"""


def _pilih_peran(u, saya):
    """Satu formulir kecil per baris pengguna. Diri sendiri tidak ditawari
    turun peran — aturannya ada di rute/auth.py, di sini hanya cerminannya."""
    if u["id"] == saya["id"]:
        return (f'<span class="cap aksen">{e(u["peran"])}</span>'
                '<div class="petunjuk">akun Anda sendiri</div>')
    pilihan = "".join(
        f'<option value="{e(n)}"{" selected" if u["peran"] == n else ""}>{e(l)}</option>'
        for n, l in izin.PILIHAN_PERAN)
    return (f'<form method="post" action="/pengguna/peran" class="simpan-baris">'
            f'<input type="hidden" name="id" value="{u["id"]}">'
            f'<select name="peran">{pilihan}</select>'
            f'<button class="btn kecil">Ubah</button></form>')


def _pengaturan_petugas(pengguna, pesan=None):
    """Petugas hanya perlu satu hal di halaman ini: mengganti kata sandinya."""
    isi = f"""<div class="judul"><div><h1>Pengaturan</h1>
<p>Akun Anda.</p></div></div>
<div class="kartu"><h2>Ubah kata sandi saya</h2><div class="badan">
<form method="post" action="/sandi" class="grid g3">
  {bidang("Kata sandi lama", "lama", "", "password")}
  {bidang("Kata sandi baru", "baru", "", "password")}
  <div style="align-self:end"><button class="btn utama">Ubah</button></div>
</form></div></div>
<div class="kartu"><div class="badan"><p class="petunjuk">Masuk sebagai
<b>{e(pengguna["nama"])}</b> dengan peran <b>petugas</b>. Identitas kantor, data
referensi, template, dan pengelolaan akun diurus admin.</p></div></div>"""
    return layout("Pengaturan", isi, pengguna, "/pengaturan", pesan)


def halaman_pengaturan(pengguna, peng, daftar_pengguna, pesan=None, ringkas_simpan=None):
    if not izin.admin(pengguna):
        return _pengaturan_petugas(pengguna, pesan)

    baris_p = "".join(
        f'<tr><td>{e(u["nama"])}</td><td class="nomor">{e(u["username"])}</td>'
        f'<td>{_pilih_peran(u, pengguna)}</td>'
        f'<td class="petunjuk">{e(u["dibuat"])}</td></tr>' for u in daftar_pengguna)
    isi_peng = "".join(
        bidang(kunci.replace("_", " ").title(), f"set_{kunci}", nilai,
               petunjuk=PETUNJUK_PENGATURAN.get(kunci, ""))
        for kunci, nilai in peng.items())

    p_kantor = f"""<div class="kartu"><h2>Identitas kantor dan pejabat</h2><div class="badan">
<p class="petunjuk" style="margin-bottom:.8rem">Dipakai di kop dan tanda tangan semua
dokumen. Yang diubah di sini langsung ikut pada dokumen yang dicetak berikutnya.</p>
<form method="post" action="/pengaturan"><div class="grid g2">{isi_peng}</div>
<button class="btn utama" style="margin-top:.8rem">Simpan</button></form>
</div></div>"""

    p_pengguna = f"""<div class="kartu"><h2>Ubah kata sandi saya</h2><div class="badan">
<form method="post" action="/sandi" class="grid g3">
  {bidang("Kata sandi lama", "lama", "", "password")}
  {bidang("Kata sandi baru", "baru", "", "password")}
  <div style="align-self:end"><button class="btn utama">Ubah</button></div>
</form></div></div>

<div class="kartu"><h2>Pengguna
<span class="petunjuk" style="font-weight:400">{len(daftar_pengguna)} akun</span></h2>
<div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr><th>Nama</th><th>Username</th><th style="width:16rem">Peran</th>
<th>Dibuat</th></tr></thead>
<tbody>{baris_p}</tbody></table></div></div></div>

<div class="kartu"><h2>Tambah pengguna</h2><div class="badan">
<form method="post" action="/pengguna" class="grid g5">
  {bidang("Nama lengkap", "nama")}
  {bidang("Username", "username")}
  {bidang("Kata sandi", "sandi", "", "password")}
  {kotak("Peran", "peran", izin.PILIHAN_PERAN, izin.PETUGAS,
         petunjuk="petugas hanya mengurus berkas yang diinputnya sendiri")}
  <div style="align-self:end"><button class="btn utama">Tambah</button></div>
</form></div></div>"""

    p_simpan = (_kartu_penyimpanan(ringkas_simpan) if ringkas_simpan else
                '<div class="kartu"><div class="kosong"><b>Ringkasan penyimpanan '
                'tidak tersedia</b></div></div>')

    isi = f"""<div class="judul"><div><h1>Pengaturan</h1>
<p>Identitas kantor, penyimpanan, dan akun petugas.</p></div></div>
{_tab("pengaturan", [("p-kantor", "Kantor"), ("p-penyimpanan", "Penyimpanan"),
                     ("p-pengguna", "Pengguna")])}
<div class="panel" id="p-kantor">{p_kantor}</div>
<div class="panel" id="p-penyimpanan">{p_simpan}</div>
<div class="panel" id="p-pengguna">{p_pengguna}</div>"""
    return layout("Pengaturan", isi, pengguna, "/pengaturan", pesan)


# ---------------------------------------------------------------- pratinjau
def tautan_berkas(nama_file, berkas_id=None):
    """Alamat pratinjau untuk dokumen berkas: semuanya berkunci nama berkasnya."""
    return {
        "kembali": f"/berkas/{berkas_id}" if berkas_id else "/berkas",
        "label_kembali": "Kembali ke berkas",
        "pdf": f"/pdf/{nama_file}",
        "pdf_unduh": f"/pdf/{nama_file}?unduh=1",
        "docx": f"/unduh/{nama_file}",
        "segarkan": f"/pratinjau/{nama_file}?segarkan=1",
        "menu": "/berkas",
    }


def halaman_pratinjau(pengguna, nama_file, berkas_id=None, judul_berkas="",
                      mesin="", galat=None, tautan=None):
    """Satu halaman untuk dua macam dokumen.

    Yang berbeda cuma alamatnya, jadi yang dipindahkan ke pemanggil cuma itu:
    dokumen berkas berkunci nama berkasnya (`/pdf/<nama>`), cetakan loket
    berkunci pradaftar dan jenisnya (`/pradaftar/<id>/pdf/<jenis>`) karena
    memang tidak pernah diarsipkan dengan nama.
    """
    t = tautan or tautan_berkas(nama_file, berkas_id)
    menu = t.get("menu", "/berkas")
    if galat:
        isi = f"""<div class="judul"><div><h1>Pratinjau tidak tersedia</h1>
  <p>{e(nama_file)}</p></div>
  <div class="aksi"><a class="btn" href="{t["kembali"]}">&larr; {e(t["label_kembali"])}</a></div></div>
<div class="pesan galat">{e(galat)}</div>
<div class="kartu"><div class="badan">
  <p>Dokumen Word-nya tetap utuh dan bisa dibuka seperti biasa.</p>
  <p style="margin-top:.7rem">
    <a class="btn utama" href="{t["docx"]}">Unduh DOCX</a></p>
</div></div>"""
        return layout("Pratinjau", isi, pengguna, menu)

    isi = f"""<div class="judul">
  <div><h1>Pratinjau</h1>
  <p>{e(nama_file)}{" &middot; " + e(judul_berkas) if judul_berkas else ""}</p></div>
  <div class="aksi">
    <a class="btn" href="{t["kembali"]}">&larr; {e(t["label_kembali"])}</a>
    <a class="btn" href="{t["segarkan"]}">Buat ulang</a>
    <a class="btn" href="{t["docx"]}">Unduh DOCX</a>
    <a class="btn" href="{t["pdf_unduh"]}">Unduh PDF</a>
    <button type="button" class="btn utama" data-cetak="bingkai-pdf"
            data-pdf="{t["pdf"]}">Cetak</button>
  </div>
</div>
<div class="kartu"><div class="badan rapat">
  <div class="pratinjau-bingkai">
    <div class="pratinjau-tunggu" id="tunggu">
      <div class="putar" aria-hidden="true"></div>
      <div><b>Menyiapkan pratinjau lewat {e(mesin)}</b>
        <div class="petunjuk">Dokumen pertama perlu beberapa detik.
        Setelah itu langsung tampil.</div></div>
    </div>
    <iframe id="bingkai-pdf" title="Pratinjau {e(nama_file)}"
            src="{t["pdf"]}"
            onload="var t=document.getElementById('tunggu'); if(t) t.hidden=true"></iframe>
  </div>
</div></div>
<p class="petunjuk">Pratinjau ini untuk memeriksa hasil sebelum dicetak.
Naskah resminya tetap berkas DOCX.</p>"""
    return layout("Pratinjau " + nama_file, isi, pengguna, menu)
