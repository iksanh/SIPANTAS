# -*- coding: utf-8 -*-
"""Lapisan tipis di atas dua basis data: SQLite dan PostgreSQL.

Kuerinya sendiri sudah ditulis dalam dialek yang dimengerti keduanya —
ON CONFLICT untuk upsert, RETURNING untuk id baris baru, dan waktu dihitung
di Python, bukan lewat fungsi basis data. Yang tersisa dan memang tidak bisa
disamakan cuma empat hal, dan keempatnya diurus di sini:

    1. penampung nilai   SQLite pakai ?, PostgreSQL pakai %s
    2. bentuk baris      sqlite3.Row bisa dibaca dengan nama maupun urutan;
                         psycopg perlu dibuatkan yang setara
    3. tipe kolom DDL    id INTEGER PRIMARY KEY di SQLite berarti auto-increment,
                         di PostgreSQL harus disebut GENERATED ... AS IDENTITY
    4. nama galat        sqlite3.IntegrityError vs psycopg.errors.IntegrityError

Sengaja bukan ORM. Seluruh kueri aplikasi ini SQL tulis tangan yang sudah
terbukti jalan; menggantinya dengan ORM berarti menulis ulang semuanya dan
membuang uji acuan yang menjaganya.
"""
import re
import sqlite3

from . import konfigurasi

# Galat yang berarti "melanggar UNIQUE atau kunci asing". Dipakai rute yang
# perlu membedakan nama kembar dari kegagalan lain. Isinya bertambah begitu
# psycopg terpasang; tanpa psycopg pun modul ini tetap bisa dimuat.
_GALAT_BENTROK = [sqlite3.IntegrityError]

try:
    import psycopg
    from psycopg import errors as _pg_galat

    _GALAT_BENTROK.append(_pg_galat.IntegrityError)
except ImportError:                                                   # noqa: S110
    psycopg = None

Bentrok = tuple(_GALAT_BENTROK)


# --------------------------------------------------------- pemindai SQL
def _pindai(sql):
    """Pecah SQL jadi potongan (teks, jenis).

    jenis: 'kode', 'literal' (di dalam tanda kutip), 'komentar'.

    Ada sendiri karena dua penerjemah di bawah sama-sama harus buta terhadap
    isi literal dan komentar. Tanpa itu: komentar yang memuat tanda kutip
    membuat pelacak kutip kacau, dan komentar yang memuat titik koma memecah
    perintah di tempat yang salah. Skema aplikasi ini memuat keduanya.
    """
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":                                  # literal teks
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":   # '' = kutip di dalam teks
                        j += 2
                        continue
                    break
                j += 1
            yield sql[i:j + 1], "literal"
            i = j + 1
        elif sql.startswith("--", i):                  # komentar sebaris
            j = sql.find(chr(10), i)
            j = n if j < 0 else j
            yield sql[i:j], "komentar"
            i = j
        elif sql.startswith("/*", i):                  # komentar blok
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
            yield sql[i:j], "komentar"
            i = j
        else:
            j = i
            while j < n and sql[j] != "'" and not sql.startswith("--", j)                     and not sql.startswith("/*", j):
                j += 1
            yield sql[i:j], "kode"
            i = j


# ------------------------------------------------------- penampung nilai
def ke_persen(sql, ada_nilai):
    """Ubah penampung ? jadi %s untuk psycopg.

    Tanda ? di dalam literal teks atau komentar dibiarkan. Tanda % ikut
    digandakan bila kuerinya membawa nilai, sebab psycopg membaca % sebagai
    awal penampung saat menyulih nilai.
    """
    keluar = []
    for teks, jenis in _pindai(sql):
        if jenis == "kode":
            if ada_nilai:
                teks = teks.replace("%", "%%")
            teks = teks.replace("?", "%s")
        keluar.append(teks)
    return "".join(keluar)


# ------------------------------------------------------------ bentuk baris
class Baris(dict):
    """Baris hasil kueri PostgreSQL yang berperilaku seperti sqlite3.Row.

    Kode aplikasi membaca baris dengan tiga cara: r["kolom"], r[0], dan
    dict(r). Ketiganya harus jalan, kalau tidak 215 potongan SQL yang ada
    harus disentuh satu per satu.
    """

    __slots__ = ("_urut",)

    def __init__(self, kolom, nilai):
        super().__init__(zip(kolom, nilai))
        self._urut = nilai

    def __getitem__(self, kunci):
        if isinstance(kunci, int):
            return self._urut[kunci]
        return super().__getitem__(kunci)


def _pabrik_baris(kursor):
    kolom = [d.name for d in (kursor.description or [])]
    return lambda nilai: Baris(kolom, nilai)


