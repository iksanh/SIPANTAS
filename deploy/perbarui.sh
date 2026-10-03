#!/usr/bin/env bash
# Pasang versi terbaru dari GitHub: cadangkan -> tarik -> pasang paket -> nyalakan ulang.
# Berhenti kalau template di server pernah diganti lewat menu Template,
# supaya git pull tidak menimpa (atau bentrok dengan) suntingan petugas.
set -euo pipefail
cd /srv/sipantas

if [ -n "$(git status --porcelain -- templates/)" ]; then
    echo "BERHENTI: template di server berbeda dengan yang ada di git:" >&2
    git status --short -- templates/ >&2
    echo >&2
    echo "Template itu disunting petugas lewat menu Template. Pilih salah satu:" >&2
    echo "  - bawa pulang ke repo: salin berkasnya ke komputer, commit, push, lalu" >&2
    echo "    git checkout -- templates/ di sini dan ulangi perbarui.sh" >&2
    echo "  - pertahankan yang di server: git stash, perbarui.sh, git stash pop" >&2
    exit 1
fi

set -a; . /etc/sipantas.env; set +a
./deploy/backup.sh

git pull --ff-only
./venv/bin/pip install --quiet -r requirements.txt
sudo systemctl restart sipantas
sleep 2
systemctl --no-pager --lines=5 status sipantas
