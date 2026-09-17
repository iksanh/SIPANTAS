# -*- coding: utf-8 -*-
"""Ambil satu berkas dari basis data, hitung nilai turunannya, dan periksa kelengkapannya.

Di sinilah prinsip "satu fakta, satu tempat" dijalankan: yang disimpan hanya
tanggal dan angka, sedangkan hari, terbilang, luas berhuruf, selisih, dan sapaan
dihitung setiap kali dokumen dirakit.
"""
import re

import db
import foto
import util


# ------------------------------------------------------------------ muat
def muat(k, berkas_id):
    """Kembalikan seluruh isi satu berkas sebagai dict biasa."""
    b = k.execute("SELECT * FROM berkas WHERE id=?", (berkas_id,)).fetchone()
    if not b:
        return None
    d = dict(b)
    d["pihak"] = [dict(r) for r in k.execute(
        "SELECT * FROM pihak WHERE berkas_id=? ORDER BY urut, id", (berkas_id,))]
    for p in d["pihak"]:
        bh = k.execute("SELECT * FROM pihak_badan_hukum WHERE pihak_id=?", (p["id"],)).fetchone()
        p["badan_hukum"] = dict(bh) if bh else {}
    t = k.execute("SELECT * FROM bidang_tanah WHERE berkas_id=?", (berkas_id,)).fetchone()
    d["tanah"] = dict(t) if t else {}
    if d["tanah"].get("desa_id"):
        ds = k.execute(
            "SELECT d.*, c.nama AS kecamatan FROM ref_desa d "
            "JOIN ref_kecamatan c ON c.id=d.kecamatan_id WHERE d.id=?",
            (d["tanah"]["desa_id"],)).fetchone()
        d["desa"] = dict(ds) if ds else {}
    else:
        d["desa"] = {}
    d["riwayat"] = [dict(r) for r in k.execute(
        "SELECT * FROM riwayat_perolehan WHERE berkas_id=? ORDER BY urut, id", (berkas_id,))]
    d["dokumen"] = [dict(r) for r in k.execute(
        "SELECT * FROM dokumen_pendukung WHERE berkas_id=? ORDER BY urut, id", (berkas_id,))]
    for r in d["dokumen"]:
        # uraian yang dikosongkan petugas disusun dari rinciannya; yang diketik
        # disimpan terpisah supaya formulir tidak menampilkan hasil susunan sebagai ketikan
        r["uraian_tulis"] = r["uraian"] or ""
        if not r["uraian_tulis"].strip():
            r["uraian"] = uraian_rincian(r)
    ha = k.execute("SELECT * FROM hak_asal WHERE berkas_id=?", (berkas_id,)).fetchone()
    d["hak_asal"] = dict(ha) if ha else {}
    pm = k.execute("SELECT * FROM pemeriksaan WHERE berkas_id=?", (berkas_id,)).fetchone()
    d["pemeriksaan"] = dict(pm) if pm else {}
    d["pendapat"] = [dict(r) for r in k.execute(
        "SELECT * FROM pendapat_anggota WHERE berkas_id=? ORDER BY urut, id", (berkas_id,))]
    d["foto"] = [dict(r) for r in k.execute(
        "SELECT * FROM foto_lapang WHERE berkas_id=? ORDER BY urut, id", (berkas_id,))]
    for f in d["foto"]:
        f["ada"] = foto.ada(f)
    r = k.execute("SELECT * FROM risalah WHERE berkas_id=?", (berkas_id,)).fetchone()
    d["risalah"] = dict(r) if r else {}
    s = k.execute("SELECT * FROM sk WHERE berkas_id=?", (berkas_id,)).fetchone()
    d["sk"] = dict(s) if s else {}
    d["hak"] = dict(k.execute("SELECT * FROM ref_jenis_hak WHERE kode=?",
                              (d["jenis_hak_dimohon"],)).fetchone())
    pid = d["pemeriksaan"].get("panitia_id")
    if pid:
        d["panitia"] = dict(k.execute("SELECT * FROM ref_panitia WHERE id=?", (pid,)).fetchone())
        d["panitia_anggota"] = [dict(r) for r in k.execute(
            "SELECT * FROM ref_panitia_anggota WHERE panitia_id=? ORDER BY urut, id", (pid,))]
    else:
        d["panitia"], d["panitia_anggota"] = {}, []
    d["pengaturan"] = {r["kunci"]: r["nilai"] for r in k.execute(
        "SELECT kunci, nilai FROM pengaturan")}
    # Kepala desa/lurah selalu menjadi anggota Panitia A (Pasal 138 ayat (1) huruf c)
    if d["desa"].get("nama_pejabat"):
        d["panitia_anggota"] = d["panitia_anggota"] + [{
            "urut": 99, "nama": d["desa"]["nama_pejabat"], "nip": "",
            "jabatan": f"{d['desa'].get('jabatan_pejabat','Kepala Desa')} {d['desa']['nama']}",
            "peran": "Anggota", "dari_desa": True,
            "pendapat_baku": "Bahwa tanah yang dimohon telah dikuasai dan dimiliki oleh pemohon, "
                             "tidak ada yang mengajukan keberatan dan tidak dalam sengketa dengan pihak lain.",
        }]
    return d


def pihak_peran(d, peran):
    for p in d["pihak"]:
        if p["peran"] == peran:
            return p
    return {}


def daftar_peran(d, *peran):
    """Semua pihak dengan salah satu peran itu, urut sesuai formulir."""
    return [p for p in d["pihak"] if p["peran"] in peran]


def penerima_hak(d):
    """Pihak yang namanya tercantum di SK: penerima hak, bukan kuasanya."""
    return pihak_peran(d, "penerima_hak") or pihak_peran(d, "pemohon") or {}


