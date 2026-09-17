# -*- coding: utf-8 -*-
"""Daftar wilayah dan riwayat kepala desa.

Dua hal yang dikerjakan berkas ini:

1. Menyimpan daftar kecamatan/desa Kabupaten Bone Bolango menurut kode wilayah
   Kemendagri, supaya nama dan ejaannya tidak diketik sendiri-sendiri. Daftar ini
   hanya dipakai untuk *menambah* yang belum ada - baris yang sudah dipakai berkas
   tidak pernah ditimpa atau dihapus.
2. Menyimpan riwayat kepala desa/lurah tiap desa dan menandai satu yang aktif.
   Kepala desa berganti (definitif, penjabat, pelaksana tugas), sedangkan berkas
   lama harus tetap bisa dibaca; jadi yang lama disimpan sebagai riwayat, bukan
   ditimpa. Nama dan jabatan yang aktif disalin balik ke ref_desa supaya
   konteks.py dan dokumen yang sudah ada tidak perlu berubah.
"""

# ------------------------------------------------------------------ jabatan
# Urutannya jadi urutan pilihan di layar; yang pertama jadi bawaan.
JABATAN_DESA = ["Kepala Desa", "Pj. Kepala Desa", "Plt. Kepala Desa", "Pjs. Kepala Desa"]
JABATAN_KELURAHAN = ["Lurah", "Plt. Lurah", "Pj. Lurah"]
JENIS_DESA = ["Desa", "Kelurahan"]


def jabatan_untuk(jenis):
    """Pilihan jabatan yang masuk akal untuk satu jenis wilayah."""
    return JABATAN_KELURAHAN if (jenis or "").strip().lower() == "kelurahan" else JABATAN_DESA


def jabatan_baku(jenis):
    return jabatan_untuk(jenis)[0]


# ------------------------------------------------- daftar wilayah Kemendagri
# Kabupaten Bone Bolango, kode 75.03 - 18 kecamatan, 160 desa, 5 kelurahan.
# (kode kecamatan, nama kecamatan, desa dipisah koma, kelurahan dipisah koma)
KODE_KABUPATEN = "75.03"
NAMA_KABUPATEN = "Kabupaten Bone Bolango"

WILAYAH = [
    ("75.03.01", "Tapa",
     "Dunggala, Kramat, Langge, Meranti, Talulobutu, Talulobutu Selatan, Talumopatu", ""),
    ("75.03.02", "Kabila",
     "Dutohe, Dutohe Barat, Poowo, Poowo Barat, Talango, Tanggilingo, Toto Selatan",
     "Oluhuta, Oluhuta Utara, Padengo, Pauwo, Tumbihe"),
    ("75.03.03", "Suwawa",
     "Boludawa, Bube, Bube Baru, Bubeya, Helumo, Huluduotamo, Tinelo, Tingkohubu, "
     "Tingkohubu Timur, Ulanta", ""),
    ("75.03.04", "Bonepantai",
     "Batu Hijau, Bilungala, Bilungala Utara, Kemiri, Lembah Hijau, Ombulo Hijau, "
     "Pelita Hijau, Tamboo, Tihu, Tolotio, Tongo, Tunas Jaya, Uabanga", ""),
    ("75.03.05", "Bulango Utara",
     "Bandungan, Boidu, Bunuo, Kopi, Lomaya, Longalo, Suka Damai, Tuloa, Tupa", ""),
    ("75.03.06", "Tilongkabila",
     "Berlian, Bongohulawa, Bongoime, Bongopini, Butu, Iloheluma, Lonuo, Motilango, "
     "Moutong, Permata, Tamboo, Toto Utara, Tunggulo, Tunggulo Selatan", ""),
    ("75.03.07", "Botupingge",
     "Buata, Luwohu, Panggulo, Panggulo Barat, Sukma, Tanah Putih, Timbuolo, "
     "Timbuolo Tengah, Timbuolo Timur", ""),
    ("75.03.08", "Kabila Bone",
     "Biluango, Bintalahe, Botubarani, Botutonuo, Huangobotu, Modelomo, Molutabu, "
     "Olele, Oluhuta", ""),
    ("75.03.09", "Bone",
     "Bilonlantunga, Cendana Putih, Ilohuuwa, Inogaluma, Masiaga, Molamahu, Monano, "
     "Moodulio, Muara Bone, Permata, Sogitia, Taludaa, Tumbuh Mekar, Waluhu", ""),
    ("75.03.10", "Bone Raya",
     "Alo, Bunga, Inomata, Laut Biru, Moopiya, Mootawa, Mootayu, Mootinelo, "
     "Pelita Jaya, Tombulilato", ""),
    ("75.03.11", "Suwawa Timur",
     "Dumbaya Bulan, Panggulo, Pangi, Poduwoma, Tilangobula, Tinemba, Tulabolo, "
     "Tulabolo Barat, Tulabolo Timur", ""),
    ("75.03.12", "Suwawa Selatan",
     "Bondaraya, Bondawuna, Bonedaa, Bulontala, Bulontala Timur, Libungo, "
     "Molintogupo, Pancuran", ""),
    ("75.03.13", "Suwawa Tengah",
     "Alale, Duano, Lombongo, Lompotoo, Tapadaa, Tolomato", ""),
    ("75.03.14", "Bulango Ulu",
     "Ilomata, Mongiilo, Mongiilo Utara, Owata, Pilolaheya, Suka Makmur", ""),
    ("75.03.15", "Bulango Selatan",
     "Ayula Selatan, Ayula Tilango, Ayula Timur, Ayula Utara, Huntu Barat, "
     "Huntu Selatan, Huntu Utara, Lamahu, Sejahtera, Tinelo Ayula", ""),
    ("75.03.16", "Bulango Timur",
     "Bulotalangi, Bulotalangi Barat, Bulotalangi Timur, Popodu, Toluwaya", ""),
    ("75.03.17", "Bulawa",
     "Bukit Hijau, Dunggilata, Kaidundu, Kaidundu Barat, Mamungaa, Mamungaa Timur, "
     "Mopuya, Patoa, Pinomotiga", ""),
    ("75.03.18", "Pinogu",
     "Bangio, Dataran Hijau, Pinogu, Pinogu Permai, Tilonggibila", ""),
]


