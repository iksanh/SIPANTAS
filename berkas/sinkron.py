# -*- coding: utf-8 -*-
"""Tarik data pemohon dan bidang tanah dari aplikasi PHPT (Laravel), by NIB.

Data yang sama sudah diketik di aplikasi pengecekan berkas pradaftar
(laravel_app, menu Pemohon dan Tanah). Supaya tidak diketik dua kali, formulir
Berkas dan Pradaftar di sini bisa menariknya lewat API:

    GET {alamat}/api/sinkron/tanah?nib=...
    Authorization: Bearer {kunci API}

Alamat dan kunci API diatur admin di Pengaturan, tab PHPT (lihat setelan()).

Arah datanya satu: PHPT -> formulir di layar. Tidak ada yang langsung ditulis
ke basis data — hasilnya diisikan ke formulir, petugas memeriksa, baru Simpan.
Dengan begitu aturan simpan yang sudah ada (formulir.py, pradaftar.py) tetap
satu-satunya jalan masuk data.

Pemetaan kolom:

    PHPT (Laravel)                      di sini
    tanah.nib / nomor_pbt / tanggal_pbt bidang_tanah.nib / nomor_pbt / tanggal_pbt
    tanah.luas                          luas_pbt (luas hasil ukur)
    tanah.luas_surat                    luas_surat
    tanah.batas_*                       batas_*
    tanah.penggunaan_tanah              penggunaan_sekarang
    tanah.rencana_penggunaan_rtrw       rencana_penggunaan (cadangan: penggunaan_tanah_sk)
    tanah.rtrw_kawasan                  rtrw
    tanah.kesesuaian_penggunaan_tanah   kesesuaian
    tanah.tgl_peta_analisis             tanggal_peta_analisis
    tanah.desa (kode Kemendagri)        desa_id — dicocokkan lewat kode kecamatan + nama desa
    pemohon.nama / nik / pekerjaan      pihak penerima hak
    pemohon.tempat_ & tanggal_lahir     ttl  "Gorontalo, 13 Januari 1986"
    pemohon.jenis_kelamin L/P           "Laki-laki" / "Perempuan"
    pemohon.alamat_detail + desa        alamat "…, Desa X, Kecamatan Y, Kabupaten Z, Provinsi W"
    pemohon.kuasa_nama / kuasa_nik      pihak kuasa
    permohonan.layanan.kode             jenis_hak_dimohon ("HM Perorangan" -> HM, "HW …" -> WAKAF)
    permohonan.nomor_berkas/tahun       nomor_berkas
    permohonan.tgl_pendaftaran          tanggal_permohonan
    riwayat_penguasaan.poin[]           riwayat_perolehan, satu poin satu baris
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from . import konfigurasi, util

KELAMIN = {"L": "Laki-laki", "P": "Perempuan"}
KESESUAIAN_BAKU = ("Sesuai", "Sesuai Bersyarat", "Tidak Sesuai")

# Awalan kode layanan PHPT -> kode ref_jenis_hak di sini. HGU tidak ada
# padanannya: aplikasi ini tidak menerbitkan HGU.
JENIS_HAK = {"HM": "HM", "HGB": "HGB", "HBG": "HGB", "HP": "HP", "HPL": "HPL",
             "HW": "WAKAF", "WAKAF": "WAKAF", "HMSRS": "HMSRS"}


class SinkronGagal(Exception):
    """Pesannya untuk dibaca petugas, apa adanya."""


# ------------------------------------------------------------------ setelan
# Alamat dan kunci API diisi admin di Pengaturan (tab PHPT) dan disimpan di
# tabel pengaturan. SINKRON_URL/SINKRON_KUNCI di .env tetap dibaca sebagai
# cadangan, supaya pemasangan lama tidak tiba-tiba kehilangan sinkronnya.
KUNCI_URL = "sinkron_url"
KUNCI_API = "sinkron_kunci"


def _dari_db(k, kunci):
    if k is None:
        return ""
    r = k.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (kunci,)).fetchone()
    return ((r["nilai"] if r else "") or "").strip()


def setelan(k=None):
    """(alamat, kunci API). Isian Pengaturan menang atas .env."""
    url = _dari_db(k, KUNCI_URL) or konfigurasi.ambil("SINKRON_URL", "").strip()
    kunci = _dari_db(k, KUNCI_API) or konfigurasi.ambil("SINKRON_KUNCI", "").strip()
    return url.rstrip("/"), kunci


def url_dasar(k=None):
    return setelan(k)[0]


def aktif(k=None):
    """Kartu "Ambil dari PHPT" hanya muncul kalau alamat dan kuncinya diisi."""
    url, kunci = setelan(k)
    return bool(url and kunci)


def periksa_url(url):
    """Rapikan alamat isian admin. Melempar ValueError bila bukan http(s)://host."""
    url = (url or "").strip().rstrip("/")
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("Alamat aplikasi PHPT harus diawali http:// atau https://, "
                         "mis. http://192.168.1.10:8000")
    if u.query or u.fragment:
        raise ValueError("Alamat aplikasi PHPT cukup alamat dasarnya, tanpa ?… atau #….")
    return url


