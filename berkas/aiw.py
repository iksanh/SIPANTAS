# -*- coding: utf-8 -*-
"""Urai teks Akta Ikrar Wakaf (AIW) / Akta Pengganti AIW (APAIW).

Teksnya hasil OCR halaman 2 akta, dibaca di peramban (app.js, Tesseract.js)
atau dari lapisan teks PDF. Di sini teks itu dipilah jadi isian formulir:
identitas Wakif, Nazhir, dan Saksi, serta nomor/tanggal akta dan PPAIW.

Sengaja longgar: hasil OCR tidak pernah rapi, dan bentuk akta berbeda antar
KUA. Yang tidak yakin dibiarkan kosong, bukan ditebak - petugas memeriksa
pratinjaunya sebelum diterapkan ke formulir, dan tidak ada yang tersimpan
sampai tombol Simpan ditekan.
"""
import re

BATAS_TEKS = 50_000

BULAN = {"januari": 1, "februari": 2, "pebruari": 2, "maret": 3, "april": 4, "mei": 5,
         "juni": 6, "juli": 7, "agustus": 8, "september": 9, "oktober": 10,
         "november": 11, "nopember": 11, "desember": 12}

_PERAN = r"(wakif|na[zd]h?ir|saksi)"
# Awalan butir: "1.", "a)", "II.", "(2)"
_BUTIR = r"(?:\(?(?:\d{1,2}|[a-z]|[ivx]{1,4})[.)]\s*)?"

# label -> kolom; urutannya penting (yang lebih panjang dulu)
_LABEL = [
    (r"nama(?:\s+lengkap)?", "nama"),
    (r"nik|n\.\s*i\.\s*k\.?|nomor\s+induk\s+kependudukan|no\.?\s*ktp|nomor\s+ktp", "nik"),
    (r"tempat\s*(?:/|,|dan|&)?\s*(?:tgl|tanggal)\.?\s*lahir(?:\s*/\s*umur)?|ttl", "ttl"),
    (r"tempat\s+lahir", "tempat_lahir"),
    (r"(?:tgl|tanggal)\.?\s*lahir", "tanggal_lahir"),
    (r"jenis\s+kelamin", "jenis_kelamin"),
    (r"pekerjaan", "pekerjaan"),
    (r"alamat(?:\s+lengkap)?|tempat\s+tinggal|tempat\s+kediaman|"
     r"bertempat\s+tinggal(?:\s+di)?|domisili", "alamat"),
    # bagian alamat gaya KTP: ikut disambungkan ke alamat
    (r"rt\s*/\s*rw|kel(?:urahan)?\s*/\s*desa|kelurahan|desa|kecamatan|"
     r"kabupaten(?:\s*/\s*kota)?|kota|provinsi", "alamat_bagian"),
    (r"agama|kewarganegaraan|umur|jabatan|status(?:\s+perkawinan)?|"
     r"golongan\s+darah", "abaikan"),
]
_POLA_LABEL = [(re.compile(rf"^\s*{_BUTIR}({pola})\s*(?::|;|\.(?=\s)|\s{{2,}}|\s(?=\S))\s*(.*)$",
                           re.I), kol) for pola, kol in _LABEL]
# "Label :" lain yang tidak dikenal - menghentikan sambungan alamat
_LABEL_LAIN = re.compile(r"^\s*[A-Za-z][A-Za-z ./]{1,30}\s*:")
_KEPALA = re.compile(rf"^\W*(?:[ivx]{{1,4}}|[a-z]|\d{{1,2}})?[.)]?\s*(?:identitas\s+|para\s+)?"
                     rf"{_PERAN}\b(?:[\s-]*(?:saksi|[ivx]{{1,3}}|\d))?\s*:?\s*$", re.I)
_SELAKU = re.compile(rf"\b(?:selaku|sebagai)\s+{_PERAN}\b", re.I)
_BARIS_PPAIW = re.compile(r"ppaiw|pejabat\s+pembuat\s+akta|kepada\s+saya", re.I)


def _peran(kata):
    kata = kata.lower()
    return "saksi" if kata.startswith("saksi") else "wakif" if kata == "wakif" else "nazhir"


def _bersih(v):
    v = re.sub(r"\s+", " ", v or "").strip()
    return v.strip(" :;.,-").strip()


def _nik(v):
    """OCR kerap membaca angka 0 sebagai O dan 1 sebagai I/l/|."""
    v = (v or "").translate(str.maketrans("OoDIl|", "000111"))
    return re.sub(r"\D", "", v)


def _jenis_kelamin(v):
    v = (v or "").lower()
    if "laki" in v or v.strip() in ("l", "lk", "pria"):
        return "Laki-laki"
    if "perempuan" in v or "wanita" in v or v.strip() in ("p", "pr"):
        return "Perempuan"
    return ""


def _tanggal(teks):
    """Tanggal pertama di teks -> 'YYYY-MM-DD', atau ''."""
    m = re.search(r"\b(\d{1,2})\s+(" + "|".join(BULAN) + r")\s+(\d{4})\b", teks, re.I)
    if m:
        d, b, y = int(m.group(1)), BULAN[m.group(2).lower()], int(m.group(3))
    else:
        m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", teks)
        if not m:
            return ""
        d, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= d <= 31 and 1 <= b <= 12):
        return ""
    return f"{y:04d}-{b:02d}-{d:02d}"


def _label(baris):
    for pola, kol in _POLA_LABEL:
        m = pola.match(baris)
        if m:
            return kol, m.group(2), m.group(1)
    return None


