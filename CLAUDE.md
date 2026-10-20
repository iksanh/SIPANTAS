# SIPANTAS (Flask) — fase stabilisasi sebelum migrasi
Rujukan: docs/audit.md. Fitur sinkron ada di branch feat/sinkron.

## Perintah
- uji: python -m pytest uji -q

## Aturan
- Tidak ada fitur baru. Hanya perbaikan bug dan uji.
- Setiap perbaikan wajib disertai uji yang gagal sebelum perbaikan.
- Jangan membaca uji/emas/, data/, keluaran/, backup/ (data pemohon asli).
- Jelaskan rencana sebelum mengubah lebih dari satu berkas.
- Saya sedang belajar: setelah selesai, jelaskan diff dalam 5 poin.