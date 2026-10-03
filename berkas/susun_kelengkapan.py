# -*- coding: utf-8 -*-
"""Menyusun formulir daftar kelengkapan dari layar: tambah, ubah, geser, hapus.

Formulir resmi dipasang sekali dari db.KELENGKAPAN_BUTIR; sesudah itu jadi
milik kantor. Tiap Kantah punya kebiasaan sendiri — Peta Analisis Tata Ruang
diminta di loket, urutan surat ditukar supaya sama dengan map berkasnya — dan
itu diatur di sini, bukan dengan mengubah kode.

Dua aturan yang dijaga seluruh fungsi di bawah:

  * `urut` adalah urutan baca SELURUH formulir (pre-order), bukan urutan di
    antara saudara. pradaftar._rakit menyusun pohon dalam satu lintasan dan
    mengandalkan anak selalu datang sesudah induknya. Karena itu setiap
    perubahan susunan diakhiri _tulis_urut(), yang menomori ulang dari pohon.

  * Butir yang sudah pernah dijawab pradaftar tidak dihapus, hanya
    dinonaktifkan (aktif=0). Menghapusnya ikut menghapus jawaban lama lewat
    ON DELETE CASCADE, dan formulir berkas yang sudah diterima akan berubah.

Tidak ada HTTP di sini; yang masuk hanya request.form.
"""
from . import db, util

_i = util.ke_int
_n = util.teks_atau_none

SIFAT = [("butir", "Butir dicentang"), ("judul", "Kepala kelompok"),
         ("alternatif", "Salah satu (alternatif)")]
SUBJEK = [("*", "Semua pemohon"), ("perorangan", "Perorangan"),
          ("badan_hukum", "Badan hukum"), ("instansi", "Instansi")]
ASAL = [("*", "Semua asal tanah"), ("tanah_negara", "Tanah Negara"),
        ("hak_pengelolaan", "Hak Pengelolaan")]
KEGIATAN = [("*", "Semua kegiatan"), ("baru", "Pemberian hak baru"),
            ("perpanjangan", "Perpanjangan"), ("pembaruan", "Pembaruan"),
            ("peningkatan", "Peningkatan")]


class Galat(ValueError):
    """Isian yang ditolak; pesannya ditampilkan apa adanya kepada admin."""


# ------------------------------------------------------------------- baca
def formulir(k, fid):
    r = k.execute("SELECT * FROM ref_kelengkapan WHERE id=?", (fid,)).fetchone()
    return dict(r) if r else None


def muat(k, fid):
    """Formulir berikut SELURUH butirnya (termasuk yang nonaktif), sebagai
    daftar datar ber-`tingkat`, plus berapa pradaftar yang menjawab tiap butir."""
    f = formulir(k, fid)
    if not f:
        return None
    dipakai = {r["butir_id"]: r["n"] for r in k.execute(
        "SELECT j.butir_id, COUNT(*) AS n FROM pradaftar_jawab j "
        "JOIN ref_kelengkapan_butir b ON b.id=j.butir_id "
        "WHERE b.kelengkapan_id=? GROUP BY j.butir_id", (fid,))}
    akar = _pohon(k, fid)
    datar = []

    def telusur(simpul, tingkat, induk_mati):
        for n in simpul:
            n["tingkat"] = tingkat
            n["dipakai"] = dipakai.get(n["id"], 0)
            n["mati_warisan"] = induk_mati
            n["jml_anak"] = len(n["anak"])
            datar.append(n)
            telusur(n["anak"], tingkat + 1, induk_mati or not n["aktif"])

    telusur(akar, 0, False)
    f["butir"] = datar
    f["jml_pradaftar"] = k.execute(
        "SELECT COUNT(*) FROM pradaftar WHERE kelengkapan_id=?", (fid,)).fetchone()[0]
    return f