def _akta(teks, baris_bebas):
    a = {"jenis": "", "nomor": "", "tanggal": "", "pejabat": "", "wilayah_pejabat": ""}
    if re.search(r"pengganti\s+akta\s+ikrar|\bapaiw\b", teks, re.I):
        a["jenis"] = "APAIW"
    elif re.search(r"ikrar\s+wakaf|\baiw\b", teks, re.I):
        a["jenis"] = "AIW"
    m = re.search(r"\bno(?:mor)?\.?\s*[:.]?\s*([A-Z][\w.\-]*(?:\s*/\s*[\w.\-]+)+)", teks, re.I)
    if m:
        a["nomor"] = re.sub(r"\s+", "", m.group(1)).strip(".")
    # tanggal akta: baris bebas (bukan identitas) yang menyebut "tanggal"/"hari ini"
    for b in baris_bebas:
        if re.search(r"tanggal|tgl|hari\s+ini", b, re.I) and _tanggal(b):
            a["tanggal"] = _tanggal(b)
            break
    else:
        a["tanggal"] = next((t for t in map(_tanggal, baris_bebas) if t), "")
    sambung = " ".join(baris_bebas)
    m = (re.search(r"kepada\s+saya\s*[:,]?\s*(.+?)(?=\s+(?:kepala|selaku|sebagai|pejabat|"
                   r"ppaiw|nip)\b)", sambung, re.I)
         or re.search(r"(?:nama\s+)?ppaiw\s*:\s*([^:]+?)(?=\s+\w+\s*:|$)", sambung, re.I))
    if m:
        a["pejabat"] = _bersih(m.group(1))
    m = re.search(r"\bkec(?:amatan|\.)\s+([A-Za-z'\-]+(?:\s+[A-Za-z'\-]+){0,3})", sambung, re.I)
    if m:
        kata = []
        for k in m.group(1).split():
            if k.lower() in ("selaku", "sebagai", "kabupaten", "kab", "kota", "provinsi",
                             "dengan", "telah", "pada", "yang", "dan", "nomor"):
                break
            kata.append(k)
        if kata:
            a["wilayah_pejabat"] = "Kecamatan " + " ".join(kata).title()
    return a


def urai(teks):
    """Teks akta -> {"akta": {...}, "pihak": [{peran, nama, ...}], "peringatan": [...]}.

    peran salah satu 'wakif', 'nazhir', 'saksi', atau '' bila tidak ketahuan.
    """
    teks = (teks or "")[:BATAS_TEKS]
    pihak, bebas = [], []
    bagian, kini, kol_akhir, sambungan = "", None, None, 0

    for mentah in teks.splitlines():
        b = mentah.strip()
        if not b:
            kol_akhir = None
            continue
        if _BARIS_PPAIW.search(b):              # pembuka akta / tanda tangan PPAIW
            bebas.append(b)
            kol_akhir = None
            continue
        m = _KEPALA.match(b)
        if m:
            bagian, kol_akhir = _peran(m.group(1)), None
            continue
        m = _SELAKU.search(b)
        if m and kini is not None:
            kini["peran"] = _peran(m.group(1))
            kini["_selaku"] = True
        lab = _label(b)
        if not lab:
            if kol_akhir == "alamat" and kini and sambungan < 3 and not _LABEL_LAIN.match(b) \
                    and not m:
                kini["alamat"] = f'{kini["alamat"]}, {_bersih(b)}'
                sambungan += 1
            elif not m:
                bebas.append(b)
                kol_akhir = None
            continue
        kol, nilai, _ = lab
        nilai = _bersih(nilai)
        if kol == "nama":
            # "selaku X" di bawah blok sebelumnya menentukan peran blok itu, jadi
            # bagian berjalan baru berlaku untuk blok yang dibuka sesudahnya
            kini = {"peran": bagian, "nama": nilai, "nik": "", "ttl": "", "tempat_lahir": "",
                    "tanggal_lahir": "", "jenis_kelamin": "", "pekerjaan": "", "alamat": ""}
            pihak.append(kini)
        elif kini is None:
            if kol != "abaikan":
                bebas.append(b)
            continue
        elif kol == "alamat_bagian":
            if nilai:
                bagian_alamat = f"{lab[2].strip()} {nilai}"
                bagian_alamat = re.sub(r"(?i)^rt\s*/\s*rw", "RT/RW", bagian_alamat)
                bagian_alamat = re.sub(r"(?i)^kecamatan", "Kecamatan", bagian_alamat)
                kini["alamat"] = (f'{kini["alamat"]}, {bagian_alamat}' if kini["alamat"]
                                  else bagian_alamat)
            kol = "alamat"
        elif kol != "abaikan" and not kini.get(kol):
            kini[kol] = nilai
        kol_akhir, sambungan = kol, 0

    peringatan = []
    hasil = []
    for p in pihak:
        if not p["nama"]:
            continue
        if not p["ttl"] and (p["tempat_lahir"] or p["tanggal_lahir"]):
            p["ttl"] = ", ".join(x for x in (p["tempat_lahir"], p["tanggal_lahir"]) if x)
        p["nik"] = _nik(p["nik"])
        p["jenis_kelamin"] = _jenis_kelamin(p["jenis_kelamin"])
        if p["nik"] and len(p["nik"]) != 16:
            peringatan.append(f'NIK {p["nama"]} terbaca {len(p["nik"])} digit, bukan 16 - periksa.')
        if not p["peran"]:
            peringatan.append(f'Peran {p["nama"]} tidak terbaca - pilih sendiri.')
        hasil.append({k: p[k] for k in ("peran", "nama", "nik", "ttl", "jenis_kelamin",
                                         "pekerjaan", "alamat")})
    akta = _akta(teks, bebas)
    if not hasil:
        peringatan.append("Tidak ada identitas (baris \"Nama : ...\") yang terbaca. "
                          "Coba foto/scan yang lebih jelas, atau halaman lain.")
    return {"akta": akta, "pihak": hasil, "peringatan": peringatan}