def _pecah(teks):
    return [x.strip() for x in (teks or "").split(",") if x.strip()]


def daftar_baku():
    """WILAYAH dibentangkan jadi [(kode_kec, nama_kec, [(nama_desa, jenis), ...]), ...]."""
    keluar = []
    for kode, kec, desa, kelurahan in WILAYAH:
        isi = [(n, "Desa") for n in _pecah(desa)]
        isi += [(n, "Kelurahan") for n in _pecah(kelurahan)]
        keluar.append((kode, kec, sorted(isi, key=lambda x: x[0].lower())))
    return keluar


def _kunci(nama):
    """Nama untuk dicocokkan: beda huruf besar-kecil dan spasi ganda dianggap sama."""
    return " ".join((nama or "").split()).lower()


# ------------------------------------------------------------- penyelarasan
def bandingkan(k):
    """Apa saja dari daftar Kemendagri yang belum ada di basis data.

    Mengembalikan {"kecamatan": [nama, ...], "desa": [(kecamatan, nama, jenis), ...]}.
    Yang sudah ada tidak pernah masuk daftar ini - penyelarasan hanya menambah.
    """
    ada_kec = {_kunci(r["nama"]): r["id"]
               for r in k.execute("SELECT id, nama FROM ref_kecamatan")}
    ada_desa = {(r["kecamatan_id"], _kunci(r["nama"]))
                for r in k.execute("SELECT kecamatan_id, nama FROM ref_desa")}
    kec_baru, desa_baru = [], []
    for _kode, kec, isi in daftar_baku():
        kid = ada_kec.get(_kunci(kec))
        if kid is None:
            kec_baru.append(kec)
        for nama, jenis in isi:
            if kid is None or (kid, _kunci(nama)) not in ada_desa:
                desa_baru.append((kec, nama, jenis))
    return {"kecamatan": kec_baru, "desa": desa_baru}


def selaraskan(k):
    """Tambahkan kecamatan dan desa Kemendagri yang belum ada. Aman diulang.

    Baris yang sudah ada hanya dilengkapi kode wilayahnya bila masih kosong;
    nama, jenis, dan pejabatnya tidak disentuh sama sekali.
    """
    ada_kec = {_kunci(r["nama"]): r["id"]
               for r in k.execute("SELECT id, nama FROM ref_kecamatan")}
    jml_kec = jml_desa = 0
    for kode, kec, isi in daftar_baku():
        kid = ada_kec.get(_kunci(kec))
        if kid is None:
            kid = k.execute("INSERT INTO ref_kecamatan (nama,kode) VALUES (?,?)",
                            (kec, kode)).lastrowid
            ada_kec[_kunci(kec)] = kid
            jml_kec += 1
        else:
            k.execute("UPDATE ref_kecamatan SET kode=? WHERE id=? AND (kode IS NULL OR kode='')",
                      (kode, kid))
        punya = {_kunci(r["nama"]) for r in
                 k.execute("SELECT nama FROM ref_desa WHERE kecamatan_id=?", (kid,))}
        for nama, jenis in isi:
            if _kunci(nama) in punya:
                continue
            k.execute("INSERT INTO ref_desa (kecamatan_id,nama,jenis,jabatan_pejabat) "
                      "VALUES (?,?,?,?)", (kid, nama, jenis, jabatan_baku(jenis)))
            jml_desa += 1
    k.commit()
    return jml_kec, jml_desa


