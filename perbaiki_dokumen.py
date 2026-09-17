# -*- coding: utf-8 -*-
"""Rapikan berkas lama agar cocok dengan slot dokumen baku.

    python perbaiki_dokumen.py

Surat baku (lihat db.SEMUA_BAKU) sekarang punya isian sendiri di
formulir, dikenali lewat kolom `kategori` di dokumen_pendukung. Berkas yang
diimpor sebelum itu masih menyimpannya sebagai 'wajib' biasa, jadi:

1. Baris riwayat "Bahwa ... dikuasai terus menerus ..." dihapus - kalimat itu
   dicetak template lewat {{penguasaan_fisik}}, bukan bagian daftar riwayat.
2. Tiap dokumen dicocokkan ke slotnya. Yang berasal dari Excel dicocokkan lewat
   isi kolomnya (paling tepat); sisanya lewat frasa khas.
3. Surat yang ada di Excel tapi belum ada di basis data ditambahkan.
4. Urutan dokumen dirapikan: slot baku dulu, baru tambahan dan alas hak.
5. Kalimat «Surat Penguasaan Fisik» dan «selisih luas» disimpan hanya bila
   berbeda dari kalimat yang bisa disusun sistem sendiri.

Aman dijalankan ulang; basis data disalin dulu ke data/berkas.db.bak-<waktu>.
"""
import datetime
import os
import shutil

import db
import impor_excel
import konteks
import util

FRASA_PF = "dikuasai terus menerus"

# Frasa khas tiap slot, untuk berkas yang tidak berasal dari Excel. Slot
# 'pernyataan' dan 'absentee' sengaja tidak ditebak: kalimatnya terlalu umum.
FRASA = {
    "sppf": ("penguasaan fisik",),
    "permohonan": ("surat permohonan hak", "permohonan hak yang dibuat"),
    "tanah_dipunyai": ("tanah-tanah yang dipunyai", "tanah yang dipunyai pemohon"),
    "penggunaan": ("pernyataan penggunaan tanah",),
    "keterangan_penguasaan": ("keterangan penguasaan tanah",),
    "tidak_sengketa": ("tidak dalam keadaan sengketa", "tidak sengketa"),
    "tanda_batas": ("pemasangan tanda batas",),
    "selisih": ("perbedaan luas", "tidak keberatan hasil pengukuran"),
    "kuasa": ("surat kuasa",),
}


def cadangkan():
    cap = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tujuan = f"{db.BERKAS_DB}.bak-{cap}"
    shutil.copy2(db.BERKAS_DB, tujuan)
    return tujuan


def baris_excel(k, jalur=impor_excel.SUMBER):
    """{berkas_id: (baris Excel, pengambil kolom)}. Dicocokkan berurutan lewat
    nama penerima hak, karena impor dulu melewati baris yang namanya kosong."""
    if not os.path.exists(jalur):
        return {}, []
    judul, data = impor_excel.baca(jalur)

    def ambil(r, nama):
        i = impor_excel.kol(judul, nama)
        return util.bersihkan(r[i]) if i is not None else ""

    urut = [r for r in data if ambil(r, "Atas Nama") or ambil(r, "Nama Pemohon")]
    berkas = k.execute("SELECT b.id, lower(p.nama) nama FROM berkas b "
                       "JOIN pihak p ON p.berkas_id=b.id AND p.peran='penerima_hak' "
                       "ORDER BY b.id").fetchall()
    peta, luar = {}, []
    for i, b in enumerate(berkas):
        nama = ""
        if i < len(urut):
            nama = (ambil(urut[i], "Atas Nama") or ambil(urut[i], "Nama Pemohon")).lower()
        if nama and nama == b["nama"]:
            peta[b["id"]] = (urut[i], ambil)
        else:
            luar.append(b["id"])
    return peta, luar


def _sama(a, b):
    return impor_excel._seragam(a) == impor_excel._seragam(b) if a and b else False


def _slot_dari_excel(c, bid, baris, ambil, dok):
    """Cocokkan tiap slot baku dengan isi kolom Excel-nya."""
    terisi, dipakai = {}, set()
    for kategori, _, kolom, _ in db.SEMUA_BAKU:
        nilai = ambil(baris, kolom)
        if not nilai:
            continue
        asli, isi = impor_excel._pisah_keaslian(nilai)
        cocok = None
        for x in dok:
            if x["id"] not in dipakai and _sama(x["uraian"], isi):
                cocok = x
                break
        if cocok is None:
            c.execute("INSERT INTO dokumen_pendukung (berkas_id,urut,kategori,uraian,keaslian) "
                      "VALUES (?,?,?,?,?)", (bid, 9000, kategori, isi, asli))
            terisi[kategori] = c.lastrowid
            continue
        if cocok["kategori"] != kategori:
            c.execute("UPDATE dokumen_pendukung SET kategori=? WHERE id=?", (kategori, cocok["id"]))
        dipakai.add(cocok["id"])
        terisi[kategori] = cocok["id"]
    return terisi


