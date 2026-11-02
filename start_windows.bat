@echo off
chcp 65001 >nul
title AdGuard DHCP Panel (Portable)
cd /d "%~dp0"

rem ------------------------------------------------------------------
rem Comprobar si se esta ejecutando sobre una unidad de red o SSHFS
rem ------------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d='%~d0'; $p='%~dp0'; $rem=($p.StartsWith('\\') -or $p -match 'sshfs'); try { $disk=Get-CimInstance Win32_LogicalDisk -Filter ('DeviceID=''' + $d + '''') -EA SilentlyContinue; if ($disk.DriveType -eq 4) { $rem=$true } } catch {}; if ($rem) { exit 42 } else { exit 0 }"
if errorlevel 42 (
    echo ==================================================================
    echo   [ERROR CRITICO] EJECUCION EN UNIDAD DE RED O SSHFS DETECTADA
    echo ==================================================================
    echo Ruta detectada: %~dp0
    echo.
    echo Se ha detectado que estas ejecutando el panel a traves de una unidad
    echo de red o almacenamiento remoto montado.
    echo.
    echo Python, SQLite y los entornos virtuales requieren ejecutarse en un
    echo disco fisico local para gestionar bloqueos y dependencias.
    echo.
    echo ==================================================================
    echo OPCIONES:
    echo ==================================================================
    echo OPCION 1: Si deseas ejecutar el panel en este PC Windows local:
    echo   1. Copia esta carpeta completa a tu disco local (ej. C:\adguard-panel)
    echo   2. Abre la carpeta en el disco local y haz doble clic en iniciar_windows.bat
    echo.
    echo OPCION 2: Si deseas ejecutar el panel en el equipo o servidor remoto:
    echo   1. Conectate directamente a dicho servidor (SSH, escritorio remoto o consola).
    echo   2. Entra en la carpeta del proyecto en ese servidor y ejecuta:
    echo      ./iniciar_linux.sh  o  iniciar_windows.bat
    echo ==================================================================
    echo.
    pause
    exit /b 1
)

set "PYTHONHOME="
set "PYTHONPATH=%~dp0"

if not exist "python_portable\Lib\site-packages" (
    mkdir "python_portable\Lib\site-packages" >nul 2>&1
)

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
