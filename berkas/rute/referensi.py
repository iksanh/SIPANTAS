# -*- coding: utf-8 -*-
"""Halaman Data referensi: jenis hak, klausa, wilayah, dan susunan Panitia A.

Kueri datanya ada di referensi.py, perakit halamannya di web.py. Yang di sini
hanya penerjemah antara permintaan HTTP dan kedua modul itu.

Semua POST berakhir dengan pengalihan, bukan halaman — menyegarkan halaman
sesudah menyimpan tidak boleh mengirim ulang formulirnya.
"""
import urllib.parse as up

from flask import Blueprint, g, redirect, request

from .. import (basis, db, izin, kabar, pradaftar, referensi, susun_kelengkapan,
               web, wilayah)
from ..util import ke_int, teks_atau_none

bp = Blueprint("referensi", __name__, url_prefix="/referensi")

# Petugas boleh membaca halaman ini — nama kepala desa dan susunan panitia
# perlu dicek saat mengisi berkas — tetapi tiap POST di bawah khusus admin.
DAFTAR_KEC = "/referensi?buka=kecamatan#b-kecamatan"
DAFTAR_DESA = "/referensi?buka=desa#b-desa"


def _v(nama):
    """Isian formulir; teks kosong jadi None."""
    return teks_atau_none(request.form.get(nama))


def _galat(teks):
    return redirect("/referensi?galat=" + up.quote(teks), 303)


def _ke(alamat, tanya):
    return redirect(kabar.ke(alamat, tanya), 303)


# ------------------------------------------------------------------ halaman
@bp.get("")
def halaman():
    """Kartu yang tertutup dikirim tanpa isi. Bagian yang diminta lewat
    ?buka=<kunci> dirakit di sini supaya tetap jalan tanpa JavaScript."""
    boleh = izin.admin(g.pengguna)
    ringkas = referensi.ringkas(g.k)
    # Jenis hak dan klausa cuma belasan baris dan masing-masing mengisi satu
    # tab sendiri, jadi selalu dirakit; begitu pula kelengkapan bila hanya
    # ada satu formulir. Membuka tab lalu masih harus membuka kartunya
    # hanya menambah satu klik.
    minta = ["jenis_hak", "klausa"]
    if len(ringkas.get("kelengkapan", [])) == 1:
        minta.append(f'kelengkapan-{ringkas["kelengkapan"][0]["id"]}')
    terbuka = {}
    for b in dict.fromkeys(minta + kabar.buka()):
        if b == "panitia_baru":             # isinya formulir kosong, tak perlu dibaca
            terbuka[b] = ""
        else:
            isi = web.bagian_referensi(b, referensi.bagian(g.k, b), boleh)
            if isi:
                terbuka[b] = isi
    return web.halaman_referensi(g.pengguna, ringkas, terbuka,
                                kabar.pesan(), boleh_ubah=boleh)


@bp.get("/bagian/<kunci>")
def bagian(kunci):
    """Potongan kartu lipat, ditandai supaya app.js tak salah menelan halaman lain."""
    isi = web.bagian_referensi(kunci, referensi.bagian(g.k, kunci),
                               izin.admin(g.pengguna))
    if not isi:
        return "bagian tidak dikenal", 404, {"Content-Type": "text/plain; charset=utf-8"}
    return isi, 200, {"X-Potongan": "1"}


@bp.get("/desa/<int:desa_id>")
def halaman_desa(desa_id):
    d = referensi.satu_desa(g.k, desa_id)
    if not d:
        return redirect(DAFTAR_DESA, 303)
    return web.halaman_desa(g.pengguna, d, referensi.daftar_kecamatan(g.k), kabar.pesan())


# ------------------------------------------------------------ susunan panitia
def _kembali_panitia(pesan, sk=None):
    """Balik ke halaman referensi dengan SK yang disunting tetap terbuka."""
    if not sk:
        return redirect(f"/referensi?pesan={pesan}#panitia", 303)
    return redirect(f"/referensi?pesan={pesan}&buka=panitia-{sk}#b-panitia-{sk}", 303)


def _pid():
    """Formulir susunan panitia memakai `id`, formulir anggotanya `panitia_id`.
    Yang dilihat keberadaan medannya, bukan isinya — sama seperti penangan lama."""
    medan = "panitia_id" if "panitia_id" in request.form else "id"
    return ke_int(request.form.get(medan))


