#!/usr/bin/env bash
# Cadangkan SIPANTAS: basis data + foto lapangan + template -> S3.
# keluaran/ dan pratinjau/ tidak ikut: keduanya dirakit ulang dari basis data.
set -euo pipefail

AKAR="${AKAR:-/srv/sipantas}"
DB_PATH="${DB_PATH:-$AKAR/data/berkas.db}"
TUJUAN_S3="${TUJUAN_S3:-s3://cadangan-bpn-bonbol/sipantas}"
SIMPAN_HARI="${SIMPAN_HARI:-30}"
LOKAL=/data/cadangan
STEMPEL="$(TZ=Asia/Makassar date +%Y%m%d-%H%M)"
KERJA="$(mktemp -d)"
trap 'rm -rf "$KERJA"' EXIT

if [ -n "${DB_URL:-}" ] && [[ "$DB_URL" == postgres* ]]; then
    ARSIP="$KERJA/sipantas-$STEMPEL.sql.gz"
    pg_dump "$DB_URL" | gzip -9 > "$ARSIP"
else
    SALINAN="$KERJA/sipantas-$STEMPEL.db"
    # .backup aman dijalankan saat aplikasi sedang menulis.
    sqlite3 "$DB_PATH" ".backup '$SALINAN'"
    HASIL="$(sqlite3 "$SALINAN" 'PRAGMA integrity_check;')"
    if [ "$HASIL" != "ok" ]; then
        echo "GAGAL: integrity_check -> $HASIL" >&2
        exit 1
    fi
    gzip -9 "$SALINAN"
    ARSIP="$SALINAN.gz"
fi

# Template ikut dicadangkan: petugas bisa menggantinya lewat menu Template.
tar -czf "$KERJA/templates-$STEMPEL.tar.gz" -C "$AKAR" templates

mkdir -p "$LOKAL"
cp "$ARSIP" "$KERJA/templates-$STEMPEL.tar.gz" "$LOKAL/"

if command -v aws >/dev/null 2>&1; then
    aws s3 cp "$ARSIP" "$TUJUAN_S3/db/$(basename "$ARSIP")" --only-show-errors
    aws s3 cp "$KERJA/templates-$STEMPEL.tar.gz" "$TUJUAN_S3/templates/" --only-show-errors
    aws s3 sync "$AKAR/data/foto" "$TUJUAN_S3/foto" --only-show-errors
    echo "Terunggah ke $TUJUAN_S3"
else
    echo "aws CLI tidak ada - salinan hanya ditinggal di $LOKAL" >&2
fi

find "$LOKAL" -name 'sipantas-*' -mtime "+$SIMPAN_HARI" -delete 2>/dev/null || true
find "$LOKAL" -name 'templates-*' -mtime "+$SIMPAN_HARI" -delete 2>/dev/null || true

echo "Cadangan selesai: $(basename "$ARSIP")"
