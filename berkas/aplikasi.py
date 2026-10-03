# -*- coding: utf-8 -*-
"""Pabrik aplikasi Flask: satu tempat merakit aplikasinya.

Yang diurus di sini hanya yang berlaku untuk semua halaman — koneksi basis
data per permintaan, pembacaan sesi, penjagaan login, dan kepala jawaban.
Halamannya sendiri ada di rute/, satu berkas per kelompok.

Folder statis dan folder Jinja dipancang lewat jalur.py, bukan relatif
terhadap berkas ini: paketnya ada di app/berkas/ sedangkan static/ ada di
app/, sehingga jalur bawaan Flask akan meleset satu tingkat.
"""
import os
import re
import secrets
from urllib.parse import quote, urlparse

from flask import Flask, Response, abort, g, redirect, request

from . import db, izin, jalur, sesi, web
from .rute import (auth, berkas, pengaturan, pradaftar, referensi, template,
                   unduhan)

# Endpoint yang boleh dibuka tanpa masuk.
BEBAS = {"auth.halaman_masuk", "auth.masuk", "static"}

# Batas kasar badan permintaan unggahan — foto dari ponsel gampang besar.
MAKS_UNGGAH = 120 * 1024 * 1024

# Metode yang menurut HTTP tidak mengubah apa pun, jadi tak perlu token.
METODE_AMAN = {"GET", "HEAD", "OPTIONS"}
MEDAN_CSRF = "_csrf"

# Tiap <form method="post"> disisipi token sesudah halamannya dirakit. Ini
# disengaja: kalau penyisipannya diserahkan ke web.py, satu formulir baru yang
# lupa memanggilnya akan lolos tanpa penjagaan. Di sini tidak ada yang bisa
# terlewat, termasuk potongan kartu lipat yang tidak melewati layout().
POLA_FORM = re.compile(r'<form\b[^>]*\bmethod="post"[^>]*>', re.I)


