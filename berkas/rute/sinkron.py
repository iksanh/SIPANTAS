# -*- coding: utf-8 -*-
"""Tarik data dari aplikasi PHPT (laravel_app) berdasarkan NIB.

Dipanggil app.js dari kartu "Ambil dari aplikasi PHPT" pada formulir Berkas
dan Pradaftar. Jawabannya JSON isian formulir; tidak ada yang ditulis ke
basis data di sini — penyimpanannya tetap lewat tombol Simpan biasa.
"""
from flask import Blueprint, g, jsonify, request

from .. import sinkron

bp = Blueprint("sinkron", __name__)


@bp.get("/sinkron/nib")
def nib():
    untuk = "pradaftar" if request.args.get("untuk") == "pradaftar" else "berkas"
    try:
        hasil = sinkron.cari(g.k, request.args.get("nib", ""), untuk)
    except sinkron.SinkronGagal as ex:
        return jsonify({"galat": str(ex)}), 502
    return jsonify({"hasil": hasil})