@bp.post("/panitia")
@izin.perlu_admin
def simpan_panitia():
    if not _v("nomor_sk"):
        return _galat("Nomor SK susunan panitia wajib diisi.")
    pid = _pid()
    nilai = (_v("nomor_sk"), _v("tanggal_sk"), _v("berlaku_dari"),
             _v("berlaku_sampai"), _v("keterangan"))
    if pid:
        g.k.execute("UPDATE ref_panitia SET nomor_sk=?, tanggal_sk=?, berlaku_dari=?, "
                    "berlaku_sampai=?, keterangan=? WHERE id=?", nilai + (pid,))
    else:
        pid = db.sisip_id(
            g.k, "INSERT INTO ref_panitia (nomor_sk,tanggal_sk,berlaku_dari,"
                 "berlaku_sampai,keterangan) VALUES (?,?,?,?,?)", nilai)
    g.k.commit()
    return _kembali_panitia("panitia", pid)


@bp.post("/panitia/hapus")
@izin.perlu_admin
def hapus_panitia():
    pid = _pid()
    dipakai = g.k.execute("SELECT COUNT(*) AS n FROM pemeriksaan WHERE panitia_id=?",
                          (pid,)).fetchone()["n"]
    if dipakai:
        return _kembali_panitia("panitia_dipakai", pid)
    g.k.execute("DELETE FROM ref_panitia_anggota WHERE panitia_id=?", (pid,))
    g.k.execute("DELETE FROM ref_panitia WHERE id=?", (pid,))
    g.k.commit()
    return _kembali_panitia("panitia_hapus")


@bp.post("/panitia/salin")
@izin.perlu_admin
def salin_panitia():
    pid = _pid()
    asal = g.k.execute("SELECT * FROM ref_panitia WHERE id=?", (pid,)).fetchone()
    if not asal:
        return redirect("/referensi#panitia", 303)
    baru = db.sisip_id(
        g.k, "INSERT INTO ref_panitia (nomor_sk,tanggal_sk,keterangan) VALUES (?,?,?)",
        (asal["nomor_sk"] + " (salinan)", None, "Disalin dari " + asal["nomor_sk"]))
    for a in g.k.execute("SELECT * FROM ref_panitia_anggota WHERE panitia_id=? "
                         "ORDER BY urut, id", (pid,)).fetchall():
        g.k.execute("INSERT INTO ref_panitia_anggota "
                    "(panitia_id,urut,nama,nip,jabatan,peran,pendapat_baku) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (baru, a["urut"], a["nama"], a["nip"], a["jabatan"], a["peran"],
                     a["pendapat_baku"]))
    g.k.commit()
    return _kembali_panitia("panitia_salin", baru)


@bp.post("/panitia/anggota")
@izin.perlu_admin
def simpan_anggota():
    pid, aid = _pid(), ke_int(request.form.get("anggota_id"))
    if not _v("nama") or not pid:
        return _galat("Nama anggota panitia wajib diisi.")
    nilai = (ke_int(request.form.get("urut")) or 0, _v("nama"), _v("nip"),
             _v("jabatan"), _v("peran"), _v("pendapat_baku"))
    if aid:
        g.k.execute("UPDATE ref_panitia_anggota SET urut=?, nama=?, nip=?, jabatan=?, "
                    "peran=?, pendapat_baku=? WHERE id=? AND panitia_id=?", nilai + (aid, pid))
    else:
        g.k.execute("INSERT INTO ref_panitia_anggota "
                    "(panitia_id,urut,nama,nip,jabatan,peran,pendapat_baku) "
                    "VALUES (?,?,?,?,?,?,?)", (pid,) + nilai)
    g.k.commit()
    return _kembali_panitia("anggota", pid)


@bp.post("/panitia/anggota/hapus")
@izin.perlu_admin
def hapus_anggota():
    g.k.execute("DELETE FROM ref_panitia_anggota WHERE id=?",
                (ke_int(request.form.get("anggota_id")),))
    g.k.commit()
    return _kembali_panitia("anggota_hapus", _pid())


# ------------------------------------------------ wilayah: kecamatan dan desa
def _kembali_wilayah(pesan, bawaan):
    """Balik ke halaman asal — daftar wilayah atau halaman satu desa."""
    asal = _v("asal") or bawaan
    return _ke(asal if asal.startswith("/referensi") else bawaan, "pesan=" + pesan)


@bp.post("/wilayah")
@izin.perlu_admin
def selaraskan_wilayah():
    """Tambahkan kecamatan dan desa yang ada di daftar induk Kemendagri
    tetapi belum ada di basis data."""
    kec, desa = wilayah.selaraskan(g.k)
    if not (kec or desa):
        return _ke(DAFTAR_DESA, "pesan=wilayah_lengkap")
    kabar_teks = (f"{kec} kecamatan dan {desa} desa/kelurahan ditambahkan dari daftar "
                  f"Kemendagri {wilayah.KODE_KABUPATEN}. Nama pejabatnya masih kosong.")
    return _ke(DAFTAR_DESA, "baik=" + up.quote(kabar_teks))