def _pohon(k, fid):
    simpul, akar = {}, []
    for r in k.execute("SELECT * FROM ref_kelengkapan_butir WHERE kelengkapan_id=? "
                       "ORDER BY urut, id", (fid,)):
        n = dict(r)
        n["anak"] = []
        simpul[n["id"]] = n
        induk = simpul.get(n["induk_id"])
        (induk["anak"] if induk else akar).append(n)
    return akar


def _cari(akar, bid):
    """(simpul, daftar saudaranya, induknya) — induk None berarti tingkat teratas."""
    def telusur(simpul, induk):
        for n in simpul:
            if n["id"] == bid:
                return n, simpul, induk
            hasil = telusur(n["anak"], n)
            if hasil:
                return hasil
        return None
    return telusur(akar, None)


def _keturunan(n):
    for a in n["anak"]:
        yield a
        yield from _keturunan(a)


# ------------------------------------------------------- tulis susunan
def _tulis_urut(k, fid, akar):
    """Tulis balik pohon: urut pre-order, induk_id, dan — bila formulirnya
    bernomor otomatis — penanda yang disusun ulang."""
    f = formulir(k, fid)
    if f and f.get("nomor_otomatis", 1):
        _nomori(akar)
    urut = 0

    def telusur(simpul, induk_id):
        nonlocal urut
        for n in simpul:
            urut += 1
            k.execute("UPDATE ref_kelengkapan_butir SET urut=?, induk_id=?, penanda=? "
                      "WHERE id=?", (urut, induk_id, n["penanda"], n["id"]))
            telusur(n["anak"], n["id"])

    telusur(akar, None)


def _huruf(i):
    """0 -> a, 25 -> z, 26 -> aa. Formulir yang anaknya lebih dari 26 jarang,
    tapi jangan sampai penandanya jadi tanda baca."""
    s = ""
    i += 1
    while i:
        i, sisa = divmod(i - 1, 26)
        s = chr(97 + sisa) + s
    return s


def _nomori(akar):
    """Susun ulang nomor dan huruf mengikuti kebiasaan lampiran Permen:

        tingkat teratas     1, 2, 3 … berurutan
        di bawahnya         a, b, c … berlanjut di seluruh cabang satu nomor,
                            termasuk melewati sub-kelompok ("Badan Hukum …"
                            yang tak berhuruf, lalu anaknya c sampai g)
        kepala sub-kelompok tanpa huruf

    Butir nonaktif tidak ikut dihitung dan penandanya dibiarkan.
    """
    nomor = 0
    for n in akar:
        if not n["aktif"]:
            continue
        nomor += 1
        n["penanda"] = str(nomor)
        huruf = 0
        for a in _keturunan(n):
            if not a["aktif"]:
                continue
            if a["sifat"] == "judul":
                a["penanda"] = ""
            else:
                a["penanda"] = _huruf(huruf)
                huruf += 1


def nomori(k, fid):
    """Nomori ulang sekarang juga, walau penomoran otomatisnya dimatikan."""
    akar = _pohon(k, fid)
    _nomori(akar)
    urut = 0

    def telusur(simpul):
        nonlocal urut
        for n in simpul:
            urut += 1
            k.execute("UPDATE ref_kelengkapan_butir SET penanda=?, urut=? WHERE id=?",
                      (n["penanda"], urut, n["id"]))
            telusur(n["anak"])

    telusur(akar)
    k.commit()


