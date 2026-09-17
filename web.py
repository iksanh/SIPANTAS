# -*- coding: utf-8 -*-
"""Perakit HTML. Semua halaman dibangun di sini sebagai teks biasa."""
import datetime as dt
import html
import json
import os

import db
import foto as foto_lapang
import konteks
import pemeliharaan
import templat
import util
import wilayah

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


def _tab(nama, butir):
    """Bilah tab. butir = (id_panel, label) atau (id_panel, label, lencana HTML).
    Peran ARIA dan panelnya dijodohkan app.js saat halaman dibuka."""
    tombol = "".join(
        f'<button type="button" role="tab" id="t-{e(b[0])}" aria-controls="{e(b[0])}"'
        f' aria-selected="false" tabindex="-1" data-panel="{e(b[0])}">{e(b[1])}'
        f'{b[2] if len(b) > 2 else ""}</button>' for b in butir)
    return (f'<div class="tab" role="tablist" data-tab="{e(nama)}"'
            f' aria-label="Bagian halaman">{tombol}</div>')


# ------------------------------------------------------------------ layout
def layout(judul, isi, pengguna=None, aktif="", pesan=None):
    menu = ""
    if pengguna:
        tautan = [("/berkas", "Berkas"), ("/referensi", "Data referensi"),
                  ("/template", "Template"), ("/pengaturan", "Pengaturan")]
        menu = "".join(
            f'<a href="{u}" class="{"aktif" if aktif == u else ""}">{e(t)}</a>' for u, t in tautan)
        menu += (f'<span class="siapa">{e(pengguna["nama"])}</span>'
                 f'<a href="/keluar">Keluar</a>')
    kepala = f"""<header class="atas"><div class="atas-isi">
  <a class="merek" href="/berkas"><span class="tanda">A</span> Berkas Panitia A</a>
  <nav>{menu}</nav></div></header>""" if pengguna else ""
    blok_pesan = ""
    if pesan:
        jenis, teks = pesan
        blok_pesan = f'<div class="pesan {e(jenis)}">{teks}</div>'
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(judul)} · Berkas Panitia A</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>{kepala}<main>{blok_pesan}{isi}</main>
<script src="/static/app.js"></script></body></html>"""


# ------------------------------------------------------------------- masuk
def halaman_masuk(galat=None):
    p = f'<div class="pesan galat">{e(galat)}</div>' if galat else ""
    isi = f"""<div class="masuk">
  <div class="merek"><span class="tanda">A</span> Berkas Panitia A</div>
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
def halaman_daftar(k, pengguna, baris, ringkasan, pesan=None):
    r = ringkasan
    kotak_ringkas = f"""<div class="ringkas">
  <div><b>{r['total']}</b><span>berkas</span></div>
  <div><b>{r['draf']}</b><span>draf</span></div>
  <div><b>{r['selesai']}</b><span>selesai</span></div>
  <div><b>{r['dokumen']}</b><span>dokumen tercetak</span></div>
  <div><b>{r['desa']}</b><span>desa terdaftar</span></div>
</div>"""

    tr = []
    for b in baris:
        cari = " ".join(str(x or "").lower() for x in
                        (b["penerima"], b["desa"], b["kecamatan"], b["nomor_risalah"],
                         b["nomor_sk"], b["kode_hak"]))
        warna = {"selesai": "hijau", "ditolak": "merah", "diperiksa": "kuning"}.get(b["status"], "abu")
        tr.append(f"""<tr data-cari="{e(cari)}" data-status="{e(b['status'])}">
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
</tr>""")

    tabel = f"""<div class="kartu"><div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr>
  <th>No</th><th>Penerima hak</th><th>Hak</th><th>Letak</th>
  <th style="text-align:right">Luas m²</th><th>Risalah</th><th>SK</th><th>Status</th>
</tr></thead><tbody>{''.join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada berkas yang cocok. Ubah kata cari atau pilih
tab <b>Semua</b>.</div></div></div>""" if tr else         '<div class="kartu"><div class="kosong"><b>Belum ada berkas</b>'         '<span>Klik "Berkas baru" untuk memulai, atau jalankan impor Excel.</span></div></div>'

    # Tab status menyaring tabel yang sama, bukan memuat ulang halaman.
    jumlah = {}
    for b in baris:
        jumlah[b["status"]] = jumlah.get(b["status"], 0) + 1
    tapis = "".join(
        f'<button type="button" data-status="{e(nilai)}" aria-pressed="false">{e(label)}'
        f'<span class="lencana">{jumlah.get(nilai, len(baris) if not nilai else 0)}</span>'
        f'</button>'
        for nilai, label in [("", "Semua")] + STATUS)

    isi = f"""<div class="judul">
  <div><h1>Daftar berkas</h1>
  <p id="jumlah-tampil">{len(baris)} berkas</p></div>
  <div class="aksi"><a class="btn utama" href="/berkas/baru">+ Berkas baru</a></div>
</div>
{kotak_ringkas}
<div class="bar"><div class="tumbuh">
  <label for="saring">Cari nama, desa, atau nomor</label>
  <input id="saring" type="search" placeholder="ketik untuk menyaring…"></div></div>
<div class="tab tapis" role="group" aria-label="Saring menurut status">{tapis}</div>
{tabel}"""
    return layout("Berkas", isi, pengguna, "/berkas", pesan)