def wakaf(d):
    """Benar bila berkas ini permohonan tanah wakaf."""
    return (d.get("jenis_hak_rekomendasi") or d.get("jenis_hak_dimohon")) == "WAKAF"


def daftar_nazhir(d):
    """Nazhir penerima hak wakaf: penerima hak, ditambah nazhir lain pada berkas.

    Satu orang satu baris — Risalah mencetak nama, TTL, NIK, alamat, dan pekerjaan
    tiap nazhir, jadi tidak ada nama yang perlu diketik ulang sebagai satu kalimat.
    """
    orang = []
    utama = penerima_hak(d)
    if utama.get("nama"):
        orang.append(utama)
    for p in daftar_peran(d, "nazhir"):
        if p.get("id") != utama.get("id"):
            orang.append(p)
    return orang


def _baris_orang(p):
    return {
        "nama": p.get("nama") or "",
        "nik": (p.get("nik") or "").strip(),
        "ttl": (p.get("ttl") or "").strip(),
        "alamat": (p.get("alamat") or "").strip(),
        "pekerjaan": (p.get("pekerjaan") or "").strip(),
        "jenis_kelamin": (p.get("jenis_kelamin") or "").strip(),
        "jenis_subjek": p.get("jenis_subjek") or "perorangan",
    }


BENTUK_NAZHIR = {"perorangan": "perseorangan", "badan_hukum": "badan hukum",
                 "instansi": "organisasi"}


def _kalimat_nazhir(x):
    """Satu kalimat identitas Nazhir, dipakai bagian Analisis yang menyebut
    semuanya dalam satu paragraf. Bagian yang kosong tidak menyisakan kata gantung."""
    bagian = [x["nama"]]
    if x["ttl"]:
        bagian.append(f"tempat tanggal lahir {x['ttl']}")
    bagian.append("Kewarganegaraan Indonesia")
    if x["alamat"]:
        bagian.append(f"bertempat tinggal di {x['alamat']}")
    if x["pekerjaan"]:
        bagian.append(f"pekerjaan {x['pekerjaan']}")
    return " ".join(bagian[:1]) + (" " + ", ".join(bagian[1:]) if len(bagian) > 1 else "")


# --------------------------------------------------------------- klausa
def pilih_klausa(k, slot, d, tanggal=None):
    """Blok klausa yang paling cocok dengan konteks berkas. Yang paling khusus menang."""
    baris = k.execute("SELECT * FROM ref_klausa WHERE slot=?", (slot,)).fetchall()
    penerima = penerima_hak(d)
    ctx = {
        "jenis_hak": d["jenis_hak_rekomendasi"] or d["jenis_hak_dimohon"],
        "kegiatan": d["jenis_kegiatan"],
        "subjek": penerima.get("jenis_subjek") or "perorangan",
    }
    terbaik, nilai_terbaik = None, -1
    for r in baris:
        skor = 0
        cocok = True
        for kolom in ("jenis_hak", "kegiatan", "subjek"):
            v = (r[kolom] or "*").strip()
            if v == "*":
                continue
            if ctx[kolom] in [x.strip() for x in v.split(",")]:
                skor += 1
            else:
                cocok = False
                break
        if cocok and skor > nilai_terbaik:
            terbaik, nilai_terbaik = r, skor
    return terbaik["isi"] if terbaik else ""


