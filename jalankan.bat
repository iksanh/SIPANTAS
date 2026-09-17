@echo off
chcp 65001 >nul
title Berkas Panitia A
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python tidak ditemukan. Pasang Python 3.10 atau lebih baru dari python.org,
  echo   dan centang "Add Python to PATH" saat memasang.
  echo.
  pause
  exit /b 1
)

python -c "import docx" >nul 2>nul
if errorlevel 1 (
  echo   Memasang pustaka yang dibutuhkan...
  python -m pip install --quiet python-docx openpyxl
)

python -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo   Memasang Pillow untuk merapikan foto lapangan...
  python -m pip install --quiet Pillow
)

if not exist "templates\sk.docx" (
  echo   Menyiapkan template dari dokumen Word...
  python siapkan_template.py
)

if not exist "data\berkas.db" (
  echo   Menyiapkan basis data...
  python db.py
  echo.
  echo   Basis data masih kosong.
  echo   Untuk memasukkan 47 berkas dari Excel lama, jalankan: impor.bat
  echo.
)

python server.py
pause
