#!/usr/bin/env bash
# Pasang versi terbaru dari GitHub: cadangkan -> tarik -> pasang paket -> nyalakan ulang.
#
#   ./deploy/perbarui.sh                  berhenti kalau template di server pernah
#                                         diganti lewat menu Template
#   ./deploy/perbarui.sh --pertahankan    simpan perubahan lokal di server (git stash),
#                                         tarik, lalu kembalikan lagi (git stash pop)
set -euo pipefail

# Folder repo = induk dari deploy/, di mana pun repo itu di-clone.
AKAR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$AKAR"

PERTAHANKAN=0
[ "${1:-}" = "--pertahankan" ] && PERTAHANKAN=1

if [ "$PERTAHANKAN" = 0 ] && [ -n "$(git status --porcelain -- templates/)" ]; then
    echo "BERHENTI: template di server berbeda dengan yang ada di git:" >&2
    git status --short -- templates/ >&2
    echo >&2
    echo "Template itu disunting petugas lewat menu Template. Pilih salah satu:" >&2
    echo "  - bawa pulang ke repo: salin berkasnya ke komputer, commit, push, lalu" >&2
    echo "    git checkout -- templates/ di sini dan ulangi perbarui.sh" >&2
    echo "  - pertahankan yang di server: $0 --pertahankan" >&2
    exit 1
fi

set -a; . /etc/sipantas.env; set +a
AKAR="$AKAR" ./deploy/backup.sh

DISIMPAN=0
if [ "$PERTAHANKAN" = 1 ] && [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "Menyimpan perubahan lokal:"
    git status --short --untracked-files=no
    git stash push -m "perbarui.sh $(date +%Y%m%d-%H%M)"
    DISIMPAN=1
fi

git pull --ff-only

if [ "$DISIMPAN" = 1 ] && ! git stash pop; then
    echo >&2
    echo "BENTROK: perubahan lokal tidak bisa dikembalikan otomatis." >&2
    echo "Kode baru sudah ditarik, tapi layanan BELUM dinyalakan ulang." >&2
    echo "Perubahan lokal masih aman di: git stash list" >&2
    echo "Pilih versi per berkas yang bentrok, lalu nyalakan ulang manual:" >&2
    echo "  versi server : git checkout --theirs <berkas>" >&2
    echo "  versi GitHub : git checkout --ours <berkas>" >&2
    echo "  lalu         : git reset && git stash drop && sudo systemctl restart sipantas" >&2
    exit 1
fi

./venv/bin/pip install --quiet -r requirements.txt
sudo systemctl restart sipantas
sleep 2
systemctl --no-pager --lines=5 status sipantas
