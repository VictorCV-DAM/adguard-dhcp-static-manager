@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalador Portable - AdGuard DHCP Panel

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
    echo Estas ejecutando el instalador a traves de una unidad remota o SSHFS
    echo (ej. disco T: conectado a minipc-gmktec@victorlike.duckdns.org).
    echo.
    echo Python, SQLite y los entornos virtuales NO funcionan a traves de
    echo un tunel SSHFS por bloqueo de archivos y rutas con caracteres especiales.
    echo.
    echo ==================================================================
    echo INSTRUCCIONES:
    echo ==================================================================
    echo OPCION 1: Si quieres ejecutar el panel en este PC Windows local:
    echo   1. Copia esta carpeta completa a tu disco local C:\ o D:\
    echo      (por ejemplo en: C:\adguard-dhcp-panel)
    echo   2. Abre la carpeta en C:\ y ejecuta instalar_windows.bat
    echo.
    echo OPCION 2: Si quieres que el panel corra dentro de tu MiniPC:
    echo   1. Conectate al MiniPC por SSH:
    echo      ssh minipc-gmktec@victorlike.duckdns.org -p 22223
    echo   2. Entra en la carpeta del panel en el MiniPC y ejecuta:
    echo      ./instalar_linux.sh
    echo ==================================================================
    echo.
    pause
    exit /b 1
)

echo ==================================================================
echo   Iniciando Instalador Portable para Windows...
echo   (Se instalara en python_portable sin tocar el Python de tu PC)
echo ==================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"

echo.
echo Presiona cualquier tecla para salir...
pause >nul