# ------------------------------------------------------------ pembungkus
class _KursorPG:
    """Kursor psycopg yang menerima ? dan bisa dilewati for-loop."""

    def __init__(self, kursor):
        self._k = kursor

    def execute(self, sql, nilai=()):
        self._k.execute(ke_persen(sql, bool(nilai)), tuple(nilai))
        return self

    def executemany(self, sql, urutan):
        urutan = [tuple(x) for x in urutan]
        self._k.executemany(ke_persen(sql, bool(urutan)), urutan)
        return self

    def fetchone(self):
        return self._k.fetchone()

    def fetchall(self):
        return self._k.fetchall()

    def __iter__(self):
        return iter(self._k)

    def close(self):
        self._k.close()

    @property
    def description(self):
        return self._k.description

    @property
    def rowcount(self):
        return self._k.rowcount


class KoneksiPG:
    """Koneksi PostgreSQL dengan tata cara yang sama seperti sqlite3."""

    def __init__(self, sambungan):
        if psycopg is None:
            raise RuntimeError(
                "psycopg belum terpasang. Jalankan: pip install -r requirements.txt")
        self._k = psycopg.connect(row_factory=_pabrik_baris, **sambungan.argumen)
        self.sebutan = sambungan.sebutan

    def execute(self, sql, nilai=()):
        return self.cursor().execute(sql, nilai)

    def executemany(self, sql, urutan):
        return self.cursor().executemany(sql, urutan)

    def cursor(self):
        return _KursorPG(self._k.cursor())

    def executescript(self, naskah):
        """psycopg menolak beberapa perintah sekaligus, jadi dipecah dulu.

        Dipecah per titik koma di luar kutip, dan tiap potongan dijalankan
        sendiri — galatnya jadi menunjuk perintah yang benar-benar gagal,
        bukan ke seluruh naskah.
        """
        with self._k.cursor() as kur:
            for potong in _pecah_perintah(naskah):
                kur.execute(potong)
        return self

    def commit(self):
        self._k.commit()

    def rollback(self):
        self._k.rollback()

    def close(self):
        self._k.close()


def _pecah_perintah(naskah):
    """Pecah naskah DDL per titik koma — hanya titik koma di luar literal
    dan komentar yang dihitung."""
    potong, kini = [], []
    for teks, jenis in _pindai(naskah):
        if jenis != "kode":
            kini.append(teks)
            continue
        for bagian in _belah_titik_koma(teks):
            if bagian is None:
                if "".join(kini).strip():
                    potong.append("".join(kini))
                kini = []
            else:
                kini.append(bagian)
    if "".join(kini).strip():
        potong.append("".join(kini))
    return potong


def _belah_titik_koma(teks):
    """Rangkaian potongan teks, dengan None sebagai penanda titik koma."""
    mulai = 0
    for i, ch in enumerate(teks):
        if ch == ";":
            yield teks[mulai:i]
            yield None
            mulai = i + 1
    yield teks[mulai:]


# ------------------------------------------------------------------- DDL
# id INTEGER PRIMARY KEY di SQLite otomatis terisi sendiri; padanannya di
# PostgreSQL harus disebutkan. Yang membawa REFERENCES bukan auto-increment —
# itu kunci utama sekaligus kunci asing — jadi dibiarkan INTEGER.
_POLA_ID_AUTO = re.compile(r"\bid INTEGER PRIMARY KEY(?!\s+REFERENCES)")
_POLA_WAKTU = re.compile(r"DEFAULT \(datetime\('now','localtime'\)\)")
_POLA_PRAGMA = re.compile(r"^\s*PRAGMA[^;]*;", re.M)


def ddl_postgres(skema):
    """Terjemahkan DDL SQLite ke PostgreSQL.

    Kolom waktu sengaja tetap TEXT 'YYYY-MM-DD HH:MM:SS', bukan timestamp:
    bentuknya persis sama dengan yang sudah tersimpan sekarang, jadi data
    berpindah apa adanya dan perbandingan < > tetap berperilaku sama.
    """
    skema = _POLA_PRAGMA.sub("", skema)
    skema = _POLA_ID_AUTO.sub("id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY", skema)
    skema = _POLA_WAKTU.sub("DEFAULT to_char(localtimestamp, 'YYYY-MM-DD HH24:MI:SS')", skema)
    return skema


# ---------------------------------------------------------------- pembuka
def buka(sambungan=None):
    """Koneksi ke basis data yang disetel untuk pemasangan ini."""
    s = sambungan or konfigurasi.sambungan()
    if s.postgres:
        return KoneksiPG(s)
    k = sqlite3.connect(s.argumen["berkas"], timeout=15)
    k.row_factory = sqlite3.Row
    k.execute("PRAGMA foreign_keys = ON")
    return k
