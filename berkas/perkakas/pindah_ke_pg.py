# -*- coding: utf-8 -*-
"""Pindahkan isi basis data SQLite ke PostgreSQL.

    python -m berkas.perkakas.pindah_ke_pg --lihat
    python -m berkas.perkakas.pindah_ke_pg

Asal diambil dari data/berkas.db (atau --dari), tujuan dari DB_URL di .env.
Nomor id dipertahankan apa adanya: dokumen yang sudah terbit menyebut nomor
berkas di nama filenya, dan riwayat cetak menunjuk id — kalau id bergeser,
tautan antar-tabel putus tanpa ada yang kelihatan salah.

Jalannya satu transaksi. Kalau ada satu baris saja yang gagal masuk, seluruh
pemindahan dibatalkan dan basis data tujuan kembali seperti semula.

Yang TIDAK ikut pindah: folder data/foto/ dan keluaran/. Keduanya berkas biasa
di cakram, bukan isi basis data — salin sendiri dengan robocopy atau rsync.
"""
import argparse
import os
import sqlite3
import sys

from .. import basis, db, jalur, konfigurasi

# Urutan tabel dihitung dari kunci asingnya, bukan ditulis tangan: menambah
# tabel baru di skema tidak boleh membuat perkakas ini diam-diam salah urut.


def _urutan_tabel(k):
    """Nama tabel, induk lebih dulu daripada anaknya."""
    tabel = [r[0] for r in k.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    induk = {t: set() for t in tabel}
    for t in tabel:
        for fk in k.execute(f"PRAGMA foreign_key_list({t})"):
            if fk[2] != t:                      # abaikan rujukan ke diri sendiri
                induk[t].add(fk[2])

    selesai, urut = set(), []
    while len(urut) < len(tabel):
        siap = [t for t in tabel if t not in selesai and induk[t] <= selesai]
        if not siap:
            sisa = [t for t in tabel if t not in selesai]
            raise SystemExit(f"  ! kunci asing melingkar pada: {', '.join(sisa)}")
        for t in sorted(siap):
            urut.append(t)
            selesai.add(t)
    return urut


def _isi(k, tabel):
    kolom = [r[1] for r in k.execute(f"PRAGMA table_info({tabel})")]
    baris = k.execute(f"SELECT {','.join(kolom)} FROM {tabel}").fetchall()
    return kolom, [tuple(b) for b in baris]


def _punya_id(kolom):
    return "id" in kolom


def pindahkan(asal_berkas, tujuan, lihat_saja=False, paksa=False):
    if not os.path.isfile(asal_berkas):
        raise SystemExit(f"  ! basis data asal tidak ada: {asal_berkas}")
    if not tujuan.postgres:
        raise SystemExit("  ! DB_URL belum menunjuk PostgreSQL. Setel di .env dulu.")

    asal = sqlite3.connect(asal_berkas)
    asal.row_factory = sqlite3.Row
    urut = _urutan_tabel(asal)

    print(f"  asal   : {asal_berkas}")
    print(f"  tujuan : {tujuan.sebutan}")
    print()

    rencana = []
    for t in urut:
        kolom, baris = _isi(asal, t)
        rencana.append((t, kolom, baris))
        if baris:
            print(f"    {t:24} {len(baris):6} baris")
    total = sum(len(b) for _, _, b in rencana)
    print(f"    {'':24} {'-' * 6}")
    print(f"    {'jumlah':24} {total:6} baris")

    if lihat_saja:
        print("\n  (--lihat: tidak ada yang ditulis)")
        asal.close()
        return

    ke = basis.buka(tujuan)
    try:
        # Yang dicari tanda basis datanya SUDAH DIPAKAI, bukan sekadar berisi.
        # siapkan() selalu mengisi tabel acuan dan satu akun admin, jadi
        # keduanya bukan tanda apa-apa. Yang menandakan orang sudah bekerja di
        # sana: sudah ada berkas, atau akunnya bertambah.
        dipakai = []
        n_berkas = ke.execute("SELECT COUNT(*) FROM berkas").fetchone()[0]
        n_pengguna = ke.execute("SELECT COUNT(*) FROM pengguna").fetchone()[0]
        if n_berkas:
            dipakai.append(f"{n_berkas} berkas")
        if n_pengguna > 1:
            dipakai.append(f"{n_pengguna} akun pengguna")
        if dipakai and not paksa:
            raise SystemExit(
                "  ! basis data tujuan sudah dipakai: " + ", ".join(dipakai)
                + "\n    Jalankan lagi dengan --paksa kalau memang mau ditimpa.")

        print("\n  mengosongkan tujuan...")
        for t in reversed(urut):
            ke.execute(f"DELETE FROM {t}")

        print("  memindahkan...")
        for t, kolom, baris in rencana:
            if not baris:
                continue
            # OVERRIDING SYSTEM VALUE: kolom id di PostgreSQL dibuat GENERATED
            # ALWAYS supaya aplikasi tidak bisa mengisinya sendiri. Hanya di
            # sini id lama dipaksa masuk, supaya nomornya tidak bergeser.
            timpa = " OVERRIDING SYSTEM VALUE" if _punya_id(kolom) else ""
            sql = (f"INSERT INTO {t} ({','.join(kolom)}){timpa} "
                   f"VALUES ({','.join('?' * len(kolom))})")
            ke.executemany(sql, baris)

        print("  menyetel ulang penomoran otomatis...")
        for t, kolom, _ in rencana:
            if _punya_id(kolom):
                ke.execute(
                    "SELECT setval(pg_get_serial_sequence(?, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + t + "), 0) + 1, false)", (t,))

        print("  memeriksa hasil...")
        salah = []
        for t, _, baris in rencana:
            n = ke.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            if n != len(baris):
                salah.append(f"{t}: asal {len(baris)}, tujuan {n}")
        if salah:
            ke.rollback()
            raise SystemExit("  ! jumlah baris tidak cocok, pemindahan dibatalkan:\n    "
                             + "\n    ".join(salah))

        ke.commit()
        print(f"\n  selesai. {total} baris pindah, jumlah tiap tabel cocok.")
        print("  Jangan lupa menyalin folder data/foto/ dan keluaran/ juga —")
        print("  keduanya berkas di cakram, bukan isi basis data.")
    finally:
        asal.close()
        ke.close()


def main():
    p = argparse.ArgumentParser(description="Pindahkan data SQLite ke PostgreSQL.")
    p.add_argument("--dari", default=jalur.BASIS_DATA,
                   help="berkas SQLite asal (bawaan: data/berkas.db)")
    p.add_argument("--lihat", action="store_true",
                   help="tampilkan rencananya saja, tanpa menulis apa pun")
    p.add_argument("--paksa", action="store_true",
                   help="timpa tujuan walau sudah berisi data")
    a = p.parse_args()

    tujuan = konfigurasi.sambungan()
    print()
    pindahkan(a.dari, tujuan, lihat_saja=a.lihat, paksa=a.paksa)
    print()


if __name__ == "__main__":
    sys.exit(main())