def geser(k, fid, bid, arah):
    """naik / turun di antara saudaranya; masuk = jadi anak terakhir saudara
    di atasnya; keluar = jadi saudara induknya, tepat sesudah induk itu."""
    akar = _pohon(k, fid)
    hasil = _cari(akar, bid)
    if not hasil:
        raise Galat("Butir itu bukan bagian formulir ini.")
    n, saudara, induk = hasil
    i = saudara.index(n)
    if arah == "naik":
        if i == 0:
            return
        saudara[i - 1], saudara[i] = saudara[i], saudara[i - 1]
    elif arah == "turun":
        if i == len(saudara) - 1:
            return
        saudara[i + 1], saudara[i] = saudara[i], saudara[i + 1]
    elif arah == "masuk":
        if i == 0:
            raise Galat("Butir paling atas tidak punya butir di atasnya untuk dimasuki.")
        saudara.pop(i)
        saudara[i - 1]["anak"].append(n)
    elif arah == "keluar":
        if induk is None:
            return
        saudara.pop(i)
        _, saudara_induk, _ = _cari(akar, induk["id"])
        saudara_induk.insert(saudara_induk.index(induk) + 1, n)
    else:
        raise Galat("Arah geser tidak dikenal.")
    _tulis_urut(k, fid, akar)
    k.commit()


def pindah_ke(k, fid, bid, sasaran_id, posisi):
    """Seret-lepas: taruh `bid` sebelum/sesudah `sasaran_id`, atau sebagai anak
    terakhirnya (posisi='dalam')."""
    akar = _pohon(k, fid)
    asal, sasaran = _cari(akar, bid), _cari(akar, sasaran_id)
    if not asal or not sasaran or bid == sasaran_id:
        raise Galat("Butir asal atau tujuannya tidak ditemukan.")
    n, saudara, _ = asal
    if sasaran_id in {x["id"] for x in _keturunan(n)}:
        raise Galat("Butir tidak bisa dipindah ke dalam anaknya sendiri.")
    saudara.remove(n)
    t, saudara_t, _ = _cari(akar, sasaran_id)
    if posisi == "dalam":
        t["anak"].append(n)
    else:
        saudara_t.insert(saudara_t.index(t) + (1 if posisi == "sesudah" else 0), n)
    _tulis_urut(k, fid, akar)
    k.commit()


# ------------------------------------------------------------ satu butir
def _pilihan(nilai, daftar, bawaan):
    return nilai if nilai in [x for x, _ in daftar] else bawaan


def simpan_butir(k, fid, f, bid=None):
    """Tambah (bid None) atau ubah satu butir. Kembalikan id-nya.

    Butir baru ditaruh sebagai anak terakhir `induk_id` — atau tepat sesudah
    butir `sesudah` bila disebut. Mengganti induk butir lama memindahkannya,
    berikut seluruh anaknya.
    """
    nama = (f.get("nama") or "").strip()
    if not nama:
        raise Galat("Bunyi butir tidak boleh kosong.")
    sifat = _pilihan(f.get("sifat"), SIFAT, "butir")
    nilai = {
        "nama": nama,
        "nama_dokumen": _n(f.get("nama_dokumen") or ""),
        "sifat": sifat,
        "wajib": 1 if f.get("wajib") else 0,
        "isian_bebas": 1 if (f.get("isian_bebas") and sifat != "judul") else 0,
        "jamak": 1 if (f.get("jamak") and sifat != "judul") else 0,
        "subjek": _pilihan(f.get("subjek"), SUBJEK, "*"),
        "asal_tanah": _pilihan(f.get("asal_tanah"), ASAL, "*"),
        "slot_baku": _n(f.get("slot_baku") or ""),
        "dasar": _n(f.get("dasar") or ""),
        "penanda": (f.get("penanda") or "").strip()[:8],
    }
    if nilai["slot_baku"] and nilai["slot_baku"] not in db.KATEGORI_BAKU:
        nilai["slot_baku"] = None

    akar = _pohon(k, fid)
    induk_id = _i(f.get("induk_id")) or None
    if induk_id and not _cari(akar, induk_id):
        raise Galat("Kelompok tujuan bukan bagian formulir ini.")

    kolom = list(nilai)
    if bid:
        hasil = _cari(akar, bid)
        if not hasil:
            raise Galat("Butir itu bukan bagian formulir ini.")
        n, saudara, induk = hasil
        if induk_id == bid or induk_id in {x["id"] for x in _keturunan(n)}:
            raise Galat("Butir tidak bisa dijadikan anak dari dirinya sendiri.")
        k.execute(f"UPDATE ref_kelengkapan_butir SET "
                  f"{', '.join(c + '=?' for c in kolom)} WHERE id=?",
                  [nilai[c] for c in kolom] + [bid])
        n.update(nilai)
        if (induk["id"] if induk else None) != induk_id:
            saudara.remove(n)
            tujuan = _cari(akar, induk_id)[0]["anak"] if induk_id else akar
            tujuan.append(n)
    else:
        bid = db.sisip_id(
            k, f"INSERT INTO ref_kelengkapan_butir (kelengkapan_id,induk_id,"
               f"{','.join(kolom)},urut) VALUES (?,?,{','.join('?' * len(kolom))},0)",
            [fid, induk_id] + [nilai[c] for c in kolom])
        n = dict(nilai, id=bid, induk_id=induk_id, aktif=1, anak=[])
        sesudah = _i(f.get("sesudah"))
        tempat = _cari(akar, sesudah) if sesudah else None
        if tempat and (tempat[2]["id"] if tempat[2] else None) == induk_id:
            tempat[1].insert(tempat[1].index(tempat[0]) + 1, n)
        else:
            (_cari(akar, induk_id)[0]["anak"] if induk_id else akar).append(n)
    _tulis_urut(k, fid, akar)
    k.commit()
    return bid