def buat_aplikasi():
    app = Flask(
        __name__,
        root_path=jalur.AKAR,
        static_folder=jalur.STATIS,
        # BUKAN templates/: folder itu sudah dipakai template .docx. Halaman
        # Jinja nanti tinggal di tampilan/ saat web.py mulai dibongkar.
        template_folder=os.path.join(jalur.AKAR, "tampilan"),
    )
    app.config.update(
        SECRET_KEY=os.environ.get("KUNCI_RAHASIA") or os.urandom(32),
        SEND_FILE_MAX_AGE_DEFAULT=300,      # sama dengan _statis() yang lama
        MAX_CONTENT_LENGTH=MAKS_UNGGAH,
    )

    @app.before_request
    def _buka_sesi():
        """Satu koneksi basis data dan satu pembacaan sesi per permintaan.

        Urutannya disengaja: penjagaan masuk lebih dulu, baru CSRF. Sesi yang
        habis di tengah pengisian formulir jadi berakhir di halaman masuk —
        bukan di halaman galat yang tidak bisa diapa-apakan petugas.
        """
        g.k = db.sambung()
        g.pengguna, g.csrf = sesi.muat(g.k, request.cookies.get(sesi.NAMA_KUKI))
        if not g.pengguna:
            # Belum masuk: tokennya dari kuki tamu, untuk menjaga halaman masuk.
            g.csrf = request.cookies.get(sesi.KUKI_TAMU) or sesi.token_baru()
            g.tamu_baru = g.csrf != request.cookies.get(sesi.KUKI_TAMU)

        if not (g.pengguna or request.endpoint in BEBAS):
            if "/bagian/" in request.path:
                # Permintaan kartu lipat dari app.js — jawab apa adanya, jangan
                # kirimi halaman masuk yang akan ditelan mentah ke dalam kartu.
                return Response("sesi habis", 401,
                                {"Content-Type": "text/plain; charset=utf-8"})
            return redirect("/masuk", 303)

        if request.method not in METODE_AMAN and not _csrf_sah():
            abort(400)
        return None

    def _csrf_sah():
        """Yang dibandingkan selalu nilai yang benar-benar pernah dikirim ke
        peramban: token sesi bagi yang sudah masuk, isi kuki tamu bagi yang
        belum. g.csrf tidak dipakai di sini — untuk tamu baru isinya token
        yang belum sempat sampai ke mana-mana."""
        harap = g.csrf if g.pengguna else request.cookies.get(sesi.KUKI_TAMU)
        kirim = request.form.get(MEDAN_CSRF) or request.headers.get("X-CSRF-Token") or ""
        return bool(harap) and secrets.compare_digest(str(kirim), str(harap))

    @app.errorhandler(404)
    def _tak_ditemukan(_galat):
        # Yang belum masuk tidak pernah sampai ke sini lewat halaman biasa —
        # penjagaan di atas sudah mengalihkannya. Yang tersisa cuma berkas
        # statis yang tidak ada, dan itu bukan urusan halaman berhias.
        if not g.get("pengguna"):
            return "tidak ditemukan", 404, {"Content-Type": "text/plain; charset=utf-8"}
        return web.layout("Tidak ditemukan",
                          '<div class="kartu"><div class="kosong">'
                          '<b>Halaman tidak ditemukan</b>'
                          '<a href="/berkas">Kembali ke daftar berkas</a>'
                          '</div></div>', g.pengguna), 404

    @app.errorhandler(400)
    def _token_tak_cocok(galat):
        """Hampir selalu halaman yang terlalu lama dibiarkan terbuka, bukan
        serangan. Jadi yang ditawarkan jalan keluarnya, bukan omelan."""
        if request.method in METODE_AMAN:
            return galat                      # 400 biasa, bukan urusan CSRF
        return web.layout("Formulir kedaluwarsa",
                          '<div class="kartu"><div class="kosong">'
                          '<b>Formulir ini sudah kedaluwarsa</b>'
                          '<span>Halamannya terlalu lama dibiarkan terbuka, atau Anda '
                          'masuk lagi di jendela lain. Muat ulang halamannya, lalu '
                          'kirim sekali lagi.</span>'
                          '<a href="/berkas">Kembali ke daftar berkas</a>'
                          '</div></div>', g.get("pengguna")), 400

    @app.errorhandler(403)
    def _tak_berwenang(_galat):
        """Petugas yang menembak alamat admin langsung. Untuk POST dikembalikan
        ke halaman asalnya dengan kabar, supaya tidak terdampar di halaman galat."""
        teks = "Bagian itu hanya untuk admin."
        if request.method != "GET":
            asal = urlparse(request.headers.get("Referer") or "").path
            if not asal.startswith("/") or asal.startswith("//"):
                asal = "/berkas"
            return redirect(f"{asal}?galat={quote(teks)}", 303)
        return web.layout("Tidak berwenang",
                          '<div class="kartu"><div class="kosong">'
                          '<b>Bagian ini hanya untuk admin</b>'
                          '<span>Hubungi Administrator kalau Anda memang perlu '
                          'mengaksesnya.</span>'
                          '<a href="/berkas">Kembali ke daftar berkas</a>'
                          '</div></div>', g.get("pengguna")), 403

    @app.errorhandler(413)
    def _unggahan_kebesaran(_galat):
        """Kembali ke halaman asal dengan kabar yang bisa dibaca orang, bukan
        halaman galat Flask."""
        mb = MAKS_UNGGAH // (1024 * 1024)
        teks = (f"Unggahan melebihi {mb} MB sehingga tidak ada yang disimpan. "
                "Unggah fotonya beberapa kali, sedikit demi sedikit.")
        asal = urlparse(request.headers.get("Referer") or "").path
        if not asal.startswith("/") or asal.startswith("//"):
            asal = "/berkas"
        return redirect(f"{asal}?galat={quote(teks)}", 303)

    @app.after_request
    def _kepala_aman(jawaban):
        """Satu tempat, jadi rute baru tidak bisa lupa memasangnya."""
        jawaban.headers.setdefault("X-Content-Type-Options", "nosniff")
        if g.get("tamu_baru"):
            sesi.pasang_kuki_tamu(jawaban, g.csrf)
        return _sisipkan_csrf(jawaban)

    def _sisipkan_csrf(jawaban):
        """Selipkan medan token tepat sesudah tiap <form method="post">."""
        if not jawaban.is_sequence or not jawaban.mimetype == "text/html":
            return jawaban
        nilai = g.get("csrf")
        if not nilai:
            return jawaban
        medan = f'<input type="hidden" name="{MEDAN_CSRF}" value="{nilai}">'
        isi = jawaban.get_data(as_text=True)
        if "<form" not in isi:
            return jawaban
        jawaban.set_data(POLA_FORM.sub(lambda m: m.group(0) + medan, isi))
        return jawaban

    @app.teardown_request
    def _tutup_sesi(_galat):
        k = g.pop("k", None)
        if k is not None:
            k.close()

    app.register_blueprint(auth.bp)
    app.register_blueprint(pradaftar.bp)
    app.register_blueprint(berkas.bp)
    app.register_blueprint(referensi.bp)
    app.register_blueprint(template.bp)
    app.register_blueprint(pengaturan.bp)
    app.register_blueprint(unduhan.bp)
    return app
