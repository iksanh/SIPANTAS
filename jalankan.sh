#!/bin/sh
# Menjalankan di Linux/macOS. Setara jalankan.bat di Windows.
#   ./jalankan.sh              -> hanya untuk komputer ini (127.0.0.1:8000)
#   ./jalankan.sh 8000 0.0.0.0 -> dipakai sejaringan
set -e
cd "$(dirname "$0")"

python3 -c "import flask, waitress, docx, openpyxl, PIL" 2>/dev/null || {
  echo "  Memasang pustaka yang dibutuhkan..."
  python3 -m pip install --quiet -r requirements.txt
}

[ -f templates/sk.docx ] || {
  echo "  Template belum ada. Salin folder templates/ dari komputer lama,"
  echo "  atau jalankan: python3 -m berkas.perkakas.siapkan_template"
}

[ -f data/berkas.db ] || python3 -m berkas.db

exec python3 jalankan.py "${1:-8000}" "${2:-127.0.0.1}"