def hapus_butir(k, fid, bid):
    """Hapus butir berikut anaknya. Yang sudah pernah dijawab pradaftar hanya
    dinonaktifkan. Kembalikan 'hapus' atau 'nonaktif'."""
    akar = _pohon(k, fid)
    hasil = _cari(akar, bid)
    if not hasil:
        raise Galat("Butir itu bukan bagian formulir ini.")
    n, saudara, _ = hasil
    ids = [bid] + [x["id"] for x in _keturunan(n)]
    tanya = ",".join("?" * len(ids))
    dijawab = k.execute(f"SELECT COUNT(*) FROM pradaftar_jawab WHERE butir_id IN ({tanya})",
                        ids).fetchone()[0]
    if dijawab:
        k.execute(f"UPDATE ref_kelengkapan_butir SET aktif=0 WHERE id IN ({tanya})", ids)
        for x in [n] + list(_keturunan(n)):
            x["aktif"] = 0
        hasil = "nonaktif"
    else:
        k.execute(f"DELETE FROM ref_catatan_koreksi WHERE butir_id IN ({tanya})", ids)
        k.execute(f"DELETE FROM ref_kelengkapan_butir WHERE id IN ({tanya})", ids)
        saudara.remove(n)
        hasil = "hapus"
    _tulis_urut(k, fid, akar)
    k.commit()
    return hasil


def pulihkan_butir(k, fid, bid):
    """Aktifkan lagi butir berikut anaknya, dan induknya bila ikut mati."""
    akar = _pohon(k, fid)
    hasil = _cari(akar, bid)
    if not hasil:
        raise Galat("Butir itu bukan bagian formulir ini.")
    n = hasil[0]
    ids = [bid] + [x["id"] for x in _keturunan(n)]
    x = n
    while x.get("induk_id"):
        ids.append(x["induk_id"])
        x = _cari(akar, x["induk_id"])[0]
    tanya = ",".join("?" * len(ids))
    k.execute(f"UPDATE ref_kelengkapan_butir SET aktif=1 WHERE id IN ({tanya})", ids)
    k.commit()
    _tulis_urut(k, fid, _pohon(k, fid))
    k.commit()


