<#
    ========================================================================
    Auto-instalador de AdGuard DHCP Panel Privado para Windows
    Instala una instancia PORTABLE y aislada de Python (sin tocar tu PC)
    ========================================================================
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

$TargetDir = Join-Path $ScriptDir "python_portable"
$ReqFile = Join-Path $ScriptDir "requirements.txt"
$ConfigFile = Join-Path $ScriptDir "config.json"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   Instalador Portable - AdGuard DHCP Panel Privado (Windows)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Directorio del proyecto: $ScriptDir" -ForegroundColor Gray
Write-Host "Destino de Python portable: $TargetDir" -ForegroundColor Gray
Write-Host ""

$pyExe = $null

function Update-PthFile($dir) {
    $pthFiles = Get-ChildItem -Path $dir -Filter "*._pth"
    foreach ($pth in $pthFiles) {
        $rawPth = [System.IO.File]::ReadAllText($pth.FullName)
        $rawPth = $rawPth -replace '#\s*import\s+site', 'import site'
        if ($rawPth -notmatch 'import\s+site') {
            $rawPth += "`r`nimport site"
        }
        if ($rawPth -notmatch 'Lib\\site-packages') {
            $rawPth += "`r`nLib\site-packages"
        }
        if ($rawPth -notmatch 'site-packages') {
            $rawPth += "`r`nsite-packages"
        }
        if ($rawPth -notmatch '(?m)^\.\.$') {
            $rawPth += "`r`n..`r`n."
        }
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($pth.FullName, $rawPth, $utf8NoBom)
    }
}

