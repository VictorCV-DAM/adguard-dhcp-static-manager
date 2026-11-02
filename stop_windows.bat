@echo off
chcp 65001 >nul
title Stop AdGuard DHCP Panel
cd /d "%~dp0"

echo ==================================================================
echo   Stopping AdGuard DHCP Panel...
echo ==================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_windows.ps1"

echo.
echo Press any key to exit...
pause >nul