# --------------------------------------------------------------- form berkas
def _baris_dinamis(nama, indeks, isi_html):
    return f"""<div class="baris">
  <div class="no">{indeks}</div>
  <div class="isi">{isi_html}</div>
  <div class="alat">
    <button type="button" class="btn kecil" data-aksi="naik" title="Naikkan">↑</button>
    <button type="button" class="btn kecil" data-aksi="turun" title="Turunkan">↓</button>
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
baris, sesuai urutan di bawah. Pakai ↑ ↓ untuk mengatur urutan dan × untuk membuang foto —
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


def halaman_form(k, pengguna, d, ref, masalah=None, terbit=None, pesan=None):
    """d = dict berkas hasil konteks.muat, atau None untuk berkas baru."""
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
        'Nazhir perseorangan paling sedikit 3 orang (Pasal 4 ayat (2) PP 42/2006).'
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
    p_terbit = _panel_terbit(d, masalah, terbit, baru)

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
    tab = _tab("berkas", [
        ("p-berkas", "Berkas"), ("p-pihak", "Pihak"), ("p-tanah", "Bidang tanah"),
        ("p-asal", "Riwayat / hak asal"), ("p-dokumen", "Dokumen"),
        ("p-foto", "Foto lapangan", lencana_foto),
        ("p-sidang", "Sidang & dokumen terbit"), ("p-terbit", "Cetak", lencana)])

    # Form cetak harus berada DI LUAR form-berkas: peramban membuang form bersarang.
    form_cetak = ("" if baru else
                  f'<form id="form-cetak" method="post" action="/berkas/{d["id"]}/cetak"></form>')
    nama_judul = penerima.get("nama") or "Berkas baru"
    isi = f"""<div class="lengket-atas">
<div class="judul">
  <div><h1>{e(nama_judul)}</h1>
  <p>{'Berkas baru' if baru else f"Berkas {d['id']:04d} · {e(d['jenis_hak_dimohon'])} · {e(d['jenis_kegiatan'])}"}</p></div>
  <div class="aksi">
    <a class="btn" href="/berkas">← Daftar</a>
    <button class="btn utama" type="submit" form="form-berkas">Simpan</button>
  </div>
</div>
{tab}
</div>
<form id="form-berkas" method="post" action="{aksi}" enctype="multipart/form-data">
<div class="panel" id="p-berkas">{p_berkas}</div>
<div class="panel" id="p-pihak">{p_pihak}</div>
<div class="panel" id="p-tanah">{p_tanah}</div>
<div class="panel" id="p-asal">{p_asal}</div>
<div class="panel" id="p-dokumen">{p_dok}</div>
<div class="panel" id="p-foto">{p_foto}</div>
<div class="panel" id="p-sidang">{p_sidang}</div>
<div class="panel" id="p-terbit">{p_terbit}</div>
</form>
{form_cetak}
<script>window.DAFTAR_DESA = {desa_json};</script>"""
    return layout(nama_judul, isi, pengguna, "/berkas", pesan)


def _panel_terbit(d, masalah, terbit, baru):
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

    return f"""{catatan}{hasil}
<div class="kartu"><h2>Pemeriksaan sebelum cetak</h2><div class="badan">
<ul class="daftar-periksa">{li}</ul></div></div>

<div class="kartu"><h2>Cetak dokumen</h2><div class="badan">
<div class="aksi" style="display:flex;gap:.5rem;flex-wrap:wrap">
  <button class="btn utama" type="submit" form="form-cetak" name="jenis" value="semua"{nonaktif}>
    Cetak semua dokumen</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="bap"{nonaktif}>BAP</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="risalah"{nonaktif}>Risalah</button>
  <button class="btn" type="submit" form="form-cetak" name="jenis" value="sk"{nonaktif}>SK</button>
