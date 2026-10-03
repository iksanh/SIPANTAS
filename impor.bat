@echo off
chcp 65001 >nul
title Impor Excel - Berkas Panitia A
cd /d "%~dp0"
python -m berkas.perkakas.impor_excel
echo.
pause
