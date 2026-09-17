#!/bin/sh
# Menjalankan di Linux/macOS. Setara jalankan.bat di Windows.
#   ./jalankan.sh              -> hanya untuk komputer ini (127.0.0.1:8000)
#   ./jalankan.sh 8000 0.0.0.0 -> dipakai sejaringan
set -e
cd "$(dirname "$0")"

python3 -c "import docx, openpyxl" 2>/dev/null || {
  echo "  Memasang pustaka yang dibutuhkan..."
  python3 -m pip install --quiet python-docx openpyxl
}
python3 -c "import PIL" 2>/dev/null || {
  echo "  Memasang Pillow untuk merapikan foto lapangan..."
  python3 -m pip install --quiet Pillow || true
}

[ -f templates/sk.docx ] || {
  echo "  Template belum ada. Salin folder templates/ dari komputer lama,"
  echo "  atau jalankan: python3 siapkan_template.py"
}

[ -f data/berkas.db ] || python3 db.py

exec python3 server.py "${1:-8000}" "${2:-127.0.0.1}"
