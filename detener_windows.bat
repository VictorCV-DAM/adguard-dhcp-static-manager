@echo off
chcp 65001 >nul
title Detener AdGuard DHCP Panel
cd /d "%~dp0"

echo ==================================================================
echo   Deteniendo AdGuard DHCP Panel Privado...
echo ==================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0detener_windows.ps1"

echo.
echo Presiona cualquier tecla para salir...
pause >nul