# --------------------------------------------------------------- konteks
def bangun(k, berkas_id):
    """Susun dict penanda untuk mesin template."""
    d = muat(k, berkas_id)
    if not d:
        return None, None
    penerima = penerima_hak(d)
    kuasa = pihak_peran(d, "kuasa")
    sebelumnya = pihak_peran(d, "pemilik_sebelumnya")
    t = d["tanah"]
    hak = d["hak"]
    ris, sk_, pem = d["risalah"], d["sk"], d["pemeriksaan"]
    bh = penerima.get("badan_hukum") or {}

    # dokumen yang punya penanda sendiri di template: dicari dulu supaya barisnya
    # bisa dikeluarkan dari daftar berulang, apa pun cara ketemunya
    dok_sppf = _dokumen_khusus(d, "sppf", "penguasaan fisik")
    dok_kuasa = _dokumen_khusus(d, "kuasa", "surat kuasa")
    dok_selisih = _dokumen_khusus(d, "selisih", "perbedaan luas")
    khusus = {x["id"] for x in (dok_sppf, dok_kuasa) if x is not None}
    teks_sppf = _teks_dokumen(dok_sppf)
    # kalimat telaah: pakai yang ditulis petugas kalau ada, kalau kosong disusun sendiri
    tulis_pf = (t.get("uraian_penguasaan_fisik") or "").strip()
    tulis_selisih = (t.get("uraian_selisih_luas") or "").strip()

    luas_pbt = t.get("luas_pbt")
    luas_surat = t.get("luas_surat")
    selisih = None
    if luas_pbt is not None and luas_surat is not None:
        selisih = int(luas_pbt) - int(luas_surat)

    tgl_bap = pem.get("tanggal_bap")
    tgl_ris = ris.get("tanggal")
    tgl_sk = sk_.get("tanggal")

    panitia = _daftar_panitia(d)

    # --- wakaf: Nazhir bisa lebih dari satu orang, Wakif pemilik tanah sebelumnya
    ini_wakaf = wakaf(d)
    dok_aiw = _dokumen_khusus(d, "akta_ikrar", "ikrar wakaf")
    dok_pengesahan = _dokumen_khusus(d, "pengesahan_nazhir", "pengesahan naz")
    nazhir = [_baris_orang(p) for p in daftar_nazhir(d)]
    daftar_wakif = [_baris_orang(p) for p in
                    (daftar_peran(d, "wakif") or
                     (daftar_peran(d, "pemilik_sebelumnya") if ini_wakaf else []))]
    nama_nazhir = ", ".join(x["nama"] for x in nazhir if x["nama"])
    nama_wakif = ", ".join(x["nama"] for x in daftar_wakif if x["nama"])

    jangka = ris.get("jangka_waktu_tahun")
    jangka_berakhir = ""
    if jangka and tgl_sk:
        dd = util.tanggal(tgl_sk)
        if dd:
            try:
                jangka_berakhir = util.tanggal_panjang(dd.replace(year=dd.year + int(jangka)))
            except ValueError:                       # 29 Februari
                jangka_berakhir = util.tanggal_panjang(
                    dd.replace(year=dd.year + int(jangka), day=28))

    c = {
        # --- pihak
        # Pada berkas wakaf yang tercantum di SK adalah seluruh Nazhir, jadi penanda
        # yang sama dipakai kedua tata naskah tanpa perlu isian nama yang kedua.
        "nama_penerima": (nama_nazhir if ini_wakaf else penerima.get("nama", "")),
        "nama_pemohon": (kuasa.get("nama") or penerima.get("nama", "")),
        "alamat_penerima": penerima.get("alamat", ""),
        "nik_penerima": penerima.get("nik", ""),
        "ttl_penerima": penerima.get("ttl", ""),
        "pekerjaan_penerima": penerima.get("pekerjaan", ""),
        "jenis_kelamin": penerima.get("jenis_kelamin", ""),
        "sapaan": util.sapaan(penerima.get("jenis_kelamin")),
        "pemilik_sebelumnya": sebelumnya.get("nama", ""),

        # --- wakaf
        "wakaf": ini_wakaf,
        "nazhir": nazhir,
        "nama_nazhir": nama_nazhir,
        "nazhir_uraian": "; ".join(_kalimat_nazhir(x) for x in nazhir),
        "nazhir_jumlah": len(nazhir),
        "nazhir_jumlah_terbilang": util.terbilang(len(nazhir)) if nazhir else "",
        "bentuk_nazhir": BENTUK_NAZHIR.get(penerima.get("jenis_subjek") or "perorangan",
                                           "perseorangan"),
        "wakif": daftar_wakif,
        "nama_wakif": nama_wakif,
        "akta_ikrar": _teks_dokumen(dok_aiw),
        "pengesahan_nazhir": _teks_dokumen(dok_pengesahan),
        # frasa Menimbang SK huruf b dan c, format Permen ATR/BPN 2/2017
        "akta_ikrar_sk": frasa_akta_ikrar(dok_aiw),
        "pengesahan_nazhir_sk": frasa_pengesahan_nazhir(dok_pengesahan),
        "akta_ikrar_nomor": (dok_aiw or {}).get("nomor") or "",
        "akta_ikrar_tanggal": util.tanggal_panjang((dok_aiw or {}).get("tanggal")),
        "ppaiw_nama": (dok_aiw or {}).get("pejabat") or "",
        "pengesahan_nazhir_nomor": (dok_pengesahan or {}).get("nomor") or "",
        "pengesahan_nazhir_tanggal": util.tanggal_panjang((dok_pengesahan or {}).get("tanggal")),
        "kesediaan_nazhir": _teks_dokumen(
            _dokumen_khusus(d, "kesediaan_nazhir", "kesediaan menjadi naz")),
        "bersedia_diaudit": _teks_dokumen(
            _dokumen_khusus(d, "bersedia_diaudit", "bersedia diaudit")),

        "surat_kuasa": _teks_dokumen(dok_kuasa),
        "via_kuasa": bool(kuasa),
        "badan_hukum": penerima.get("jenis_subjek") == "badan_hukum",
        "bh_kedudukan": bh.get("kedudukan", ""),
        "bh_akta_nomor": bh.get("akta_nomor", ""),
        "bh_akta_tanggal": util.tanggal_panjang(bh.get("akta_tanggal")),
        "bh_notaris": bh.get("notaris", ""),
        "bh_pengesahan_nomor": bh.get("pengesahan_nomor", ""),
        "bh_pengesahan_tanggal": util.tanggal_panjang(bh.get("pengesahan_tanggal")),

        # --- jenis hak
        "nama_hak": hak["nama"],
        "nama_hak_kapital": hak["nama"].upper(),
        "kode_hak": hak["kode"],
        "jenis_kegiatan": d["jenis_kegiatan"],
        "ada_jangka_waktu": bool(hak["ada_jangka_waktu"]),
        "jangka_tahun": jangka or "",
        "jangka_terbilang": util.terbilang(jangka) if jangka else "",
        "jangka_berakhir": jangka_berakhir,
        "uang_pemasukan": util.format_angka(sk_.get("uang_pemasukan")) if sk_.get("uang_pemasukan") else "",

        # --- wilayah
        "jenis_desa": d["desa"].get("jenis", ""),
        "nama_desa": d["desa"].get("nama", ""),
        "kecamatan": d["desa"].get("kecamatan", ""),
        "jabatan_pejabat": d["desa"].get("jabatan_pejabat", ""),
        "nama_pejabat": d["desa"].get("nama_pejabat", ""),

        # --- bidang tanah
        "nomor_pbt": t.get("nomor_pbt", ""),
        "tanggal_pbt": util.tanggal_panjang(t.get("tanggal_pbt")),
        "nib": t.get("nib", ""),
        "luas_teks": util.luas_teks(luas_pbt),
        # luas_teks sudah memuat terbilang; slot lama «Luas Text» dikosongkan
        # supaya tidak tercetak dua kali seperti pada template asli.
        "luas_terbilang": "",
        "luas_terbilang_saja": util.terbilang(luas_pbt) if luas_pbt else "",
        "luas_surat_teks": util.luas_kira(luas_surat),
        "selisih_teks": tulis_selisih or _kalimat_selisih(selisih, luas_pbt, luas_surat,
                                                          _teks_dokumen(dok_selisih)),
        "ada_selisih": bool(tulis_selisih or selisih),
        "batas_utara": t.get("batas_utara", ""),
        "batas_timur": t.get("batas_timur", ""),
        "batas_selatan": t.get("batas_selatan", ""),
        "batas_barat": t.get("batas_barat", ""),
        "penggunaan_sekarang": t.get("penggunaan_sekarang", ""),
        "rencana_penggunaan": t.get("rencana_penggunaan", ""),
        "rtrw": t.get("rtrw", ""),
        "kesesuaian": (t.get("kesesuaian") or "").strip(),
        "tanggal_peta_analisis": util.tanggal_panjang(t.get("tanggal_peta_analisis")),

        # --- tanggal
        "tanggal_permohonan": util.tanggal_panjang(d.get("tanggal_permohonan")),
        "tgl_bap": util.tanggal_panjang(tgl_bap),
        "tgl_bap_pendek": util.tanggal_pendek(tgl_bap),
        "hari_bap": util.nama_hari(tgl_bap),
        "tgl_bap_terbilang": util.hari_terbilang(tgl_bap),
        "bulan_bap": util.nama_bulan(tgl_bap),
        "tahun_bap_terbilang": util.tahun_terbilang(tgl_bap),
        "nomor_risalah": ris.get("nomor", ""),
        "tgl_risalah": util.tanggal_panjang(tgl_ris),
        "tgl_risalah_pendek": util.tanggal_pendek(tgl_ris),
        "hari_risalah": util.nama_hari(tgl_ris),
        "tgl_risalah_terbilang": util.hari_terbilang(tgl_ris),
        "bulan_risalah": util.nama_bulan(tgl_ris),
        "tahun_risalah_terbilang": util.tahun_terbilang(tgl_ris),
        "nomor_sk": sk_.get("nomor", ""),
        "tgl_sk": util.tanggal_panjang(tgl_sk),
        "validasi_pph": sk_.get("validasi_pph", ""),
        "pejabat_nama": sk_.get("pejabat_nama", ""),
        "pejabat_nip": sk_.get("pejabat_nip", ""),

        # --- panitia
        "panitia_nomor_sk": d["panitia"].get("nomor_sk", ""),
        "panitia_tanggal_sk": util.tanggal_panjang(d["panitia"].get("tanggal_sk")),
        "panitia": panitia,
        "panitia_jumlah": len(panitia),
        "panitia_jumlah_terbilang": util.terbilang(len(panitia)) if panitia else "",
        "kasi_pgt_nama": _anggota_peran(d, "Penataan"),
        "kasi_pgt_nip": _anggota_nip(d, "Penataan"),

        # --- daftar berulang
        "riwayat": [{"uraian": r["uraian"], "dokumen_bukti": r["dokumen_bukti"] or ""}
                    for r in d["riwayat"]],
        # 'sppf' dan 'kuasa' dicetak template lewat penandanya sendiri; kalau ikut
        # masuk daftar ini, DATA PENDUKUNG memuatnya dua kali.
        "dokumen": [{"uraian": _uraian_dokumen(r, "Asli")} for r in d["dokumen"]
                    if r["id"] not in khusus],
        "pendapat": d["pendapat"],
        "penguasaan_fisik": tulis_pf or _penguasaan_fisik(teks_sppf),
        "sppf": teks_sppf,
    }
    # klausa bersyarat
    for slot in ("telaah_subjek", "uraian_jangka", "diktum_uang_pemasukan", "asal_tanah_judul"):
        isi = pilih_klausa(k, slot, d)
        for nama, nilai in list(c.items()):
            if isinstance(nilai, str):
                isi = isi.replace("{{" + nama + "}}", nilai)
        c[slot] = isi
    return c, d


