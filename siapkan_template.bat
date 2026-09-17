@echo off
chcp 65001 >nul
title Siapkan Template - Berkas Panitia A
cd /d "%~dp0"
python siapkan_template.py
echo.
pause
