@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalador Portable - AdGuard DHCP Panel

echo ==================================================================
echo   Iniciando Instalador Portable para Windows...
echo   (Se instalara en python_portable sin tocar el Python de tu PC)
echo ==================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"

echo.
echo Presiona cualquier tecla para salir...
pause >nul