def _kalimat_selisih(selisih, luas_pbt, luas_surat, surat=""):
    """Kalimat selisih luas, susunannya sama dengan kolom «selisih luas» pada Excel lama."""
    if not selisih:
        return ""
    n = util.luas_teks(abs(int(selisih)))
    kal = (f"Bahwa terdapat selisih seluas {n} antara jumlah keseluruhan luas tanah yang "
           f"tercantum pada bukti surat tanah seluas {util.luas_kira(luas_surat)}, dengan hasil "
           f"pengukuran kadastral seluas {util.luas_teks(luas_pbt)}")
    if surat:
        kal += (f". Bahwa terhadap selisih luas {n} tidak terdapat keberatan dari pemohon "
                f"dikuatkan dengan {surat}")
    return kal


def _kunci_nama(nama):
    """Nama untuk dicocokkan: tanpa gelar-gelaran, spasi, dan tanda baca."""
    return "".join(ch for ch in (nama or "").upper() if ch.isalnum())


def _daftar_panitia(d):
    """Susunan Panitia A siap cetak, satu baris per anggota.

    Diambil dari SK susunan panitia yang dipilih pada berkas (`ref_panitia_anggota`),
    ditambah kepala desa/lurah. Pendapat yang diketik petugas di berkas dipakai lebih
    dulu; kalau dikosongkan, dipakai pendapat baku dari susunan panitianya.
    """
    pendapat = {}
    for pd in d.get("pendapat", []):
        pendapat.setdefault(_kunci_nama(pd.get("nama")), pd)
    kantor = (d.get("pengaturan") or {}).get("kantor_nama", "")

    hasil = []
    for a in d.get("panitia_anggota", []):
        pd = pendapat.get(_kunci_nama(a.get("nama"))) or {}
        jabatan = (a.get("jabatan") or "").strip()
        instansi = "" if a.get("dari_desa") else kantor
        peran = (pd.get("peran") or a.get("peran") or "").strip()
        lengkap = " ".join(x for x in (jabatan, instansi) if x)
        if peran:
            lengkap = f"{lengkap}, sebagai {peran}" if lengkap else f"Sebagai {peran}"
        hasil.append({
            "nama": a.get("nama") or "",
            "nip": (a.get("nip") or "").strip(),
            "jabatan": jabatan,
            "instansi": instansi,
            "peran": peran,
            "jabatan_lengkap": lengkap,
            "pendapat": ((pd.get("alasan") or "").strip()
                         or (a.get("pendapat_baku") or "").strip()),
            "setuju": bool(pd.get("setuju", 1)),
            "menandatangani": bool(pd.get("menandatangani", 1)),
            "diwakili_oleh": pd.get("diwakili_oleh") or "",
        })
    return hasil