# ------------------------------------------------------------ pejabat desa
def riwayat(k, desa_id):
    """Semua kepala desa/lurah yang pernah didaftarkan, yang aktif di atas."""
    return [dict(r) for r in k.execute(
        "SELECT * FROM ref_desa_pejabat WHERE desa_id=? "
        "ORDER BY aktif DESC, COALESCE(mulai,'') DESC, id DESC", (desa_id,))]


def pejabat_aktif(k, desa_id):
    r = k.execute("SELECT * FROM ref_desa_pejabat WHERE desa_id=? AND aktif=1 "
                  "ORDER BY id DESC LIMIT 1", (desa_id,)).fetchone()
    return dict(r) if r else None


def jadikan_aktif(k, desa_id, pejabat_id):
    """Tandai satu pejabat sebagai yang menjabat sekarang; sisanya jadi riwayat."""
    k.execute("UPDATE ref_desa_pejabat SET aktif=0 WHERE desa_id=?", (desa_id,))
    if pejabat_id:
        k.execute("UPDATE ref_desa_pejabat SET aktif=1 WHERE id=? AND desa_id=?",
                  (pejabat_id, desa_id))
    segarkan(k, desa_id)


def segarkan(k, desa_id):
    """Salin pejabat aktif ke ref_desa.

    konteks.py dan template membaca nama_pejabat/jabatan_pejabat dari ref_desa,
    jadi kedua kolom itu tetap dipelihara sebagai salinan pejabat yang aktif -
    bukan sumber datanya lagi.
    """
    a = pejabat_aktif(k, desa_id)
    if a:
        k.execute("UPDATE ref_desa SET nama_pejabat=?, jabatan_pejabat=? WHERE id=?",
                  (a["nama"], a["jabatan"], desa_id))
    else:
        r = k.execute("SELECT jenis FROM ref_desa WHERE id=?", (desa_id,)).fetchone()
        k.execute("UPDATE ref_desa SET nama_pejabat=NULL, jabatan_pejabat=? WHERE id=?",
                  (jabatan_baku(r["jenis"] if r else "Desa"), desa_id))


def simpan_pejabat(k, desa_id, pejabat_id, nama, jabatan, mulai=None, sampai=None,
                   sk_nomor=None, catatan=None, aktif=False):
    """Tambah atau ubah satu baris riwayat pejabat. Mengembalikan id barisnya."""
    nilai = (nama, jabatan, mulai, sampai, sk_nomor, catatan)
    if pejabat_id:
        k.execute("UPDATE ref_desa_pejabat SET nama=?, jabatan=?, mulai=?, sampai=?, "
                  "sk_nomor=?, catatan=? WHERE id=? AND desa_id=?",
                  nilai + (pejabat_id, desa_id))
    else:
        pejabat_id = k.execute(
            "INSERT INTO ref_desa_pejabat (desa_id,nama,jabatan,mulai,sampai,sk_nomor,catatan) "
            "VALUES (?,?,?,?,?,?,?)", (desa_id,) + nilai).lastrowid
        # Pejabat pertama sebuah desa otomatis jadi yang aktif - tanpa itu desanya
        # tetap terhitung "belum ada pejabat" walau barusan diisi.
        aktif = aktif or not k.execute(
            "SELECT COUNT(*) FROM ref_desa_pejabat WHERE desa_id=? AND aktif=1",
            (desa_id,)).fetchone()[0]
    if aktif:
        jadikan_aktif(k, desa_id, pejabat_id)
    else:
        segarkan(k, desa_id)
    return pejabat_id


def hapus_pejabat(k, desa_id, pejabat_id):
    k.execute("DELETE FROM ref_desa_pejabat WHERE id=? AND desa_id=?", (pejabat_id, desa_id))
    segarkan(k, desa_id)