</div>
<div class="petunjuk" style="margin-top:.6rem">Nomor Risalah dan SK diberikan otomatis saat
pertama kali dicetak, berurutan per jenis hak per tahun.</div>
</div></div>
{riwayat}"""


# ---------------------------------------------------------------- referensi
# Halaman referensi dirakit sebagai kartu yang bisa dibuka-tutup. Yang ikut
# terkirim saat halaman dibuka hanyalah kepala kartunya (judul + ringkasan);
# isi tabelnya baru diambil app.js dari /referensi/bagian/<kunci> ketika kartu
# itu dibuka, jadi satu halaman tidak pernah memuat seluruh data sekaligus.
# Tanpa JavaScript kepala kartu tetap tautan biasa (?buka=<kunci>) yang dijawab
# server dengan kartu tersebut sudah terbuka.

def _lipat(kunci, judul, ringkas, isi=None, cap="", terbuka=False, cari="",
           dasar="/referensi"):
    """Satu kartu lipat. isi=None berarti isinya diambil belakangan dari
    <dasar>/bagian/<kunci>; kepalanya menaut ke <dasar>?buka=<kunci> sebagai
    jalan keluar bila JavaScript mati."""
    ident, sarang = f"b-{kunci}", f"i-{kunci}"
    muat = "" if isi is not None else f' data-muat="{dasar}/bagian/{e(kunci)}"'
    tanda = f' data-cari="{e(cari.lower())}"' if cari else ""
    return f"""<section class="kartu lipat{' terbuka' if terbuka else ''}" id="{ident}"{tanda}>
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


