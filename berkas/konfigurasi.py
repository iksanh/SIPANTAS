# -*- coding: utf-8 -*-
"""Setelan yang berbeda antar-pemasangan: basis data, kunci rahasia, alamat.

Urutan pembacaan, yang di atas menang:

    1. variabel lingkungan          (systemd, Docker, set di shell)
    2. berkas .env di samping app/  (paling praktis di komputer kantor)
    3. nilai bawaan di berkas ini

Yang di atas menang supaya satu setelan bisa ditimpa sekali jalan tanpa
menyunting berkas apa pun — berguna saat menguji atau memulihkan keadaan.

.env tidak ikut dilacak git (lihat .gitignore): isinya kata sandi basis data.
"""
import os
import urllib.parse as up

from . import jalur

BERKAS_ENV = os.path.join(jalur.AKAR, ".env")


def _baca_env(jalur_berkas=BERKAS_ENV):
    """Pembaca .env seadanya: NAMA=nilai per baris, # untuk komentar.

    Tanda kutip di sekeliling nilai dibuang, karena orang cenderung
    menuliskannya. Tidak ada penafsiran $VARIABEL — sebuah kata sandi yang
    memuat tanda $ harus tetap terbaca apa adanya.
    """
    hasil = {}
    try:
        with open(jalur_berkas, encoding="utf-8") as fh:
            for baris in fh:
                baris = baris.strip()
                if not baris or baris.startswith("#") or "=" not in baris:
                    continue
                nama, _, nilai = baris.partition("=")
                nilai = nilai.strip()
                if len(nilai) >= 2 and nilai[0] == nilai[-1] and nilai[0] in "\"'":
                    nilai = nilai[1:-1]
                hasil[nama.strip()] = nilai
    except OSError:
        pass
    return hasil


_ENV = _baca_env()


def ambil(nama, bawaan=""):
    """Satu setelan, menurut urutan di atas."""
    nilai = os.environ.get(nama)
    if nilai is None:
        nilai = _ENV.get(nama, bawaan)
    return nilai


def benar(nama, bawaan=False):
    """Setelan ya/tidak. Kosong berarti tidak."""
    nilai = ambil(nama, "1" if bawaan else "").strip().lower()
    return nilai not in ("", "0", "tidak", "false", "no")


def angka(nama, bawaan):
    try:
        return int(ambil(nama, "") or bawaan)
    except ValueError:
        return bawaan


# ------------------------------------------------------------- basis data
JENIS_SQLITE = "sqlite"
JENIS_POSTGRES = "postgres"


class Sambungan:
    """Ke mana harus menyambung, sudah terurai.

    jenis      'sqlite' atau 'postgres'
    argumen    kata kunci siap pakai untuk penggeraknya
    sebutan    teks aman untuk dicetak — kata sandinya tidak ikut
    """

    def __init__(self, jenis, argumen, sebutan):
        self.jenis = jenis
        self.argumen = argumen
        self.sebutan = sebutan

    @property
    def postgres(self):
        return self.jenis == JENIS_POSTGRES

    def __repr__(self):
        return f"<Sambungan {self.sebutan}>"


def _dari_url(url):
    u = up.urlparse(url)
    skema = u.scheme.lower()

    if skema == "sqlite":
        # sqlite:///D:/dir/berkas.db  atau  sqlite:///data/berkas.db (relatif AKAR)
        berkas = up.unquote(u.path or "")
        berkas = berkas.lstrip("/") if not os.path.isabs(berkas.lstrip("/")) else berkas.lstrip("/")
        if not berkas:
            berkas = jalur.BASIS_DATA
        elif not os.path.isabs(berkas):
            berkas = os.path.join(jalur.AKAR, berkas)
        return Sambungan(JENIS_SQLITE, {"berkas": berkas}, f"sqlite {berkas}")

    if skema in ("postgres", "postgresql"):
        argumen = {
            "host": u.hostname or "127.0.0.1",
            "port": u.port or 5432,
            "user": up.unquote(u.username or "postgres"),
            "password": up.unquote(u.password or ""),
            "dbname": up.unquote((u.path or "").lstrip("/")) or "panitia_a",
        }
        # ?sslmode=require dan kawan-kawannya diteruskan apa adanya
        for nama, nilai in up.parse_qsl(u.query):
            argumen[nama] = nilai
        return Sambungan(JENIS_POSTGRES, argumen,
                         f"postgres {argumen['user']}@{argumen['host']}:"
                         f"{argumen['port']}/{argumen['dbname']}")

    raise ValueError(
        f"DB_URL tidak dikenal: {skema!r}. Yang didukung 'sqlite' dan 'postgresql'.")


def _dari_bagian():
    """Alternatif DB_URL: setelan per bagian, supaya kata sandi yang memuat
    tanda @ atau / tidak perlu disandikan dulu seperti di dalam URL."""
    argumen = {
        "host": ambil("DB_HOST", "127.0.0.1"),
        "port": angka("DB_PORT", 5432),
        "user": ambil("DB_USER", "postgres"),
        "password": ambil("DB_PASSWORD", ""),
        "dbname": ambil("DB_NAMA", "panitia_a"),
    }
    if ambil("DB_SSLMODE"):
        argumen["sslmode"] = ambil("DB_SSLMODE")
    return Sambungan(JENIS_POSTGRES, argumen,
                     f"postgres {argumen['user']}@{argumen['host']}:"
                     f"{argumen['port']}/{argumen['dbname']}")


def sambungan():
    """Tujuan basis data untuk pemasangan ini."""
    url = ambil("DB_URL").strip()
    if url:
        return _dari_url(url)
    if ambil("DB_JENIS").strip().lower() in ("postgres", "postgresql"):
        return _dari_bagian()
    return Sambungan(JENIS_SQLITE, {"berkas": jalur.BASIS_DATA},
                     f"sqlite {jalur.BASIS_DATA}")
