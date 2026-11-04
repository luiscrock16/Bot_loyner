@echo off
title Subir a GitHub
color 0A
echo ========================================================
echo   Subiendo archivos a https://github.com/luiscrock16/Bot_loyner
echo ========================================================
cd /d "%~dp0"
git push -u origin main
pause