# ------------------------------------------------------------------- ambil
def ambil(nib, k=None):
    """Daftar rekaman mentah dari API PHPT. Melempar SinkronGagal."""
    url, kunci = setelan(k)
    if not (url and kunci):
        raise SinkronGagal("Sinkron PHPT belum diatur — admin mengisi alamat dan kunci API "
                           "di Pengaturan, tab PHPT.")
    alamat = f"{url}/api/sinkron/tanah?" + urllib.parse.urlencode({"nib": nib})
    minta = urllib.request.Request(alamat, headers={
        "Authorization": "Bearer " + kunci,
        "Accept": "application/json",
    })
    batas = konfigurasi.angka("SINKRON_BATAS_WAKTU", 8)
    try:
        with urllib.request.urlopen(minta, timeout=batas) as jawab:
            isi = json.loads(jawab.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        pesan = _pesan_galat(ex)
        if ex.code == 401:
            raise SinkronGagal("Kunci API ditolak aplikasi PHPT — samakan kunci API di "
                               "Pengaturan dengan SINKRON_API_KEY di laravel_app.") from ex
        raise SinkronGagal(pesan or f"Aplikasi PHPT menjawab galat {ex.code}.") from ex
    except (urllib.error.URLError, TimeoutError, OSError) as ex:
        raise SinkronGagal(f"Aplikasi PHPT tidak bisa dihubungi di {url}.") from ex
    except ValueError as ex:
        raise SinkronGagal("Jawaban aplikasi PHPT tidak terbaca.") from ex
    data = isi.get("data") if isinstance(isi, dict) else None
    if not isinstance(data, list):
        raise SinkronGagal("Jawaban aplikasi PHPT tidak berisi daftar data.")
    return data


def _pesan_galat(ex):
    try:
        return (json.loads(ex.read().decode("utf-8")) or {}).get("message")
    except Exception:                                               # noqa: BLE001
        return None


# ---------------------------------------------------------------- wilayah
def _polos(s):
    """'Kelurahan  TUMBIHE' -> 'tumbihe'. Untuk membandingkan nama wilayah."""
    s = (s or "").lower()
    s = re.sub(r"^(desa|kelurahan|kel\.|kecamatan|kec\.)\s+", "", s.strip())
    return re.sub(r"[^a-z0-9]+", "", s)


def _kode_titik(kode, potong):
    """'7503021010' -> '75.03.02.1010'; dipakai untuk ref_*.kode di sini."""
    kode = re.sub(r"\D", "", str(kode or ""))
    bagian, i = [], 0
    for n in potong:
        if i >= len(kode):
            break
        bagian.append(kode[i:i + n])
        i += n
    return ".".join(bagian)


def cari_desa(k, desa):
    """Padanan desa PHPT di ref_desa sini, atau None.

    ref_desa.kode di sini kebanyakan kosong, jadi kuncinya kecamatan (lewat
    kode Kemendagri, cadangannya nama) lalu nama desa di dalam kecamatan itu.
    Tanpa kecamatan yang cocok, nama desa saja diterima hanya bila tunggal.
    """
    if not desa or not desa.get("nama"):
        return None
    r = k.execute("SELECT d.id, d.kecamatan_id, d.jenis, d.nama FROM ref_desa d "
                  "WHERE d.kode=?", (_kode_titik(desa.get("id"), (2, 2, 2, 4)),)).fetchone()
    if r:
        return dict(r)

    kec = desa.get("kecamatan") or {}
    kec_id = None
    if kec:
        r = k.execute("SELECT id FROM ref_kecamatan WHERE kode=?",
                      (_kode_titik(kec.get("id"), (2, 2, 2)),)).fetchone()
        if r:
            kec_id = r["id"]
        else:
            nama = _polos(kec.get("nama"))
            for r in k.execute("SELECT id, nama FROM ref_kecamatan"):
                if _polos(r["nama"]) == nama:
                    kec_id = r["id"]
                    break

    nama = _polos(desa["nama"])
    if kec_id is not None:
        calon = k.execute("SELECT id, kecamatan_id, jenis, nama FROM ref_desa "
                          "WHERE kecamatan_id=?", (kec_id,)).fetchall()
    else:
        calon = k.execute("SELECT id, kecamatan_id, jenis, nama FROM ref_desa").fetchall()
    cocok = [dict(r) for r in calon if _polos(r["nama"]) == nama]
    return cocok[0] if len(cocok) == 1 else None


def _rapi(nama):
    """'KAB. BONE BOLANGO' -> 'Bone Bolango'. Nama huruf besar semua dijadikan
    huruf awal besar, sama dengan cara alamat ditulis di berkas yang ada."""
    nama = re.sub(r"^(kab\.|kabupaten)\s*", "", (nama or "").strip(), flags=re.I)
    return nama.title() if nama.isupper() else nama


def alamat(pemohon, desa_sini=None):
    """Alamat satu baris: rincian jalan/dusun, lalu desa sampai provinsi."""
    bagian = []
    rinci = (pemohon.get("alamat_detail") or "").strip()
    if rinci and rinci not in ("-", "."):
        bagian.append(rinci)
    w = pemohon.get("desa") or {}
    if w.get("nama"):
        jenis = (desa_sini or {}).get("jenis") or (
            "Kelurahan" if (w.get("jenis") or "").upper() == "KELURAHAN" else "Desa")
        bagian.append(f"{jenis} {(desa_sini or {}).get('nama') or _rapi(w['nama'])}")
    if (w.get("kecamatan") or {}).get("nama"):
        bagian.append(f"Kecamatan {_rapi(w['kecamatan']['nama'])}")
    kab = (w.get("kabupaten") or {}).get("nama") or ""
    if kab:
        bagian.append(_rapi(kab) if kab.strip().upper().startswith("KOTA")
                      else f"Kabupaten {_rapi(kab)}")
    if (w.get("provinsi") or {}).get("nama"):
        bagian.append(f"Provinsi {_rapi(w['provinsi']['nama'])}")
    return ", ".join(bagian)


# ---------------------------------------------------------------- pemetaan
def jenis_hak(layanan, boleh):
    """Kode layanan PHPT -> kode jenis hak di sini, atau None bila tak dikenal."""
    if not layanan:
        return None
    kode = (layanan.get("kode") or "").strip().upper()
    m = re.match(r"[A-Z]+", kode)
    hasil = JENIS_HAK.get(m.group(0)) if m else None
    if not hasil and "WAKAF" in (layanan.get("nama") or "").upper():
        hasil = "WAKAF"
    return hasil if hasil in boleh else None


def jenis_subjek(layanan):
    teks = " ".join((layanan or {}).get(x) or "" for x in ("kode", "nama")).upper()
    return "badan_hukum" if "BADAN HUKUM" in teks else "perorangan"


def ttl(pemohon):
    tempat = (pemohon.get("tempat_lahir") or "").strip()
    tgl = util.tanggal_panjang(pemohon.get("tanggal_lahir"))
    return ", ".join(x for x in (tempat, tgl) if x)


def luas(nilai, label, peringatan):
    """INTEGER di sini, desimal di PHPT."""
    if nilai in (None, ""):
        return None
    try:
        f = float(nilai)
    except (TypeError, ValueError):
        return None
    n = int(round(f))
    if abs(f - n) > 1e-9:
        peringatan.append(f"{label} {f:g} m² dibulatkan jadi {n} m².")
    return n


def riwayat(poin):
    """Poin PHPT berakhiran ';' atau '; dan' — di sini tanda baca akhirnya
    dipasang sendiri oleh dokumen, jadi dibuang. Spasi ganda dirapatkan."""
    hasil = []
    for p in poin or []:
        if not isinstance(p, str):
            continue
        p = re.sub(r"\s+", " ", p).strip()
        p = re.sub(r"(?:[;,]\s*dan)?[\s;,.]*$", "", p)
        if p:
            hasil.append(p)
    return hasil


def _nib_dipakai(nib_cari, nib_phpt):
    """Yang lebih lengkap menang: PHPT sering hanya menyimpan nomor urutnya."""
    a = re.sub(r"\D", "", nib_cari or "")
    b = re.sub(r"\D", "", nib_phpt or "")
    return nib_phpt if len(b) >= len(a) else nib_cari


def _nomor_berkas(p):
    nomor = (p.get("nomor_berkas") or "").strip()
    if nomor and p.get("tahun_berkas") and "/" not in nomor:
        nomor = f"{nomor}/{p['tahun_berkas']}"
    return nomor


def olah(k, rekaman, nib_cari, untuk="berkas"):
    """Satu rekaman API -> isian formulir.

    Kembalian: {ringkas, cocok, isian{nama_medan: nilai}, riwayat[], peringatan[]}.
    Nama medannya persis nama <input> di web.py, jadi app.js tinggal
    mengisikannya tanpa tahu arti tiap kolom.
    """
    t = rekaman.get("tanah") or {}
    pm = rekaman.get("pemohon") or {}
    pr = rekaman.get("permohonan") or {}
    lay = pr.get("layanan")
    peringatan = []

    boleh = {r["kode"] for r in k.execute("SELECT kode FROM ref_jenis_hak WHERE aktif=1")}
    hak = jenis_hak(lay, boleh)
    if lay and not hak:
        peringatan.append(f"Layanan PHPT «{lay.get('kode')}» tidak punya padanan jenis hak "
                          "di sini — pilih jenis haknya sendiri.")

    desa = cari_desa(k, t.get("desa"))
    nama_desa = (t.get("desa") or {}).get("nama")
    if nama_desa and not desa:
        peringatan.append(f"Desa «{nama_desa}» tidak ditemukan di daftar wilayah — "
                          "pilih desanya sendiri.")
    desa_pemohon = cari_desa(k, pm.get("desa")) if pm else None
    kuasa = pm.get("kuasa") or {}

    if not pm:
        peringatan.append("Tanah ini belum punya data pemohon di PHPT.")
    if rekaman.get("cocok") == "sebagian":
        peringatan.append(f"NIB di PHPT tertulis «{t.get('nib')}», tidak persis sama — "
                          "pastikan desa dan pemohonnya benar.")

    isian = {}
    if untuk == "pradaftar":
        isian.update({
            "jenis_hak": hak,
            "pemohon_jenis_subjek": jenis_subjek(lay) if pm else None,
            "pemohon_nama": pm.get("nama"),
            "pemohon_nik": pm.get("nik"),
            "pemohon_alamat": alamat(pm, desa_pemohon) if pm else None,
            "pemohon_telepon": kuasa.get("no_hp"),
            "kuasa_nama": kuasa.get("nama"),
            "kuasa_nik": kuasa.get("nik"),
            "luas_surat": luas(t.get("luas_surat"), "Luas surat", peringatan),
            "nomor_pbt": t.get("nomor_pbt"),
        })
    else:
        kes = (t.get("kesesuaian_penggunaan_tanah") or "").strip()
        isian.update({
            "jenis_hak_dimohon": hak,
            "nomor_berkas": _nomor_berkas(pr) if pr else None,
            "tanggal_permohonan": pr.get("tgl_pendaftaran"),
            "penerima_jenis_subjek": jenis_subjek(lay) if pm else None,
            "penerima_nama": pm.get("nama"),
            "penerima_nik": pm.get("nik"),
            "penerima_ttl": ttl(pm) if pm else None,
            "penerima_jenis_kelamin": KELAMIN.get(pm.get("jenis_kelamin") or ""),
            "penerima_pekerjaan": pm.get("pekerjaan"),
            "penerima_alamat": alamat(pm, desa_pemohon) if pm else None,
            "kuasa_nama": kuasa.get("nama"),
            "kuasa_nik": kuasa.get("nik"),
            "nomor_pbt": t.get("nomor_pbt"),
            "tanggal_pbt": t.get("tanggal_pbt"),
            "nib": _nib_dipakai(nib_cari, t.get("nib")),
            "luas_pbt": luas(t.get("luas"), "Luas hasil ukur", peringatan),
            "luas_surat": luas(t.get("luas_surat"), "Luas surat", peringatan),
            "batas_utara": t.get("batas_utara"),
            "batas_timur": t.get("batas_timur"),
            "batas_selatan": t.get("batas_selatan"),
            "batas_barat": t.get("batas_barat"),
            "penggunaan_sekarang": t.get("penggunaan_tanah"),
            "rencana_penggunaan": t.get("rencana_penggunaan_rtrw") or t.get("penggunaan_tanah_sk"),
            "tanggal_peta_analisis": t.get("tgl_peta_analisis"),
            "rtrw": t.get("rtrw_kawasan"),
            "kesesuaian": kes if kes in KESESUAIAN_BAKU else None,
            "kesesuaian_lain": kes if kes and kes not in KESESUAIAN_BAKU else None,
        })
    if desa:
        isian["kecamatan"] = desa["kecamatan_id"]
        isian["desa_id"] = desa["id"]

    # Yang kosong tidak dikirim: formulir tidak boleh dikosongkan oleh PHPT.
    isian = {a: b for a, b in isian.items() if b not in (None, "")}

    letak = ", ".join(x for x in (nama_desa, ((t.get("desa") or {}).get("kecamatan") or {})
                                  .get("nama")) if x)
    ringkas = " · ".join(x for x in (
        f"NIB {t.get('nib')}", pm.get("nama") or "(tanpa pemohon)", letak,
        f"PBT {t['nomor_pbt']}" if t.get("nomor_pbt") else "",
        f"{util.format_angka(isian['luas_pbt'])} m²" if isian.get("luas_pbt") else "",
        pr.get("nomor_registrasi") or "") if x)
    return {
        "ringkas": ringkas,
        "cocok": rekaman.get("cocok"),
        "registrasi": pr.get("nomor_registrasi"),
        "isian": isian,
        "riwayat": riwayat(rekaman.get("riwayat_penguasaan")) if untuk == "berkas" else [],
        "peringatan": peringatan,
    }


def cari(k, nib, untuk="berkas"):
    """NIB -> daftar hasil olahan, siap dikirim ke app.js."""
    nib = (nib or "").strip()
    if len(re.sub(r"\D", "", nib)) < 3:
        raise SinkronGagal("Ketik NIB-nya dulu, paling sedikit 3 angka.")
    return [olah(k, r, nib, untuk) for r in ambil(nib, k)]
