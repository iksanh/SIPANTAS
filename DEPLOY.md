# DEPLOY — SIPANTAS (Sistem Panitia A Terpadu)

Mengikuti pola `warkah.service` dan `wakaf.service` yang sudah jalan di produksi:
Ubuntu Server, systemd, nginx sebagai reverse proxy, TLS lewat certbot, cadangan
harian ke S3. Bisa dipasang di server yang sama dengan wakaf.

## Bedanya dengan aplikasi wakaf

Stack-nya tidak sama persis, jadi beberapa langkah disesuaikan:

| | Wakaf | SIPANTAS | Akibatnya |
|---|---|---|---|
| Server aplikasi | uvicorn (ASGI), 2 worker | **waitress (WSGI), 1 proses 8 utas** | Jangan tambah proses — SQLite tidak suka ditulisi banyak proses. Kalau lambat, naikkan `--threads`. |
| Porta | 8000 | **8002** | Supaya tidak bentrok. Cek dulu dengan `ss -ltnp`. |
| Letak data | dari env (`DB_PATH`, `UPLOAD_DIR`) | **tetap di dalam folder aplikasi** (`data/`, `keluaran/`, `pratinjau/`) | Dipindah ke `/data/sipantas` lewat symlink. |
| Kunci sesi | `SECRET_KEY` | **`KUNCI_RAHASIA`** | Sesi disimpan di tabel `sesi`, jadi restart tidak memutus login. |
| Akun admin awal | `ADMIN_PASSWORD` dari env | **`admin` / `admin123` bawaan** | Wajib diganti segera setelah deploy. |
| Migrasi skema | file `.sql` bernomor | **`db.siapkan()`** saat aplikasi mulai | Jalan sendiri, tidak ada langkah terpisah. |
| Unggahan maksimum | 10 MB | **120 MB** | `client_max_body_size 120M` di nginx. |
| Kebutuhan tambahan | — | **LibreOffice + huruf Bookman Old Style** | Untuk pratinjau PDF. Tanpa huruf yang sama, pergantian halaman bisa bergeser. |
| Isi yang disunting di server | — | **`templates/*.docx`** (menu Template) | Template ikut dicadangkan, dan `git pull` dijaga lewat `deploy/perbarui.sh`. |

Satu fitur hanya jalan di Windows: **kata penyambung** di kanan bawah halaman
(perlu Microsoft Word untuk menghitung halaman). Di server langkah itu dilewati
diam-diam, dan dokumennya tetap terbit. Kalau kata penyambung wajib ada, cetak
dokumen akhirnya dari komputer kantor yang ada Word-nya, atau tambahkan secara manual.

---

## 1. Paket Sistem

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git sqlite3 \
                    libreoffice-writer-nogui fonts-dejavu
sudo apt install -y ttf-mscorefonts-installer      # Times New Roman, Arial
```

Bookman Old Style tidak ada di paket Ubuntu. Salin dari komputer Windows kantor
(`C:\Windows\Fonts\BOOKOS*.TTF` — empat berkas). Jalankan dari PowerShell di komputer kantor:

```powershell
scp -i kunci.pem C:\Windows\Fonts\BOOKOS*.TTF ubuntu@<ip-server>:/tmp/
```

Lalu di server:

```bash
sudo mkdir -p /usr/share/fonts/truetype/bookman
sudo mv /tmp/BOOKOS*.TTF /usr/share/fonts/truetype/bookman/
sudo fc-cache -f
fc-list | grep -i bookman          # harus muncul
```

## 2. Kode dan Direktori Data

```bash
sudo mkdir -p /srv/sipantas /data/sipantas/{data,keluaran,pratinjau} /data/cadangan
sudo chown -R ubuntu:ubuntu /srv/sipantas /data/sipantas /data/cadangan

cd /srv/sipantas
git clone https://github.com/iksanh/SIPANTAS.git .
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Repo ini privat? Pakai *deploy key* (SSH, read-only) di GitHub → Settings →
Deploy keys, lalu clone lewat `git@github.com:iksanh/SIPANTAS.git`.

Folder data dipindah ke `/data` lewat symlink, supaya tetap terpisah dari kode
seperti pada wakaf:

```bash
cd /srv/sipantas
ln -s /data/sipantas/data      data
ln -s /data/sipantas/keluaran  keluaran
ln -s /data/sipantas/pratinjau pratinjau
# symlink tidak cocok dengan pola "data/" di .gitignore; abaikan secara lokal
printf 'data\nkeluaran\npratinjau\n' >> .git/info/exclude
git status --short                 # harus kosong
```

## 3. Environment

```bash
sudo cp deploy/sipantas.env.contoh /etc/sipantas.env
python3 -c "import secrets; print(secrets.token_hex(32))"   # salin hasilnya
sudo nano /etc/sipantas.env          # tempel ke KUNCI_RAHASIA
sudo chown root:root /etc/sipantas.env
sudo chmod 600 /etc/sipantas.env
```

> `KUNCI_RAHASIA` jangan ditaruh di kode atau di repo. `HTTPS=1` membuat kuki
> sesi ber-tanda `Secure` — wajib, karena nginx melayani lewat HTTPS.

## 4. Data Awal

Ada dua pilihan.

**a. Memindahkan data dari komputer kantor** (yang selama ini menjalankan `jalankan.bat`):

1. Di komputer kantor, tutup jendela hitam SIPANTAS dulu, supaya basis datanya
   tidak sedang ditulisi.
2. Dari PowerShell, di folder `app\`:

   ```powershell
   scp -i kunci.pem data\berkas.db ubuntu@<ip-server>:/data/sipantas/data/
   scp -i kunci.pem -r data\foto  ubuntu@<ip-server>:/data/sipantas/data/
   ```

3. Kalau template pernah disunting lewat menu **Template** di komputer kantor,
   salin juga isinya (yang di git bisa jadi sudah ketinggalan):

   ```powershell
   scp -i kunci.pem templates\*.docx ubuntu@<ip-server>:/srv/sipantas/templates/
   ```

   Sesudahnya `git status` di server akan menandai template itu berubah.
   Sebaiknya di-commit dari komputer kantor supaya repo dan server sama
   (lihat bagian 9).

4. Periksa di server:

   ```bash
   sqlite3 /data/sipantas/data/berkas.db "PRAGMA integrity_check; SELECT COUNT(*) FROM berkas;"
   ```

**b. Mulai dari kosong.** Tidak perlu apa-apa: basis data, akun
`admin` / `admin123`, dan data referensi dibuat sendiri saat layanan pertama
kali menyala. Data lama dari Excel bisa diimpor sesudahnya:

```bash
cd /srv/sipantas
set -a && . /etc/sipantas.env && set +a
./venv/bin/python -m berkas.perkakas.impor_excel /path/ke/berkas.xlsx
```

## 5. systemd

```bash
ss -ltnp | grep -E ':800[0-9]'       # pastikan 8002 belum dipakai
sudo cp deploy/sipantas.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sipantas
sudo systemctl status sipantas
curl -sI http://127.0.0.1:8002/masuk | head -1     # HTTP/1.1 200 OK
```

Kalau porta 8002 sudah terpakai, ganti di `sipantas.service` **dan**
`nginx-sipantas.conf`.

Log aplikasi: `journalctl -u sipantas -f`.

## 6. nginx + TLS

```bash
sudo cp deploy/nginx-sipantas.conf /etc/nginx/sites-available/sipantas
sudo nano /etc/nginx/sites-available/sipantas     # ganti server_name
sudo ln -sf /etc/nginx/sites-available/sipantas /etc/nginx/sites-enabled/sipantas
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d sipantas.example.go.id
```

Subdomain baru perlu catatan DNS (A record ke IP server) sebelum certbot
dijalankan.

## 7. Akun

1. Buka `https://<domain>/masuk`, masuk sebagai `admin` / `admin123`.
2. **Segera ganti sandinya** di menu **Pengaturan → Pengguna**.
3. Buat satu akun per petugas. Jangan memakai akun bersama.
4. Periksa **Pengaturan → Kantor**: nama kantor dan kepala kantor.

## 8. Cadangan Harian

