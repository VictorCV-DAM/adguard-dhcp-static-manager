@echo off
chcp 65001 >nul
title AdGuard DHCP Panel (Portable)
cd /d "%~dp0"

set "PYTHONPATH=%~dp0;%PYTHONPATH%"

echo ==================================================================
echo   Iniciando AdGuard DHCP Panel Privado (Instancia Portable)
echo ==================================================================

if exist "python_portable\python.exe" (
    "python_portable\python.exe" app.py
) else if exist "python_portable\Scripts\python.exe" (
    "python_portable\Scripts\python.exe" app.py
) else (
    echo [ERROR] No se encontro la instancia portable de Python.
    echo Ejecuta primero instalar_windows.bat
    pause
    exit /b 1
)

pause