@bp.post("/kecamatan")
@izin.perlu_admin
def simpan_kecamatan():
    nama, kid = _v("nama"), ke_int(request.form.get("id"))
    if not nama:
        return _galat("Nama kecamatan wajib diisi.")
    try:
        if kid:
            g.k.execute("UPDATE ref_kecamatan SET nama=?, kode=? WHERE id=?",
                        (nama, _v("kode"), kid))
        else:
            g.k.execute("INSERT INTO ref_kecamatan (nama,kode) VALUES (?,?)",
                        (nama, _v("kode")))
    except basis.Bentrok:
        return _ke(DAFTAR_KEC, "pesan=kecamatan_ada")
    g.k.commit()
    return _kembali_wilayah("kecamatan", DAFTAR_KEC)


@bp.post("/kecamatan/hapus")
@izin.perlu_admin
def hapus_kecamatan():
    kid = ke_int(request.form.get("id"))
    if g.k.execute("SELECT COUNT(*) FROM ref_desa WHERE kecamatan_id=?", (kid,)).fetchone()[0]:
        return _ke(DAFTAR_KEC, "pesan=kecamatan_isi")
    g.k.execute("DELETE FROM ref_kecamatan WHERE id=?", (kid,))
    g.k.commit()
    return _ke(DAFTAR_KEC, "pesan=kecamatan_hapus")


@bp.post("/desa")
@izin.perlu_admin
def simpan_desa():
    did = ke_int(request.form.get("id"))
    nama, kid = _v("nama"), ke_int(request.form.get("kecamatan_id"))
    jenis = _v("jenis") or "Desa"
    if not (nama and kid):
        return _galat("Kecamatan dan nama desa/kelurahan wajib diisi.")
    try:
        if did:
            g.k.execute("UPDATE ref_desa SET kecamatan_id=?, nama=?, jenis=?, kode=? "
                        "WHERE id=?", (kid, nama, jenis, _v("kode"), did))
        else:
            did = db.sisip_id(
                g.k, "INSERT INTO ref_desa (kecamatan_id,nama,jenis,kode,jabatan_pejabat) "
                     "VALUES (?,?,?,?,?)",
                (kid, nama, jenis, _v("kode"), wilayah.jabatan_baku(jenis)))
    except basis.Bentrok:
        return _ke(DAFTAR_DESA, "pesan=desa_ada")
    # Jabatan pejabat aktif ikut menyesuaikan bila Desa diubah jadi Kelurahan.
    wilayah.segarkan(g.k, did)
    g.k.commit()
    return _kembali_wilayah("desa", f"/referensi/desa/{did}")


@bp.post("/desa/hapus")
@izin.perlu_admin
def hapus_desa():
    did = ke_int(request.form.get("id"))
    if g.k.execute("SELECT COUNT(*) FROM bidang_tanah WHERE desa_id=?", (did,)).fetchone()[0]:
        return redirect(f"/referensi/desa/{did}?pesan=desa_dipakai", 303)
    g.k.execute("DELETE FROM ref_desa_pejabat WHERE desa_id=?", (did,))
    g.k.execute("DELETE FROM ref_desa WHERE id=?", (did,))
    g.k.commit()
    return _ke(DAFTAR_DESA, "pesan=desa_hapus")


# ----------------------------------------------------- kepala desa dan lurah
def _did():
    return ke_int(request.form.get("desa_id"))


@bp.post("/desa/pejabat")
@izin.perlu_admin
def simpan_pejabat():
    did = _did()
    if not (did and _v("nama")):
        return _galat("Nama kepala desa/lurah wajib diisi.")
    wilayah.simpan_pejabat(
        g.k, did, ke_int(request.form.get("pejabat_id")), _v("nama"),
        _v("jabatan") or wilayah.jabatan_baku(_v("jenis")),
        _v("mulai"), _v("sampai"), _v("sk_nomor"), _v("catatan"),
        aktif=bool(request.form.get("aktif")))
    g.k.commit()
    return _kembali_wilayah("pejabat", f"/referensi/desa/{did}")


