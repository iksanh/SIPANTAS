# -*- coding: utf-8 -*-
"""Pradaftar: kelengkapan berkas diperiksa di loket, sebelum berkas didaftarkan.

Alurnya satu arah:

    pemohon datang -> pradaftar diisi -> centang daftar kelengkapan
      -> lengkap?  ya  -> terima() -> berkas, lalu Panitia A seperti biasa
                   tidak -> surat pengembalian, pemohon melengkapi, datang lagi

Sengaja bukan tahap di dalam `berkas`: permohonan yang belum lengkap tidak
boleh memakan nomor berkas, dan seluruh pemeriksaan Panitia A di
dokumen/konteks.py tidak berlaku untuk berkas yang belum ada.

Yang **tidak** disimpan di sini: lengkap atau kurangnya sebuah pradaftar.
Itu dihitung ulang dari jawabannya tiap kali dibutuhkan (`pohon`, `kurang`),
mengikuti aturan yang sama dengan nilai turunan lain di aplikasi ini — kalau
disimpan, akan ada baris bertanda "lengkap" yang jawabannya sudah berubah.

Tidak ada HTTP di sini; yang masuk hanya request.form.
"""
import datetime as dt

from . import db, izin, util

_n = util.teks_atau_none
_i = util.ke_int

# Jawaban per butir. Formulir cetaknya hanya punya dua kolom (Ada / Tidak Ada),
# tapi layar perlu membedakan "tidak ada" dari "tidak berlaku" — grup Badan
# Hukum pada pemohon perorangan, misalnya. TIDAK_BERLAKU tercetak sebagai dua
# kolom kosong, sesuai catatan "coret yang tidak perlu" pada formulirnya.
#
# KOREKSI: suratnya dibawa tetapi ada yang salah — belum dilegalisir, NIK-nya
# beda, sudah kedaluwarsa. Dicetak di kolom Ada (suratnya memang ada), tetapi
# menahan penerimaan seperti butir yang kurang, dan disertai catatan apa yang
# harus diperbaiki. Menyebutnya "Tidak Ada" membuat surat pengembalian meminta
# surat yang sebenarnya sudah dibawa pemohon.
TIDAK_ADA, ADA, TIDAK_BERLAKU, KOREKSI = 0, 1, 2, 3

STATUS = [("baru", "Sedang diproses"), ("diterima", "Diterima di loket"),
          ("dikembalikan", "Dikembalikan ke pemohon"), ("batal", "Batal")]
# Status yang tidak boleh disunting lagi: berkasnya sudah terbit atau urusannya
# sudah ditutup. Halaman tetap bisa dibuka, hanya baca-saja.
STATUS_KUNCI = ("diterima", "batal")


# ------------------------------------------------------------------ daftar
def daftar(k, pengguna):
    """Pradaftar yang boleh dilihat pengguna ini, berikut angka ringkasannya.

    Kelengkapan tiap baris ikut dihitung di sini — satu kueri jawaban untuk
    semua baris sekaligus, bukan satu kueri per baris.
    """
    saring, parameter = ("", ()) if izin.admin(pengguna) else (
        "WHERE p.dibuat_oleh IS NULL OR p.dibuat_oleh = ?", (pengguna["id"],))
    baris = [dict(r) for r in k.execute(f"""
        SELECT p.*, d.nama AS desa, c.nama AS kecamatan, u.nama AS pemilik,
               h.nama AS nama_hak, f.kode AS kode_formulir
        FROM pradaftar p
        LEFT JOIN ref_desa d ON d.id=p.desa_id
        LEFT JOIN ref_kecamatan c ON c.id=d.kecamatan_id
        LEFT JOIN pengguna u ON u.id=p.dibuat_oleh
        LEFT JOIN ref_jenis_hak h ON h.kode=p.jenis_hak
        LEFT JOIN ref_kelengkapan f ON f.id=p.kelengkapan_id
        {saring}
        ORDER BY p.id DESC""", parameter)]
    if baris:
        butir = _butir_per_formulir(k, {b["kelengkapan_id"] for b in baris})
        jawab = _jawab_banyak(k, [b["id"] for b in baris])
        for b in baris:
            pohon = _rakit(butir.get(b["kelengkapan_id"], []), jawab.get(b["id"], {}),
                           b["pemohon_jenis_subjek"], b["asal_tanah"])
            b["kurang"] = _kurang(pohon)
            b["koreksi"] = _koreksi(pohon)
            b["lengkap"] = not b["kurang"] and not b["koreksi"]
            b["boleh_ubah"] = (izin.boleh_ubah(pengguna, b["dibuat_oleh"])
                               and b["status"] not in STATUS_KUNCI)

    ringkas = {
        "total": len(baris),
        "kurang": sum(1 for b in baris if b["status"] == "baru" and not b["lengkap"]),
        "siap": sum(1 for b in baris if b["status"] == "baru" and b["lengkap"]),
        "diterima": sum(1 for b in baris if b["status"] == "diterima"),
        "dikembalikan": sum(1 for b in baris if b["status"] == "dikembalikan"),
    }
    return baris, ringkas


