@echo off
chcp 65001 >nul
title AdGuard DHCP Panel - Portable Instance
cd /d "%~dp0"

set "PYTHONHOME="
set "PYTHONPATH=%~dp0"

if not exist "python_portable\Lib\site-packages" mkdir "python_portable\Lib\site-packages" >nul 2>&1

echo ==================================================================
echo   Starting AdGuard DHCP Panel (Portable Instance)
echo ==================================================================
echo.

set "PY_EXE="
if exist "python_portable\Scripts\python.exe" set "PY_EXE=python_portable\Scripts\python.exe"
if "%PY_EXE%"=="" if exist "python_portable\python.exe" set "PY_EXE=python_portable\python.exe"

set "NEED_INSTALL=0"
if "%PY_EXE%"=="" set "NEED_INSTALL=1"
if not "%PY_EXE%"=="" (
    "%PY_EXE%" -c "import flask, cryptography" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
    echo [INFO] Setting up portable dependencies: Flask, cryptography...
    echo This will only take a few seconds.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
    echo.
    if exist "python_portable\Scripts\python.exe" set "PY_EXE=python_portable\Scripts\python.exe"
    if "%PY_EXE%"=="" if exist "python_portable\python.exe" set "PY_EXE=python_portable\python.exe"
)

if "%PY_EXE%"=="" (
    echo.
    echo [ERROR] Could not configure portable Python instance.
    echo Run install_windows.bat to review details.
    echo.
    pause
    exit /b 1
)

"%PY_EXE%" -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Installing Flask directly into portable instance...
    "%PY_EXE%" -m pip install flask cryptography --prefer-binary --no-warn-script-location
)

"%PY_EXE%" app.py

if errorlevel 1 (
    echo.
    echo [ERROR] The application exited with an error.
    pause
)