def halaman_referensi(pengguna, ringkas, terbuka=None, pesan=None):
    """ringkas = angka tiap bagian + kepala tiap SK panitia.
    terbuka = {kunci: potongan HTML} untuk bagian yang diminta lewat ?buka=."""
    t = terbuka or {}
    r = ringkas
    ada = lambda kunci: kunci in t
    kurang = r["desa_kosong"]

    bagian = [
        _lipat("jenis_hak", "Matriks jenis hak",
               f'{r["jenis_hak"]} jenis hak aktif · jangka waktu, subjek yang boleh, '
               f'kegiatan, dan dasar hukumnya',
               t.get("jenis_hak"), terbuka=ada("jenis_hak")),
        _lipat("klausa", "Pustaka blok klausa",
               f'{r["klausa"]} blok kalimat baku yang disisipkan ke dokumen',
               t.get("klausa"), terbuka=ada("klausa")),
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

    isi = f"""<div class="judul"><div><h1>Data referensi</h1>
<p>Yang berulang disimpan sekali di sini, bukan diketik ulang di tiap dokumen.
Klik judul bagian untuk membukanya — isinya baru diambil saat dibuka.</p></div></div>

{"".join(bagian)}

<datalist id="peran-panitia">{"".join(f'<option value="{e(x)}">' for x in PERAN_PANITIA)}</datalist>
<h2 class="pemisah" id="panitia">Susunan Panitia A</h2>
<p class="petunjuk" style="margin:-.4rem 0 .8rem">Diambil dari SK Kepala Kantor tentang
penunjukan Panitia Pemeriksaan Tanah A. Setiap kali susunannya berganti, tambah SK baru —
jangan menimpa yang lama, supaya berkas lama tetap merujuk susunan yang benar saat itu.
Kepala desa/lurah letak tanah ditambahkan otomatis sebagai anggota (Pasal 138 ayat (1)
huruf c), jadi tidak perlu didaftarkan di sini.</p>
{cari_sk}
<div id="daftar-sk">{sk}</div>
<div class="tak-cocok" hidden>Tidak ada SK yang cocok.</div>
{_lipat("panitia_baru", "Tambah SK susunan panitia",
        "Nomor dan masa berlaku SK baru; anggotanya diisi setelah tersimpan",
        _isi_panitia_baru(), terbuka=ada("panitia_baru"))}

<h2 class="pemisah">Wilayah</h2>
<p class="petunjuk" style="margin:-.4rem 0 .8rem">Letak tanah pada berkas menunjuk ke daftar
ini, dan kepala desa/lurah yang sedang menjabat ikut tercetak sebagai anggota Panitia A.
Kepala desa yang diganti tidak ditimpa — yang lama tetap tersimpan sebagai riwayat supaya
berkas lama masih bisa ditelusuri.</p>
{kemendagri}
{kecamatan}
{desa}"""
    return layout("Data referensi", isi, pengguna, "/referensi", pesan)


# --------------------------------------------------------- potongan bagian
def bagian_referensi(kunci, data):
    """Potongan HTML satu bagian. Dipakai halaman /referensi maupun permintaan
    terpisah ke /referensi/bagian/<kunci> saat kartunya dibuka."""
    if data is None:
        return ""
    if kunci == "jenis_hak":
        return _tabel_jenis_hak(data)
    if kunci == "klausa":
        return _tabel_klausa(data)
    if kunci == "desa":
        return _tabel_desa(data)
    if kunci == "kecamatan":
        return _tabel_kecamatan(data)
    if kunci == "kemendagri":
        return _isi_kemendagri(data)
    if kunci.startswith("panitia-"):
        return _isi_panitia(data)
    return ""


def _tabel_jenis_hak(baris):
    tr = "".join(
        f'<tr><td class="nomor">{e(r["kode"])}</td><td>{e(r["nama"])}</td>'
        f'<td>{"berjangka " + str(r["jangka_maks"]) + " th" if r["ada_jangka_waktu"] else "tidak berjangka"}'
        f'{" · perpanjangan " + str(r["perpanjangan_maks"]) + " th" if r["perpanjangan_maks"] else ""}</td>'
        f'<td>{e(r["subjek_boleh"].replace("_", " "))}</td>'
        f'<td>{e(r["kegiatan_boleh"])}</td>'
        f'<td class="petunjuk">{e(r["dasar_subjek"])}</td></tr>' for r in baris)
    return f"""<div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr><th>Kode</th><th>Nama</th><th>Jangka waktu</th><th>Subjek yang boleh</th>
<th>Kegiatan</th><th>Dasar</th></tr></thead><tbody>{tr}</tbody></table></div></div>"""


def _tabel_klausa(baris):
    tr = "".join(
        f'<tr><td class="nomor">{e(r["slot"])}</td><td class="nomor">{e(r["jenis_hak"])}</td>'
        f'<td class="nomor">{e(r["kegiatan"])}</td><td class="nomor">{e(r["subjek"])}</td>'
        f'<td>{e(r["isi"][:150])}{"…" if len(r["isi"]) > 150 else ""}</td></tr>' for r in baris)
    return f"""<div class="badan rapat"><div class="tabel-bungkus">
<table><thead><tr><th>Slot</th><th>Jenis hak</th><th>Kegiatan</th><th>Subjek</th><th>Isi</th>
</tr></thead><tbody>{tr}</tbody></table></div></div>"""


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


def _tabel_desa(data):
    baris, kecamatan = data["baris"], data["kecamatan"]
    tr = []
    for r in baris:
        desa = f'{r["jenis"]} {r["nama"]}'
        riwayat = len(r["pejabat"])
        cari = " ".join([r["kecamatan"], desa, r["nama_pejabat"] or "",
                         r["jabatan_pejabat"] or ""]
                        + [p["nama"] for p in r["pejabat"]])
        if r["nama_pejabat"]:
            jabatan = _cap_jabatan(r["jabatan_pejabat"])
        else:
            jabatan = '<span class="cap kuning">belum diisi</span>'
        tr.append(
            f'<tr data-cari="{e(cari.lower())}"><td>{e(r["kecamatan"])}</td>'
            f'<td>{e(desa)}</td><td>{jabatan}</td>'
            f'<td>{_pilih_pejabat(r)}</td>'
            f'<td class="nomor">{riwayat or "—"}</td>'
            f'<td><a class="btn kecil" href="/referensi/desa/{r["id"]}">Kelola</a></td></tr>')
    return f"""<div class="badan rapat">
{_saring("tabel-desa", "Cari kecamatan, desa, atau nama pejabat…", len(baris), "desa")}
<div class="tabel-bungkus" id="tabel-desa"><table><thead><tr><th>Kecamatan</th>
<th>Desa/Kelurahan</th><th>Jabatan</th><th>Yang menjabat sekarang</th><th>Riwayat</th>
<th></th></tr></thead>
<tbody>{"".join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada desa yang cocok.</div>
{_tambah_desa(kecamatan)}</div>"""


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


def _tabel_kecamatan(baris):
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
    return f"""<div class="badan rapat">
{_saring("tabel-kecamatan", "Cari nama atau kode kecamatan…", len(baris), "kecamatan")}
<div class="tabel-bungkus" id="tabel-kecamatan"><table><thead><tr><th>Kode</th>
<th>Nama kecamatan</th><th>Desa</th></tr></thead><tbody>{"".join(tr)}</tbody></table></div>
<div class="tak-cocok" hidden>Tidak ada kecamatan yang cocok.</div>
<div class="badan" style="border-top:1px solid var(--garis)">
<h3 class="sub">Tambah kecamatan</h3>
<form method="post" action="/referensi/kecamatan"><div class="grid g2">
  {_isian("Nama kecamatan", "nama", atribut="required")}
  {_isian("Kode wilayah", "kode", petunjuk="kode Kemendagri, mis. 75.03.02")}
</div>
<input type="hidden" name="asal" value="{e(ASAL_KECAMATAN)}">
<div class="aksi-baris"><button class="btn utama">Tambah kecamatan</button></div>
</form></div></div>"""


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
<div class="grid g4">
  {_isian("Urut", "urut", a.get("urut", ""), "number", 'style="max-width:5rem"')}
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
<div class="grid g4">
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
<form method="post" action="/referensi/panitia"><div class="grid g4">
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

    kartu = []
    for j in templat.JENIS:
        info = templat.info(j)
        ringkas, cap = _kepala_template(info, c)
        kartu.append(lipat("tpl-" + j, info["nama"], ringkas, cap))

    isi = f"""<div class="judul"><div><h1>Template dokumen</h1>
<p>Tata naskah BAP, Risalah, dan SK. Sunting di Word, bukan di kode.
Buka kartunya untuk mengunduh, mengganti, atau melihat penandanya.</p></div></div>

{"".join(kartu)}

<h2 class="pemisah">Penjelasan</h2>
{lipat("cara", "Cara mengubah template",
       "Empat langkah: unduh, sunting di Word, simpan .docx, unggah lagi")}
{lipat("arti", "Arti penanda",
       "Bentuk {{nilai}}, {{*berulang}}, {{?bila ada}}, {{#blok}} dan kawan-kawannya")}
{lipat("penanda", "Penanda yang tersedia",
       "Daftar lengkap penanda beserta contoh isinya dari berkas sungguhan")}"""
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


def halaman_pengaturan(pengguna, peng, daftar_pengguna, pesan=None, ringkas_simpan=None):
    baris_p = "".join(
        f'<tr><td>{e(u["nama"])}</td><td class="nomor">{e(u["username"])}</td>'
        f'<td><span class="cap abu">{e(u["peran"])}</span></td>'
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
<table><thead><tr><th>Nama</th><th>Username</th><th>Peran</th><th>Dibuat</th></tr></thead>
<tbody>{baris_p}</tbody></table></div></div></div>

<div class="kartu"><h2>Tambah pengguna</h2><div class="badan">
<form method="post" action="/pengguna" class="grid g4">
  {bidang("Nama lengkap", "nama")}
  {bidang("Username", "username")}
  {bidang("Kata sandi", "sandi", "", "password")}
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
def halaman_pratinjau(pengguna, nama_file, berkas_id=None, judul_berkas="",
                      mesin="", galat=None):
    kembali = f"/berkas/{berkas_id}" if berkas_id else "/berkas"
    if galat:
        isi = f"""<div class="judul"><div><h1>Pratinjau tidak tersedia</h1>
  <p>{e(nama_file)}</p></div>
  <div class="aksi"><a class="btn" href="{kembali}">&larr; Kembali ke berkas</a></div></div>
<div class="pesan galat">{e(galat)}</div>
<div class="kartu"><div class="badan">
  <p>Dokumen Word-nya tetap utuh dan bisa dibuka seperti biasa.</p>
  <p style="margin-top:.7rem">
    <a class="btn utama" href="/unduh/{e(nama_file)}">Unduh DOCX</a></p>
</div></div>"""
        return layout("Pratinjau", isi, pengguna, "/berkas")

    isi = f"""<div class="judul">
  <div><h1>Pratinjau</h1>
  <p>{e(nama_file)}{" &middot; " + e(judul_berkas) if judul_berkas else ""}</p></div>
  <div class="aksi">
    <a class="btn" href="{kembali}">&larr; Kembali ke berkas</a>
    <a class="btn" href="/pratinjau/{e(nama_file)}?segarkan=1">Buat ulang</a>
    <a class="btn" href="/unduh/{e(nama_file)}">Unduh DOCX</a>
    <a class="btn utama" href="/pdf/{e(nama_file)}?unduh=1">Unduh PDF</a>
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
            src="/pdf/{e(nama_file)}"
            onload="var t=document.getElementById('tunggu'); if(t) t.hidden=true"></iframe>
  </div>
</div></div>
<p class="petunjuk">Pratinjau ini untuk memeriksa hasil sebelum dicetak.
Naskah resminya tetap berkas DOCX.</p>"""
    return layout("Pratinjau " + nama_file, isi, pengguna, "/berkas")