# -------------------------------------------------------------------- muat
def muat(k, pid):
    """Satu pradaftar lengkap dengan pohon butir dan jawabannya."""
    r = k.execute("""
        SELECT p.*, d.nama AS desa, d.jenis AS jenis_desa, c.nama AS kecamatan,
               h.nama AS nama_hak, f.kode AS kode_formulir, f.judul AS judul_formulir,
               f.dasar AS dasar_formulir, f.varian_template
        FROM pradaftar p
        LEFT JOIN ref_desa d ON d.id=p.desa_id
        LEFT JOIN ref_kecamatan c ON c.id=d.kecamatan_id
        LEFT JOIN ref_jenis_hak h ON h.kode=p.jenis_hak
        LEFT JOIN ref_kelengkapan f ON f.id=p.kelengkapan_id
        WHERE p.id=?""", (pid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    butir = _butir_per_formulir(k, [d["kelengkapan_id"]]).get(d["kelengkapan_id"], [])
    jawab = _jawab_banyak(k, [pid]).get(pid, {})
    d["pohon"] = _rakit(butir, jawab, d["pemohon_jenis_subjek"], d["asal_tanah"])
    d["kurang"] = _kurang(d["pohon"])
    d["koreksi"] = _koreksi(d["pohon"])
    d["lengkap"] = not d["kurang"] and not d["koreksi"]
    d["catatan_baku"] = catatan_koreksi(k, d["kelengkapan_id"])
    d["boleh_terima"] = d["status"] == "baru"
    return d


def formulir(k, jenis_hak, kegiatan="baru"):
    """Formulir kelengkapan yang berlaku untuk satu jenis hak.

    Yang paling khusus menang, sama seperti pemilihan klausa: baris untuk jenis
    hak ini dipakai lebih dulu daripada baris '*'. Tidak ada yang cocok berarti
    jenis hak itu belum punya formulir resminya — pradaftar tetap bisa dibuat,
    tab Kelengkapan yang kosong dan mengatakan begitu.
    """
    r = k.execute(
        "SELECT * FROM ref_kelengkapan WHERE aktif=1 "
        "AND (jenis_hak='*' OR jenis_hak=?) AND (kegiatan='*' OR kegiatan=?) "
        "ORDER BY CASE WHEN jenis_hak='*' THEN 1 ELSE 0 END, "
        "         CASE WHEN kegiatan='*' THEN 1 ELSE 0 END, urut, id LIMIT 1",
        (jenis_hak or "", kegiatan or "baru")).fetchone()
    return dict(r) if r else None


def daftar_formulir(k):
    """Seluruh formulir kelengkapan berikut jumlah butirnya — untuk halaman referensi."""
    return [dict(r) for r in k.execute(
        "SELECT f.*, (SELECT COUNT(*) FROM ref_kelengkapan_butir b "
        "             WHERE b.kelengkapan_id=f.id AND b.aktif=1) AS jml_butir "
        "FROM ref_kelengkapan f ORDER BY f.urut, f.id")]


def butir_formulir(k, kelengkapan_id):
    """Pohon butir satu formulir, tanpa jawaban — untuk halaman referensi."""
    butir = _butir_per_formulir(k, [kelengkapan_id]).get(kelengkapan_id, [])
    return _rakit(butir, {}, None, None)


# ------------------------------------------------------ pembacaan mentah
def catatan_koreksi(k, kelengkapan_id):
    """Catatan baku yang aktif untuk satu formulir: (umum, {butir_id: [teks]}).

    Yang umum ditawarkan di semua butir; yang khusus hanya pada butirnya
    sendiri, di atas yang umum.
    """
    umum, khusus = [], {}
    for r in k.execute(
            "SELECT c.butir_id, c.teks FROM ref_catatan_koreksi c "
            "LEFT JOIN ref_kelengkapan_butir b ON b.id=c.butir_id "
            "WHERE c.aktif=1 AND (c.butir_id IS NULL OR b.kelengkapan_id=?) "
            "ORDER BY c.urut, c.id", (kelengkapan_id,)):
        if r["butir_id"] is None:
            umum.append(r["teks"])
        else:
            khusus.setdefault(r["butir_id"], []).append(r["teks"])
    return umum, khusus


def _butir_per_formulir(k, ids):
    """Butir seluruh formulir yang dipakai, satu kueri. {kelengkapan_id: [baris]}"""
    ids = [x for x in ids if x]
    if not ids:
        return {}
    tanya = ",".join("?" * len(ids))
    per = {}
    for r in k.execute(f"SELECT * FROM ref_kelengkapan_butir "
                       f"WHERE kelengkapan_id IN ({tanya}) ORDER BY urut, id", ids):
        per.setdefault(r["kelengkapan_id"], []).append(dict(r))
    return per


def _jawab_banyak(k, pids):
    """Jawaban seluruh pradaftar yang diminta, satu kueri. {pid: {butir_id: baris}}"""
    pids = [x for x in pids if x]
    if not pids:
        return {}
    tanya = ",".join("?" * len(pids))
    per = {}
    for r in k.execute(f"SELECT * FROM pradaftar_jawab "
                       f"WHERE pradaftar_id IN ({tanya})", pids):
        per.setdefault(r["pradaftar_id"], {})[r["butir_id"]] = dict(r)
    return per


# ------------------------------------------------------- pohon & kelengkapan
def _cocok(nilai, pilihan):
    """Apakah sebuah butir berlaku untuk nilai ini. '*' berarti selalu berlaku.

    pilihan None = belum ditentukan (halaman referensi, yang menampilkan semua
    butir apa adanya), jadi dianggap berlaku.
    """
    if nilai == "*" or pilihan is None:
        return True
    return pilihan in [x.strip() for x in nilai.split(",") if x.strip()]


def _rakit(butir, jawab, subjek, asal_tanah):
    """Susun baris datar jadi pohon, sambil menandai berlaku/tidaknya tiap butir.

    Urutan baris sudah urutan formulir (lihat db._sisip_butir), jadi anak selalu
    datang sesudah induknya dan satu lintasan sudah cukup.
    """
    simpul, akar, buang = {}, [], set()
    for b in butir:
        # Butir yang sudah dihapus dari formulir hanya muncul pada pradaftar
        # yang dulu menjawabnya — supaya cetakan dan berkas lamanya tetap utuh.
        # Anak dari butir yang dibuang ikut dibuang, bukan naik jadi akar.
        if b["induk_id"] in buang or (not b.get("aktif", 1) and b["id"] not in jawab):
            buang.add(b["id"])
            continue
        n = dict(b)
        n["anak"] = []
        j = jawab.get(b["id"]) or {}
        n["ada"] = j.get("ada", TIDAK_ADA)
        # Belum diperiksa dan dinyatakan Tidak Ada sama-sama menahan penerimaan,
        # tetapi petugas perlu tahu butir mana yang belum ia sentuh sama sekali.
        n["dijawab"] = b["id"] in jawab
        n["uraian"] = j.get("uraian") or ""
        # Satu surat sebaris: butir `jamak` boleh berisi lebih dari satu.
        n["uraian_daftar"] = [x.strip() for x in n["uraian"].split("\n") if x.strip()]
        n["catatan_jawab"] = j.get("catatan") or ""
        induk = simpul.get(b["induk_id"])
        # Tidak berlaku menurun: anak grup Badan Hukum ikut tidak berlaku pada
        # pemohon perorangan, tanpa perlu menuliskan syaratnya lagi di tiap anak.
        n["berlaku"] = (_cocok(b["subjek"], subjek) and _cocok(b["asal_tanah"], asal_tanah)
                        and (induk is None or induk["berlaku"]))
        simpul[b["id"]] = n
        (induk["anak"] if induk else akar).append(n)
    for n in akar:
        _nilai(n)
    return akar


def _nilai(n):
    """Tetapkan status satu simpul, dari bawah ke atas.

        ada      sudah terpenuhi
        kurang   wajib tapi belum ada — inilah yang menahan penerimaan di loket
        koreksi  suratnya ada tapi perlu diperbaiki — ikut menahan penerimaan
        lewat    tidak berlaku, atau tidak wajib dan memang belum ada

    Grup terpenuhi kalau: di antara anak yang bersifat `alternatif` ada minimal
    satu yang ada (itu arti "a ... atau b ..." pada formulirnya), DAN seluruh
    anak wajib yang bukan alternatif sudah ada. Kurang mengalahkan koreksi:
    grup yang masih kekurangan surat disebut kurang walau anak lainnya cuma
    perlu diperbaiki — butir koreksinya tetap terlaporkan lewat `_koreksi`.
    """
    for a in n["anak"]:
        _nilai(a)
    if not n["berlaku"] or n["ada"] == TIDAK_BERLAKU:
        n["status"] = "lewat"
        return n["status"]
    if not n["anak"]:
        if n["ada"] == ADA:
            n["status"] = "ada"
        elif n["ada"] == KOREKSI:
            # Tidak memandang wajib: petugas sendiri yang menyatakan surat ini
            # harus diperbaiki, jadi pernyataan itu tidak boleh diam-diam hilang.
            n["status"] = "koreksi"
        elif n["sifat"] == "alternatif":
            # Butir alternatif tidak pernah kurang sendirian: yang wajib adalah
            # grupnya, dan grup itu terpenuhi begitu satu di antaranya ada.
            # Kalau tiap alternatif ikut ditandai kurang, sembilan butir alas
            # hak yang memang tidak dipakai akan tampak merah semua.
            n["status"] = "lewat"
        else:
            n["status"] = "kurang" if n["wajib"] else "lewat"
        return n["status"]

    berlaku = [a for a in n["anak"] if a["berlaku"]]
    pilihan = [a for a in berlaku if a["sifat"] == "alternatif"]
    tetap = [a for a in berlaku if a["sifat"] != "alternatif"]
    cukup = (not pilihan) or any(a["status"] == "ada" for a in pilihan)
    tetap_ok = all(a["status"] != "kurang" for a in tetap)
    ada_koreksi = any(a["status"] == "koreksi" for a in berlaku)
    if not tetap_ok:
        n["status"] = "kurang" if n["wajib"] else "lewat"
    elif not cukup:
        # Alternatifnya dibawa tapi salah: yang diminta dari pemohon adalah
        # memperbaiki surat itu, bukan membawa salah satu dari a sampai j.
        n["status"] = ("koreksi" if ada_koreksi
                       else "kurang" if n["wajib"] else "lewat")
    else:
        n["status"] = "koreksi" if ada_koreksi else "ada"
    return n["status"]


def _kurang(pohon):
    """Butir yang masih menahan penerimaan, sebagai daftar datar untuk dicetak.

    Grup yang kurang dilaporkan sebagai satu baris, bukan sepuluh anaknya:
    "Dasar Penguasaan atau Alas Hak" yang kosong berarti pemohon perlu membawa
    salah satu dari a sampai j — menyebut kesepuluhnya sebagai kekurangan justru
    menyesatkan.
    """
    hasil = []

    def telusur(simpul):
        for n in simpul:
            if n["status"] != "kurang":
                continue
            if n["anak"] and any(a["sifat"] == "alternatif" and a["berlaku"]
                                 for a in n["anak"]):
                hasil.append(n)            # cukup salah satu — sebut grupnya saja
                continue
            if n["anak"]:
                telusur(n["anak"])
            else:
                hasil.append(n)

    telusur(pohon)
    return hasil


def _koreksi(pohon):
    """Butir yang ada tapi perlu diperbaiki, sebagai daftar datar untuk dicetak.

    Selalu butirnya sendiri, bukan grupnya: yang harus diperbaiki pemohon
    adalah satu surat tertentu, lengkap dengan catatannya.
    """
    hasil = []

    def telusur(simpul):
        for n in simpul:
            if n["anak"]:
                telusur(n["anak"])
            elif n["status"] == "koreksi":
                hasil.append(n)

    telusur(pohon)
    return hasil


def progres(pohon):
    """(sudah, semua): berapa satuan pemeriksaan yang sudah dijawab petugas.

    Satu satuan = satu butir yang bisa dicentang, KECUALI butir alternatif:
    sekelompok "a ... atau b ..." dihitung satu, dan selesai begitu salah satunya
    dinyatakan ada (atau semuanya sudah dijawab). Kalau tiap alternatif dihitung
    sendiri, petugas harus mengklik Tidak Ada sembilan kali untuk alas hak yang
    memang tidak dipakai hanya supaya angkanya penuh.

    app.js menghitung ulang angka yang sama di peramban tiap kali pilihan
    diganti (hitungPeriksa); aturan keduanya harus tetap sama.
    """
    satuan = {}
    for n in ratakan(pohon):
        if not n["berlaku"] or n["sifat"] == "judul":
            continue
        kunci = (("g", n["induk_id"]) if n["sifat"] == "alternatif"
                 else ("b", n["id"]))
        satuan.setdefault(kunci, []).append(n)

    def selesai(jenis, isi):
        if jenis == "b":
            return isi[0]["dijawab"]
        return (any(x["dijawab"] and x["ada"] in (ADA, KOREKSI) for x in isi)
                or all(x["dijawab"] for x in isi))

    return (sum(1 for (jenis, _), isi in satuan.items() if selesai(jenis, isi)),
            len(satuan))


def ratakan(pohon, tingkat=0):
    """Pohon jadi daftar datar berurutan — untuk tabel di layar dan di DOCX.

    Indentasi dibawa sebagai angka `tingkat`, bukan spasi di depan nama, supaya
    HTML dan DOCX bebas menatanya masing-masing.
    """
    hasil = []
    for n in pohon:
        r = dict(n)
        r["tingkat"] = tingkat
        r.pop("anak", None)
        hasil.append(r)
        hasil.extend(ratakan(n["anak"], tingkat + 1))
    return hasil


# ------------------------------------------------------------------ simpan
def simpan(k, f, pid=None, pengguna_id=None):
    """Tulis satu pradaftar berikut seluruh centangannya. f = request.form.

    Sama dengan formulir.simpan: getlist() dipakai supaya medan yang ada tapi
    kosong menimpa nilai lama, bukan jatuh ke nilai bawaan.
    """
    satu = lambda n, d="": (f.getlist(n) or [d])[0].strip()
    c = k.cursor()

    jenis_hak = satu("jenis_hak") or "HM"
    kegiatan = satu("jenis_kegiatan") or "baru"
    form = formulir(k, jenis_hak, kegiatan)
    kolom = (satu("tanggal") or dt.date.today().isoformat(),
             jenis_hak, kegiatan, satu("asal_tanah") or "tanah_negara",
             form["id"] if form else None,
             satu("pemohon_nama") or "(tanpa nama)",
             satu("pemohon_jenis_subjek") or "perorangan",
             _n(satu("pemohon_nik")), _n(satu("pemohon_alamat")),
             _n(satu("pemohon_telepon")),
             _n(satu("kuasa_nama")), _n(satu("kuasa_nik")),
             _i(satu("desa_id")), _n(satu("letak_lain")),
             _i(satu("luas_surat")), _n(satu("nomor_pbt")),
             _n(satu("catatan")))
    if pid:
        c.execute("UPDATE pradaftar SET tanggal=?, jenis_hak=?, jenis_kegiatan=?, "
                  "asal_tanah=?, kelengkapan_id=?, pemohon_nama=?, pemohon_jenis_subjek=?, "
                  "pemohon_nik=?, pemohon_alamat=?, pemohon_telepon=?, kuasa_nama=?, "
                  "kuasa_nik=?, desa_id=?, letak_lain=?, luas_surat=?, nomor_pbt=?, "
                  "catatan=?, diubah=? WHERE id=?", kolom + (db.sekarang(), pid))
    else:
        pid = db.sisip_id(
            c, "INSERT INTO pradaftar (tanggal,jenis_hak,jenis_kegiatan,asal_tanah,"
               "kelengkapan_id,pemohon_nama,pemohon_jenis_subjek,pemohon_nik,"
               "pemohon_alamat,pemohon_telepon,kuasa_nama,kuasa_nik,desa_id,letak_lain,"
               "luas_surat,nomor_pbt,catatan,nomor,dibuat_oleh,dibuat) "
               "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            kolom + (_nomor_baru(k), pengguna_id, db.sekarang()))

    _simpan_jawab(c, f, pid)
    k.commit()
    return pid


def _simpan_jawab(c, f, pid):
    """Centangan ditulis ulang seluruhnya, seperti daftar lain di aplikasi ini.

    Yang dikirim peramban hanya butir yang tampil di halaman, jadi butir yang
    tidak ikut terkirim memang tidak boleh tersentuh — karena itu yang dihapus
    lebih dulu cuma butir yang disebut `jawab_butir`, bukan seluruh barisnya.
    """
    ids = [x for x in (_i(v) for v in f.getlist("jawab_butir")) if x]
    if not ids:
        return
    tanya = ",".join("?" * len(ids))
    c.execute(f"DELETE FROM pradaftar_jawab WHERE pradaftar_id=? "
              f"AND butir_id IN ({tanya})", [pid] + ids)
    for bid in ids:
        mentah = f.get(f"jawab_ada_{bid}")
        ada = _i(mentah) or TIDAK_ADA
        if ada not in (TIDAK_ADA, ADA, TIDAK_BERLAKU, KOREKSI):
            ada = TIDAK_ADA
        # Kotak uraiannya boleh lebih dari satu (butir jamak) — satu surat
        # sebaris, yang kosong dibuang.
        uraian = "\n".join(x.strip() for x in f.getlist(f"jawab_uraian_{bid}")
                           if x.strip())
        # Catatan hanya milik butir yang perlu koreksi. Kotaknya tetap ikut
        # terkirim saat pilihannya diganti ke Ada, dan catatan yang tertinggal
        # di situ akan terbaca sebagai koreksi yang sudah tidak berlaku.
        catatan = ((f.get(f"jawab_catatan_{bid}") or "").strip()
                   if ada == KOREKSI else "")
        # Tak satu pun pilihan dicentang: belum diperiksa, barisnya tak perlu
        # ada. "Tidak Ada" yang dipilih sendiri tetap disimpan — itu jawaban.
        if mentah is None and not uraian:
            continue
        c.execute("INSERT INTO pradaftar_jawab (pradaftar_id,butir_id,ada,uraian,catatan) "
                  "VALUES (?,?,?,?,?)", (pid, bid, ada, uraian or None, catatan or None))


def simpan_jawab(k, f, pid):
    """Tulis centangan saja, tanpa menyentuh data pemohon dan letak tanah.

    Dipakai halaman periksa layar penuh, yang formulirnya hanya memuat daftar
    kelengkapan — lewat simpan() medan pemohon yang tidak ikut terkirim akan
    tertimpa kosong.
    """
    c = k.cursor()
    _simpan_jawab(c, f, pid)
    c.execute("UPDATE pradaftar SET diubah=? WHERE id=?", (db.sekarang(), pid))
    k.commit()


def _nomor_baru(k):
    """Nomor agenda loket, berjalan per tahun. PD-0012/2026"""
    tahun = dt.date.today().year
    return f"PD-{db.ambil_nomor(k, 'pradaftar', '-', tahun):04d}/{tahun}"


def ubah_status(k, pid, status, alasan=None):
    """Tutup atau buka kembali sebuah pradaftar tanpa menyentuh isinya."""
    k.execute("UPDATE pradaftar SET status=?, catatan=COALESCE(?,catatan), diubah=? "
              "WHERE id=?", (status, _n(alasan or ""), db.sekarang(), pid))
    k.commit()


# ------------------------------------------------------- naik jadi berkas
def terima(k, pid, pengguna_id, alasan=None):
    """Terima di loket: bikin berkas dari pradaftar ini, lalu kunci pradaftarnya.

    Inilah alasan pradaftar ada di aplikasi yang sama, bukan di buku tersendiri:
    yang sudah diketik petugas loket tidak diketik ulang petugas Panitia A.

    Kembalikan (berkas_id, galat). Sekali berhasil, pradaftar yang sama tidak
    bisa diterima dua kali — nomor berkas yang telanjur keluar tidak bisa
    ditarik, dan berkas kembar berarti satu permohonan disidangkan dua kali.
    """
    d = muat(k, pid)
    if not d:
        return None, "Pradaftar tidak ditemukan."
    if d["status"] != "baru":
        return d["berkas_id"], f"Pradaftar ini sudah berstatus {d['status']}."
    if not d["lengkap"] and not (alasan or "").strip():
        return None, ("Masih ada dokumen yang kurang atau perlu koreksi. Terima "
                      "bersyarat hanya bisa dengan alasan tertulis.")

    c = k.cursor()
    bid = db.sisip_id(
        c, "INSERT INTO berkas (jenis_hak_dimohon,jenis_kegiatan,asal_tanah,status,"
           "tanggal_permohonan,catatan,dibuat_oleh,dibuat) VALUES (?,?,?,'draf',?,?,?,?)",
        (d["jenis_hak"], d["jenis_kegiatan"], d["asal_tanah"], d["tanggal"],
         _n(d.get("catatan")), pengguna_id, db.sekarang()))

    c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,alamat,urut) "
              "VALUES (?,'penerima_hak',?,?,?,?,0)",
              (bid, d["pemohon_jenis_subjek"], d["pemohon_nama"],
               _n(d.get("pemohon_nik")), _n(d.get("pemohon_alamat"))))
    if (d.get("kuasa_nama") or "").strip():
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,urut) "
                  "VALUES (?,'kuasa','perorangan',?,?,1)",
                  (bid, d["kuasa_nama"], _n(d.get("kuasa_nik"))))
    if d.get("desa_id") or d.get("luas_surat") or (d.get("nomor_pbt") or "").strip():
        c.execute("INSERT INTO bidang_tanah (berkas_id,desa_id,luas_surat,nomor_pbt) "
                  "VALUES (?,?,?,?)",
                  (bid, d.get("desa_id"), d.get("luas_surat"), _n(d.get("nomor_pbt"))))

    _salin_dokumen(c, bid, d["pohon"])
    c.execute("UPDATE pradaftar SET status='diterima', berkas_id=?, alasan_terima=?, "
              "diubah=? WHERE id=?",
              (bid, _n(alasan or ""), db.sekarang(), pid))
    k.commit()
    return bid, None


