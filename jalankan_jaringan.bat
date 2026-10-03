@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Sama dengan jalankan.bat, tetapi bisa dibuka dari perangkat lain
rem di Wi-Fi/LAN yang sama. jalankan.py membaca ALAMAT dan PORTA dari lingkungan.

set ALAMAT=0.0.0.0
if "%PORTA%"=="" set PORTA=8000

echo.
echo   Mode jaringan
echo   ------------------------------------------------
echo   Buka dari HP/laptop lain di jaringan yang sama:
set ADA_IP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration).Where({ $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' }).IPv4Address.IPAddress"`) do (
  echo     http://%%i:%PORTA%
  set ADA_IP=1
)
if not defined ADA_IP echo     (IP tidak terbaca - cek dengan perintah: ipconfig)
echo.
echo   Di komputer ini  : http://localhost:%PORTA%
echo.
echo   Perhatian: sambungannya belum HTTPS, jadi kata sandi lewat
echo   jaringan tanpa disandikan. Pakai hanya di jaringan kantor
echo   yang dipercaya.
echo.
echo   Kalau perangkat lain tidak bisa membuka, izinkan Python di
echo   Windows Firewall (Private networks).
echo   ------------------------------------------------

call "%~dp0jalankan.bat"
