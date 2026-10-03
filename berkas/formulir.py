# -*- coding: utf-8 -*-
"""Penyimpanan formulir berkas, dan kueri untuk daftarnya.

Satu berkas tersebar di sebelas tabel. simpan() menulis semuanya dalam satu
transaksi: kolom induk di-UPDATE, sedangkan daftar (pihak, riwayat, dokumen
pendukung, pendapat anggota) dihapus lalu ditulis ulang seluruhnya. Cara itu
dipilih supaya baris yang dihapus petugas di formulir benar-benar hilang,
tanpa perlu melacak mana yang berubah.

Tidak ada HTTP di sini; yang masuk hanya request.form.
"""
from . import db, izin, util

_n = util.teks_atau_none
_i = util.ke_int


def daftar(k, pengguna):
    """Berkas yang boleh dilihat pengguna ini, berikut angka ringkasannya.

    Admin mendapat semuanya. Petugas mendapat miliknya sendiri ditambah arsip
    impor yang tidak bertuan. Angka ringkasannya dihitung dari baris yang sama,
    supaya yang tertulis "61 berkas" memang 61 baris yang kelihatan.
    """
    saring, parameter = izin.saringan_daftar(pengguna)
    baris = [dict(r) for r in k.execute(f"""
        SELECT b.id, b.status, b.jenis_kegiatan, b.jenis_hak_dimohon AS kode_hak,
               b.dibuat_oleh, u.nama AS pemilik,
               (SELECT nama FROM pihak WHERE berkas_id=b.id AND peran IN ('penerima_hak','pemohon')
                 ORDER BY urut LIMIT 1) AS penerima,
               (SELECT nama FROM pihak WHERE berkas_id=b.id AND peran='kuasa' LIMIT 1) AS kuasa,
               d.nama AS desa, c.nama AS kecamatan, t.luas_pbt,
               r.nomor AS nomor_risalah, s.nomor AS nomor_sk
        FROM berkas b
        LEFT JOIN bidang_tanah t ON t.berkas_id=b.id
        LEFT JOIN ref_desa d ON d.id=t.desa_id
        LEFT JOIN ref_kecamatan c ON c.id=d.kecamatan_id
        LEFT JOIN risalah r ON r.berkas_id=b.id
        LEFT JOIN sk s ON s.berkas_id=b.id
        LEFT JOIN pengguna u ON u.id=b.dibuat_oleh
        {saring}
        ORDER BY b.id DESC""", parameter)]
    for b in baris:
        b["boleh_ubah"] = izin.boleh_ubah(pengguna, b["dibuat_oleh"])

    terlihat = [b["id"] for b in baris]
    tanya = ",".join("?" * len(terlihat)) or "NULL"
    ringkas = {
        "total": len(baris),
        "draf": sum(1 for b in baris if b["status"] == "draf"),
        "selesai": sum(1 for b in baris if b["status"] == "selesai"),
        "dokumen": k.execute(f"SELECT COUNT(*) FROM dokumen_terbit "
                             f"WHERE berkas_id IN ({tanya})", terlihat).fetchone()[0],
        "desa": k.execute("SELECT COUNT(*) FROM ref_desa").fetchone()[0],
    }
    return baris, ringkas


def saring(baris, cari="", hak="", status="", kegiatan="", kecamatan=""):
    """Pilih baris daftar() yang cocok dengan saringan di atas tabel.

    Dikerjakan di sini, bukan di SQL daftar(), supaya angka ringkasan tetap
    dihitung dari seluruh berkas yang boleh dilihat — saringan hanya memilih
    mana yang ditampilkan. Kata cari dipecah per kata dan semuanya harus ada,
    jadi "wakaf tapa" menemukan berkas wakaf di Kecamatan Tapa.
    """
    kata = cari.lower().split()

    def cocok(b):
        if hak and (b["kode_hak"] or "") != hak:
            return False
        if status and b["status"] != status:
            return False
        if kegiatan and b["jenis_kegiatan"] != kegiatan:
            return False
        if kecamatan and (b["kecamatan"] or "") != kecamatan:
            return False
        if kata:
            teks = " ".join(str(x or "").lower() for x in (
                f"{b['id']:04d}", b["penerima"], b["kuasa"], b["desa"], b["kecamatan"],
                b["nomor_risalah"], b["nomor_sk"], b["kode_hak"], b["pemilik"]))
            return all(x in teks for x in kata)
        return True

    return [b for b in baris if cocok(b)]