def _salin_dokumen(c, bid, pohon):
    """Butir yang dicentang Ada — atau ada tapi perlu koreksi — jadi baris
    dokumen pendukung pada berkas baru.

    Kategorinya ditentukan begini, berurutan:

      slot_baku butirnya sendiri  -> slot dokumen baku, mis. butir 6 -> `sppf`
      slot_baku grup induknya     -> diwarisi; anak "Dasar Penguasaan atau Alas
                                     Hak" semuanya masuk kategori `alas_hak`
      tidak ada keduanya          -> `tambahan`

    Uraiannya: yang diketik petugas di titik-titik kalau ada — satu baris
    dokumen per surat bila isinya lebih dari satu — kalau tidak
    `nama_dokumen`, kalau itu pun kosong barulah bunyi formulirnya. Bunyi
    formulir dipakai paling akhir karena memuat keterangan dalam kurung yang
    benar di formulir tapi janggal sebagai nama surat.

    Butir koreksi ikut disalin dengan catatannya di belakang uraian: suratnya
    memang ada di dalam map, dan petugas Panitia A perlu tahu apa yang masih
    harus diperbaiki. Ini hanya terjadi pada terima bersyarat.

    Yang disalin hanya nama suratnya. Nomor, tanggal, dan pejabatnya tetap
    diisi petugas Panitia A — loket tidak mencatat itu.
    """
    urut = 0

    def telusur(simpul, kategori_induk):
        nonlocal urut
        for n in simpul:
            kategori = n["slot_baku"] or kategori_induk
            if n["anak"]:
                telusur(n["anak"], kategori)
                continue
            if n["status"] not in ("ada", "koreksi"):
                continue
            # Satu surat satu baris dokumen: dua akta pemindahan hak adalah
            # dua dokumen pada berkas, masing-masing dengan nomornya sendiri.
            for uraian in (n["uraian_daftar"] or [n["nama_dokumen"] or n["nama"]]):
                if n["status"] == "koreksi":
                    uraian += (f" (perlu koreksi: {n['catatan_jawab']})"
                               if n["catatan_jawab"] else " (perlu koreksi)")
                c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,"
                          "keaslian) VALUES (?,?,?,?,'')",
                          (bid, urut, kategori or "tambahan", uraian))
                urut += 1

    telusur(pohon, None)


def dari_berkas(k, berkas_id):
    """Pradaftar asal sebuah berkas, untuk tautan balik di tab Dokumen.

    Tautannya satu arah — berkas tidak menyimpan kolom pradaftar_id. Satu fakta
    satu tempat: yang tahu dirinya sudah naik jadi berkas adalah pradaftarnya.
    """
    r = k.execute("SELECT id, nomor, tanggal FROM pradaftar WHERE berkas_id=?",
                  (berkas_id,)).fetchone()
    return dict(r) if r else None