# 1. Comprobar si ya existe una instancia previa en python_portable
if (Test-Path (Join-Path $TargetDir "Scripts\python.exe")) {
    $pyExe = Join-Path $TargetDir "Scripts\python.exe"
    Write-Host "[OK] Detectada instancia virtual/portable en python_portable\Scripts\python.exe" -ForegroundColor Green
} elseif (Test-Path (Join-Path $TargetDir "python.exe")) {
    $pyExe = Join-Path $TargetDir "python.exe"
    Update-PthFile $TargetDir
    Write-Host "[OK] Detectada instancia portable existente en python_portable\python.exe" -ForegroundColor Green
} else {
    # 1.1 Intentar crear entorno aislado ultra-rápido en 2 segundos si el sistema tiene python
    $sysPython = (Get-Command py, python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if ($sysPython) {
        Write-Host "[1/3] Creando instancia aislada portable en python_portable\ (Ultra-rápido)..." -ForegroundColor Yellow
        Write-Host "      (Tu instalación principal de Python NO será tocada ni alterada)" -ForegroundColor Gray
        & $sysPython -m venv $TargetDir
        if (Test-Path (Join-Path $TargetDir "Scripts\python.exe")) {
            $pyExe = Join-Path $TargetDir "Scripts\python.exe"
            Write-Host "[OK] Instancia portable configurada en segundos en python_portable\" -ForegroundColor Green
        }
    }

    # 1.2 Si el sistema no tiene Python instalado, descargar paquete oficial Portable Embeddable
    if (-not $pyExe) {
        Write-Host "[1/3] Descargando y configurando Python Portable oficial (Embeddable 3.11)..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

        $is64Bit = [Environment]::Is64BitOperatingSystem
        $pyVer = "3.11.9"
        $arch = if ($is64Bit) { "amd64" } else { "win32" }
        $zipUrl = "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-$arch.zip"
        $zipPath = Join-Path $TargetDir "python_embed.zip"

        try {
            Write-Host "      Descargando paquete oficial de Python.org ($arch)..." -ForegroundColor Gray
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
            
            Write-Host "      Descomprimiendo archivos..." -ForegroundColor Gray
            Expand-Archive -Path $zipPath -DestinationPath $TargetDir -Force
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

            Update-PthFile $TargetDir

            Write-Host "      Instalando gestor de paquetes pip en la instancia portable..." -ForegroundColor Gray
            $pipUrl = "https://bootstrap.pypa.io/get-pip.py"
            $pipPath = Join-Path $TargetDir "get-pip.py"
            Invoke-WebRequest -Uri $pipUrl -OutFile $pipPath -UseBasicParsing -TimeoutSec 45

            $candidatePy = Join-Path $TargetDir "python.exe"
            & $candidatePy $pipPath --no-warn-script-location
            Remove-Item $pipPath -Force -ErrorAction SilentlyContinue

            $pipVer = & $candidatePy -m pip --version 2>$null
            if ($pipVer) {
                $pyExe = $candidatePy
                Write-Host "[OK] Python Portable 3.11 instalado correctamente en python_portable\" -ForegroundColor Green
            }
        } catch {
            Write-Host "      [!] Falló la descarga de Python embeddable: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if (-not $pyExe -or -not (Test-Path $pyExe)) {
    Write-Host ""
    Write-Host "[ERROR] No se pudo preparar la instancia portable de Python." -ForegroundColor Red
    Write-Host "Verifica tu conexión a Internet para descargar Python Portable o instala Python en Windows." -ForegroundColor Red
    exit 1
}

# 1.3 Asegurar pip en python_portable si se usa python.exe embeddable
Update-PthFile $TargetDir
$hasPip = & $pyExe -m pip --version 2>$null
if (-not $hasPip) {
    Write-Host "      Configurando pip en python_portable..." -ForegroundColor Yellow
    $pipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $pipPath = Join-Path $TargetDir "get-pip.py"
    try {
        Invoke-WebRequest -Uri $pipUrl -OutFile $pipPath -UseBasicParsing -TimeoutSec 45
        & $pyExe $pipPath --no-warn-script-location
        Remove-Item $pipPath -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "      [!] Advertencia con get-pip.py: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[2/3] Instalando dependencias en la instancia portable..." -ForegroundColor Yellow
Write-Host "      (Tu instalación principal de Python NO será tocada ni alterada)" -ForegroundColor Cyan

if (Test-Path $ReqFile) {
    & $pyExe -m pip install -r $ReqFile --no-warn-script-location --prefer-binary --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Advertencia: pip devolvió un código de error al instalar requerimientos." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Dependencias instaladas satisfactoriamente en python_portable." -ForegroundColor Green
    }
} else {
    Write-Host "[!] No se encontró requirements.txt. Instalando flask y cryptography directamente..." -ForegroundColor Yellow
    & $pyExe -m pip install flask cryptography --no-warn-script-location --prefer-binary --disable-pip-version-check
}

# Verificación de Flask
Update-PthFile $TargetDir
$verifyFlask = & $pyExe -c "import flask; print('FLASK_OK')" 2>$null
if ($verifyFlask -notmatch 'FLASK_OK') {
    Write-Host "      Asegurando instalacion de Flask en site-packages..." -ForegroundColor Yellow
    & $pyExe -m pip install flask cryptography --prefer-binary --no-warn-script-location --force-reinstall
}

# 3. Comprobar o generar config.json
Write-Host ""
Write-Host "[3/3] Comprobando archivo de configuración config.json..." -ForegroundColor Yellow
if (-not (Test-Path $ConfigFile)) {
    $defaultConfig = @"
{
  "adguard_url": "",
  "adguard_user": "",
  "adguard_pass": "",
  "port": 5001,
  "debug": false,
  "home_assistant_instances": [],
  "routers": [],
  "session_secret": "$([Guid]::NewGuid().ToString('N'))"
}
"@
    $defaultConfig | Set-Content -Path $ConfigFile -Encoding UTF8
    Write-Host "[OK] Se ha creado un archivo config.json neutro y limpio." -ForegroundColor Green
} else {
    Write-Host "[OK] config.json ya existe." -ForegroundColor Green
}

# 4. Crear lanzadores .bat auto-reparables
$launcherContent = @'
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
'@

$launcherPath1 = Join-Path $ScriptDir "iniciar_windows.bat"
$launcherPath2 = Join-Path $ScriptDir "start_windows.bat"
$launcherContent | Set-Content -Path $launcherPath1 -Encoding UTF8
$launcherContent | Set-Content -Path $launcherPath2 -Encoding UTF8

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   ¡Instalación completada con éxito!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "La instancia portable está lista en: python_portable\" -ForegroundColor Gray
Write-Host "Para iniciar el servidor ejecuta: iniciar_windows.bat (o start_windows.bat)" -ForegroundColor Cyan
Write-Host ""