def _slot_dari_frasa(c, dok, terisi):
    """Tebakan untuk berkas yang tidak berasal dari Excel."""
    dipakai = set(terisi.values())
    for kategori, frasa in FRASA.items():
        if kategori in terisi:
            continue
        for x in dok:
            if x["id"] in dipakai or x["kategori"] == "alas_hak":
                continue
            isi = (x["uraian"] or "").lower()
            if any(f in isi for f in frasa):
                c.execute("UPDATE dokumen_pendukung SET kategori=? WHERE id=?",
                          (kategori, x["id"]))
                terisi[kategori] = x["id"]
                dipakai.add(x["id"])
                break
    return terisi


def _rapikan_urut(c, bid):
    """Slot baku dulu sesuai urutan SEMUA_BAKU, sisanya menyusul apa adanya."""
    dok = c.execute("SELECT id,kategori FROM dokumen_pendukung WHERE berkas_id=? "
                    "ORDER BY urut, id", (bid,)).fetchall()
    per_kategori = {}
    for x in dok:
        per_kategori.setdefault(x["kategori"], []).append(x["id"])
    urutan = []
    for kategori, _, _, _ in db.SEMUA_BAKU:
        urutan += per_kategori.get(kategori, [])
    urutan += [x["id"] for x in dok if x["kategori"] not in db.KATEGORI_BAKU]
    for i, did in enumerate(urutan):
        c.execute("UPDATE dokumen_pendukung SET urut=? WHERE id=?", (i, did))


def _simpan_uraian(c, k, bid, baris, ambil):
    """Simpan kalimat telaah dari Excel hanya bila beda dari kalimat bawaan."""
    d = konteks.muat(k, bid)
    otomatis = konteks.kalimat_otomatis(d)
    n = 0
    for kolom, _, kolom_xl, _ in db.URAIAN_BAKU:
        nilai = ambil(baris, kolom_xl)
        ada = (d["tanah"].get(kolom) or "").strip()
        baru = nilai if nilai and not _sama(nilai, otomatis[kolom]) else None
        if (baru or "") != ada:
            c.execute(f"UPDATE bidang_tanah SET {kolom}=? WHERE berkas_id=?", (baru, bid))
            n += 1
    return n


def jalankan(k):
    c = k.cursor()
    peta, luar = baris_excel(k)
    n_riwayat = n_slot = n_uraian = 0

    # ejaan keaslian yang tidak ada di pilihan formulir akan hilang begitu berkas
    # disimpan ulang, jadi dibakukan dulu
    n_keaslian = 0
    for ejaan, baku in impor_excel.KEASLIAN.items():
        r = c.execute("UPDATE dokumen_pendukung SET keaslian=? "
                      "WHERE lower(keaslian)=? AND keaslian<>?", (baku, ejaan, baku))
        n_keaslian += r.rowcount

    for b in k.execute("SELECT id FROM berkas ORDER BY id").fetchall():
        bid = b["id"]
        for r in c.execute("SELECT id FROM riwayat_perolehan WHERE berkas_id=? "
                           "AND lower(uraian) LIKE ?", (bid, f"%{FRASA_PF}%")).fetchall():
            c.execute("DELETE FROM riwayat_perolehan WHERE id=?", (r["id"],))
            n_riwayat += 1

        dok = c.execute("SELECT id,kategori,uraian FROM dokumen_pendukung WHERE berkas_id=? "
                        "ORDER BY urut, id", (bid,)).fetchall()
        sebelum = {x["kategori"] for x in dok if x["kategori"] in db.KATEGORI_BAKU}
        terisi = {}
        if bid in peta:
            terisi = _slot_dari_excel(c, bid, peta[bid][0], peta[bid][1], dok)
        terisi = _slot_dari_frasa(c, dok, terisi)
        n_slot += len(set(terisi) - sebelum)
        _rapikan_urut(c, bid)
        k.commit()
        if bid in peta:
            n_uraian += _simpan_uraian(c, k, bid, peta[bid][0], peta[bid][1])
    k.commit()
    return n_riwayat, n_slot, n_uraian, n_keaslian, luar


def main():
    if not os.path.exists(db.BERKAS_DB):
        print("Basis data belum ada:", db.BERKAS_DB)
        return 1
    salinan = cadangkan()
    print("Salinan basis data:", os.path.basename(salinan))
    k = db.siapkan()
    n_riwayat, n_slot, n_uraian, n_keaslian, luar = jalankan(k)
    print(f"  baris riwayat penguasaan fisik dihapus    : {n_riwayat}")
    print(f"  dokumen masuk slot baku                   : {n_slot}")
    print(f"  kalimat telaah khusus disimpan            : {n_uraian}")
    print(f"  ejaan keaslian dibakukan                  : {n_keaslian}")
    if luar:
        print(f"  berkas di luar Excel (ditebak lewat frasa): "
              f"{', '.join(str(x) for x in luar)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
