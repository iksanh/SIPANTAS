@echo off
chcp 65001 >nul
title Siapkan Template - SIPANTAS
cd /d "%~dp0"
python -m berkas.perkakas.siapkan_template
echo.
pause
