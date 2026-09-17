@echo off
chcp 65001 >nul
title Impor Excel - Berkas Panitia A
cd /d "%~dp0"
python impor_excel.py
echo.
pause