@bp.post("/desa/pejabat/aktif")
@izin.perlu_admin
def jadikan_pejabat_aktif():
    did = _did()
    if did:
        wilayah.jadikan_aktif(g.k, did, ke_int(request.form.get("pejabat_id")))
        g.k.commit()
    return _kembali_wilayah("pejabat_aktif", f"/referensi/desa/{did}")


@bp.post("/desa/pejabat/hapus")
@izin.perlu_admin
def hapus_pejabat():
    did, pid = _did(), ke_int(request.form.get("pejabat_id"))
    if did and pid:
        wilayah.hapus_pejabat(g.k, did, pid)
        g.k.commit()
    return _kembali_wilayah("pejabat_hapus", f"/referensi/desa/{did}")


DAFTAR_CATATAN = "/referensi?buka=catatan_koreksi#b-catatan_koreksi"


@bp.post("/catatan-koreksi")
@izin.perlu_admin
def simpan_catatan_koreksi():
    """Tambah atau sunting satu catatan koreksi baku.

    butir_id diperiksa keberadaannya: pilihan yang dikirim peramban bisa saja
    menunjuk butir yang baru dihapus, dan rujukan yang putus membuat catatannya
    tidak pernah ditawarkan di mana pun.
    """
    cid, teks = ke_int(request.form.get("id")), _v("teks")
    if not teks:
        return _galat("Bunyi catatan koreksi wajib diisi.")
    bid = ke_int(request.form.get("butir_id"))
    if bid and not g.k.execute("SELECT 1 FROM ref_kelengkapan_butir WHERE id=?",
                               (bid,)).fetchone():
        return _galat("Butir kelengkapan tujuan catatan itu tidak ditemukan.")
    aktif = 1 if request.form.get("aktif") else 0
    if cid:
        g.k.execute("UPDATE ref_catatan_koreksi SET teks=?, butir_id=?, aktif=? WHERE id=?",
                    (teks[:300], bid, aktif, cid))
    else:
        urut = g.k.execute("SELECT COALESCE(MAX(urut),0)+1 FROM ref_catatan_koreksi"
                           ).fetchone()[0]
        g.k.execute("INSERT INTO ref_catatan_koreksi (teks,butir_id,aktif,urut) "
                    "VALUES (?,?,?,?)", (teks[:300], bid, aktif, urut))
    g.k.commit()
    return _ke(DAFTAR_CATATAN, "pesan=catatan_koreksi")


@bp.post("/catatan-koreksi/hapus")
@izin.perlu_admin
def hapus_catatan_koreksi():
    """Aman dihapus kapan saja: pradaftar menyimpan teksnya, bukan rujukannya."""
    g.k.execute("DELETE FROM ref_catatan_koreksi WHERE id=?",
                (ke_int(request.form.get("id")),))
    g.k.commit()
    return _ke(DAFTAR_CATATAN, "pesan=catatan_koreksi_hapus")


@bp.post("/kelengkapan")
@izin.perlu_admin
def simpan_kelengkapan():
    """Bunyi butir dan wajib-tidaknya. Susunannya tidak diubah dari layar.

    Yang dikirim peramban cuma butir yang tampil, jadi yang diperbarui hanya
    itu — dan `wajib` dibaca dari ada-tidaknya kotak centang, bukan dari nilai
    kiriman, karena kotak yang tidak dicentang memang tidak ikut terkirim.
    """
    fid = ke_int(request.form.get("id"))
    if not fid:
        return _galat("Formulir kelengkapan tidak dikenali.")
    ids = [ke_int(x.split("_", 1)[1]) for x in request.form
           if x.startswith("nama_") and ke_int(x.split("_", 1)[1])]
    milik = {r["id"] for r in g.k.execute(
        "SELECT id FROM ref_kelengkapan_butir WHERE kelengkapan_id=?", (fid,))}
    for bid in ids:
        if bid not in milik:               # butir formulir lain: jangan disentuh
            continue
        nama = (request.form.get(f"nama_{bid}") or "").strip()
        if not nama:
            continue                       # bunyi butir tidak boleh dikosongkan
        g.k.execute("UPDATE ref_kelengkapan_butir SET nama=?, wajib=? WHERE id=?",
                    (nama, 1 if request.form.get(f"wajib_{bid}") else 0, bid))
    g.k.commit()
    return _ke(f"/referensi?buka=kelengkapan-{fid}#b-kelengkapan-{fid}",
               "pesan=referensi")


# ------------------------------------------------------ susun formulir
# Halaman kerja sendiri untuk satu formulir kelengkapan: menambah butir yang
# diminta Kantah (mis. Peta Analisis), mengubah urutan, memindah butir ke
# kelompok lain, dan membuat formulir untuk jenis permohonan lain. Logikanya
# di susun_kelengkapan.py; di sini cuma izin dan pengalihan.
S = susun_kelengkapan