def _anggota_peran(d, kata):
    for a in d["panitia_anggota"]:
        if kata.lower() in (a.get("jabatan") or "").lower():
            return a["nama"]
    return ""


def _anggota_nip(d, kata):
    for a in d["panitia_anggota"]:
        if kata.lower() in (a.get("jabatan") or "").lower():
            return a.get("nip") or ""
    return ""


DASAR_PENGUASAAN_FISIK = (
    "Bahwa bidang tanah yang dimohon sampai dengan saat ini dikuasai terus menerus oleh "
    "pemohon, belum bersertipikat dan tidak dijadikan ataupun menjadi jaminan sesuatu hutang "
    "serta tidak dalam sengketa")


def _uraian_dokumen(r, bawaan=""):
    """Uraian dokumen siap cetak. `bawaan` dipakai bila keaslian belum dicatat —
    daftar DATA PENDUKUNG selalu diawali keterangan asli/fotokopi, kalimat telaah tidak."""
    keaslian = (r["keaslian"] or "").strip() or bawaan
    return ((keaslian + " " if keaslian else "") + (r["uraian"] or "")).strip()


def _dokumen_khusus(d, kategori, frasa=""):
    """Baris dokumen pendukung berkategori `kategori`. `frasa` jadi cadangan untuk
    berkas yang kategorinya belum ditandai."""
    for r in d["dokumen"]:
        if (r.get("kategori") or "") == kategori:
            return r
    for r in d["dokumen"]:
        if frasa and frasa in (r["uraian"] or "").lower():
            return r
    return None


def _teks_dokumen(r):
    """Uraian tanpa keterangan asli/fotokopi — dipakai di tengah kalimat telaah."""
    return (r["uraian"] or "").strip() if r else ""


# ------------------------------------------------ akta ikrar & pengesahan Nazhir
NAMA_AKTA = {"AIW": "Akta Ikrar Wakaf", "APAIW": "Akta Pengganti Akta Ikrar Wakaf"}


def _ada_rincian(r):
    return bool(r) and any((r.get(x) or "").strip() for x in db.KOLOM_RINCIAN
                           if x != "jenis")


def _nama_akta(r):
    return NAMA_AKTA.get((r.get("jenis") or "").upper(), NAMA_AKTA["AIW"])


def _jabatan_ppaiw(r, akta="Akta Ikrar Wakaf"):
    wil = (r.get("wilayah_pejabat") or "").strip()
    return f"Pejabat Pembuat {akta}" + (f" {wil}" if wil else "")


def _oleh(r, akta="Akta Ikrar Wakaf"):
    """«Nama selaku Pejabat Pembuat AIW Kecamatan X» — isian «..../ Pejabat ...» Permen."""
    nama = (r.get("pejabat") or "").strip()
    jabatan = _jabatan_ppaiw(r, akta)
    return f"{nama} selaku {jabatan}" if nama else jabatan


def _gabung(*bagian):
    return " ".join(b for b in bagian if b)


def frasa_akta_ikrar(r):
    """Sambungan «... yang diwakafkan kepada Nazhir sesuai ___» pada Menimbang huruf b:
    AIW/APAIW tanggal .... Nomor .... yang dibuat oleh ..../Pejabat Pembuat AIW/APAIW ....
    Berkas lama yang hanya punya uraian bebas tetap memakai uraian itu."""
    if not _ada_rincian(r):
        return _teks_dokumen(r)
    akta = _nama_akta(r)
    tgl = util.tanggal_panjang(r.get("tanggal"))
    nomor = (r.get("nomor") or "").strip()
    return _gabung(akta, f"tanggal {tgl}" if tgl else "", f"Nomor {nomor}" if nomor else "",
                   "yang dibuat oleh " + _oleh(r, akta))


def frasa_pengesahan_nazhir(r):
    """Sambungan «Nazhir tanah wakaf tersebut telah disahkan ___» pada huruf c:
    oleh ..../Pejabat AIW/APAIW tanggal .... Nomor ...."""
    if not _ada_rincian(r):
        teks = _teks_dokumen(r)
        return f"sesuai {teks}" if teks else ""
    tgl = util.tanggal_panjang(r.get("tanggal"))
    nomor = (r.get("nomor") or "").strip()
    return _gabung("oleh " + _oleh(r), f"tanggal {tgl}" if tgl else "",
                   f"Nomor {nomor}" if nomor else "")


