# SIPANTAS (Flask) — fase stabilisasi sebelum migrasi
Rujukan: docs/audit.md. Fitur sinkron ada di branch feat/sinkron.

## Perintah
- uji: python -m pytest uji -q

## Aturan
- Fitur baru hanya bila diminta langsung oleh pemilik; selebihnya perbaikan bug dan uji.
- Setiap perbaikan/fitur wajib disertai uji yang gagal sebelum perubahan.
- Jangan membaca uji/emas/, data/, keluaran/, backup/ (data pemohon asli).
- Jelaskan rencana sebelum mengubah lebih dari satu berkas.
- Saya sedang belajar: setelah selesai, jelaskan diff dalam 5 poin.