def _ke_susun(fid, tanya="pesan=referensi", jangkar=""):
    return _ke(f"/referensi/kelengkapan/{fid}" + (f"#{jangkar}" if jangkar else ""), tanya)


def _galat_susun(fid, teks):
    alamat = f"/referensi/kelengkapan/{fid}" if fid else "/referensi/kelengkapan/baru"
    return redirect(alamat + "?galat=" + up.quote(teks), 303)


@bp.get("/kelengkapan/baru")
@izin.perlu_admin
def formulir_baru():
    return web.halaman_formulir_baru(g.pengguna, pradaftar.daftar_formulir(g.k),
                                     referensi.semua(g.k)["jenis_hak"], kabar.pesan())


@bp.post("/kelengkapan/baru")
@izin.perlu_admin
def buat_formulir():
    try:
        fid = S.simpan_formulir(g.k, request.form)
    except S.Galat as ex:
        return _galat_susun(None, str(ex))
    return _ke_susun(fid, "pesan=formulir_baru")


@bp.get("/kelengkapan/<int:fid>")
def susun(fid):
    d = S.muat(g.k, fid)
    if not d:
        return redirect("/referensi?buka=kelengkapan#r-lengkap", 303)
    return web.halaman_susun_kelengkapan(
        g.pengguna, d, referensi.semua(g.k)["jenis_hak"], kabar.pesan(),
        boleh_ubah=izin.admin(g.pengguna), induk_pilih=ke_int(request.args.get("induk")),
        dibuka=ke_int(request.args.get("ubah")))


@bp.post("/kelengkapan/<int:fid>")
@izin.perlu_admin
def simpan_kepala(fid):
    try:
        S.simpan_formulir(g.k, request.form, fid)
    except S.Galat as ex:
        return _galat_susun(fid, str(ex))
    return _ke_susun(fid)


@bp.post("/kelengkapan/<int:fid>/hapus")
@izin.perlu_admin
def hapus_formulir(fid):
    hasil = S.hapus_formulir(g.k, fid)
    if hasil == "nonaktif":
        return _ke_susun(fid, "pesan=formulir_nonaktif")
    return _ke("/referensi#r-lengkap", "pesan=formulir_hapus")


@bp.post("/kelengkapan/<int:fid>/nomori")
@izin.perlu_admin
def nomori(fid):
    S.nomori(g.k, fid)
    return _ke_susun(fid, "pesan=butir_nomor")


@bp.post("/kelengkapan/<int:fid>/butir")
@izin.perlu_admin
def simpan_butir(fid):
    bid = ke_int(request.form.get("id")) or None
    try:
        bid = S.simpan_butir(g.k, fid, request.form, bid)
    except S.Galat as ex:
        return _galat_susun(fid, str(ex))
    return _ke_susun(fid, "pesan=butir", f"s-{bid}")


@bp.post("/kelengkapan/<int:fid>/butir/<int:bid>/geser")
@izin.perlu_admin
def geser_butir(fid, bid):
    try:
        if request.form.get("sasaran"):
            S.pindah_ke(g.k, fid, bid, ke_int(request.form.get("sasaran")),
                        request.form.get("posisi") or "sesudah")
        else:
            S.geser(g.k, fid, bid, request.form.get("arah") or "")
    except S.Galat as ex:
        if request.headers.get("X-Diam"):
            return str(ex), 400, {"Content-Type": "text/plain; charset=utf-8"}
        return _galat_susun(fid, str(ex))
    if request.headers.get("X-Diam"):     # seret-lepas dari app.js: cukup "beres"
        return "", 204
    return redirect(f"/referensi/kelengkapan/{fid}#s-{bid}", 303)


@bp.post("/kelengkapan/<int:fid>/butir/<int:bid>/hapus")
@izin.perlu_admin
def hapus_butir(fid, bid):
    try:
        hasil = S.hapus_butir(g.k, fid, bid)
    except S.Galat as ex:
        return _galat_susun(fid, str(ex))
    return _ke_susun(fid, "pesan=butir_" + hasil)


@bp.post("/kelengkapan/<int:fid>/butir/<int:bid>/pulihkan")
@izin.perlu_admin
def pulihkan_butir(fid, bid):
    try:
        S.pulihkan_butir(g.k, fid, bid)
    except S.Galat as ex:
        return _galat_susun(fid, str(ex))
    return _ke_susun(fid, "pesan=butir", f"s-{bid}")