def tebak_rincian(r):
    """Rincian yang bisa dibaca dari uraian bebas berkas lama (nomor, tanggal, jenis
    akta) — hanya untuk mengisi awal formulir; tersimpan setelah petugas menekan Simpan."""
    if not r or _ada_rincian(r):
        return {}
    teks = r.get("uraian_tulis") or r.get("uraian") or ""
    hasil = {}
    m = re.search(r"\b(?:nomor|no\.)\s*:?\s*([A-Za-z0-9][^\s,;]*)", teks, re.I)
    if m:
        hasil["nomor"] = m.group(1).rstrip(".")
    bulan = "|".join(util.BULAN)
    m = re.search(rf"\b(\d{{1,2}})\s+({bulan})\s+(\d{{4}})\b", teks, re.I)
    if m:
        b = [x.lower() for x in util.BULAN].index(m.group(2).lower()) + 1
        hasil["tanggal"] = f"{int(m.group(3)):04d}-{b:02d}-{int(m.group(1)):02d}"
    if r.get("kategori") == "akta_ikrar" and "pengganti" in teks.lower():
        hasil["jenis"] = "APAIW"
    return hasil


def uraian_rincian(r):
    """Uraian DATA PENDUKUNG yang disusun dari rincian, bila petugas tidak mengetiknya."""
    if not _ada_rincian(r):
        return ""
    if r.get("kategori") == "akta_ikrar":
        return frasa_akta_ikrar(r)
    if r.get("kategori") == "pengesahan_nazhir":
        return "Surat Pengesahan Nazhir yang disahkan " + frasa_pengesahan_nazhir(r)
    return ""


def kalimat_otomatis(d):
    """Kalimat telaah yang dipakai bila isiannya dikosongkan. Dipakai formulir
    sebagai contoh isian, dan oleh impor untuk tahu mana yang tidak perlu disimpan."""
    t = d.get("tanah") or {}
    lp, ls = t.get("luas_pbt"), t.get("luas_surat")
    selisih = int(lp) - int(ls) if lp is not None and ls is not None else None
    return {
        "uraian_penguasaan_fisik": _penguasaan_fisik(
            _teks_dokumen(_dokumen_khusus(d, "sppf", "penguasaan fisik"))),
        "uraian_selisih_luas": _kalimat_selisih(
            selisih, lp, ls, _teks_dokumen(_dokumen_khusus(d, "selisih", "perbedaan luas"))),
    }


def _penguasaan_fisik(sppf):
    """Kolom «Surat Penguasaan Fisik» Excel lama = kalimat baku + rujukan SPPF."""
    if not sppf:
        return DASAR_PENGUASAAN_FISIK
    return f"{DASAR_PENGUASAAN_FISIK}, dimana hal ini sesuai dengan {sppf}"


