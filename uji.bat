@echo off
chcp 65001 >nul
title Uji Berkas Panitia A
cd /d "%~dp0"

rem Uji acuan: membandingkan hasil sekarang dengan rekaman di uji\emas\.
rem
rem   uji.bat            konteks saja - cepat, dipakai sehari-hari
rem   uji.bat penuh      konteks + dokumen - lambat (sekitar semenit)
rem   uji.bat rekam      rekam ulang acuan (hanya bila perubahannya disengaja)

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python tidak ditemukan. Pasang Python 3.10 atau lebih baru dari python.org,
  echo   dan centang "Add Python to PATH" saat memasang.
  echo.
  pause
  exit /b 1
)

python -c "import flask, waitress, docx" >nul 2>nul
if errorlevel 1 (
  echo   Memasang pustaka yang dibutuhkan...
  python -m pip install --quiet -r requirements.txt
)

if not exist "data\berkas.db" (
  echo.
  echo   Basis data belum ada, jadi tidak ada yang bisa diuji.
  echo   Jalankan jalankan.bat sekali dulu.
  echo.
  pause
  exit /b 1
)

if /i "%~1"=="rekam" (
  echo   Merekam ulang acuan. Ini menimpa rekaman lama.
  echo   Lakukan ini HANYA kalau perubahan isi dokumen memang disengaja.
  echo.
  python -m uji.bikin_emas
  echo.
  pause
  exit /b 0
)

if not exist "uji\emas" (
  echo   Belum ada rekaman acuan. Merekam untuk pertama kali...
  echo.
  python -m uji.bikin_emas
  echo.
)

if /i "%~1"=="penuh" (
  python -m unittest discover -s uji -p "uji_*.py" -t . -v
) else (
  echo   Menguji konteks dan lapisan web. Untuk ikut menguji isi DOCX: uji.bat penuh
  echo.
  python -m unittest uji.uji_konteks uji.uji_web -v
)

echo.
pause
