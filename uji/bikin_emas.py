# -*- coding: utf-8 -*-
"""Rekam ulang berkas acuan.

    python -m uji.bikin_emas              rekam konteks dan dokumen
    python -m uji.bikin_emas konteks      konteks saja (beberapa detik)
    python -m uji.bikin_emas dokumen      dokumen saja (beberapa menit)

KAPAN INI DIJALANKAN

Hanya di dua keadaan:

  1. Pertama kali memasang uji ini.
  2. Setelah sebuah perubahan MEMANG dimaksudkan mengubah isi dokumen -
     misalnya tata naskahnya berubah karena ada peraturan baru.

Di luar itu, jangan. Kalau uji gagal, yang benar adalah membaca selisihnya
dulu dan memastikan perubahannya memang diinginkan. Merekam ulang untuk
"membuat uji jadi hijau" sama saja dengan membuang jaring pengamannya:
kesalahan terbilang atau penomoran akan ikut terekam sebagai kebenaran baru.

Rekamannya ditulis ke `uji/emas/`, yang tidak dilacak git karena berisi data
pribadi pemohon - nama, NIK, alamat, letak tanah.
"""
import os
import sys
import time

from . import dasar


def _bersihkan(jenis, dipakai):
    """Buang rekaman berkas yang sudah tidak ada lagi di basis data."""
    folder = os.path.join(dasar.DIR_EMAS, jenis)
    if not os.path.isdir(folder):
        return
    for nama in sorted(os.listdir(folder)):
        if nama not in dipakai:
            os.remove(os.path.join(folder, nama))
            print(f"  dibuang  {jenis}/{nama}  (berkasnya tidak ada lagi)")


def rekam_konteks(k):
    ids = dasar.semua_berkas(k)
    print(f"Konteks: {len(ids)} berkas")

    dipakai = set()
    for berkas_id in ids:
        potret = dasar.potret_konteks(k, berkas_id)
        if potret is None:
            continue
        nama = f"{berkas_id:04d}.json"
        dasar.tulis_emas("konteks", nama, potret)
        dipakai.add(nama)
    _bersihkan("konteks", dipakai)
    print(f"  {len(dipakai)} rekaman konteks tersimpan")


def rekam_dokumen(k):
    ids = dasar.berkas_contoh(k)
    total = len(ids) * len(dasar.JENIS_DOKUMEN)
    print(f"Dokumen: {len(ids)} berkas contoh x {len(dasar.JENIS_DOKUMEN)} = {total} dokumen")
    print("  (perakitan DOCX memang lambat, beberapa detik per dokumen)")

    dipakai, n = set(), 0
    for berkas_id in ids:
        for jenis in dasar.JENIS_DOKUMEN:
            n += 1
            mulai = time.time()
            nama = f"{berkas_id:04d}-{jenis}.txt"
            try:
                teks = dasar.rakit_teks(k, berkas_id, jenis)
            except Exception as galat:                  # noqa: BLE001
                print(f"  [{n}/{total}] GAGAL  {nama}: {galat}")
                continue
            dasar.tulis_emas("dokumen", nama, teks)
            dipakai.add(nama)
            print(f"  [{n}/{total}] {nama}  ({time.time() - mulai:.1f}s)")
    _bersihkan("dokumen", dipakai)
    print(f"  {len(dipakai)} rekaman dokumen tersimpan")


def main(argv):
    pilihan = argv[1] if len(argv) > 1 else "semua"
    if pilihan not in ("semua", "konteks", "dokumen"):
        print(__doc__)
        return 2

    mulai = time.time()
    with dasar.sambung_salinan() as k:
        if pilihan in ("semua", "konteks"):
            rekam_konteks(k)
        if pilihan in ("semua", "dokumen"):
            rekam_dokumen(k)
    print(f"\nSelesai dalam {time.time() - mulai:.1f}s. Rekaman ada di {dasar.DIR_EMAS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