def terbit(k, berkas_id):
    """Dokumen yang pernah dicetak untuk berkas ini, terbaru di atas."""
    return [dict(r) for r in k.execute(
        "SELECT * FROM dokumen_terbit WHERE berkas_id=? ORDER BY id DESC", (berkas_id,))]


def simpan(k, f, berkas_id=None, pengguna_id=None):
    """Tulis seluruh isi formulir berkas. f = request.form.

    getlist() dipakai, bukan get(): medan yang ada tapi kosong harus terbaca
    sebagai "" dan menimpa nilai lama, bukan jatuh ke nilai bawaan.
    """
    satu = lambda n, d="": (f.getlist(n) or [d])[0].strip()
    banyak = lambda n: [x.strip() for x in f.getlist(n)]
    c = k.cursor()

    kolom = (satu("nomor_berkas") or None, satu("tanggal_permohonan") or None,
             satu("jenis_hak_dimohon") or "HM", satu("jenis_hak_rekomendasi") or None,
             satu("jenis_kegiatan") or "baru", satu("asal_tanah") or "tanah_negara",
             satu("kewenangan") or "kantah", satu("status") or "draf",
             satu("catatan") or None)
    if berkas_id:
        c.execute("UPDATE berkas SET nomor_berkas=?, tanggal_permohonan=?, jenis_hak_dimohon=?, "
                  "jenis_hak_rekomendasi=?, jenis_kegiatan=?, asal_tanah=?, kewenangan=?, "
                  "status=?, catatan=?, diubah=? WHERE id=?",
                  kolom + (db.sekarang(), berkas_id))
    else:
        berkas_id = db.sisip_id(
            c, "INSERT INTO berkas (nomor_berkas,tanggal_permohonan,jenis_hak_dimohon,"
               "jenis_hak_rekomendasi,jenis_kegiatan,asal_tanah,kewenangan,status,catatan,"
               "dibuat_oleh) VALUES (?,?,?,?,?,?,?,?,?,?)", kolom + (pengguna_id,))

    # ---- pihak: ditulis ulang seluruhnya
    c.execute("DELETE FROM pihak WHERE berkas_id=?", (berkas_id,))
    if satu("penerima_nama"):
        pihak_id = db.sisip_id(
            c, "INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,ttl,jenis_kelamin,"
               "alamat,pekerjaan,urut) VALUES (?,'penerima_hak',?,?,?,?,?,?,?,0)",
            (berkas_id, satu("penerima_jenis_subjek") or "perorangan",
             satu("penerima_nama"), _n(satu("penerima_nik")), _n(satu("penerima_ttl")),
             _n(satu("penerima_jenis_kelamin")), _n(satu("penerima_alamat")),
             _n(satu("penerima_pekerjaan"))))
        if satu("penerima_jenis_subjek") == "badan_hukum" or satu("bh_akta_nomor"):
            c.execute(db.upsert(
                "pihak_badan_hukum",
                "pihak_id,bentuk,kedudukan,akta_nomor,akta_tanggal,notaris,"
                "pengesahan_nomor,pengesahan_tanggal,npwp,nib,wakil_nama,wakil_jabatan",
                kunci="pihak_id"),
                      (pihak_id, _n(satu("bh_bentuk")), _n(satu("bh_kedudukan")),
                       _n(satu("bh_akta_nomor")), _n(satu("bh_akta_tanggal")),
                       _n(satu("bh_notaris")), _n(satu("bh_pengesahan_nomor")),
                       _n(satu("bh_pengesahan_tanggal")), _n(satu("bh_npwp")),
                       _n(satu("bh_nib")), _n(satu("bh_wakil_nama")),
                       _n(satu("bh_wakil_jabatan"))))
            # Rincian untuk SK Hak Pakai. Formulir selain Hak Pakai membawanya
            # sebagai medan tersembunyi (web._rincian_bh_hak_pakai), jadi
            # baris yang ditulis ulang ini tidak kehilangan isinya.
            kol = [x[0] for x in db.KOLOM_BH_RINCIAN]
            c.execute(f"UPDATE pihak_badan_hukum SET {', '.join(x + '=?' for x in kol)} "
                      "WHERE pihak_id=?",
                      [_n(satu("bh_" + x)) for x in kol] + [pihak_id])
    if satu("kuasa_nama"):
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,urut) "
                  "VALUES (?,'kuasa','perorangan',?,?,1)",
                  (berkas_id, satu("kuasa_nama"), _n(satu("kuasa_nik"))))
    # Pihak lain dibawa lengkap dengan identitasnya: Nazhir kedua dan seterusnya
    # dicetak Risalah wakaf per orang, jadi NIK/TTL/pekerjaannya diisi di barisnya.
    lain = (banyak("lain_peran"), banyak("lain_nama"), banyak("lain_nik"),
            banyak("lain_ttl"), banyak("lain_pekerjaan"), banyak("lain_alamat"))
    for i, nama in enumerate(lain[1]):
        if not nama:
            continue
        ambil = lambda kol: lain[kol][i] if i < len(lain[kol]) else ""
        c.execute("INSERT INTO pihak (berkas_id,peran,jenis_subjek,nama,nik,ttl,pekerjaan,"
                  "alamat,urut) VALUES (?,?,'perorangan',?,?,?,?,?,?)",
                  (berkas_id, ambil(0) or "saksi", nama, _n(ambil(2)), _n(ambil(3)),
                   _n(ambil(4)), _n(ambil(5)), 2 + i))

    # ---- bidang tanah
    kes = satu("kesesuaian_lain") or satu("kesesuaian")
    c.execute(db.upsert(
        "bidang_tanah",
        "berkas_id,desa_id,nomor_pbt,tanggal_pbt,nib,luas_pbt,luas_surat,"
        "batas_utara,batas_timur,batas_selatan,batas_barat,penggunaan_sekarang,"
        "rencana_penggunaan,rtrw,kesesuaian,tanggal_peta_analisis,"
        "uraian_penguasaan_fisik,uraian_selisih_luas"),
              (berkas_id, _i(satu("desa_id")), _n(satu("nomor_pbt")), _n(satu("tanggal_pbt")),
               _n(satu("nib")), _i(satu("luas_pbt")), _i(satu("luas_surat")),
               _n(satu("batas_utara")), _n(satu("batas_timur")), _n(satu("batas_selatan")),
               _n(satu("batas_barat")), _n(satu("penggunaan_sekarang")),
               _n(satu("rencana_penggunaan")), _n(satu("rtrw")), _n(kes),
               _n(satu("tanggal_peta_analisis")),
               _n(satu("uraian_penguasaan_fisik")), _n(satu("uraian_selisih_luas"))))

    # ---- riwayat
    c.execute("DELETE FROM riwayat_perolehan WHERE berkas_id=?", (berkas_id,))
    uraian, bukti = banyak("riwayat_uraian"), banyak("riwayat_bukti")
    n = 0
    for i, u in enumerate(uraian):
        if u:
            c.execute("INSERT INTO riwayat_perolehan (berkas_id,urut,uraian,dokumen_bukti) "
                      "VALUES (?,?,?,?)",
                      (berkas_id, n, u, bukti[i] if i < len(bukti) else None))
            n += 1

    # ---- hak asal
    if satu("asal_sertipikat") or satu("asal_nomor_sk"):
        c.execute(db.upsert(
            "hak_asal",
            "berkas_id,jenis_hak_lama,nomor_sertipikat,nomor_sk,tanggal_sk,"
            "tanggal_berakhir,luas"),
                  (berkas_id, _n(satu("asal_jenis_hak")), _n(satu("asal_sertipikat")),
                   _n(satu("asal_nomor_sk")), _n(satu("asal_tanggal_sk")),
                   _n(satu("asal_tanggal_berakhir")), _i(satu("asal_luas"))))
    else:
        c.execute("DELETE FROM hak_asal WHERE berkas_id=?", (berkas_id,))

    # ---- dokumen pendukung: slot baku dulu (urutannya tetap), baru sisanya
    c.execute("DELETE FROM dokumen_pendukung WHERE berkas_id=?", (berkas_id,))
    n = 0
    for kategori, _, _, _ in db.dokumen_baku(satu("jenis_hak_dimohon")):
        u = satu("baku_" + kategori)
        # Akta Ikrar Wakaf dan Pengesahan Nazhir diisi per unsur; uraiannya boleh kosong
        # (disusun konteks.py), jenis akta saja belum berarti suratnya ada
        rincian = {x: _n(satu(f"baku_{x}_{kategori}"))
                   for x, _, _ in db.RINCIAN_BAKU.get(kategori, [])}
        if u or any(v for x, v in rincian.items() if x != "jenis"):
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian,"
                      "jenis,nomor,tanggal,pejabat,wilayah_pejabat) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (berkas_id, n, kategori, u or "", satu("baku_asli_" + kategori) or "",
                       *(rincian.get(x) for x in db.KOLOM_RINCIAN)))
            n += 1
    du, dk, dg = banyak("dokumen_uraian"), banyak("dokumen_keaslian"), banyak("dokumen_kategori")
    for i, u in enumerate(du):
        if u:
            kategori = (dg[i] if i < len(dg) else "") or "tambahan"
            if kategori in db.KATEGORI_BAKU:      # slot baku hanya diisi lewat isiannya sendiri
                kategori = "tambahan"
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian) "
                      "VALUES (?,?,?,?,?)",
                      (berkas_id, n, kategori, u, dk[i] if i < len(dk) else ""))
            n += 1

    # ---- pemeriksaan
    c.execute(db.upsert(
        "pemeriksaan",
        "berkas_id,tanggal_surat_tugas,tanggal_bap,panitia_id,keberatan"),
              (berkas_id, _n(satu("tanggal_surat_tugas")), _n(satu("tanggal_bap")),
               _i(satu("panitia_id")), _n(satu("keberatan"))))

    # ---- pendapat anggota
    c.execute("DELETE FROM pendapat_anggota WHERE berkas_id=?", (berkas_id,))
    pn, pp, pa = banyak("pendapat_nama"), banyak("pendapat_peran"), banyak("pendapat_alasan")
    ps, pt, pw = banyak("pendapat_setuju"), banyak("pendapat_ttd"), banyak("pendapat_diwakili")
    n = 0
    for i, nama in enumerate(pn):
        if nama:
            c.execute("INSERT INTO pendapat_anggota (berkas_id,urut,nama,peran,setuju,alasan,"
                      "menandatangani,diwakili_oleh) VALUES (?,?,?,?,?,?,?,?)",
                      (berkas_id, n, nama, pp[i] if i < len(pp) else None,
                       1 if (ps[i] if i < len(ps) else "1") == "1" else 0,
                       pa[i] if i < len(pa) else None,
                       1 if (pt[i] if i < len(pt) else "1") == "1" else 0,
                       _n(pw[i]) if i < len(pw) else None))
            n += 1

    # ---- risalah & sk
    c.execute(db.upsert(
        "risalah",
        "berkas_id,nomor,tanggal,kesimpulan,jangka_waktu_tahun,alasan"),
              (berkas_id, _n(satu("risalah_nomor")), _n(satu("risalah_tanggal")),
               satu("risalah_kesimpulan") or "dikabulkan", _i(satu("risalah_jangka")),
               _n(satu("risalah_alasan"))))
    c.execute(db.upsert(
        "sk",
        "berkas_id,nomor,tanggal,pejabat_nama,pejabat_nip,validasi_pph,uang_pemasukan"),
              (berkas_id, _n(satu("sk_nomor")), _n(satu("sk_tanggal")),
               _n(satu("sk_pejabat_nama")), _n(satu("sk_pejabat_nip")),
               _n(satu("sk_validasi_pph")), _i(satu("sk_uang"))))
    k.commit()
    return berkas_id