# ------------------------------------------------------------- validasi
def periksa(k, berkas_id):
    """Daftar masalah sebelum dokumen boleh dicetak.
    Setiap butir: (tingkat, pesan). tingkat = 'galat' menghalangi cetak."""
    d = muat(k, berkas_id)
    if not d:
        return [("galat", "Berkas tidak ditemukan.")]
    m = []
    hak = d["hak"]
    penerima = penerima_hak(d)
    t = d["tanah"]
    ris, pem = d["risalah"], d["pemeriksaan"]

    # --- pihak
    if not penerima:
        m.append(("galat", "Belum ada pihak berperan pemohon atau penerima hak."))
    else:
        subjek = penerima.get("jenis_subjek") or "perorangan"
        if subjek not in [x.strip() for x in hak["subjek_boleh"].split(",")]:
            m.append(("galat", f"{hak['nama']} tidak dapat diberikan kepada subjek "
                               f"'{subjek}'. Dasar: {hak['dasar_subjek']}."))
        if subjek == "perorangan":
            nik = (penerima.get("nik") or "").strip()
            if not nik:
                m.append(("galat", "NIK penerima hak belum diisi."))
            elif not (nik.isdigit() and len(nik) == 16):
                m.append(("galat", f"NIK harus 16 digit angka, sekarang '{nik}'."))
            if not (penerima.get("jenis_kelamin") or "").strip():
                m.append(("peringatan", "Jenis kelamin belum diisi - sapaan Sdr./Sdri. tidak bisa ditentukan."))
        if subjek == "badan_hukum" and not penerima.get("badan_hukum", {}).get("akta_nomor"):
            m.append(("galat", "Pemohon badan hukum: akta pendirian belum diisi "
                               "(Pasal 54 ayat (1) huruf a angka 2)."))

    # --- wakaf: Nazhir dan Wakif (UU 41/2004, PP 42/2006, Permen ATR/BPN 2/2017)
    if wakaf(d):
        m += _periksa_wakaf(d)

    # --- kegiatan yang sah untuk jenis hak ini
    if d["jenis_kegiatan"] not in [x.strip() for x in hak["kegiatan_boleh"].split(",")]:
        m.append(("galat", f"Kegiatan '{d['jenis_kegiatan']}' tidak berlaku untuk {hak['nama']}."))

    # --- bidang tanah
    if not t.get("desa_id"):
        m.append(("galat", "Desa/kelurahan letak tanah belum dipilih."))
    if not t.get("luas_pbt"):
        m.append(("galat", "Luas hasil pengukuran (Peta Bidang Tanah) belum diisi."))
    if not t.get("nomor_pbt") or not t.get("nib"):
        m.append(("galat", "Nomor Peta Bidang Tanah dan NIB wajib diisi."))
    kosong = [n for n in ("batas_utara", "batas_timur", "batas_selatan", "batas_barat")
              if not (t.get(n) or "").strip()]
    if kosong:
        m.append(("peringatan", "Batas belum lengkap: " + ", ".join(x.replace("_", " ") for x in kosong)))
    if t.get("luas_pbt") and t.get("luas_surat"):
        if int(t["luas_pbt"]) != int(t["luas_surat"]):
            ada = any("perbedaan luas" in (r["uraian"] or "").lower() or
                      "selisih" in (r["uraian"] or "").lower() for r in d["dokumen"])
            if not ada:
                m.append(("peringatan", "Ada selisih luas tetapi Surat Pernyataan Perbedaan Luas "
                                        "belum tercatat di dokumen pendukung."))

    # --- asal tanah
    if d["jenis_kegiatan"] == "baru" and not d["riwayat"]:
        m.append(("galat", "Riwayat perolehan tanah belum diisi."))
    if d["jenis_kegiatan"] != "baru" and not d["hak_asal"].get("nomor_sertipikat"):
        m.append(("galat", f"Kegiatan '{d['jenis_kegiatan']}' memerlukan data hak asal "
                           "(nomor sertipikat) - Pasal 159 ayat (1) huruf b."))

    # --- jangka waktu (Pasal 139 ayat (4))
    if hak["ada_jangka_waktu"]:
        if not ris.get("jangka_waktu_tahun"):
            m.append(("galat", f"{hak['nama']} wajib menyebut jangka waktu dalam kesimpulan "
                               "Risalah (Pasal 139 ayat (4) Permen 18/2021)."))
        elif hak["jangka_maks"] and int(ris["jangka_waktu_tahun"]) > int(hak["jangka_maks"]):
            m.append(("galat", f"Jangka waktu {ris['jangka_waktu_tahun']} tahun melebihi batas "
                               f"{hak['jangka_maks']} tahun untuk {hak['nama']}."))

    # --- panitia (Pasal 138 ayat (1))
    n = len(d["panitia_anggota"])
    if not d["pemeriksaan"].get("panitia_id"):
        m.append(("galat", "Susunan Panitia A belum dipilih."))
    elif n == 0:
        m.append(("galat", "Susunan Panitia A kosong."))
    else:
        if n < 3:
            m.append(("galat", f"Anggota Panitia A hanya {n} orang, paling kurang 3 "
                               "(Pasal 138 ayat (1))."))
        if n % 2 == 0:
            m.append(("galat", f"Jumlah anggota Panitia A harus ganjil, sekarang {n} "
                               "(Pasal 138 ayat (1))."))

    # --- foto lapangan: dilampirkan BAP di halaman tersendiri
    n_foto = sum(1 for f in d["foto"] if f["ada"])
    if n_foto < foto.MINIMAL:
        m.append(("galat", f"Foto lapangan baru {n_foto}, paling sedikit {foto.MINIMAL} — "
                           "dilampirkan di halaman terakhir BAP. Unggah di tab Foto lapangan."))

    # --- urutan tanggal
    tp = util.tanggal(d.get("tanggal_permohonan"))
    tb = util.tanggal(pem.get("tanggal_bap"))
    tr = util.tanggal(ris.get("tanggal"))
    ts = util.tanggal(d["sk"].get("tanggal"))
    for a, b, na, nb in ((tp, tb, "permohonan", "BAP"), (tb, tr, "BAP", "Risalah"),
                         (tr, ts, "Risalah", "SK")):
        if a and b and b < a:
            m.append(("galat", f"Tanggal {nb} lebih awal dari tanggal {na}."))

    # --- tenggat 14 hari kerja (Pasal 136 ayat (1))
    tt = util.tanggal(pem.get("tanggal_surat_tugas"))
    if not tt:
        m.append(("peringatan", "Tanggal surat tugas belum diisi - tenggat 14 hari kerja "
                                "Panitia A tidak bisa dipantau (Pasal 136)."))
    elif tr:
        hk = util.hari_kerja_antara(tt, tr)
        if hk is not None and hk > 14:
            m.append(("peringatan", f"Risalah selesai {hk} hari kerja setelah surat tugas, "
                                    "melewati tenggat 14 hari kerja (Pasal 136 ayat (1))."))

    # --- tanggal yang dibutuhkan untuk penomoran
    if not util.tanggal(ris.get("tanggal")):
        m.append(("peringatan", "Tanggal Risalah belum diisi — Risalah belum bisa dicetak "
                                "karena nomornya belum bisa diberikan."))
    if (ris.get("kesimpulan") or "dikabulkan") == "dikabulkan" and             not util.tanggal(d["sk"].get("tanggal")):
        m.append(("peringatan", "Tanggal SK belum diisi — SK belum bisa dicetak karena "
                                "nomornya belum bisa diberikan."))

    # --- pendapat anggota (Pasal 139 ayat (6) & (7))
    for p in d["pendapat"]:
        if not p["setuju"] and not (p["alasan"] or "").strip():
            m.append(("galat", f"Anggota {p['nama']} menyatakan tidak setuju tetapi alasannya "
                               "belum diisi (Pasal 139 ayat (4))."))
        if not p["menandatangani"] and not (p["alasan"] or "").strip():
            m.append(("galat", f"Anggota {p['nama']} tidak menandatangani; catatan alasan wajib "
                               "dibuat (Pasal 139 ayat (7))."))

    # --- kelengkapan dokumen wajib
    kode = d["jenis_hak_dimohon"]
    syarat = k.execute(
        "SELECT * FROM ref_dokumen_syarat WHERE wajib=1 AND (jenis_hak='*' OR jenis_hak=?) "
        "AND (kegiatan='*' OR kegiatan=?) ORDER BY urut", (kode, d["jenis_kegiatan"])).fetchall()
    subjek = penerima.get("jenis_subjek") or "perorangan"
    punya = " | ".join((r["uraian"] or "").lower() for r in d["dokumen"])
    for s in syarat:
        if s["kategori"] == "badan_hukum" and subjek != "badan_hukum":
            continue
        kunci = _kata_kunci(s["nama"])
        if not any(x in punya for x in kunci):
            m.append(("peringatan", f"Dokumen wajib belum tercatat: {s['nama']} ({s['dasar']})."))
    return m