`deploy/backup.sh` mencadangkan tiga hal:
- `data/berkas.db`, disalin aman dengan `.backup` lalu diperiksa integritasnya;
- `data/foto/`;
- `templates/`.

`keluaran/` dan `pratinjau/` tidak ikut, karena keduanya dirakit ulang dari basis data.
Semuanya diunggah ke S3, dan salinan basis data serta template juga
disimpan 30 hari di `/data/cadangan`.

```bash
sudo apt install -y awscli
chmod +x /srv/sipantas/deploy/*.sh
sudo cp deploy/sipantas-backup.service deploy/sipantas-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sipantas-backup.timer
systemctl list-timers sipantas-backup
sudo systemctl start sipantas-backup && journalctl -u sipantas-backup -n 10   # uji sekali
```

Bucket-nya sama dengan wakaf (`cadangan-bpn-bonbol`), dengan prefix `sipantas/`.
Kredensial lewat IAM role instance atau `~ubuntu/.aws/credentials`, bukan di
dalam repo. Jadwalnya 02.30 WITA, setengah jam setelah wakaf.

Uji pemulihan minimal sekali:

```bash
gunzip -c /data/cadangan/sipantas-YYYYMMDD-HHMM.db.gz > /tmp/uji.db
sqlite3 /tmp/uji.db "PRAGMA integrity_check; SELECT COUNT(*) FROM berkas;"
```

Memulihkan sungguhan: `systemctl stop sipantas`, timpa
`/data/sipantas/data/berkas.db`, salin balik `foto/` dari S3
(`aws s3 sync s3://.../sipantas/foto /data/sipantas/data/foto`), lalu
`systemctl start sipantas`.

## 9. Pembaruan Versi

Dari komputer pengembang: commit lalu `git push`. Lalu di server:

```bash
/srv/sipantas/deploy/perbarui.sh
```

Skrip itu menjalankan lima langkah:
1. cadangan;
2. `git pull --ff-only`;
3. `pip install`;
4. `systemctl restart sipantas`;
5. menampilkan status layanan.

Restart wajib: `style.css` dan `app.js` diberi nomor versi saat aplikasi mulai,
dan perubahan skema basis data dijalankan `db.siapkan()` di saat yang sama.

**Kalau skripnya berhenti dengan pesan "template di server berbeda"**, artinya
ada petugas yang mengganti template lewat menu Template, sehingga `git pull`
bisa menimpanya. Pilih salah satu:

- **Simpan suntingan itu di repo** (dianjurkan):
  1. Unduh template dari server, dari menu Template atau lewat `scp`.
  2. Commit dan push dari komputer pengembang.
  3. Di server, jalankan `git checkout -- templates/`, lalu ulangi `perbarui.sh`.
- **Pertahankan yang di server untuk sementara:**
  `git stash && ./deploy/perbarui.sh && git stash pop`.

## 10. Pemeriksaan Setelah Deploy

- [ ] `systemctl status sipantas` aktif; `journalctl -u sipantas` bersih dari galat
- [ ] `https://…/masuk` tampil dengan judul SIPANTAS, bisa masuk, sandi admin sudah diganti
- [ ] Menu **Berkas** menampilkan data yang dipindah (jumlahnya sama dengan di komputer kantor)
- [ ] Buka satu berkas → tab **Cetak** → BAP, Risalah, dan SK terunduh sebagai DOCX
- [ ] Pratinjau PDF tampil, huruf Bookman benar, dan pergantian halaman sama dengan hasil Word
- [ ] Unggah satu foto lapangan; filenya muncul di `/data/sipantas/data/foto/`
- [ ] **Pengaturan → Penyimpanan** menampilkan ukuran folder tanpa galat
- [ ] Timer cadangan terdaftar, dan uji cadangan sekali menghasilkan `.gz` di S3

## 11. Yang Tidak Boleh Ada di Repo

- `KUNCI_RAHASIA`, sandi basis data, atau kredensial S3 → semuanya di `/etc/sipantas.env`.
- `data/` (basis data dan foto berisi nama, NIK, dan letak tanah pemohon),
  `backup/`, `keluaran/`, `pratinjau/`, dan `uji/emas/` → sudah ada di `.gitignore`.
- Repo GitHub sebaiknya **Private**.
