@echo off
chcp 65001 >nul
title Install AdGuard DHCP Panel (Portable)
cd /d "%~dp0"

echo ==================================================================
echo   Installing AdGuard DHCP Panel Portable Instance...
echo ==================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"

echo.
echo Press any key to exit...
pause >nul
