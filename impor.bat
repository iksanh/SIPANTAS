@echo off
chcp 65001 >nul
title Impor Excel - SIPANTAS
cd /d "%~dp0"
python -m berkas.perkakas.impor_excel
echo.
pause
