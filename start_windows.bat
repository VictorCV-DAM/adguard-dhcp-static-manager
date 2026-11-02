@echo off
chcp 65001 >nul
title AdGuard DHCP Panel (Portable)
cd /d "%~dp0"

set "PYTHONPATH=%~dp0;%PYTHONPATH%"

echo ==================================================================
echo   Iniciando AdGuard DHCP Panel Privado (Instancia Portable)
echo ==================================================================
echo.

set "PY_EXE="
if exist "python_portable\Scripts\python.exe" (
    set "PY_EXE=python_portable\Scripts\python.exe"
) else if exist "python_portable\python.exe" (
    set "PY_EXE=python_portable\python.exe"
)

set "NEED_INSTALL=0"
if "%PY_EXE%"=="" (
    set "NEED_INSTALL=1"
) else (
    "%PY_EXE%" -c "import flask, cryptography" >nul 2>&1
    if errorlevel 1 (
        set "NEED_INSTALL=1"
    )
)

if "%NEED_INSTALL%"=="1" (
    echo [INFO] Configurando dependencias portables (Flask, etc.)...
    echo Esto solo tardara unos segundos.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
    echo.
    if exist "python_portable\Scripts\python.exe" (
        set "PY_EXE=python_portable\Scripts\python.exe"
    ) else if exist "python_portable\python.exe" (
        set "PY_EXE=python_portable\python.exe"
    )
)

if "%PY_EXE%"=="" (
    echo.
    echo [ERROR] No se pudo configurar la instancia portable de Python.
    echo Ejecuta instalar_windows.bat para revisar los detalles.
    echo.
    pause
    exit /b 1
)

rem Comprobacion de Flask antes de lanzar
"%PY_EXE%" -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Instalando Flask directamente en la instancia portable...
    "%PY_EXE%" -m pip install flask cryptography --prefer-binary --no-warn-script-location
)

"%PY_EXE%" app.py

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se ha cerrado con error.
    pause
)