# -------------------------------------------------------------- formulir
def simpan_formulir(k, f, fid=None):
    """Kepala formulir. Formulir baru boleh menyalin seluruh butir formulir lain.
    Kembalikan id-nya."""
    judul = (f.get("judul") or "").strip()
    kode = (f.get("kode") or "").strip().upper()
    if not judul or not kode:
        raise Galat("Kode dan judul formulir wajib diisi.")
    jenis_hak = (f.get("jenis_hak") or "*").strip() or "*"
    if jenis_hak != "*" and not k.execute(
            "SELECT 1 FROM ref_jenis_hak WHERE kode=?", (jenis_hak,)).fetchone():
        raise Galat("Jenis hak itu tidak dikenal.")
    bentrok = k.execute("SELECT id FROM ref_kelengkapan WHERE kode=? AND id<>?",
                        (kode, fid or 0)).fetchone()
    if bentrok:
        raise Galat(f"Kode {kode} sudah dipakai formulir lain.")
    nilai = (kode, judul, jenis_hak, _pilihan(f.get("kegiatan"), KEGIATAN, "*"),
             _n(f.get("dasar") or ""), 1 if f.get("aktif") else 0,
             1 if f.get("nomor_otomatis") else 0)
    if fid:
        k.execute("UPDATE ref_kelengkapan SET kode=?, judul=?, jenis_hak=?, kegiatan=?, "
                  "dasar=?, aktif=?, nomor_otomatis=? WHERE id=?", nilai + (fid,))
        k.commit()
        return fid

    asal = formulir(k, _i(f.get("salin_dari"))) if f.get("salin_dari") else None
    urut = k.execute("SELECT COALESCE(MAX(urut),0)+1 FROM ref_kelengkapan").fetchone()[0]
    fid = db.sisip_id(
        k, "INSERT INTO ref_kelengkapan (kode,judul,jenis_hak,kegiatan,dasar,aktif,"
           "nomor_otomatis,varian_template,urut) VALUES (?,?,?,?,?,?,?,?,?)",
        nilai + ((asal or {}).get("varian_template") or "", urut))
    if asal:
        _salin_butir(k, asal["id"], fid)
    k.commit()
    return fid


def _salin_butir(k, dari, ke):
    """Salin butir aktif satu formulir ke formulir lain, induknya dipetakan ulang."""
    peta = {}
    kolom = ("penanda,nama,nama_dokumen,sifat,wajib,isian_bebas,subjek,asal_tanah,"
             "slot_baku,syarat_id,dasar,jamak,urut")
    for r in k.execute(f"SELECT id,induk_id,{kolom} FROM ref_kelengkapan_butir "
                       f"WHERE kelengkapan_id=? AND aktif=1 ORDER BY urut, id",
                       (dari,)).fetchall():
        if r["induk_id"] and r["induk_id"] not in peta:
            continue                       # induknya nonaktif: ikut tertinggal
        peta[r["id"]] = db.sisip_id(
            k, f"INSERT INTO ref_kelengkapan_butir (kelengkapan_id,induk_id,{kolom}) "
               f"VALUES (?,?,{','.join('?' * 13)})",
            [ke, peta.get(r["induk_id"])] + [r[c] for c in kolom.split(",")])


def hapus_formulir(k, fid):
    """Formulir yang sudah dipakai pradaftar hanya dinonaktifkan."""
    dipakai = k.execute("SELECT COUNT(*) FROM pradaftar WHERE kelengkapan_id=?",
                        (fid,)).fetchone()[0]
    if dipakai:
        k.execute("UPDATE ref_kelengkapan SET aktif=0 WHERE id=?", (fid,))
        k.commit()
        return "nonaktif"
    k.execute("DELETE FROM ref_catatan_koreksi WHERE butir_id IN "
              "(SELECT id FROM ref_kelengkapan_butir WHERE kelengkapan_id=?)", (fid,))
    k.execute("DELETE FROM ref_kelengkapan_butir WHERE kelengkapan_id=?", (fid,))
    k.execute("DELETE FROM ref_kelengkapan WHERE id=?", (fid,))
    k.commit()
    return "hapus"