def _periksa_wakaf(d):
    """Pemeriksaan yang hanya berlaku untuk berkas tanah wakaf."""
    m = []
    nazhir = daftar_nazhir(d)
    subjek = (penerima_hak(d).get("jenis_subjek") or "perorangan")
    if not nazhir:
        m.append(("galat", "Nazhir belum diisi — penerima hak wakaf adalah Nazhir."))
    elif subjek == "perorangan" and len(nazhir) < 3:
        m.append(("galat", f"Nazhir perseorangan hanya {len(nazhir)} orang, paling sedikit 3 "
                           "(Pasal 4 ayat (2) PP 42/2006). Tambahkan di tab Pihak."))
    for n in nazhir[1:]:
        nik = (n.get("nik") or "").strip()
        if nik and not (nik.isdigit() and len(nik) == 16):
            m.append(("galat", f"NIK Nazhir {n.get('nama')} harus 16 digit angka, sekarang '{nik}'."))
        elif not nik:
            m.append(("peringatan", f"NIK Nazhir {n.get('nama')} belum diisi — "
                                    "Risalah mencetaknya per orang."))
        if not (n.get("ttl") or "").strip():
            m.append(("peringatan", f"Tempat/tanggal lahir Nazhir {n.get('nama')} belum diisi."))
    if not daftar_peran(d, "wakif", "pemilik_sebelumnya"):
        m.append(("galat", "Wakif belum diisi — SK menyebut siapa yang mewakafkan tanahnya."))
    if not _dokumen_khusus(d, "akta_ikrar", "ikrar wakaf"):
        m.append(("galat", "Akta Ikrar Wakaf belum diisi (Pasal 32 UU 41/2004) — "
                           "isi di tab Dokumen."))
    if not _dokumen_khusus(d, "pengesahan_nazhir", "pengesahan naz"):
        m.append(("peringatan", "Surat Pengesahan Nazhir dari PPAIW belum tercatat "
                                "(Pasal 14 PP 42/2006)."))
    for kategori, judul in (("akta_ikrar", "Akta Ikrar Wakaf"),
                            ("pengesahan_nazhir", "Pengesahan Nazhir")):
        r = _dokumen_khusus(d, kategori)
        if not r:
            continue
        if not _ada_rincian(r):
            m.append(("peringatan", f"{judul} masih berupa uraian bebas — isi nomor, tanggal, "
                                    "dan PPAIW-nya di tab Dokumen agar Menimbang SK sesuai "
                                    "format Permen ATR/BPN 2/2017."))
            continue
        kurang = [label for kolom, label, _ in db.RINCIAN_BAKU[kategori]
                  if kolom != "jenis" and not (r.get(kolom) or "").strip()]
        if kurang:
            m.append(("peringatan", f"{judul}: {', '.join(kurang).lower()} belum diisi."))
    if d["risalah"].get("jangka_waktu_tahun"):
        m.append(("peringatan", "Hak Wakaf tidak berjangka waktu — isian jangka waktu "
                                "pada Risalah sebaiknya dikosongkan."))
    return m


def _kata_kunci(nama):
    n = nama.lower()
    for frasa in ("surat permohonan", "penguasaan fisik", "peta bidang", "peta analisis",
                  "tanda batas", "akta pendirian", "nomor induk berusaha", "sertipikat",
                  # wakaf: dicocokkan sependek mungkin karena ejaannya beragam
                  # di berkas lama ("Akta Ikra Wakaf", "Pengesahan Nazir")
                  "akta ikra", "pengesahan naz", "kesediaan menjadi naz",
                  "kartu keluarga", "alas hak"):
        if frasa in n:
            return [frasa]
    return [n[:22]]


# ------------------------------------------------- katalog penanda template
def konteks_contoh(k):
    """Konteks satu berkas nyata, untuk halaman Template.

    Dipakai dua hal: mendaftar penanda yang tersedia beserta contoh nilainya,
    dan menguji apakah template yang baru diunggah bisa dirakit. Berkas yang
    datanya belum lengkap dilewati, dicoba berkas berikutnya.
    """
    for r in k.execute("SELECT id FROM berkas ORDER BY id DESC LIMIT 10"):
        try:
            c, _ = bangun(k, r["id"])
            return c, r["id"]
        except Exception:                                          # noqa: BLE001
            continue
    return {}, None


# kolom daftar berulang yang tetap ada walau berkas contohnya belum mengisinya
KOLOM_DAFTAR = {
    "nazhir": ["nama", "nik", "ttl", "alamat", "pekerjaan"],
    "wakif": ["nama", "nik", "ttl", "alamat", "pekerjaan"],
    "riwayat": ["uraian", "dokumen_bukti"],
    "dokumen": ["uraian"],
    "pendapat": ["nama", "peran", "alasan", "diwakili_oleh"],
    "panitia": ["nama", "nip", "jabatan", "jabatan_lengkap", "peran", "pendapat"],
}


def katalog_penanda(c):
    """Penanda yang tersedia: [(penanda, keterangan, contoh), ...] siap ditampilkan."""
    hasil = []
    for nama in sorted(c):
        nilai = c[nama]
        if isinstance(nilai, (list, tuple)):
            kolom = sorted(nilai[0].keys()) if nilai and isinstance(nilai[0], dict) else []
            kolom = kolom or KOLOM_DAFTAR.get(nama, [])
            hasil.append(("{{*" + nama + "." + (kolom[0] if kolom else "uraian") + "}}",
                          "daftar berulang · kolom: " + (", ".join(kolom + ["_akhir", "_nomor", "_huruf"])),
                          f"{len(nilai)} baris pada berkas contoh"))
        else:
            teks = "" if nilai is None else str(nilai)
            hasil.append(("{{" + nama + "}}", "nilai",
                          teks[:120] + ("…" if len(teks) > 120 else "")))
    return hasil
