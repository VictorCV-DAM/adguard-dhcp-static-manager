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
    echo Se ha detectado que estas ejecutando el instalador a traves de una unidad
    echo de red o almacenamiento remoto montado.
    echo.
    echo Python, SQLite y los entornos virtuales requieren ejecutarse en un
    echo disco fisico local para gestionar bloqueos y dependencias.
    echo.
    echo ==================================================================
    echo OPCIONES:
    echo ==================================================================
    echo OPCION 1: Si deseas instalar el panel en este PC Windows local:
    echo   1. Copia esta carpeta completa a tu disco local (ej. C:\adguard-panel)
    echo   2. Abre la carpeta en el disco local y haz doble clic en instalar_windows.bat
    echo.
    echo OPCION 2: Si deseas instalar el panel en el equipo o servidor remoto:
    echo   1. Conectate directamente a dicho servidor (SSH, escritorio remoto o consola).
    echo   2. Entra en la carpeta del proyecto en ese servidor y ejecuta:
    echo      ./instalar_linux.sh  o  instalar_windows.bat
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
