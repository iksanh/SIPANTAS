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

python -c "import flask, waitress, docx, openpyxl, PIL" >nul 2>nul
if errorlevel 1 (
  echo   Memasang pustaka yang dibutuhkan...
  python -m pip install --quiet -r requirements.txt
)

if not exist "templates\sk.docx" (
  echo   Menyiapkan template dari dokumen Word...
  python -m berkas.perkakas.siapkan_template
)

if not exist "data\berkas.db" (
  echo   Menyiapkan basis data...
  python -m berkas.db
  echo.
  echo   Basis data masih kosong.
  echo   Untuk memasukkan 47 berkas dari Excel lama, jalankan: impor.bat
  echo.
)

python jalankan.py
pause
